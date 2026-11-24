#!/usr/bin/env python3
"""Build, publish and retrieve Buy02 images with isolated Docker credentials."""
import argparse
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import tempfile
from uuid import uuid4
from urllib import error, parse, request

from manage import ROOT, SERVICES, coordinates
from nexus_api import NexusError, NoRedirect, required


def registry(value):
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?(?::[0-9]{1,5})?', value):
        raise NexusError('NEXUS_DOCKER_REGISTRY must be hostname[:port], without scheme or path.')
    if ':' in value and not 1 <= int(value.rsplit(':', 1)[1]) <= 65535:
        raise NexusError('Invalid registry port.')
    return value


def tag(value):
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', value) or value == 'latest':
        raise NexusError('Use a unique version/commit/build tag, not latest.')
    return value


def validate_challenge(status, challenge, host):
    realm = re.search(r'\brealm="([^"]+)"', challenge)
    if status != 401 or not challenge.lower().startswith('bearer ') or not realm:
        raise NexusError('Expected an authenticated Docker bearer challenge; verify DockerToken/anonymous settings.')
    target = parse.urlsplit(realm[1])
    if (target.scheme != 'https' or target.netloc != host or target.username or target.password
            or target.fragment):
        raise NexusError('Registry token endpoint must use HTTPS on the configured registry host/port.')


def verify_tls(host):
    """Validate TLS/challenge before sending any credentials, including on loopback."""
    context = ssl.create_default_context(cafile=os.environ.get('NEXUS_CA_BUNDLE') or None)
    opener = request.build_opener(NoRedirect(), request.HTTPSHandler(context=context))
    try:
        try:
            response = opener.open('https://' + host + '/v2/', timeout=30)
        except error.HTTPError as exc:
            response = exc
        with response:
            validate_challenge(response.code, response.headers.get('WWW-Authenticate', ''), host)
    except (error.URLError, TimeoutError, OSError):
        raise NexusError('Registry TLS/connectivity check failed. Check CA trust, DNS and proxy configuration.') from None


def docker(args, config=None, password=None, check=True):
    command = ['docker'] + (['--config', str(config)] if config else []) + args
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('NEXUS_')}
    result = subprocess.run(command, input=password, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=env, check=False)
    if check and result.returncode:
        # Docker output is useful, but a login response must never echo a secret.
        message = 'Docker login failed; check TLS trust, account and registry endpoint.' if password else result.stdout
        raise NexusError(message.strip())
    return result


def login(config, host, prefix):
    user, password = required(prefix + '_USERNAME'), required(prefix + '_PASSWORD')
    docker(['login', host, '--username', user, '--password-stdin'], config, password + '\n')


def image_id(reference, config=None):
    return docker(['image', 'inspect', '--format', '{{.Id}}', reference], config).stdout.strip()


def read_manifest(path, host):
    data = json.loads(Path(path).read_text())
    if data.get('schema') != 1 or data.get('registry') != host:
        raise NexusError('Manifest schema/registry mismatch.')
    tag(data.get('source_tag', ''))
    entries = data.get('images', [])
    names = [item.get('service') for item in entries]
    expected = set(SERVICES) | ({'frontend'} if 'frontend' in names else set())
    if len(names) != len(expected) or set(names) != expected:
        raise NexusError('Manifest must contain each service exactly once.')
    for item in entries:
        if (item.get('repository') != host + '/buy02/' + item['service']
                or not re.fullmatch(r'sha256:[0-9a-f]{64}', item.get('digest', ''))
                or not re.fullmatch(r'sha256:[0-9a-f]{64}', item.get('image_id', ''))):
            raise NexusError('Invalid repository, digest or image ID in release manifest.')
        tag(item.get('tag', ''))
    return data


def pull(data, config, smoke=False):
    for item in data['images']:
        pinned = item['repository'] + '@' + item['digest']
        docker(['pull', pinned], config)
        if image_id(pinned, config) != item['image_id']:
            raise NexusError('Pulled image differs from the published image: ' + item['service'])
        if smoke and item['service'] != 'frontend':
            docker(['run', '--rm', '--network', 'none', '--entrypoint', 'java', pinned, '-version'], config)
        # Restore the exact source tag expected by the existing staging Compose/rollback.
        docker(['tag', pinned, item['service'] + ':' + tag(data['source_tag'])], config)
        print('VERIFIED pull ' + pinned)


