"""Credential loader safety checks; use only synthetic test values."""
import os
import io
import contextlib
from unittest.mock import Mock, patch
from types import SimpleNamespace
import setup_credentials
from pathlib import Path
import shlex
import tempfile
import unittest

from nexus_api import NexusError
from setup_credentials import load_private


class CredentialTests(unittest.TestCase):
    def test_shell_metacharacters_are_data_and_never_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.env'
            value = 'quote\' $(exit 99); spaces'
            values = {'NEXUS_URL': 'http://127.0.0.1:18081'}
            for prefix in ('NEXUS_ADMIN', 'NEXUS_READ', 'NEXUS_PUBLISH'):
                values[prefix + '_USERNAME'] = prefix.lower()
                values[prefix + '_PASSWORD'] = value
            path.write_text(''.join(k + '=' + shlex.quote(v) + '\n' for k, v in values.items()))
            path.chmod(0o600)
            self.assertEqual(load_private(path), values)

    def test_rejects_readable_by_others_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.env'
            path.touch(mode=0o644)
            path.chmod(0o644)
            with self.assertRaises(NexusError):
                load_private(path)
            link = Path(directory) / 'link'
            link.symlink_to(path)
            with self.assertRaises(OSError):
                load_private(link)

    def test_rejects_unexpected_environment_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.env'
            path.write_text('LD_PRELOAD=untrusted\n')
            path.chmod(0o600)
            with self.assertRaises(NexusError):
                load_private(path)


    def test_bootstrap_keeps_generated_and_chosen_passwords_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.env'
            answers = ['admin', 'chosen-admin-secret', 'reader', 'chosen-reader-secret',
                       'reader@example.invalid', 'publisher', 'chosen-publisher-secret', 'publisher@example.invalid']
            output = io.StringIO()
            with patch('sys.argv', ['setup', '--bootstrap', '--file', str(path)]), \
                 patch('sys.stdin.isatty', return_value=True), \
                 patch('sys.stderr.isatty', return_value=True), \
                 patch('setup_credentials.hidden', side_effect=answers), \
                 patch('setup_credentials.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout='generated-initial-secret')), \
                 patch('setup_credentials.Client') as client, contextlib.redirect_stdout(output):
                self.assertEqual(setup_credentials.main(), 0)
            self.assertEqual(load_private(path)['NEXUS_ADMIN_PASSWORD'], 'chosen-admin-secret')
            for secret in ('chosen-admin-secret', 'chosen-reader-secret', 'chosen-publisher-secret', 'generated-initial-secret'):
                self.assertNotIn(secret, output.getvalue())
            client.return_value.open.assert_called_once()

    def test_existing_file_refused_before_bootstrap_or_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.env'
            path.write_text('existing-private-content')
            with patch('sys.argv', ['setup', '--bootstrap', '--file', str(path)]), \
                 patch('setup_credentials.subprocess.run') as run, \
                 patch('setup_credentials.hidden') as prompt, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(setup_credentials.main(), 1)
            run.assert_not_called()
            prompt.assert_not_called()
            self.assertEqual(path.read_text(), 'existing-private-content')

    def repair_fixture(self, directory, reader='short', publisher='valid-publisher-password'):
        path = Path(directory) / 'private.env'
        values = {'NEXUS_URL': 'http://127.0.0.1:18081'}
        for prefix, user, password in [('NEXUS_ADMIN', 'admin', 'valid-admin-password'),
                                       ('NEXUS_READ', 'reader', reader),
                                       ('NEXUS_PUBLISH', 'publisher', publisher)]:
            values[prefix + '_USERNAME'] = user
            values[prefix + '_PASSWORD'] = password
        path.write_text(''.join(k + '=' + shlex.quote(v) + '\n' for k, v in values.items()))
        path.chmod(0o600)
        return path, values

    def test_repair_validates_confirmation_and_preserves_other_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path, values = self.repair_fixture(directory)
            before = path.read_text().splitlines()
            output = io.StringIO()
            with patch('sys.stdin.isatty', return_value=True), patch('sys.stderr.isatty', return_value=True), \
                 patch('setup_credentials.Client') as client, \
                 patch('setup_credentials.getpass.getpass', side_effect=['bad', 'valid-reader-password', 'mismatch',
                                                                          'valid-reader-password', 'valid-reader-password']), \
                 contextlib.redirect_stdout(output):
                client.return_value.json.return_value = []
                repaired = setup_credentials.repair_service_passwords(path, values)
            self.assertEqual(repaired['NEXUS_READ_PASSWORD'], 'valid-reader-password')
            for key in values.keys() - {'NEXUS_READ_PASSWORD'}:
                self.assertEqual(repaired[key], values[key])
            self.assertEqual([line for line in before if not line.startswith('NEXUS_READ_PASSWORD=')],
                             [line for line in path.read_text().splitlines() if not line.startswith('NEXUS_READ_PASSWORD=')])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('valid-reader-password', output.getvalue())
            client.return_value.json.assert_called_once_with('GET', '/security/users')

    def test_repair_does_not_change_existing_accounts_or_valid_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path, values = self.repair_fixture(directory)
            original = path.read_bytes()
            with patch('sys.stdin.isatty', return_value=True), patch('sys.stderr.isatty', return_value=True), \
                 patch('setup_credentials.Client') as client, \
                 patch('setup_credentials.getpass.getpass') as prompt, contextlib.redirect_stdout(io.StringIO()):
                client.return_value.json.return_value = [{'userId': 'reader', 'source': 'default'}]
                setup_credentials.repair_service_passwords(path, values)
            prompt.assert_not_called()
            self.assertEqual(path.read_bytes(), original)

    def test_cancelling_repair_leaves_original_file_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path, values = self.repair_fixture(directory, publisher='short')
            original = path.read_bytes()
            with patch('sys.stdin.isatty', return_value=True), patch('sys.stderr.isatty', return_value=True), \
                 patch('setup_credentials.Client') as client, \
                 patch('setup_credentials.getpass.getpass', side_effect=['', KeyboardInterrupt]):
                client.return_value.json.return_value = []
                with self.assertRaises(KeyboardInterrupt):
                    setup_credentials.repair_service_passwords(path, values)
            self.assertEqual(path.read_bytes(), original)

    def test_snapshot_inventory_uses_base_version_for_all_six_services(self):
        from urllib.parse import parse_qs, urlsplit
        import manage
        client = Mock()
        # Stored timestamped versions differ from the requested base version.
        client.json.return_value = {'items': [{'version': '0.0.1-20261117.132126-2'}]}
        with contextlib.redirect_stdout(io.StringIO()) as output:
            setup_credentials.verify_snapshot_inventory(client)
        self.assertEqual(client.json.call_count, 6)
        for service, call in zip(manage.SERVICES, client.json.call_args_list):
            group, artifact, version = manage.coordinates(service)
            self.assertEqual(call.args[0], 'GET')
            self.assertEqual(parse_qs(urlsplit(call.args[1]).query),
                             {'repository': ['maven-snapshots'], 'maven.groupId': [group],
                              'maven.artifactId': [artifact], 'maven.baseVersion': [version]})
        self.assertEqual(output.getvalue().count('PASS published component:'), 6)

    def test_snapshot_inventory_fails_if_component_is_missing(self):
        client = Mock()
        client.json.return_value = {'items': []}
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaisesRegex(NexusError, 'inventory verification failed'):
                setup_credentials.verify_snapshot_inventory(client)
        self.assertNotIn('PASS', output.getvalue())
