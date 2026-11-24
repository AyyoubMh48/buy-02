#!/usr/bin/env python3
"""Provision a Docker hosted repository without changing Maven accounts or roles."""
import argparse
import re
import sys

from nexus_api import Client, NexusError, differences, merge, required

REPOSITORY = 'docker-hosted'
DESIRED = {
    'name': REPOSITORY, 'online': True,
    'storage': {'blobStoreName': 'default', 'strictContentTypeValidation': True,
                'writePolicy': 'ALLOW_ONCE'},
    'docker': {'v1Enabled': False, 'forceBasicAuth': False, 'httpPort': 8082},
}


def roles():
    read = ['nx-repository-view-docker-docker-hosted-' + action for action in ('browse', 'read')]
    return [dict(id='buy02-docker-reader', name='Buy02 Docker reader',
                 description='Pull application images', privileges=read, roles=[]),
            dict(id='buy02-docker-publisher', name='Buy02 Docker publisher',
                 description='Publish immutable images; no delete or administration',
                 privileges=['nx-repository-view-docker-docker-hosted-' + action
                             for action in ('browse', 'read', 'add', 'edit')], roles=[])]


def plan(client):
    """Preflight every collision before any writes; retain unrelated realms/settings."""
    changes = []
    inventory = {item['name']: item for item in client.json('GET', '/repositories')}
    endpoint = '/repositories/docker/hosted'
    existing = inventory.get(REPOSITORY)
    if existing:
        if existing['format'] != 'docker' or existing['type'] != 'hosted':
            raise NexusError('docker-hosted already exists with another format/type.')
        current = client.json('GET', endpoint + '/' + REPOSITORY)
        if current['storage']['blobStoreName'] != DESIRED['storage']['blobStoreName']:
            raise NexusError('Refusing to migrate the existing Docker blob store.')
        if differences(current, DESIRED):
            payload = merge(current, DESIRED)
            for key in ('url', 'format', 'type'):
                payload.pop(key, None)
            changes.append(('PUT', endpoint + '/' + REPOSITORY, payload))
    else:
        # A connector collision must be resolved by the operator, never by replacing it.
        for item in inventory.values():
            if item.get('format') == 'docker':
                config = client.json('GET', '/repositories/docker/' + item['type'] + '/' + item['name'])
                if config.get('docker', {}).get('httpPort') == 8082:
                    raise NexusError('Docker connector 8082 is already assigned to another repository.')
        changes.append(('POST', endpoint, DESIRED))
    active = client.json('GET', '/security/realms/active')
    if 'DockerToken' not in active:
        changes.append(('PUT', '/security/realms/active', active + ['DockerToken']))
    current_roles = {role['id']: role for role in client.json('GET', '/security/roles')
                     if role.get('source', 'default') == 'default'}
    for desired in roles():
        current = current_roles.get(desired['id'])
        if current is None:
            changes.append(('POST', '/security/roles', desired))
        elif (set(current['privileges']) != set(desired['privileges'])
              or set(current['roles']) != set(desired['roles'])):
            raise NexusError('Existing Docker role differs; review it before provisioning.')
    users = set()
    for prefix, role in [('NEXUS_DOCKER_READ', 'buy02-docker-reader'),
                         ('NEXUS_DOCKER_PUBLISH', 'buy02-docker-publisher')]:
        user, password = required(prefix + '_USERNAME'), required(prefix + '_PASSWORD')
        if (not re.fullmatch(r'[A-Za-z0-9_.-]+', user) or user in users
                or user in ('admin', 'anonymous', required('NEXUS_ADMIN_USERNAME'))):
            raise NexusError('Use separate, valid Docker reader/publisher account names.')
        users.add(user)
        matches = [u for u in client.json('GET', '/security/users?userId=' + user + '&source=default')
                   if u['userId'] == user and u.get('source', 'default') == 'default']
        if matches:
            if set(matches[0]['roles']) != {role} or matches[0]['status'] != 'active':
                raise NexusError('Existing Docker account has unexpected roles/status; takeover refused.')
        else:
            if len(password) < 16 or any(c in password for c in '\r\n'):
                raise NexusError('Choose Docker service passwords of at least 16 characters without newlines.')
            changes.append(('POST', '/security/users', dict(
                userId=user, firstName='Buy02', lastName='Docker', emailAddress=required(prefix + '_EMAIL'),
                password=password, status='active', roles=[role])))
    anonymous = client.json('GET', '/security/anonymous')
    if anonymous['enabled']:
        raise NexusError('Complete Anas\'s Maven provisioning first: anonymous access must be disabled.')
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply the reviewed plan')
    parser.add_argument('--verify', action='store_true', help='Read-only configuration verification')
    args = parser.parse_args()
    if args.apply and args.verify:
        parser.error('--apply and --verify are mutually exclusive')
    try:
        client = Client()
        changes = plan(client)
        for method, endpoint, _ in changes:
            print(method + ' ' + endpoint)  # Never log account payloads/passwords.
        if args.verify:
            if changes:
                raise NexusError('Docker configuration is incomplete or differs from the expected configuration.')
            print('VERIFIED Docker repository, immutable policy, realm and least-privilege accounts.')
        elif args.apply:
            for method, endpoint, payload in changes:
                client.json(method, endpoint, payload)
            if plan(client):
                raise NexusError('Post-provision configuration verification failed.')
            print('VERIFIED Docker provisioning; live push/pull still requires image verification.')
        else:
            print('PLAN ONLY. Review, then use --apply. Maven configuration is preserved.')
    except (NexusError, OSError, ValueError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
