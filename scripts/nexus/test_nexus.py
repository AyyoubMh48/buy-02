"""Offline regression tests. These do not claim to verify a live Nexus server."""
import argparse
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import manage
from nexus_api import (Client, NexusError, NoRedirect, artifact_paths, base_url,
                       repository_plan, role_specs, validate_version)


class Response(io.BytesIO):
    status = 200


class NexusTests(unittest.TestCase):
    def test_reject_remote_cleartext_and_embedded_secrets(self):
        for url in ('http://nexus.example.com', 'https://user:secret@nexus.example.com',
                    'https://nexus.example.com/?password=x', 'file:///etc/passwd'):
            with self.subTest(url=url), self.assertRaises(NexusError):
                base_url(url)

    def test_accept_loopback_and_tls_context_path(self):
        self.assertEqual(base_url('http://127.0.0.1:8081/'), 'http://127.0.0.1:8081')
        self.assertEqual(base_url('https://nexus.example.com/nexus/'), 'https://nexus.example.com/nexus')

    def test_redirects_never_forward_authorization(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere'))

    @patch.dict(os.environ, {'NEXUS_URL': 'http://127.0.0.1:8081'}, clear=True)
    def test_missing_credentials_fail_before_requests(self):
        with self.assertRaisesRegex(NexusError, 'NEXUS_ADMIN_USERNAME'):
            Client()

    @patch.dict(os.environ, {'NEXUS_URL': 'http://127.0.0.1:8081',
                            'NEXUS_ADMIN_USERNAME': 'admin', 'NEXUS_ADMIN_PASSWORD': 'private-value'}, clear=True)
    def test_http_errors_do_not_echo_server_body_or_secret(self):
        client = Client()
        client.opener = Mock()
        client.opener.open.side_effect = HTTPError('http://localhost', 403, 'private-value', {}, io.BytesIO(b'private-value'))
        with self.assertRaises(NexusError) as result:
            client.json('GET', '/security/roles')
        self.assertIn('403', str(result.exception))
        self.assertNotIn('private-value', str(result.exception))

    def inventory_client(self, specs):
        client = Mock()
        inventory = [dict(name=s['config']['name'], format='maven2', type=s['type']) for s in specs]
        configs = {'/repositories/maven/' + s['type'] + '/' + s['config']['name']: s['config'] for s in specs}
        client.json.side_effect = lambda method, path: inventory if path == '/repositories' else configs[path]
        return client

    def test_matching_default_repositories_are_not_duplicated(self):
        specs = manage.specs()
        self.assertEqual(repository_plan(self.inventory_client(specs), specs), [])

    def test_missing_repositories_created_in_member_order(self):
        client = Mock()
        client.json.return_value = []
        plan = repository_plan(client, manage.specs())
        self.assertEqual([p[0] for p in plan], ['POST'] * 4)
        self.assertEqual(plan[-1][3], 'maven-public')

    def test_type_collision_refused(self):
        client = Mock()
        client.json.return_value = [dict(name='maven-releases', format='docker', type='hosted')]
        with self.assertRaisesRegex(NexusError, 'different format/type'):
            repository_plan(client, manage.specs())

    def test_blob_migration_refused(self):
        current = copy.deepcopy(manage.specs())
        current[0]['config']['storage']['blobStoreName'] = 'other'
        with self.assertRaisesRegex(NexusError, 'data migration is refused'):
            repository_plan(self.inventory_client(current), manage.specs())

    def test_update_preserves_proxy_options(self):
        current = copy.deepcopy(manage.specs())
        current[2]['config']['proxy']['remoteUrl'] = 'https://old.example/maven/'
        current[2]['config']['httpClient']['connection'] = {'timeout': 17}
        current[2]['config']['url'] = 'http://old.example/'
        plan = repository_plan(self.inventory_client(current), manage.specs())
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0][0], 'PUT')
        self.assertEqual(plan[0][2]['httpClient']['connection']['timeout'], 17)
        self.assertNotIn('url', plan[0][2])

    def test_group_extra_members_preserved_on_update(self):
        current = copy.deepcopy(manage.specs())
        current[3]['config']['group']['memberNames'] = ['team-releases', 'maven-central']
        plan = repository_plan(self.inventory_client(current), manage.specs())
        self.assertEqual(plan[0][2]['group']['memberNames'],
                         ['maven-releases', 'maven-snapshots', 'maven-central', 'team-releases'])

    def test_group_extra_members_do_not_cause_update(self):
        current = copy.deepcopy(manage.specs())
        current[3]['config']['group']['memberNames'].append('team-releases')
        self.assertEqual(repository_plan(self.inventory_client(current), manage.specs()), [])

    def test_roles_have_no_admin_delete_or_wildcards(self):
        reader, publisher = role_specs()
        self.assertEqual(reader['roles'], [])
        self.assertEqual(publisher['roles'], [reader['id']])
        for role in (reader, publisher):
            for privilege in role['privileges']:
                self.assertNotIn('*', privilege)
                self.assertNotIn('admin', privilege)
                self.assertFalse(privilege.endswith('-delete'))
        self.assertEqual(len(reader['privileges']), 2)
        self.assertEqual(len(publisher['privileges']), 8)

    @patch.dict(os.environ, {'NEXUS_ADMIN_USERNAME': 'admin', 'NEXUS_READ_USERNAME': 'same-user',
                            'NEXUS_PUBLISH_USERNAME': 'same-user'}, clear=True)
    def test_reusing_reader_as_publisher_is_refused(self):
        with self.assertRaisesRegex(NexusError, 'separate accounts'):
            manage.user_plan(Mock())

    @patch.dict(os.environ, {'NEXUS_ADMIN_USERNAME': 'admin', 'NEXUS_READ_USERNAME': 'reader',
                            'NEXUS_PUBLISH_USERNAME': 'publisher',
                            'NEXUS_READ_PASSWORD': 'example-test-password-only'}, clear=True)
    def test_existing_administrator_role_on_reader_is_refused(self):
        client = Mock()
        client.json.return_value = [dict(userId='reader', source='default', status='active',
                                        roles=['buy02-maven-reader', 'nx-admin'])]
        with self.assertRaisesRegex(NexusError, 'account takeover is refused'):
            manage.user_plan(client)

    @patch.dict(os.environ, {'NEXUS_ADMIN_USERNAME': 'admin', 'NEXUS_READ_USERNAME': 'reader',
                            'NEXUS_PUBLISH_USERNAME': 'publisher',
                            'NEXUS_READ_PASSWORD': 'example-reader-password',
                            'NEXUS_PUBLISH_PASSWORD': 'example-publisher-password'}, clear=True)
    def test_existing_account_passwords_are_never_reset(self):
        client = Mock()
        client.json.side_effect = [[dict(userId='reader', source='default', status='active', roles=['buy02-maven-reader'])],
                                   [dict(userId='publisher', source='default', status='active', roles=['buy02-maven-publisher'])]]
        with patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(manage.user_plan(client), [])
        self.assertTrue(all(call.args[0] == 'GET' for call in client.json.call_args_list))

    def test_release_paths(self):
        paths = artifact_paths(None, 'maven-releases', 'com.buy-01', 'media', '1.0.1')
        self.assertEqual(paths['jar'], '/repository/maven-releases/com/buy-01/media/1.0.1/media-1.0.1.jar')

    def test_timestamped_snapshot_paths_ignore_sources(self):
        client = Mock()
        xml = b'''<metadata><versioning><snapshotVersions>
          <snapshotVersion><extension>jar</extension><value>1.0.0-20261116.120000-2</value><updated>20261116120000</updated></snapshotVersion>
          <snapshotVersion><extension>pom</extension><value>1.0.0-20261116.120000-2</value></snapshotVersion>
          <snapshotVersion><extension>jar</extension><classifier>sources</classifier><value>bad</value></snapshotVersion>
        </snapshotVersions></versioning></metadata>'''
        client.open.return_value = Response(xml)
        result = artifact_paths(client, 'maven-snapshots', 'com.buy01', 'gateway', '1.0.0-SNAPSHOT')
        self.assertTrue(result['jar'].endswith('/gateway-1.0.0-20261116.120000-2.jar'))

    def test_missing_snapshot_metadata_fails(self):
        client = Mock()
        client.open.return_value = Response(b'<metadata/>')
        with self.assertRaisesRegex(NexusError, 'no unclassified'):
            artifact_paths(client, 'maven-snapshots', 'com.buy01', 'gateway', '1.0.0-SNAPSHOT')

    def test_untrusted_snapshot_path_fails(self):
        client = Mock()
        client.open.return_value = Response(b'<metadata><versioning><snapshotVersions><snapshotVersion><extension>jar</extension><value>../../secret</value></snapshotVersion></snapshotVersions></versioning></metadata>')
        with self.assertRaisesRegex(NexusError, 'Unexpected timestamped'):
            artifact_paths(client, 'maven-snapshots', 'com.buy01', 'gateway', '1.0.0-SNAPSHOT')

    def test_version_validation(self):
        for value in ('1.0.0-SNAPSHOT', '1.0.0', '1.0.1', '0.0.1-SNAPSHOT'):
            self.assertEqual(validate_version(value), value)
        for value in ('LATEST', '../secret', '1.0', '1.0.1;echo secret', '01.0.0'):
            with self.subTest(value=value), self.assertRaises(NexusError):
                validate_version(value)

    @patch('manage.Client')
    def test_failed_publish_does_not_claim_success(self, client):
        with patch('manage.maven', side_effect=NexusError('test failure')), patch('manage.verify_artifact') as verify:
            with self.assertRaisesRegex(NexusError, 'test failure'):
                manage.publish(argparse.Namespace(service='gateway'))
            verify.assert_not_called()

    @patch.dict(os.environ, {'NEXUS_URL': 'http://127.0.0.1:8081/',
                            'NEXUS_READ_USERNAME': 'reader', 'NEXUS_READ_PASSWORD': 'example-test-password',
                            'NEXUS_ADMIN_USERNAME': 'admin', 'NEXUS_ADMIN_PASSWORD': 'example-admin-secret',
                            'MAVEN_BIN': '/usr/bin/mvn'}, clear=True)
    def test_build_subprocess_cannot_inherit_admin_credentials(self):
        with patch('manage.subprocess.run', return_value=Mock(returncode=0)) as run:
            manage.maven('gateway', ['clean', 'verify'])
        env = run.call_args.kwargs['env']
        self.assertNotIn('NEXUS_ADMIN_USERNAME', env)
        self.assertNotIn('NEXUS_ADMIN_PASSWORD', env)
        self.assertEqual(env['NEXUS_URL'], 'http://127.0.0.1:8081')

    @patch('manage.Client')
    def test_existing_release_is_not_uploaded(self, client):
        client.return_value.exists.return_value = True
        with patch('manage.coordinates', return_value=('com.buy01', 'gateway', '1.0.0')), patch('manage.maven') as mvn:
            with self.assertRaisesRegex(NexusError, 'already exists'):
                manage.publish(argparse.Namespace(service='gateway'))
            mvn.assert_not_called()

    def test_successful_upload_requires_matching_download(self):
        publisher, reader = Mock(), Mock()
        publisher.digest.return_value = 'hash-a'
        reader.digest.return_value = 'hash-b'
        with patch('manage.Client', side_effect=[publisher, reader]), self.assertRaisesRegex(NexusError, 'checksums differ'):
            manage.verify_artifact(argparse.Namespace(service='gateway', version='1.0.0', local=False))

    def test_access_checks_never_delete_or_reuse_a_probe_coordinate(self):
        reader, publisher, anonymous = Mock(), Mock(), Mock()
        for client in (reader, publisher, anonymous):
            client.open.side_effect = lambda *args, **kwargs: Response()
        with patch('manage.Client', side_effect=[reader, publisher, anonymous] * 2), patch('sys.stdout', new_callable=io.StringIO):
            manage.verify_access(argparse.Namespace())
            manage.verify_access(argparse.Namespace())
        calls = reader.open.call_args_list + publisher.open.call_args_list + anonymous.open.call_args_list
        self.assertFalse(any(call.args[0] == 'DELETE' for call in calls))
        probes = [call for call in reader.open.call_args_list if call.args[0] == 'PUT']
        self.assertEqual(len(probes), 2)
        self.assertNotEqual(probes[0].args[1], probes[1].args[1])
        for call in probes:
            self.assertEqual(call.kwargs['allowed'], (401, 403))
            artifact = manage.ET.fromstring(call.args[2]).findtext('artifactId')
            self.assertIn('/' + artifact + '/', call.args[1])
            self.assertIn('/maven-snapshots/', call.args[1])

    def test_local_xml_audit(self):
        with patch('sys.stdout', new_callable=io.StringIO):
            manage.audit(argparse.Namespace(java11=False))

    def test_java11_audit_reports_incompatibility(self):
        with patch('sys.stdout', new_callable=io.StringIO), self.assertRaisesRegex(NexusError, 'Java 11 incompatible'):
            manage.audit(argparse.Namespace(java11=True))

    def test_health_requires_writable_endpoint(self):
        # Fake curl uses HTTP paths to fail only the write-readiness endpoint.
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / 'curl'
            stub.write_text('#!/bin/bash\n[[ "$*" != *status/writable* ]]\n')
            stub.chmod(0o755)
            env = dict(os.environ, PATH=tmp + ':' + os.environ['PATH'])
            result = subprocess.run(['bash', str(manage.ROOT / 'nexus/healthcheck.sh')], env=env, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn(b'readiness failed', result.stderr)

    def test_health_succeeds_when_both_endpoints_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / 'curl'
            stub.write_text('#!/bin/bash\nexit 0\n')
            stub.chmod(0o755)
            env = dict(os.environ, PATH=tmp + ':' + os.environ['PATH'])
            result = subprocess.run(['bash', str(manage.ROOT / 'nexus/healthcheck.sh')], env=env, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn(b'ready for reads and writes', result.stdout)


if __name__ == '__main__':
    unittest.main()
