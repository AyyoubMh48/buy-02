#!/usr/bin/env python3
"""Create a private Docker service-account file; never reset existing accounts."""
import argparse
import getpass
import os
from pathlib import Path
import re
import secrets
import shlex
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', default='.local/nexus-docker.env')
    args = parser.parse_args()
    path = Path(args.file)
    if path.exists():
        parser.error('File already exists; load/reuse it instead of replacing credentials.')
    values = {}
    for prefix, default in [('NEXUS_DOCKER_READ', 'buy02-docker-reader'),
                            ('NEXUS_DOCKER_PUBLISH', 'buy02-docker-publisher')]:
        user = input(f'{prefix} username [{default}]: ').strip() or default
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', user) or user in ('admin', 'anonymous'):
            parser.error('Invalid service-account username.')
        email = input(f'{prefix} email: ').strip()
        if not email or '@' not in email:
            parser.error('Supply a service-account email address.')
        password = getpass.getpass(f'{prefix} password (Enter generates one for a NEW account): ')
        if password:
            if len(password) < 16 or any(c in password for c in '\r\n'):
                parser.error('Use at least 16 characters without newlines.')
            if getpass.getpass('Confirm password: ') != password:
                parser.error('Passwords differ.')
        else:
            password = secrets.token_urlsafe(32)
        values.update({prefix + '_USERNAME': user, prefix + '_PASSWORD': password,
                       prefix + '_EMAIL': email})
    if values['NEXUS_DOCKER_READ_USERNAME'] == values['NEXUS_DOCKER_PUBLISH_USERNAME']:
        parser.error('Reader and publisher accounts must differ.')
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        for key, value in values.items():
            stream.write(key + '=' + shlex.quote(value) + '\n')
    print('Created private service-account file: ' + str(path))
    print('Existing Nexus account passwords must match; provisioning never resets them.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
