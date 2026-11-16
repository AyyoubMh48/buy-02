#!/usr/bin/env python3
"""Provision and verify the Maven portion of buy-02's Nexus installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlencode
from uuid import uuid4
from xml.etree import ElementTree as ET

from nexus_api import (Client, NexusError, artifact_directory, artifact_paths, base_url,
                       repository_plan, required, role_specs, validate_version)

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ('discovery', 'gateway', 'user-service', 'product-service', 'media-service', 'order-service')
NS = {'m': 'http://maven.apache.org/POM/4.0.0'}
SETTINGS = ROOT / 'nexus/maven/settings.xml'


def specs():
    return json.loads((ROOT / 'nexus/repositories.json').read_text())


def coordinates(service):
    pom = ET.parse(ROOT / service / 'pom.xml').getroot()
    return tuple(pom.findtext('m:' + key, namespaces=NS) for key in ('groupId', 'artifactId', 'version'))


def selected(service):
    return SERVICES if service == 'all' else (service,)


def maven(service, goals, nexus=True):
    command = [os.environ['MAVEN_BIN']] if os.environ.get('MAVEN_BIN') else ['bash', './mvnw']
    args = ['-B', '-ntp']
    normalized_url = None
    if nexus:
        # Maven accepts HTTP URLs; enforce the same TLS policy as the REST client first.
        normalized_url = base_url(required('NEXUS_URL'))
        required('NEXUS_READ_USERNAME')
        required('NEXUS_READ_PASSWORD')
        args += ['-s', str(SETTINGS)]
    if os.environ.get('NEXUS_MAVEN_CACHE'):
        args += ['-Dmaven.repo.local=' + str(Path(os.environ['NEXUS_MAVEN_CACHE']).resolve())]
    env = os.environ.copy()
    if normalized_url:
        env['NEXUS_URL'] = normalized_url
    # Provisioning credentials are never needed in a build or its test subprocesses.
    for key in ('NEXUS_ADMIN_USERNAME', 'NEXUS_ADMIN_PASSWORD'):
        env.pop(key, None)
    result = subprocess.run(command + args + goals, cwd=ROOT / service, env=env, check=False)
    if result.returncode:
        raise NexusError(f'Maven failed for {service} (exit {result.returncode}). Nothing is confirmed published. '
                         'Check the first Maven error, JDK version, Nexus availability, permissions, '
                         'release immutability and Docker for Testcontainers. Do not skip tests to publish.')


def user_plan(client):
    plan = []
    ids = [required(p + '_USERNAME') for p in ('NEXUS_READ', 'NEXUS_PUBLISH')]
    if len(set(ids)) != 2 or any(user in ('admin', 'anonymous', required('NEXUS_ADMIN_USERNAME')) for user in ids):
        raise NexusError('Reader, publisher and administrator must be separate accounts; do not reuse admin/anonymous.')
    for prefix, role in [('NEXUS_READ', 'buy02-maven-reader'), ('NEXUS_PUBLISH', 'buy02-maven-publisher')]:
        user = required(prefix + '_USERNAME')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', user):
            raise NexusError('Use an account name containing only letters, numbers, dot, dash or underscore.')
        password = required(prefix + '_PASSWORD')
        users = client.json('GET', '/security/users?' + urlencode({'userId': user, 'source': 'default'}))
        matches = [u for u in users if u['userId'] == user and u.get('source', 'default') == 'default']
        if matches:
            if set(matches[0]['roles']) != {role} or matches[0].get('status') != 'active':
                raise NexusError(f'Existing {user} has unexpected roles/status. Review it manually; account takeover is refused.')
            print(f'KEEP account {user} (existing password is unchanged)')
        else:
            if len(password) < 16:
                raise NexusError(f'Choose a password of at least 16 characters for {prefix}.')
            plan.append(dict(userId=user, firstName='buy02', lastName=role,
                             emailAddress=required(prefix + '_EMAIL'), password=password,
                             status='active', roles=[role]))
    return plan


def provision(args):
    client = Client()
    repositories = repository_plan(client, specs())
    existing_roles = {r['id']: r for r in client.json('GET', '/security/roles') if r.get('source', 'default') == 'default'}
    roles = []
    for desired in role_specs():
        actual = existing_roles.get(desired['id'])
        if actual is None or (set(actual['privileges']) != set(desired['privileges'])
                              or set(actual['roles']) != set(desired['roles'])):
            roles.append(('POST' if actual is None else 'PUT', desired))
    users = user_plan(client)  # Validate all account collisions before the first write.
    anonymous = client.json('GET', '/security/anonymous')
    for method, endpoint, payload, name in repositories:
        print(f'{method} repository {name}')
    for method, payload in roles:
        print(f'{method} role {payload["id"]}')
    for payload in users:
        print(f'POST account {payload["userId"]}')
    if anonymous['enabled']:
        print('PUT anonymous access: disabled (global setting; container clients must also authenticate)')
    if not args.apply:
        print('PLAN ONLY. Use provision --apply to perform these changes.')
        return
    for method, endpoint, payload, name in repositories:
        client.json(method, endpoint, payload)
    for method, payload in roles:
        endpoint = '/security/roles' + ('/' + payload['id'] if method == 'PUT' else '')
        client.json(method, endpoint, payload)
    for payload in users:
        client.json('POST', '/security/users', payload)
    if anonymous['enabled']:
        anonymous['enabled'] = False
        client.json('PUT', '/security/anonymous', anonymous)
    verify_config(args)


def verify_config(args):
    client = Client()
    for path in ('/service/rest/v1/status', '/service/rest/v1/status/writable'):
        with client.open('GET', path):
            pass
    changes = repository_plan(client, specs())
    if changes:
        raise NexusError('Repository configuration differs: ' + ', '.join(p[3] for p in changes))
    for role in role_specs():
        actual = client.json('GET', '/security/roles/' + role['id'])
        if set(actual['privileges']) != set(role['privileges']) or set(actual['roles']) != set(role['roles']):
            raise NexusError('Role privileges differ: ' + role['id'])
    if client.json('GET', '/security/anonymous')['enabled']:
        raise NexusError('Anonymous access is still enabled.')
    # This also rejects users with extra roles and never changes an existing password.
    if user_plan(client):
        raise NexusError('One or more required service accounts do not exist.')
    for spec in specs():
        print('VERIFIED ' + client.url + '/repository/' + spec['config']['name'] + '/')
    print('VERIFIED readiness, repository policies, roles, accounts and anonymous access configuration.')


def file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(args):
    publisher = Client('NEXUS_PUBLISH')
    reader = Client('NEXUS_READ')
    group, artifact, current = coordinates(args.service)
    version = args.version or current
    repository = 'maven-snapshots' if version.endswith('-SNAPSHOT') else 'maven-releases'
    paths = artifact_paths(publisher, repository, group, artifact, version)
    for extension, path in paths.items():
        hosted_hash = publisher.digest(path)
        group_path = path.replace('/repository/' + repository + '/', '/repository/maven-public/', 1)
        if reader.digest(group_path) != hosted_hash:
            raise NexusError('Hosted and group artifact checksums differ. Retry after metadata propagation.')
        if args.local:
            if version != current:
                raise NexusError('Local verification requires the POM and requested version to match.')
            local = (ROOT / args.service / 'pom.xml' if extension == 'pom' else
                     ROOT / args.service / 'target' / f'{artifact}-{version}.jar')
            if not local.is_file() or file_digest(local) != hosted_hash:
                raise NexusError(f'Local {extension} does not match the downloaded Nexus artifact.')
        print(f'VERIFIED {extension} sha256={hosted_hash} {reader.url}{group_path}')
    print(f'CONFIRMED available: {group}:{artifact}:{version}')


def build(args):
    for service in selected(args.service):
        maven(service, ['clean', 'verify'], nexus=not args.direct)


def publish(args):
    publisher = Client('NEXUS_PUBLISH')
    Client('NEXUS_READ')  # Fail early if resolution credentials are missing.
    # Repository policy is established by provision/verify-config. Builds need
    # only reader/publisher accounts; never require an administrator in CI.
    for service in selected(args.service):
        group, artifact, version = coordinates(service)
        validate_version(version)
        if not version.endswith('-SNAPSHOT'):
            path = '/repository/maven-releases/' + artifact_directory(group, artifact, version)
            if publisher.exists(path + f'/{artifact}-{version}.pom'):
                raise NexusError(f'Release {group}:{artifact}:{version} already exists. Use a new version.')
        # deploy includes test, package and verify before the deploy phase, including JaCoCo.
        maven(service, ['clean', 'deploy'])
        verify_artifact(argparse.Namespace(service=service, version=version, local=True))


def set_version(args):
    version = validate_version(args.version)
    for service in selected(args.service):
        # Maven's versions plugin updates only the application version, preserving its parent/dependencies.
        maven(service, ['org.codehaus.mojo:versions-maven-plugin:2.19.1:set',
                        '-DnewVersion=' + version, '-DgenerateBackupPoms=false',
                        '-DprocessAllModules=false'])
        print(f'Updated {service}: {coordinates(service)[2]}. Review git diff, then build before publishing.')


def resolve(args):
    group, artifact, current = coordinates(args.service)
    version = validate_version(args.version or current)
    maven(args.service, ['org.apache.maven.plugins:maven-dependency-plugin:3.8.1:get',
                         '-Dartifact=' + f'{group}:{artifact}:{version}:jar', '-Dtransitive=false', '-U'])
    print(f'Resolved {group}:{artifact}:{version} through nexus-public.')


def cached_asset(admin, group, artifact, version, path):
    params = dict(repository='maven-central', group=group, name=artifact, version=version)
    while True:
        result = admin.json('GET', '/search/assets?' + urlencode(params))
        for item in result['items']:
            if item['path'] == path:
                return item
        token = result.get('continuationToken')
        if not token:
            return None
        params['continuationToken'] = token


def cache(args):
    admin, reader = Client(), Client('NEXUS_READ')
    # Fixed, small public release; no project or global Maven cache is modified.
    group, artifact, version = 'org.apache.commons', 'commons-lang3', '3.17.0'
    path = artifact_directory(group, artifact, version) + f'/{artifact}-{version}.jar'
    before = cached_asset(admin, group, artifact, version, path)
    print('Proxy asset before request: ' + ('already cached' if before else 'not found in search index'))
    group_path = '/repository/maven-public/' + path
    first = reader.digest(group_path)
    second = reader.digest(group_path)
    # Search indexing is asynchronous; verify the proxy bytes as well as index evidence.
    proxy_hash = admin.digest('/repository/maven-central/' + path)
    after = cached_asset(admin, group, artifact, version, path)
    if first != second or first != proxy_hash:
        raise NexusError('Group and proxy checksums differ.')
    if not after:
        raise NexusError('Bytes match but proxy search index is not yet available. Retry cache; caching is not confirmed yet.')
    if after.get('checksum', {}).get('sha256') not in (None, first):
        raise NexusError('Proxy asset checksum differs from the download.')
    print('VERIFIED repeated group downloads and stored maven-central asset: sha256=' + first)
    print('No local Maven cache was used. Inspect request.log for the two GET requests; '
          'this check alone does not prove upstream was offline.')


def verify_access(args):
    reader, publisher, anonymous = Client('NEXUS_READ'), Client('NEXUS_PUBLISH'), Client(anonymous=True)
    path = '/repository/maven-public/org/apache/commons/commons-lang3/3.17.0/commons-lang3-3.17.0.pom'
    for client, label in ((reader, 'reader'), (publisher, 'publisher')):
        with client.open('GET', path):
            pass
        print('VERIFIED ' + label + ' can resolve through maven-public')
    with anonymous.open('GET', path, allowed=(401, 403)):
        pass
    print('VERIFIED anonymous artifact download is denied')
    # A fresh coordinate avoids overwriting an earlier probe if the reader is
    # misconfigured. Never issue DELETE: configuration verification checks the
    # absence of delete privileges without risking stored artifacts.
    artifact = 'nexus-access-probe-' + uuid4().hex
    probe = f'/repository/maven-snapshots/com/buy01/{artifact}/0.0.0-SNAPSHOT/{artifact}-0.0.0-SNAPSHOT.pom'
    payload = (f'<project><modelVersion>4.0.0</modelVersion><groupId>com.buy01</groupId>'
               f'<artifactId>{artifact}</artifactId><version>0.0.0-SNAPSHOT</version></project>').encode()
    with reader.open('PUT', probe, payload, 'application/xml', allowed=(401, 403)):
        pass
    with publisher.open('GET', '/service/rest/v1/security/users', allowed=(401, 403)):
        pass
    print('VERIFIED reader cannot publish; publisher cannot administer users.')
    print('Delete privileges are checked by verify-config; no DELETE request was sent.')
    print('Positive hosted upload permission is verified only by successful publish commands.')


def audit(args):
    failures = []
    for service in SERVICES:
        pom = ET.parse(ROOT / service / 'pom.xml').getroot()
        group, artifact, version = coordinates(service)
        validate_version(version)
        java = pom.findtext('m:properties/m:java.version', namespaces=NS)
        parent = pom.findtext('m:parent/m:version', namespaces=NS)
        packaging = pom.findtext('m:packaging', default='jar', namespaces=NS)
        print(f'{service}: {group}:{artifact}:{version}, {packaging}, Spring Boot {parent}, Java {java}')
        if packaging != 'jar':
            failures.append(service + ': expected existing executable JAR packaging')
        for element, server, repo in [('repository', 'nexus-releases', 'maven-releases'),
                                      ('snapshotRepository', 'nexus-snapshots', 'maven-snapshots')]:
            node = pom.find('m:distributionManagement/m:' + element, NS)
            if node is None or node.findtext('m:id', namespaces=NS) != server or node.findtext('m:url', namespaces=NS) != '${env.NEXUS_URL}/repository/' + repo + '/':
                failures.append(service + ': invalid deployment configuration')
        if args.java11 and (int(java) > 11 or int(parent.split('.')[0]) >= 3):
            failures.append(service + ': Java 11 incompatible with existing Spring Boot/Java baseline')
    settings = ET.parse(SETTINGS).getroot()
    ns = {'s': 'http://maven.apache.org/SETTINGS/1.2.0'}
    if settings.findtext('s:mirrors/s:mirror/s:mirrorOf', namespaces=ns) != '*':
        failures.append('Dependency/plugin resolution must use the Nexus mirror')
    ids = {n.findtext('s:id', namespaces=ns) for n in settings.findall('s:servers/s:server', ns)}
    if ids != {'nexus-public', 'nexus-releases', 'nexus-snapshots'}:
        failures.append('Maven server IDs do not match repository/mirror IDs')
    if failures:
        raise NexusError('\n'.join(failures))
    print('VERIFIED local POM/settings XML, coordinates, deployment IDs and mirror configuration.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('audit', help='Validate local XML/configuration; no network')
    p.add_argument('--java11', action='store_true', help='Fail if the existing app is incompatible with Java 11')
    p.set_defaults(run=audit)
    for name, action in [('provision', provision), ('verify-config', verify_config),
                         ('cache', cache), ('verify-access', verify_access)]:
        p = commands.add_parser(name)
        if name == 'provision':
            p.add_argument('--apply', action='store_true', help='Apply the displayed configuration to the selected Nexus')
        p.set_defaults(run=action)
    for name, action in [('build', build), ('publish', publish), ('set-version', set_version),
                         ('verify-artifact', verify_artifact), ('resolve', resolve)]:
        p = commands.add_parser(name)
        p.add_argument('service', choices=SERVICES + (() if name in ('verify-artifact', 'resolve') else ('all',)))
        if name in ('verify-artifact', 'resolve'):
            p.add_argument('--version')
        if name == 'set-version':
            p.add_argument('version')
        if name == 'verify-artifact':
            p.add_argument('--local', action='store_true', help='Compare hosted JAR/POM SHA-256 to local files')
        if name == 'build':
            p.add_argument('--direct', action='store_true', help='Baseline build using normal Maven settings without Nexus')
        p.set_defaults(run=action)
    args = parser.parse_args()
    try:
        args.run(args)
    except (NexusError, OSError, ET.ParseError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
