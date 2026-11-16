"""Real curl/TLS fixture tests; no sudo, Nexus service or external network needed."""
import hashlib
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import os
from pathlib import Path
import random
import shlex
import shutil
import socket
import ssl
import subprocess
import tarfile
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[2]
DOWNLOADER = ROOT / 'nexus/download.sh'


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory()
        cls.base = Path(cls.workspace.name)
        cert, key = cls.base / 'cert.pem', cls.base / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-days', '1', '-subj', '/CN=localhost',
                        '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1',
                        '-keyout', str(key), '-out', str(cert)],
                       check=True, capture_output=True)
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            contents = random.Random(17).randbytes(128 * 1024)
            member = tarfile.TarInfo('nexus-fixture/bin/nexus')
            member.size = len(contents)
            archive.addfile(member, io.BytesIO(contents))
        cls.payload = stream.getvalue()
        cls.checksum = hashlib.sha256(cls.payload).hexdigest()
        cls.requests = []
        cls.mode = 'range'

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def do_GET(self):
                range_header = self.headers.get('Range')
                cls.requests.append(range_header)
                mode = cls.mode
                if mode == 'missing':
                    self.send_response(404)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                offset = int(range_header[6:-1]) if range_header else 0
                if range_header and (mode == 'reject-range' or offset >= len(cls.payload)):
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{len(cls.payload)}')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                if mode == 'ignore-range':
                    offset = 0
                body = cls.payload[offset:]
                if mode == 'bad':
                    body = b'x' * len(body)
                resumed = range_header and mode != 'ignore-range'
                self.send_response(206 if resumed else 200)
                if resumed:
                    self.send_header('Content-Range', f'bytes {offset}-{len(cls.payload)-1}/{len(cls.payload)}')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                if mode == 'always-drop' or (mode == 'drop-once' and len(cls.requests) == 1):
                    self.wfile.write(body[:4096])
                    self.wfile.flush()
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                else:
                    self.wfile.write(body)

        class Server(ThreadingHTTPServer):
            daemon_threads = True

            def handle_error(self, request, client_address):
                # Early client disconnects are expected in range-refusal fixtures.
                pass

        cls.server = Server(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.url = f'https://localhost:{cls.server.server_port}/nexus-fixture.tar.gz'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.workspace.cleanup()

    def setUp(self):
        type(self).requests = []
        type(self).mode = 'range'
        self.temp = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.destination = self.folder / 'nexus-fixture.tar.gz'
        self.partial = Path(str(self.destination) + '.part')
        self.source = Path(str(self.destination) + '.source')
        self.bin = self.folder / 'bin'
        self.bin.mkdir()
        sleep = self.bin / 'sleep'
        sleep.write_text('#!/bin/bash\nprintf "%s\\n" "$1" >> "$DOWNLOAD_TEST_SLEEP_LOG"\n')
        sleep.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'],
                        CURL_CA_BUNDLE=str(self.base / 'cert.pem'),
                        NO_PROXY='localhost,127.0.0.1', no_proxy='localhost,127.0.0.1',
                        DOWNLOAD_TEST_SLEEP_LOG=str(self.folder / 'delays'))

    def run_download(self, checksum=None, recovery=None):
        command = ['bash', str(DOWNLOADER), self.url, checksum or self.checksum, str(self.destination)]
        if recovery:
            command.append(str(recovery))
        return subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=30)

    def seed_partial(self, content, url=None):
        self.partial.write_bytes(content)
        self.source.write_text(f'{url or self.url}\n{self.checksum}\n')

    def assert_verified(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertFalse(self.partial.exists())
        with tarfile.open(self.destination) as archive:
            self.assertEqual(archive.getnames(), ['nexus-fixture/bin/nexus'])

    def test_fresh_https_download_is_verified(self):
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, [None])

    def test_valid_partial_uses_real_http_range(self):
        self.seed_partial(self.payload[:8192])
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, ['bytes=8192-'])

    def test_reset_preserves_bytes_and_resumes_next_attempt(self):
        type(self).mode = 'drop-once'
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, [None, 'bytes=4096-'])
        self.assertEqual((self.folder / 'delays').read_text(), '2\n')

    def test_reported_curl_56_is_retried_with_retained_bytes(self):
        type(self).mode = 'drop-once'
        curl = self.bin / 'curl'
        real_curl = shlex.quote(shutil.which('curl'))
        # Preserve real curl's transferred bytes, but normalize its reset code
        # to the exact reported regression (56; some builds return 18 instead).
        curl.write_text(f'#!/bin/bash\n{real_curl} "$@"\nresult=$?\n'
                        'if ((result != 0)); then exit 56; fi\nexit 0\n')
        curl.chmod(0o755)
        result = self.run_download()
        self.assert_verified(result)
        self.assertIn('curl 56', result.stderr)
        self.assertEqual(self.requests, [None, 'bytes=4096-'])

    def test_ignored_range_restarts_only_partial(self):
        type(self).mode = 'ignore-range'
        self.seed_partial(self.payload[:8192])
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, ['bytes=8192-', None])
        rejected = list(self.folder.glob('*.part.rejected.*'))
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].read_bytes(), self.payload[:8192])

    def test_http_416_restarts_only_partial(self):
        type(self).mode = 'reject-range'
        self.seed_partial(self.payload[:8192])
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, ['bytes=8192-', None])

    def test_complete_partial_promotes_without_network(self):
        self.seed_partial(self.payload)
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, [])

    def test_complete_partial_without_metadata_still_reuses_trusted_bytes(self):
        self.partial.write_bytes(self.payload)
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, [])

    def test_verified_cached_archive_is_not_overwritten(self):
        self.destination.write_bytes(self.payload)
        before = self.destination.stat().st_mtime_ns
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, [])
        self.assertEqual(self.destination.stat().st_mtime_ns, before)

    def test_partial_from_different_url_is_not_resumed(self):
        self.seed_partial(b'wrong source', url='https://other.invalid/archive')
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, [None])
        self.assertEqual(next(self.folder.glob('*.part.rejected.*')).read_bytes(), b'wrong source')

    def test_unbound_partial_is_preserved_before_fresh_download(self):
        self.partial.write_bytes(self.payload[:8192])
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, [None])
        self.assertEqual(len(list(self.folder.glob('*.part.rejected.*'))), 1)

    def test_corrupt_partial_fails_hash_then_recovers_fresh(self):
        self.seed_partial(b'x' * 8192)
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests, ['bytes=8192-', None])

    def test_wrong_checksum_never_publishes_a_verified_archive(self):
        result = self.run_download(checksum='0' * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SHA-256 mismatch', result.stderr)
        self.assertFalse(self.destination.exists())
        self.assertTrue(self.partial.exists())

    def test_bad_cached_complete_file_is_preserved_and_replaced(self):
        self.destination.write_bytes(b'corrupt cache')
        self.assert_verified(self.run_download())
        self.assertEqual(next(self.folder.glob('*.tar.gz.rejected.*')).read_bytes(), b'corrupt cache')

    def test_retry_exhaustion_retains_partial_and_next_run_resumes(self):
        type(self).mode = 'always-drop'
        result = self.run_download()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.destination.exists())
        self.assertTrue(self.partial.exists())
        self.assertEqual(self.partial.read_bytes(), self.payload[:self.partial.stat().st_size])
        self.assertEqual((self.folder / 'delays').read_text(), '2\n4\n8\n16\n')
        self.assertEqual(len(self.requests), 5)
        size = self.partial.stat().st_size
        type(self).mode = 'range'
        self.assert_verified(self.run_download())
        self.assertEqual(self.requests[-1], f'bytes={size}-')

    def test_import_existing_partial_preserves_original(self):
        old = self.folder / 'old-partial'
        old.write_bytes(self.payload[:12288])
        self.assert_verified(self.run_download(recovery=old))
        self.assertEqual(self.requests, ['bytes=12288-'])
        self.assertEqual(old.read_bytes(), self.payload[:12288])

    def test_404_does_not_retry_or_create_verified_archive(self):
        type(self).mode = 'missing'
        result = self.run_download()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.requests, [None])
        self.assertFalse(self.destination.exists())
        self.assertFalse((self.folder / 'delays').exists())

    def test_cache_symlink_is_refused_without_touching_target(self):
        target = self.folder / 'existing-data'
        target.write_bytes(b'preserve this')
        self.partial.symlink_to(target)
        result = self.run_download()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), b'preserve this')
        self.assertEqual(self.requests, [])

    def test_concurrent_downloader_is_refused_without_changing_partial(self):
        self.seed_partial(self.payload[:8192])
        with Path(str(self.destination) + '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_download()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Another process', result.stderr)
        self.assertEqual(self.partial.read_bytes(), self.payload[:8192])
        self.assertEqual(self.requests, [])

    def test_plain_http_is_rejected(self):
        result = subprocess.run(['bash', str(DOWNLOADER), 'http://localhost/archive',
                                 self.checksum, str(self.destination)], env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.requests, [])


if __name__ == '__main__':
    unittest.main()
