#!/usr/bin/env python3
"""Idempotent provisioning; API response bodies and credentials are never logged."""
import json
import os
from pathlib import Path
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

COMPONENTS = {'product': 'product-service', 'user': 'user-service',
              'media': 'media-service', 'gateway': 'gateway',
              'discovery': 'discovery', 'frontend': 'frontend'}

class API:
    def __init__(self, url, token=''):
        self.url, self.token = url.rstrip('/'), token

    def call(self, endpoint, params=None, post=False):
        data = urllib.parse.urlencode(params or {}).encode()
        url = self.url + '/api/' + endpoint
        if not post and data:
            url += '?' + data.decode()
        request = urllib.request.Request(url, data=data if post else None)
        if post:
            request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        if self.token:
            request.add_header('Authorization', 'Bearer ' + self.token)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else {}
        except (urllib.error.URLError, TimeoutError) as error:
            if isinstance(error, urllib.error.HTTPError):
                raise RuntimeError(f'{endpoint}: HTTP {error.code}; check administrator User Token permissions and installed API schema') from None
            raise RuntimeError(f'{endpoint}: connection failed or timed out; check SonarQube health and rerun bootstrap; completed credentials are preserved') from None


def provision(api, directory):
    for component, suffix in COMPONENTS.items():
        key = 'buy01-' + suffix
        found = api.call('projects/search', {'projectKeys': key})['components']
        existing = next((project for project in found
                         if project['key'].casefold() == key.casefold()), None)
        if existing:
            key = existing['key']
        else:
            api.call('projects/create', {'project': key, 'name': key}, post=True)
            print('Created project ' + key)
        path = directory / ('sonar-' + component + '-token')
        if path.exists():
            if path.is_symlink() or not path.read_text().strip():
                raise RuntimeError(f'{path.name}: empty or unsafe existing file; resolve explicitly, no overwrite performed')
            valid = API(api.url, path.read_text().strip()).call('authentication/validate')['valid']
            if not valid:
                raise RuntimeError(f'{path.name}: invalid token; back up and remove this file to create a replacement; old remote tokens will not be revoked')
            os.chmod(path, 0o600)
            print('Preserved credential ' + path.name)
            continue
        # SonarQube only returns token values at generation. A unique name safely
        # recovers from a lost local file without revoking any remote credential.
        result = api.call('user_tokens/generate', {
            'name': 'jenkins-' + component + '-' + secrets.token_hex(8),
            'type': 'PROJECT_ANALYSIS_TOKEN', 'projectKey': key,
        }, post=True)
        token = result.get('token')
        if not token:
            raise RuntimeError('Token API did not return a token; provisioning stopped')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(token + '\n')
            output.flush()
            os.fsync(output.fileno())
        print('Stored credential ' + path.name)
    url = os.environ.get('JENKINS_WEBHOOK_URL', 'http://jenkins:8080/sonarqube-webhook/')
    hooks = api.call('webhooks/list')['webhooks']
    if not any(hook['url'] == url for hook in hooks):
        api.call('webhooks/create', {'name': 'Buy01 Jenkins', 'url': url}, post=True)
        print('Created Jenkins webhook')
    print('Provisioning complete; recreate Jenkins to load secret files')


def main():
    os.umask(0o077)
    directory = Path(os.environ.get('SECRETS_DIR', '/run/secrets'))
    token_path = directory / 'sonar-bootstrap-token'
    if not token_path.is_file() or token_path.is_symlink():
        raise RuntimeError('Supply sonar-bootstrap-token as an administrator User Token in the local secrets directory')
    os.chmod(token_path, 0o600)
    token = token_path.read_text().strip()
    if not token:
        raise RuntimeError('sonar-bootstrap-token is empty')
    api = API(os.environ.get('SONAR_HOST_URL', 'http://sonarqube:9000'), token)
    deadline = time.monotonic() + int(os.environ.get('SONAR_READY_TIMEOUT', '600'))
    while True:
        try:
            if api.call('system/status').get('status') == 'UP':
                break
        except (RuntimeError, urllib.error.URLError, TimeoutError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError('SonarQube readiness timed out; check service health and bootstrap authentication')
        time.sleep(5)
    if not api.call('authentication/validate')['valid']:
        raise RuntimeError('Bootstrap authentication rejected')
    provision(api, directory)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not print API bodies, URLs with credentials, or token values.
        print('Bootstrap failed: ' + (str(error) if isinstance(error, RuntimeError) else type(error).__name__), flush=True)
        raise SystemExit(1)
