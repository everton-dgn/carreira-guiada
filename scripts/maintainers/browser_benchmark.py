"""Local tool laboratory. This module never starts a model or uses a real account."""
import argparse
from datetime import datetime, timedelta
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import signal
import time

from .bench_candidate import seed


def serve(directory, lifetime):
    from .bench_site import Site
    from .bench_browser import Browser
    from .bench_tools import Tools
    site = Site(directory)
    browser = None
    server = None
    stopping = False
    token = secrets.token_hex(24)
    try:
        browser = Browser(directory, site)
        toolset = Tools(directory, browser, require_session=True)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                nonlocal stopping
                size = int(self.headers.get('Content-Length', 0))
                if self.path not in ('/call', '/shutdown') or self.headers.get('X-Lab-Key') != token or not 0 < size <= 65536:
                    self.send_error(403)
                    return
                try:
                    data = json.loads(self.rfile.read(size))
                    if self.path == '/shutdown':
                        stopping = True
                        output = {'stopping': True}
                    else:
                        calls = data['calls'] if set(data) == {'calls'} else [data]
                        if not isinstance(calls, list) or not 1 <= len(calls) <= 12:
                            raise ValueError('Use no máximo 12 operações por chamada.')
                        result = []
                        for item in calls:
                            result.append(toolset.invoke(item))
                            if not result[-1]['ok']:
                                break
                        output = {'results': result}
                except (ValueError, TypeError, KeyError) as exc:
                    output = {'error': str(exc)}
                raw = json.dumps(output, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = HTTPServer(('127.0.0.1', 0), Handler)
        server.timeout = .5
        connection = directory / 'connection.json'
        connection.write_text(json.dumps({'port': server.server_port, 'key': token}))
        connection.chmod(0o600)
        print(json.dumps({'ready': True, 'port': server.server_port}), flush=True)
        def stop(*args):
            nonlocal stopping
            stopping = True
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        deadline = time.monotonic() + lifetime
        while not stopping and time.monotonic() < deadline:
            server.handle_request()
    finally:
        if server is not None:
            server.server_close()
        if browser is not None:
            browser.close()
            state = json.loads((directory / 'state.json').read_text())
            (directory / f'network-phase-{state["phase"]}.json').write_text(json.dumps({'blocked': browser.blocked, 'proxy_denied': site.state['blocked']}))
        site.close()


def request(connection, data, path='/call'):
    info = json.loads(connection.read_text())
    if type(info['port']) is not int or not 1 <= info['port'] <= 65535:
        raise ValueError('Porta local inválida.')
    conn = http.client.HTTPConnection('127.0.0.1', info['port'], timeout=40)
    try:
        conn.request('POST', path, json.dumps(data), {'Content-Type': 'application/json', 'X-Lab-Key': info['key']})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError(f'Laboratório recusou a chamada: HTTP {response.status}')
        return json.loads(response.read())
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'serve', 'call', 'start-session', 'finish-session', 'shutdown', 'advance', 'score'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--data')
    parser.add_argument('--lifetime', type=int, default=600)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if args.command == 'init':
        directory.mkdir(parents=True, exist_ok=False)
        seed(directory)
        print(json.dumps({'created': True}))
    elif args.command == 'serve':
        if not 1 <= args.lifetime <= 900:
            parser.error('lifetime deve ficar entre 1 e 900 segundos')
        serve(directory, args.lifetime)
    elif args.command == 'call':
        print(json.dumps(request(directory / 'connection.json', json.loads(args.data)), ensure_ascii=False))
    elif args.command in ('start-session', 'finish-session'):
        from .bench_tools import begin_session, finish_session
        result = (begin_session if args.command == 'start-session' else finish_session)(directory)
        print(json.dumps(result))
    elif args.command == 'shutdown':
        print(json.dumps(request(directory / 'connection.json', {}, '/shutdown')))
    elif args.command == 'advance':
        state = json.loads((directory / 'state.json').read_text())
        if state['phase'] != 1:
            raise ValueError('Esta jornada já avançou.')
        state.update(phase=2, clock=(datetime.fromisoformat(state['clock']) + timedelta(days=1)).isoformat())
        (directory / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print(json.dumps({'phase': 2, 'clock': state['clock']}))
    else:
        from .bench_score import score
        print(json.dumps(score(directory), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