def publish(args):
    host = registry(required('NEXUS_DOCKER_REGISTRY'))
    output = Path(args.manifest)
    if output.exists():
        raise NexusError('Release manifest already exists; preserve it and choose a new output file.')
    names = SERVICES + (('frontend',) if args.include_frontend else ())
    source_tag, release_tag = tag(args.source_tag), tag(args.tag)
    # Inspect all sources and credentials before the first upload.
    for prefix in ('NEXUS_DOCKER_PUBLISH', 'NEXUS_DOCKER_READ'):
        required(prefix + '_USERNAME')
        required(prefix + '_PASSWORD')
    entries = [dict(service=name, repository=host + '/buy02/' + name,
                    tag=release_tag, image_id=image_id(name + ':' + source_tag)) for name in names]
    verify_tls(host)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True,
                            capture_output=True, check=True).stdout.strip()
    data = dict(schema=1, registry=host, source_tag=source_tag, git_commit=commit,
                maven={name: ':'.join(coordinates(name)) for name in SERVICES}, images=entries)
    with tempfile.TemporaryDirectory(prefix='buy02-docker-publish-') as publisher:
        login(publisher, host, 'NEXUS_DOCKER_PUBLISH')
        for item in entries:
            reference = item['repository'] + ':' + release_tag
            docker(['tag', item['service'] + ':' + source_tag, reference], publisher)
            result = docker(['push', reference], publisher)
            digests = re.findall(r'digest:\s*(sha256:[0-9a-f]{64})', result.stdout)
            if not digests:
                raise NexusError('Push returned no manifest digest for ' + item['service'])
            item['digest'] = digests[-1]
            print('PUBLISHED ' + reference + '@' + item['digest'])
    # Save uploaded digests even if reader verification fails, for safe retry/rollback.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
    with tempfile.TemporaryDirectory(prefix='buy02-docker-read-') as reader:
        login(reader, host, 'NEXUS_DOCKER_READ')
        pull(data, reader, smoke=True)
        # Test a NEW tag so immutability cannot masquerade as reader access denial.
        probe = host + '/buy02/rbac-probe:reader-' + uuid4().hex
        docker(['tag', entries[0]['service'] + ':' + source_tag, probe], reader)
        try:
            result = docker(['push', probe], reader, check=False)
            if result.returncode == 0 or not re.search(r'denied|unauthorized|not authorized|forbidden|403', result.stdout, re.I):
                raise NexusError('Reader upload denial was not demonstrated; inspect Docker RBAC.')
        finally:
            # Remove only the temporary local probe tag, never a remote artifact.
            docker(['image', 'rm', probe], reader)
        print('VERIFIED reader cannot push a new image tag.')
    print('VERIFIED release manifest: ' + str(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('tag', help='Generate version/commit/build tag')
    p.add_argument('--build', required=True)
    p = commands.add_parser('build', help='Build existing packaged application artifacts')
    p.add_argument('--source-tag', required=True)
    p.add_argument('--include-frontend', action='store_true')
    p = commands.add_parser('publish', help='Push images, then pull/verify as reader')
    p.add_argument('--source-tag', required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--include-frontend', action='store_true')
    p = commands.add_parser('pull', help='Retrieve an existing release, including rollback')
    p.add_argument('--manifest', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'tag':
            if not re.fullmatch(r'[0-9]+', args.build):
                raise NexusError('Build identifier must be numeric.')
            versions = {coordinates(name)[2] for name in SERVICES}
            if len(versions) != 1:
                raise NexusError('Service versions differ; select a release tag explicitly.')
            commit = subprocess.run(['git', 'rev-parse', '--short=12', 'HEAD'], cwd=ROOT,
                                    capture_output=True, text=True, check=True).stdout.strip()
            print(tag(next(iter(versions)) + '-g' + commit + '-b' + args.build))
        elif args.command == 'build':
            for name in SERVICES + (('frontend',) if args.include_frontend else ()):
                print(docker(['build', '--load', '-t', name + ':' + tag(args.source_tag),
                              str(ROOT / name)]).stdout, end='')
        elif args.command == 'publish':
            publish(args)
        else:
            host = registry(required('NEXUS_DOCKER_REGISTRY'))
            data = read_manifest(args.manifest, host)
            verify_tls(host)
            with tempfile.TemporaryDirectory(prefix='buy02-docker-read-') as reader:
                login(reader, host, 'NEXUS_DOCKER_READ')
                pull(data, reader, smoke=True)
    except (NexusError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
