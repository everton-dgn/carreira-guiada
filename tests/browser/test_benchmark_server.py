"""Exercise the authenticated server lifecycle using only fictional services."""
import json
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import unittest

from scripts.maintainers.bench_candidate import seed
from scripts.maintainers.bench_tools import begin_session, finish_session, session_path
from scripts.maintainers.browser_benchmark import request


class BenchmarkServerTests(unittest.TestCase):
    def test_deadline_stops_batch_and_authenticated_shutdown_closes_server(self):
        with tempfile.TemporaryDirectory(prefix='fictional-server-') as tmp:
            directory = Path(tmp).resolve()
            seed(directory)
            command = [sys.executable, '-m', 'scripts.maintainers.browser_benchmark',
                       'serve', '--directory', str(directory), '--lifetime', '30']
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as server:
                try:
                    self.assertTrue(select.select([server.stdout], [], [], 20)[0], 'Server readiness deadline')
                    self.assertTrue(json.loads(server.stdout.readline())['ready'])
                    connection = directory / 'connection.json'
                    call = {'op': 'say', 'message': 'Dado fictício'}
                    self.assertFalse(request(connection, call)['results'][0]['ok'])
                    begin_session(directory)
                    self.assertTrue(request(connection, call)['results'][0]['ok'])
                    path = session_path(directory)
                    timing = json.loads(path.read_text())
                    timing['deadline'] = timing['started_at'] - 1
                    path.write_text(json.dumps(timing))
                    result = request(connection, {'calls': [call, call]})
                    self.assertEqual(len(result['results']), 1)
                    self.assertTrue(result['results'][0]['outside_session_deadline'])
                    self.assertTrue(finish_session(directory)['timed_out'])
                    wrong = directory / 'wrong-connection.json'
                    wrong.write_text(json.dumps({**json.loads(connection.read_text()), 'key': 'wrong-fictional-key'}))
                    with self.assertRaisesRegex(ValueError, '403'):
                        request(wrong, {}, '/shutdown')
                    self.assertIsNone(server.poll())
                    self.assertTrue(request(connection, {}, '/shutdown')['stopping'])
                    self.assertEqual(server.wait(timeout=10), 0)
                finally:
                    if server.poll() is None:
                        server.terminate()
                        try:
                            server.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            server.kill()
                            server.wait(timeout=5)
