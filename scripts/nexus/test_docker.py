"""Regression tests for Docker permission boundaries and publishing failure paths."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import images
from nexus_api import NexusError
import registry

ENV = {
    'NEXUS_ADMIN_USERNAME': 'admin',
    'NEXUS_DOCKER_READ_USERNAME': 'image-reader', 'NEXUS_DOCKER_READ_PASSWORD': 'r' * 24,
    'NEXUS_DOCKER_READ_EMAIL': 'reader@example.test',
    'NEXUS_DOCKER_PUBLISH_USERNAME': 'image-publisher', 'NEXUS_DOCKER_PUBLISH_PASSWORD': 'p' * 24,
    'NEXUS_DOCKER_PUBLISH_EMAIL': 'publisher@example.test',
    'NEXUS_DOCKER_REGISTRY': 'localhost:5443',
}
IMAGE_ID = 'sha256:' + 'a' * 64
DIGEST = 'sha256:' + 'b' * 64


class Server:
    def __init__(self):
        self.repository = copy.deepcopy(registry.DESIRED)
        self.realms = ['NexusAuthenticatingRealm', 'DockerToken']
        self.roles = registry.roles()
        self.users = [dict(userId=ENV[prefix + '_USERNAME'], source='default',
                           roles=[role], status='active') for prefix, role in
                      [('NEXUS_DOCKER_READ', 'buy02-docker-reader'),
                       ('NEXUS_DOCKER_PUBLISH', 'buy02-docker-publisher')]]
        self.calls = []

    def json(self, method, path, payload=None):
        self.calls.append((method, path))
        if method != 'GET':
            raise AssertionError('Planning must never mutate the server')
        if path == '/repositories':
            return [dict(name='docker-hosted', format='docker', type='hosted')]
        if path == '/repositories/docker/hosted/docker-hosted':
            return self.repository
        if path == '/security/realms/active':
            return self.realms
        if path == '/security/roles':
            return self.roles
        if path.startswith('/security/users?'):
            return self.users
        if path == '/security/anonymous':
            return {'enabled': False}
        raise AssertionError(path)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.server = Server()

    def test_idempotence(self):
        self.assertEqual(registry.plan(self.server), [])

    def test_realm_activation_preserves_other_realms(self):
        self.server.realms = ['NexusAuthenticatingRealm', 'CustomRealm']
        changes = registry.plan(self.server)
        self.assertEqual(changes, [('PUT', '/security/realms/active',
                                   ['NexusAuthenticatingRealm', 'CustomRealm', 'DockerToken'])])

    def test_existing_maven_account_cannot_be_taken_over(self):
        self.server.users[0]['roles'] = ['buy02-maven-reader']
        with self.assertRaises(NexusError):
            registry.plan(self.server)

    def test_existing_privileged_role_is_refused(self):
        self.server.roles[0]['privileges'].append('nx-all')
        with self.assertRaises(NexusError):
            registry.plan(self.server)

    def test_blob_store_migration_is_refused(self):
        self.server.repository['storage']['blobStoreName'] = 'existing-blobs'
        with self.assertRaises(NexusError):
            registry.plan(self.server)

    def test_unknown_settings_preserved_when_correcting_policy(self):
        self.server.repository['storage']['writePolicy'] = 'ALLOW'
        self.server.repository['cleanup'] = {'policyNames': ['keep-me']}
        changes = registry.plan(self.server)
        self.assertEqual(changes[0][2]['cleanup'], {'policyNames': ['keep-me']})
        self.assertEqual(changes[0][2]['storage']['writePolicy'], 'ALLOW_ONCE')

    def test_reader_and_publisher_must_differ(self):
        os.environ['NEXUS_DOCKER_PUBLISH_USERNAME'] = ENV['NEXUS_DOCKER_READ_USERNAME']
        with self.assertRaises(NexusError):
            registry.plan(self.server)

    def test_roles_never_grant_delete_or_admin(self):
        for role in registry.roles():
            self.assertFalse(role['roles'])
            for privilege in role['privileges']:
                self.assertTrue(privilege.startswith('nx-repository-view-docker-docker-hosted-'))
                self.assertNotIn(privilege.rsplit('-', 1)[1], ('delete', '*'))


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_registry_rejects_credentials_scheme_path_and_shell_input(self):
        for value in ('http://localhost:5443', 'user:pass@host', 'host/repo', 'host;id', 'host:99999'):
            with self.subTest(value=value), self.assertRaises(NexusError):
                images.registry(value)

    def test_tags_are_unique_named_and_safe(self):
        for value in ('latest', '../other', 'bad tag', 'a' * 129):
            with self.subTest(value=value), self.assertRaises(NexusError):
                images.tag(value)
        self.assertEqual(images.tag('1.0.0-gabc123-b1'), '1.0.0-gabc123-b1')

    def test_token_challenge_cannot_downgrade_tls_or_redirect_credentials(self):
        for url in ('http://localhost:5443/token', 'https://attacker.test/token',
                    'https://user:pass@localhost:5443/token'):
            with self.subTest(url=url), self.assertRaises(NexusError):
                images.validate_challenge(401, 'Bearer realm="' + url + '"', 'localhost:5443')
        images.validate_challenge(401, 'Bearer realm="https://localhost:5443/token",service="nexus"',
                                  'localhost:5443')

    def test_unprotected_registry_is_rejected_before_login(self):
        with self.assertRaises(NexusError):
            images.validate_challenge(200, '', 'localhost:5443')

    @patch('images.subprocess.run')
    def test_password_uses_stdin_and_admin_is_removed(self, run):
        os.environ['NEXUS_ADMIN_PASSWORD'] = 'never-pass-to-docker'
        run.return_value = subprocess.CompletedProcess([], 0, 'ok')
        images.login('/tmp/isolated', 'localhost:5443', 'NEXUS_DOCKER_READ')
        args, kwargs = run.call_args
        self.assertNotIn(ENV['NEXUS_DOCKER_READ_PASSWORD'], args[0])
        self.assertEqual(kwargs['input'], ENV['NEXUS_DOCKER_READ_PASSWORD'] + '\n')
        self.assertNotIn('NEXUS_ADMIN_PASSWORD', kwargs['env'])

    @patch('images.subprocess.run')
    def test_login_error_does_not_echo_server_response(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, 'private-response')
        with self.assertRaises(NexusError) as caught:
            images.login('/tmp/isolated', 'localhost:5443', 'NEXUS_DOCKER_READ')
        self.assertNotIn('private-response', str(caught.exception))

    def manifest(self):
        return dict(schema=1, registry='localhost:5443', source_tag='1', images=[
            dict(service=name, repository='localhost:5443/buy02/' + name,
                 digest=DIGEST, image_id=IMAGE_ID, tag='1.0.0-gabc-b1') for name in images.SERVICES])

    def test_manifest_cannot_pull_from_another_registry(self):
        data = self.manifest()
        data['images'][0]['repository'] = 'attacker.test/image'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.json'
            path.write_text(json.dumps(data))
            with self.assertRaises(NexusError):
                images.read_manifest(path, 'localhost:5443')

    def test_manifest_requires_complete_release(self):
        data = self.manifest()
        data['images'].pop()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.json'
            path.write_text(json.dumps(data))
            with self.assertRaises(NexusError):
                images.read_manifest(path, 'localhost:5443')

    @patch('images.docker')
    @patch('images.image_id', return_value='sha256:' + 'c' * 64)
    def test_mismatched_pull_never_retags_for_deployment(self, identify, docker):
        with self.assertRaises(NexusError):
            images.pull(self.manifest(), '/tmp/isolated')
        self.assertEqual(len(docker.call_args_list), 1)
        self.assertEqual(docker.call_args.args[0][0], 'pull')

    @patch('images.docker')
    @patch('images.image_id', return_value=IMAGE_ID)
    def test_pull_uses_digest_and_restores_staging_tags(self, identify, docker):
        images.pull(self.manifest(), '/tmp/isolated')
        calls = [call.args[0] for call in docker.call_args_list]
        self.assertEqual(calls[0], ['pull', 'localhost:5443/buy02/discovery@' + DIGEST])
        self.assertEqual(calls[1][-1], 'discovery:1')

    @patch('images.docker')
    @patch('images.image_id', side_effect=NexusError('missing source image'))
    def test_missing_source_cannot_start_upload(self, identify, docker):
        with tempfile.TemporaryDirectory() as folder:
            args = SimpleNamespace(manifest=folder + '/release.json', source_tag='1',
                                   tag='1.0.0-gabc-b1', include_frontend=False)
            with self.assertRaises(NexusError):
                images.publish(args)
            docker.assert_not_called()
            self.assertFalse(Path(args.manifest).exists())

    @patch('images.docker')
    def test_existing_manifest_is_never_overwritten(self, docker):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'release.json'
            path.write_text('existing-evidence')
            with self.assertRaises(NexusError):
                images.publish(SimpleNamespace(manifest=str(path)))
            docker.assert_not_called()
            self.assertEqual(path.read_text(), 'existing-evidence')

    def publish_with_fake_docker(self, folder, *, fail_push=False, fail_pull=False, allow_reader_push=False):
        configs = []

        def fake_docker(args, config=None, password=None, check=True):
            if config:
                configs.append(config)
            if args[0] == 'push':
                if '/rbac-probe:' in args[1]:
                    return subprocess.CompletedProcess([], 0 if allow_reader_push else 1,
                                                       '' if allow_reader_push else 'denied: access forbidden')
                if fail_push:
                    raise NexusError('registry upload failed')
                return subprocess.CompletedProcess([], 0, 'digest: ' + DIGEST)
            if args[0] == 'pull' and fail_pull:
                raise NexusError('reader authentication failed')
            return subprocess.CompletedProcess([], 0, '')

        args = SimpleNamespace(manifest=folder + '/release.json', source_tag='1',
                               tag='1.0.0-gabc-b1', include_frontend=True)
        with (patch('images.docker', side_effect=fake_docker),
              patch('images.image_id', return_value=IMAGE_ID), patch('images.verify_tls')):
            try:
                images.publish(args)
            finally:
                for config in configs:
                    self.assertFalse(Path(config).exists(), 'Temporary credentials must be cleaned on failure too')

    def test_failed_upload_cannot_report_complete_release(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(NexusError, 'upload failed'):
                self.publish_with_fake_docker(folder, fail_push=True)
            self.assertFalse((Path(folder) / 'release.json').exists())

    def test_reader_failure_retains_uploaded_digest_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(NexusError, 'reader authentication'):
                self.publish_with_fake_docker(folder, fail_pull=True)
            manifest = images.read_manifest(Path(folder) / 'release.json', 'localhost:5443')
            self.assertEqual(len(manifest['images']), 7)

    def test_reader_unexpected_upload_permission_fails_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(NexusError, 'denial was not demonstrated'):
                self.publish_with_fake_docker(folder, allow_reader_push=True)

    def test_complete_release_contains_all_seven_verified_images(self):
        with tempfile.TemporaryDirectory() as folder:
            self.publish_with_fake_docker(folder)
            manifest = images.read_manifest(Path(folder) / 'release.json', 'localhost:5443')
            self.assertEqual(len(manifest['images']), 7)
            self.assertTrue(all(item['digest'] == DIGEST for item in manifest['images']))


if __name__ == '__main__':
    unittest.main()
