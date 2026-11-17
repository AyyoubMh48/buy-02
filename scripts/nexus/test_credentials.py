"""Credential loader safety checks; use only synthetic test values."""
import os
import io
import contextlib
from unittest.mock import patch
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
