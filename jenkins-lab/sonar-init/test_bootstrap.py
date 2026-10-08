import tempfile
import urllib.parse
import unittest
from pathlib import Path
from unittest.mock import patch
import bootstrap

class FakeAPI:
    url = 'http://test'
    def __init__(self):
        self.projects, self.hooks, self.generated = [], [], 0
        self.valid = True
    def call(self, endpoint, params=None, post=False):
        if endpoint == 'projects/search':
            return {'components': [{'key': k} for k in self.projects
                                   if k.casefold() == params['projectKeys'].casefold()]}
        if endpoint == 'projects/create':
            self.projects.append(params['project'])
            return {}
        if endpoint == 'user_tokens/generate':
            assert params['type'] == 'PROJECT_ANALYSIS_TOKEN'
            self.generated += 1
            return {'token': 'fixture-only'}
        if endpoint == 'authentication/validate':
            return {'valid': self.valid}
        if endpoint == 'webhooks/list':
            return {'webhooks': self.hooks}
        if endpoint == 'webhooks/create':
            self.hooks.append({'url': params['url']})
            return {}
        raise AssertionError(endpoint)

class BootstrapTests(unittest.TestCase):
    def test_existing_mixed_case_project_is_reused_for_token(self):
        api = FakeAPI()
        api.projects = ['Buy01-Product-Service']
        original = api.call
        def checked_call(endpoint, params=None, post=False):
            if endpoint == 'projects/create':
                self.assertNotEqual(params['project'].casefold(), 'buy01-product-service')
            if endpoint == 'user_tokens/generate' and api.generated == 0:
                self.assertEqual(params['projectKey'], 'Buy01-Product-Service')
            return original(endpoint, params, post)
        with tempfile.TemporaryDirectory() as folder, patch.object(api, 'call', side_effect=checked_call):
            bootstrap.provision(api, Path(folder))
        self.assertEqual(len(api.projects), 6)
        self.assertEqual(api.generated, 6)

    def test_create_uses_form_parameters(self):
        with patch.object(bootstrap.urllib.request, 'urlopen') as opened:
            opened.return_value.__enter__.return_value.read.return_value = b'{}'
            bootstrap.API('http://test').call('projects/create', {
                'project': 'buy01-product-service', 'name': 'Buy01 Product Service'}, post=True)
        request = opened.call_args.args[0]
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(request.get_header('Content-type'), 'application/x-www-form-urlencoded')
        self.assertEqual(urllib.parse.parse_qs(request.data.decode()), {
            'project': ['buy01-product-service'], 'name': ['Buy01 Product Service']})

    def test_repeat_preserves_history_tokens_and_webhook(self):
        api = FakeAPI()
        with tempfile.TemporaryDirectory() as folder, patch.object(bootstrap, 'API', return_value=api):
            root = Path(folder)
            bootstrap.provision(api, root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            bootstrap.provision(api, root)
            self.assertEqual(len(api.projects), 6)
            self.assertEqual(api.generated, 6)
            self.assertEqual(len(api.hooks), 1)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            for p in root.iterdir():
                self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_invalid_existing_token_not_overwritten(self):
        api = FakeAPI()
        api.valid = False
        with tempfile.TemporaryDirectory() as folder, patch.object(bootstrap, 'API', return_value=api):
            p = Path(folder) / 'sonar-product-token'
            p.write_text('old-token')
            with self.assertRaises(RuntimeError):
                bootstrap.provision(api, Path(folder))
            self.assertEqual(p.read_text(), 'old-token')
            self.assertEqual(api.generated, 0)

    def test_empty_existing_token_not_overwritten(self):
        api = FakeAPI()
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'sonar-product-token'
            p.touch()
            with self.assertRaises(RuntimeError):
                bootstrap.provision(api, Path(folder))
            self.assertEqual(p.read_bytes(), b'')
            self.assertEqual(api.generated, 0)

    def test_partial_failure_rerun_preserves_completed_tokens(self):
        api = FakeAPI()
        original = api.call
        def fail(endpoint, params=None, post=False):
            if endpoint == 'user_tokens/generate' and api.generated == 2:
                raise RuntimeError('temporary API failure')
            return original(endpoint, params, post)
        with tempfile.TemporaryDirectory() as folder, patch.object(bootstrap, 'API', return_value=api):
            root = Path(folder)
            with patch.object(api, 'call', side_effect=fail):
                with self.assertRaises(RuntimeError):
                    bootstrap.provision(api, root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            bootstrap.provision(api, root)
            self.assertEqual(api.generated, 6)
            self.assertEqual(len(list(root.iterdir())), 6)
            for name, value in before.items():
                self.assertEqual((root / name).read_bytes(), value)

    def test_missing_admin_token_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(bootstrap.os.environ, {'SECRETS_DIR': folder}):
            with self.assertRaisesRegex(RuntimeError, 'administrator User Token'):
                bootstrap.main()
