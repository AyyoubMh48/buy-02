"""Small standard-library Nexus REST client. Never logs credentials or response bodies."""
import base64
import copy
import hashlib
import json
import os
import re
import ssl
from urllib import error, parse, request
from xml.etree import ElementTree as ET


class NexusError(RuntimeError):
    pass


def required(name):
    value = os.environ.get(name, '')
    if not value.strip() or '${env.' in value:
        raise NexusError(f'Set {name} in your private environment.')
    return value


def base_url(value):
    p = parse.urlsplit(value)
    if (p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password
            or p.query or p.fragment):
        raise NexusError('NEXUS_URL must be an HTTP(S) base URL without credentials, query or fragment.')
    if p.scheme == 'http' and p.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise NexusError('Remote Nexus requires HTTPS. For a local lab use an SSH tunnel to 127.0.0.1.')
    return value.rstrip('/')


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward Authorization to a redirect target.


class Client:
    def __init__(self, prefix='NEXUS_ADMIN', anonymous=False):
        self.url = base_url(required('NEXUS_URL'))
        self.authorization = None
        if not anonymous:
            user, password = required(prefix + '_USERNAME'), required(prefix + '_PASSWORD')
            if ':' in user or any(c in user + password for c in '\r\n'):
                raise NexusError('Credentials contain an invalid username colon or newline.')
            token = base64.b64encode(f'{user}:{password}'.encode()).decode()
            self.authorization = 'Basic ' + token
        context = ssl.create_default_context(cafile=os.environ.get('NEXUS_CA_BUNDLE') or None)
        self.opener = request.build_opener(NoRedirect(), request.HTTPSHandler(context=context))

    def open(self, method, path, data=None, content_type='application/json', allowed=(200, 201, 204)):
        if not path.startswith('/') or path.startswith('//'):
            raise NexusError('Request path must be relative to the configured Nexus host.')
        headers = {'Accept': '*/*'}
        if self.authorization:
            headers['Authorization'] = self.authorization
        if data is not None:
            headers['Content-Type'] = content_type
        req = request.Request(self.url + path, data=data, headers=headers, method=method)
        try:
            response = self.opener.open(req, timeout=30)
        except error.HTTPError as exc:
            if exc.code in allowed:
                return exc
            exc.close()
            hints = {400: 'Check the payload in the server Swagger API and repository version policy.',
                     401: 'Check username/password and complete the administrator setup wizard.',
                     403: 'Check repository privileges; never grant admin to the publishing account.',
                     404: 'Check NEXUS_URL, repository name and artifact coordinates.',
                     409: 'A release may already exist; select a new version.',
                     301: 'Use the final Nexus base URL; credentialed redirects are refused.',
                     302: 'Use the final Nexus base URL; credentialed redirects are refused.'}
            raise NexusError(f'HTTP {exc.code} for {method} {path.split("?")[0]}. '
                             + hints.get(exc.code, 'Inspect Nexus server logs and storage/readiness.')) from None
        except (error.URLError, TimeoutError, OSError):
            raise NexusError('Cannot connect to Nexus. Check NEXUS_URL, TLS trust, SSH tunnel and service readiness.') from None
        if response.status not in allowed:
            response.close()
            raise NexusError(f'Unexpected HTTP status {response.status}.')
        return response

    def json(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        with self.open(method, '/service/rest/v1' + path, data) as response:
            raw = response.read()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError):
            raise NexusError('Nexus returned invalid JSON. Check base URL and reverse proxy routing.') from None

    def exists(self, path):
        with self.open('GET', path, allowed=(200, 404)) as response:
            return response.status == 200

    def digest(self, path):
        digest = hashlib.sha256()
        with self.open('GET', path) as response:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()


def merge(current, desired):
    """Keep server-only optional settings when patching writable REST payloads."""
    result = copy.deepcopy(current)
    for key, value in desired.items():
        result[key] = merge(result.get(key, {}), value) if isinstance(value, dict) else copy.deepcopy(value)
    return result


