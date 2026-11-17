#!/usr/bin/env python3
"""Create/load private credentials and optionally finish the existing Nexus workflow."""
import argparse
import getpass
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

from nexus_api import Client, NexusError, base_url

DESTINATION = Path('/tmp/nexus-migration-credentials.env')
ROOT = Path(__file__).resolve().parents[2]
PREFIXES = ('NEXUS_ADMIN', 'NEXUS_READ', 'NEXUS_PUBLISH')


def hidden(label, default=''):
    value = getpass.getpass(label) or default
    if not value or any(c in value for c in '\r\n\0'):
        raise NexusError('Empty or invalid input; no credentials displayed.')
    return value


def load_private(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, encoding='utf-8') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise NexusError('Credential file must be a regular file owned by you with mode 0600.')
        values = {}
        allowed = {'NEXUS_URL'} | {p + suffix for p in PREFIXES for suffix in ('_USERNAME', '_PASSWORD', '_EMAIL')}
        for line in stream:
            key, separator, raw = line.rstrip('\n').partition('=')
            if not separator or key not in allowed or key in values:
                raise NexusError('Invalid private credential file structure.')
            words = shlex.split(raw)
            if len(words) != 1:
                raise NexusError('Invalid private credential file value.')
            values[key] = words[0]
    base_url(values.get('NEXUS_URL', ''))
    for prefix in PREFIXES:
        if not values.get(prefix + '_USERNAME') or not values.get(prefix + '_PASSWORD'):
            raise NexusError('Private credential file is incomplete.')
    return values


def repair_service_passwords(path, values):
    """Repair only short passwords for accounts not yet present; no server writes."""
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise NexusError('Password repair requires your local interactive terminal.')
    if path.resolve().is_relative_to(ROOT):
        raise NexusError('Credential file must be outside the checkout.')
    previous = {key: os.environ.get(key) for key in values}
    try:
        os.environ.update(values)
        users = Client().json('GET', '/security/users')
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    existing = {u['userId'] for u in users if u.get('source', 'default') == 'default'}
    updates = {}
    for prefix in ('NEXUS_READ', 'NEXUS_PUBLISH'):
        if values[prefix + '_USERNAME'] in existing or len(values[prefix + '_PASSWORD']) >= 16:
            continue
        while True:
            password = getpass.getpass(prefix + ' new password (hidden; Enter generates securely): ')
            if not password:
                password = secrets.token_urlsafe(32)
            else:
                if len(password) < 16 or not password.strip() or any(c in password for c in '\r\n\0'):
                    print('Use at least 16 characters, without line breaks; try again.')
                    continue
                if password != getpass.getpass('Confirm new password (hidden): '):
                    print('Passwords did not match; try again.')
                    continue
            updates[prefix + '_PASSWORD'] = password
            break
    if not updates:
        print('No invalid new-account passwords found; private file unchanged.')
        return values
    # Preserve all untouched lines, including administrator and valid passwords.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        original_stat = os.fstat(stream.fileno())
        original = stream.read()
    if load_private(path) != values:
        raise NexusError('Credential file changed during repair; no update saved.')
    lines = original.decode('utf-8').splitlines(keepends=True)
    replacement = ''.join(key + '=' + shlex.quote(updates[key]) + '\n'
                          if (key := line.partition('=')[0]) in updates else line
                          for line in lines).encode('utf-8')
    temp_fd, temp_name = tempfile.mkstemp(prefix='.nexus-credentials-', dir=path.parent)
    try:
        with os.fdopen(temp_fd, 'wb') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(replacement)
            stream.flush()
            os.fsync(stream.fileno())
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (original_stat.st_dev, original_stat.st_ino) or load_private(path) != values:
            raise NexusError('Credential file changed during repair; no update saved.')
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print('Updated only invalid new-account passwords; retained mode 0600. No Nexus account was reset.')
    return load_private(path)


def verify_snapshot_inventory(admin):
    """Find timestamped SNAPSHOT components by their Maven base version."""
    from urllib.parse import urlencode
    import manage
    for service in manage.SERVICES:
        group, artifact, version = manage.coordinates(service)
        params = {'repository': 'maven-snapshots', 'maven.groupId': group,
                  'maven.artifactId': artifact, 'maven.baseVersion': version}
        data = admin.json('GET', '/search?' + urlencode(params))
        if not data.get('items'):
            raise NexusError('No published SNAPSHOT component found for ' + service + '; inventory verification failed.')
        print('PASS published component: ' + service + ' ' + version + ' maven-snapshots')


