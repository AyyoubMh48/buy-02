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
    def call(self, endpoint, params=None, post=False, raw=False):
        if endpoint == 'projects/search':
            return {'components': [{'key': k} for k in self.projects]}
        if endpoint == 'projects/create':
            self.projects.append(params['project'])
            return {}
        if endpoint == 'user_tokens/generate':
            assert params['type'] == 'PROJECT_ANALYSIS_TOKEN'
            self.generated += 1
            return {'token': 'fixture-only'}
        if endpoint == 'analysis_cache/get':
            return {}
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
        def checked_call(endpoint, params=None, post=False, raw=False):
            if endpoint == 'projects/create':
                self.assertNotEqual(params['project'].casefold(), 'buy01-product-service')
            if endpoint == 'user_tokens/generate' and api.generated == 0:
                self.assertEqual(params['projectKey'], 'Buy01-Product-Service')
            return original(endpoint, params, post, raw)
        with tempfile.TemporaryDirectory() as folder, patch.object(api, 'call', side_effect=checked_call), patch.object(bootstrap, 'API', return_value=api):
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

    def test_invalid_existing_token_is_replaced_after_validation(self):
        api = FakeAPI()
        invalid = FakeAPI()
        invalid.valid = False
        with tempfile.TemporaryDirectory() as folder, patch.object(
                bootstrap, 'API', side_effect=lambda url, token: invalid if token == 'old-token' else api):
            p = Path(folder) / 'sonar-product-token'
            p.write_text('old-token')
            bootstrap.provision(api, Path(folder))
            self.assertEqual(p.read_text(), 'fixture-only\n')
            self.assertEqual(api.generated, 6)

    def test_empty_existing_token_is_repaired(self):
        api = FakeAPI()
        with tempfile.TemporaryDirectory() as folder, patch.object(bootstrap, 'API', return_value=api):
            p = Path(folder) / 'sonar-product-token'
            p.touch()
            bootstrap.provision(api, Path(folder))
            self.assertEqual(p.read_text(), 'fixture-only\n')

    def test_wrong_project_permission_replaces_token(self):
        api = FakeAPI()
        denied = FakeAPI()
        original = denied.call
        def reject(endpoint, params=None, post=False, raw=False):
            if endpoint == 'analysis_cache/get':
                raise bootstrap.APIError(endpoint, 403, 'Insufficient privileges')
            return original(endpoint, params, post, raw)
        denied.call = reject
        with tempfile.TemporaryDirectory() as folder, patch.object(
                bootstrap, 'API', side_effect=lambda url, token: denied if token == 'wrong-project' else api):
            p = Path(folder) / 'sonar-product-token'
            p.write_text('wrong-project')
            bootstrap.provision(api, Path(folder))
            self.assertEqual(p.read_text(), 'fixture-only\n')

    def test_permission_probe_network_error_preserves_token(self):
        api = FakeAPI()
        with tempfile.TemporaryDirectory() as folder, patch.object(bootstrap, 'API', return_value=api):
            p = Path(folder) / 'sonar-product-token'
            p.write_text('working-token')
            with patch.object(api, 'call', side_effect=RuntimeError('connection failed')):
                with self.assertRaises(RuntimeError):
                    bootstrap.provision(api, Path(folder))
            self.assertEqual(p.read_text(), 'working-token')

    def test_symlink_is_never_overwritten(self):
        api = FakeAPI()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'protected'
            target.write_text('protected')
            (root / 'sonar-product-token').symlink_to(target)
            with self.assertRaises(RuntimeError):
                bootstrap.provision(api, root)
            self.assertEqual(target.read_text(), 'protected')

    def test_http_error_reports_api_message_and_redacts_token(self):
        import io
        error = bootstrap.urllib.error.HTTPError('http://test', 400, 'bad', {},
            io.BytesIO(b'{"errors":[{"msg":"Project already exists; squ_fixtureSecret"}]}'))
        with patch.object(bootstrap.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaisesRegex(bootstrap.APIError, 'Project already exists') as caught:
                bootstrap.API('http://test', 'squ_fixtureSecret').call('projects/create', post=True)
        self.assertNotIn('squ_fixtureSecret', str(caught.exception))

    def test_partial_failure_rerun_preserves_completed_tokens(self):
        api = FakeAPI()
        original = api.call
        def fail(endpoint, params=None, post=False, raw=False):
            if endpoint == 'user_tokens/generate' and api.generated == 2:
                raise RuntimeError('temporary API failure')
            return original(endpoint, params, post, raw)
        with tempfile.TemporaryDirectory() as folder, patch.object(bootstrap, 'API', return_value=api):
            root = Path(folder)
            with patch.object(api, 'call', side_effect=fail):
                with self.assertRaises(RuntimeError):
                    bootstrap.provision(api, root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            bootstrap.provision(api, root)
            self.assertEqual(api.generated, 6)
            self.assertEqual(len(list(root.iterdir())), 12)
            for name, value in before.items():
                self.assertEqual((root / name).read_bytes(), value)

    def test_missing_cache_proves_analysis_permission(self):
        api = FakeAPI()
        original = api.call
        def call(endpoint, params=None, post=False, raw=False):
            if endpoint == 'analysis_cache/get':
                raise bootstrap.APIError(endpoint, 404, 'No cache for given branch or pull request')
            return original(endpoint, params, post, raw)
        api.call = call
        self.assertTrue(bootstrap.analysis_authorized(api, 'buy01-product-service'))

    def test_missing_project_is_not_mistaken_for_missing_cache(self):
        api = FakeAPI()
        original = api.call
        def call(endpoint, params=None, post=False, raw=False):
            if endpoint == 'analysis_cache/get':
                raise bootstrap.APIError(endpoint, 404, 'Project not found')
            return original(endpoint, params, post, raw)
        api.call = call
        with self.assertRaises(bootstrap.APIError):
            bootstrap.analysis_authorized(api, 'buy01-product-service')

    def test_invalid_admin_token_fails_after_public_health_check(self):
        api = FakeAPI()
        api.valid = False
        health = FakeAPI()
        original = health.call
        def ready(endpoint, params=None, post=False, raw=False):
            if endpoint == 'system/status':
                return {'status': 'UP'}
            return original(endpoint, params, post, raw)
        health.call = ready
        with tempfile.TemporaryDirectory() as folder, patch.dict(bootstrap.os.environ, {'SECRETS_DIR': folder}), patch.object(bootstrap, 'API', side_effect=[api, health]):
            (Path(folder) / 'sonar-bootstrap-token').write_text('fixture-admin')
            with self.assertRaisesRegex(RuntimeError, 'Bootstrap authentication rejected'):
                bootstrap.main()
            self.assertEqual(api.generated, 0)

    def test_missing_admin_token_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(bootstrap.os.environ, {'SECRETS_DIR': folder}):
            with self.assertRaisesRegex(RuntimeError, 'administrator User Token'):
                bootstrap.main()