def differences(current, desired, prefix=''):
    result = []
    for key, value in desired.items():
        path = prefix + key
        actual = current.get(key)
        if isinstance(value, dict):
            result += differences(actual if isinstance(actual, dict) else {}, value, path + '.')
        elif path == 'group.memberNames':
            if not set(value).issubset(actual or []):
                result.append(path)
        elif isinstance(value, str) and path == 'storage.writePolicy':
            if value.upper() != str(actual).upper():
                result.append(path)
        elif value != actual:
            result.append(path)
    return result


def repository_plan(client, specs):
    """Read all repositories and detect unsafe collisions before doing any writes."""
    inventory = {r['name']: r for r in client.json('GET', '/repositories')}
    plan = []
    for spec in specs:
        desired = spec['config']
        name, kind = desired['name'], spec['type']
        endpoint = '/repositories/maven/' + kind
        existing = inventory.get(name)
        if existing is None:
            plan.append(('POST', endpoint, desired, name))
            continue
        if existing['format'] != 'maven2' or existing['type'] != kind:
            raise NexusError(f'{name} already exists with a different format/type; refusing to replace it.')
        endpoint += '/' + name
        current = client.json('GET', endpoint)
        blob = current.get('storage', {}).get('blobStoreName')
        if blob != desired['storage']['blobStoreName']:
            raise NexusError(f'{name} uses another blob store. Review repositories.json; automatic data migration is refused.')
        changes = differences(current, desired)
        if not changes:
            continue
        payload = merge(current, desired)
        for key in ('url', 'format', 'type'):
            payload.pop(key, None)
        if kind == 'group':
            payload['group']['memberNames'] = list(dict.fromkeys(
                desired['group']['memberNames'] + current.get('group', {}).get('memberNames', [])))
        plan.append(('PUT', endpoint, payload, name))
    return plan


def role_specs():
    # Reading the group exposes its member content without granting direct proxy access.
    read = ['nx-repository-view-maven2-maven-public-' + a for a in ('browse', 'read')]
    publish = ['nx-repository-view-maven2-' + repo + '-' + action
               for repo in ('maven-releases', 'maven-snapshots')
               for action in ('browse', 'read', 'add', 'edit')]
    return [dict(id='buy02-maven-reader', name='buy02 Maven reader',
                 description='Authenticated Maven group resolution', privileges=read, roles=[]),
            dict(id='buy02-maven-publisher', name='buy02 Maven publisher',
                 description='Publish Maven hosted artifacts; no delete or administration',
                 privileges=publish, roles=['buy02-maven-reader'])]


def validate_version(version):
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-SNAPSHOT)?', version):
        raise NexusError('Use a version such as 1.0.0-SNAPSHOT, 1.0.0 or 1.0.1.')
    return version


def artifact_directory(group, artifact, version):
    validate_version(version)
    for value in (group, artifact):
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', value) or '..' in value:
            raise NexusError('Invalid Maven coordinate.')
    return group.replace('.', '/') + '/' + artifact + '/' + version


def artifact_paths(client, repository, group, artifact, version):
    directory = f'/repository/{repository}/' + artifact_directory(group, artifact, version)
    values = {ext: version for ext in ('jar', 'pom')}
    if version.endswith('-SNAPSHOT'):
        with client.open('GET', directory + '/maven-metadata.xml') as response:
            metadata = ET.fromstring(response.read())
        for ext in values:
            candidates = [s for s in metadata.findall('./versioning/snapshotVersions/snapshotVersion')
                          if s.findtext('extension') == ext and not s.findtext('classifier')]
            if not candidates:
                raise NexusError(f'Snapshot metadata has no unclassified {ext} entry.')
            value = max(candidates, key=lambda s: s.findtext('updated', '')).findtext('value', '')
            pattern = re.escape(version[:-len('SNAPSHOT')]) + r'\d{8}\.\d{6}-\d+'
            if not re.fullmatch(pattern, value):
                raise NexusError('Unexpected timestamped snapshot version in server metadata.')
            values[ext] = value
    return {ext: f'{directory}/{artifact}-{value}.{ext}' for ext, value in values.items()}