def finish(values):
    os.environ.update(values)
    if not os.environ.get('MAVEN_BIN') and shutil.which('mvn'):
        os.environ['MAVEN_BIN'] = shutil.which('mvn')
    admin = Client()
    eula = admin.json('GET', '/system/eula')
    if not eula.get('accepted'):
        raise NexusError('Accept the Nexus EULA in your private browser first, then rerun with --reuse --finish.')
    repositories = admin.json('GET', '/repositories')
    users = admin.json('GET', '/security/users')
    roles = admin.json('GET', '/security/roles')
    print(f'PASS administrator authentication: {len(repositories)} repositories, {len(users)} users, {len(roles)} roles.')
    for repo in repositories:
        print('Repository: ' + repo['name'] + ' (' + repo['type'] + ')')
    import manage
    if any(not manage.coordinates(s)[2].endswith('-SNAPSHOT') for s in manage.SERVICES):
        raise NexusError('All six versions must be SNAPSHOTs; POM changes are refused.')
    commands = [['audit'], ['provision'], ['provision', '--apply'], ['verify-config'],
                ['publish', 'all'], ['cache'], ['verify-access']]
    for service in manage.SERVICES:
        commands.extend([['verify-artifact', service, '--local'], ['resolve', service]])
    for command in commands:
        print('Running: manage.py ' + ' '.join(command), flush=True)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/nexus/manage.py'), *command],
                                cwd=ROOT, check=False)
        if result.returncode:
            raise NexusError('Workflow stopped at: ' + ' '.join(command) + '. Correct the failure and rerun with --reuse --finish.')
    verify_snapshot_inventory(admin)
    print('PASS authenticated workflow. Port remains unchanged; request approval before cutover.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=DESTINATION)
    parser.add_argument('--url', default='http://127.0.0.1:18081')
    parser.add_argument('--bootstrap', action='store_true', help='Fresh local container only: read generated admin password privately and replace it with your prompted password')
    parser.add_argument('--container', default='buy02-nexus')
    parser.add_argument('--reuse', action='store_true', help='Load existing mode-0600 file without replacing it')
    parser.add_argument('--repair-service-passwords', action='store_true', help='Privately repair only short passwords for new reader/publisher accounts; requires --reuse')
    parser.add_argument('--finish', action='store_true', help='Authenticate, provision, build/deploy/check all six SNAPSHOTs, cache and RBAC')
    args = parser.parse_args()
    try:
        if args.reuse and args.bootstrap:
            raise NexusError('--bootstrap cannot be combined with --reuse.')
        if args.repair_service_passwords and not args.reuse:
            raise NexusError('--repair-service-passwords requires --reuse.')
        if args.reuse:
            values = load_private(args.file)
            if args.repair_service_passwords:
                values = repair_service_passwords(args.file, values)
        else:
            if args.file.exists() or args.file.is_symlink():
                raise NexusError('Credential file exists; refusing overwrite. Use --reuse to load it.')
            if not sys.stdin.isatty() or not sys.stderr.isatty():
                raise NexusError('Run from your local interactive terminal; private prompts require a TTY.')
            path = args.file.expanduser().resolve()
            if path.is_relative_to(ROOT):
                raise NexusError('Choose a credential path outside the checkout.')
            print('Use the current admin password. Rotate any exposed password in Nexus first.')
            values = {'NEXUS_URL': base_url(args.url)}
            for prefix, default in zip(PREFIXES, ('admin', 'buy02-reader', 'buy02-publisher')):
                username = hidden(prefix + ' username (hidden; Enter for default): ', default)
                if not re.fullmatch(r'[A-Za-z0-9_.-]+', username):
                    raise NexusError('Invalid account name.')
                values[prefix + '_USERNAME'] = username
                generated = '' if prefix == 'NEXUS_ADMIN' else secrets.token_urlsafe(32)
                label = (' admin password (hidden): ' if prefix == 'NEXUS_ADMIN' else ' password (hidden; Enter generates only for a NEW account): ')
                values[prefix + '_PASSWORD'] = hidden(prefix + label, generated)
                if prefix != 'NEXUS_ADMIN':
                    values[prefix + '_EMAIL'] = hidden(prefix + ' email (hidden): ')
            ids = [values[p + '_USERNAME'] for p in PREFIXES]
            if len(set(ids)) != 3 or 'anonymous' in ids:
                raise NexusError('Admin, reader and publisher must be distinct accounts.')
            if args.bootstrap:
                if values['NEXUS_ADMIN_USERNAME'] != 'admin' or values['NEXUS_URL'] not in ('http://127.0.0.1:8081', 'http://127.0.0.1:18081', 'http://127.0.0.1:28081'):
                    raise NexusError('Bootstrap requires the local admin account and localhost endpoint.')
                initial = subprocess.run(['docker', 'exec', args.container, 'cat', '/nexus-data/admin.password'], capture_output=True, text=True, check=False)
                if initial.returncode or not initial.stdout.strip():
                    raise NexusError('Fresh bootstrap password unavailable; use normal interactive setup for an existing instance.')
                previous = {k: os.environ.get(k) for k in ('NEXUS_URL', 'NEXUS_ADMIN_USERNAME', 'NEXUS_ADMIN_PASSWORD')}
                try:
                    os.environ.update(NEXUS_URL=values['NEXUS_URL'], NEXUS_ADMIN_USERNAME='admin', NEXUS_ADMIN_PASSWORD=initial.stdout.strip())
                    with Client().open('PUT', '/service/rest/v1/security/users/admin/change-password', values['NEXUS_ADMIN_PASSWORD'].encode(), 'text/plain'):
                        pass
                finally:
                    for key, value in previous.items():
                        if value is None: os.environ.pop(key, None)
                        else: os.environ[key] = value
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                os.fchmod(stream.fileno(), 0o600)
                for key, value in values.items():
                    stream.write(f'{key}={shlex.quote(value)}\n')
                stream.flush()
                os.fsync(stream.fileno())
            print('Saved private mode-0600 file; no values displayed. Existing account passwords are never reset.')
        if args.finish:
            finish(values)
        return 0
    except NexusError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError):
        # Never echo exception text from file parsing or OS/environment values.
        print('Setup/workflow failed safely. Check file existence/0600 ownership, inputs and the last reported workflow step. No secret values displayed.', file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled; no secret values displayed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
