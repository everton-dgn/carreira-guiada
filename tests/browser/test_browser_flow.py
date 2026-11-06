"""Real managed Chromium, real CLI, fictional loopback destinations only.

Routes map exact .invalid identities to fixed loopback HTTP destinations. Redirects are
returned to Chromium and rechecked, never followed by the Python adapter.
A denying loopback proxy is the backstop for unrouted browser HTTP traffic.
"""
from datetime import datetime, timedelta, timezone
from email.parser import BytesParser
from email.policy import default
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import sqlite3
import threading
import unittest
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_job_process_journey as journey
from playwright.sync_api import Error, sync_playwright

ORIGIN = 'http://portal.example.invalid'


class LocalServices:
    def __init__(self):
        self.submissions = []
        self.replies = []
        self.complements = []
        self.denied = []
        services = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, body, status=200, **headers):
                self.send_response(status)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(body.encode())

            def do_CONNECT(self):
                services.denied.append(self.path)
                self.respond('denied', 403)

            def do_GET(self):
                if self.path.startswith(('http:', 'https:')):
                    target = urlsplit(self.path)
                    if target.scheme != 'http' or target.netloc != f'127.0.0.1:{services.server.server_port}':
                        services.denied.append(self.path)
                        return self.respond('denied', 403)
                    self.path = target.path or '/'
                pages = {
                    '/': '<form method="post" enctype="multipart/form-data" action="/apply"><input name="name"><input type="file" name="cv"><button>Enviar</button></form>',
                    '/receipts': '<p id="receipt">' + ('application-1' if services.submissions else 'none') + '</p>',
                    '/mail': '<p id="empty">empty</p>' if not services.submissions else '<article data-message-id="mail-1"><span id="sender">recruiter@company.invalid</span><p id="message">Confirme disponibilidade</p></article><form method="post" action="/reply"><input name="reply"><button>Responder</button></form>',
                    '/complement': '<form method="post" action="/complement"><input name="availability"><button>Salvar</button></form>',
                }
                if self.path == '/redirect':
                    return self.respond('', 302, Location='https://external.invalid/escaped')
                self.respond(pages.get(self.path, 'missing'), 200 if self.path in pages else 404)

            def do_POST(self):
                if self.path.startswith(('http:', 'https:')):
                    target = urlsplit(self.path)
                    if target.scheme != 'http' or target.netloc != f'127.0.0.1:{services.server.server_port}':
                        services.denied.append(self.path)
                        return self.respond('denied', 403)
                    self.path = target.path or '/'
                body = self.rfile.read(int(self.headers['Content-Length']))
                if self.path == '/apply':
                    message = BytesParser(policy=default).parsebytes(('Content-Type: ' + self.headers['Content-Type'] + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + body)
                    parts = {part.get_param('name', header='content-disposition'): part for part in message.iter_parts()}
                    services.submissions.append({'name': parts['name'].get_payload(decode=True).decode(), 'filename': parts['cv'].get_filename(), 'cv': parts['cv'].get_payload(decode=True)})
                    return self.respond('<p id="receipt">application-1</p>')
                values = parse_qs(body.decode())
                if self.path == '/reply':
                    services.replies.append(values['reply'][0])
                    return self.respond('<p id="receipt">reply-mail-1</p>')
                if self.path == '/complement':
                    services.complements.append(values['availability'][0])
                    return self.respond('<p id="receipt">complement-1</p>')
                self.respond('denied', 403)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)
        if self.thread.is_alive():
            raise AssertionError('Fixture server failed to stop')

    def forward(self, route):
        request = route.request
        parsed = urlsplit(request.url)
        if (parsed.scheme, parsed.netloc) != ('http', 'portal.example.invalid'):
            route.abort('blockedbyclient')
            return
        route.continue_(url=f'http://127.0.0.1:{self.server.server_port}' + (parsed.path or '/'))



class BrowserFlowTests(unittest.TestCase):
    def setUp(self):
        self.services = LocalServices()
        self.addCleanup(self.services.close)
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        self.browser = self.playwright.chromium.launch(
            headless=True, timeout=15000,
            proxy={'server': f'http://127.0.0.1:{self.services.server.server_port}', 'bypass': '<-loopback>'},
            args=['--disable-background-networking', '--disable-quic',
                  '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1',
                  '--force-webrtc-ip-handling-policy=disable_non_proxied_udp'])
        self.addCleanup(self.browser.close)
        self.blocked = []

    def context(self):
        context = self.browser.new_context(service_workers='block', accept_downloads=False)
        context.set_default_timeout(5000)
        def guarded(route):
            parsed = urlsplit(route.request.url)
            if (parsed.scheme, parsed.netloc) != ('http', 'portal.example.invalid'):
                self.blocked.append(route.request.url)
            self.services.forward(route)
        context.route('**/*', guarded)
        context.route_web_socket('**/*', lambda socket: socket.close())
        return context

    def test_network_guard_navigation_fetch_redirect_and_proxy(self):
        with self.context() as context:
            page = context.new_page()
            with self.assertRaises(Error):
                page.goto('https://external.invalid/')
            page.close()
            page = context.new_page()
            page.goto(ORIGIN)
            self.assertEqual(page.evaluate("fetch('https://external.invalid/data').then(() => 'escaped').catch(() => 'blocked')"), 'blocked')
            denied_before = len(self.services.denied)
            with self.assertRaises(Error):
                page.goto(ORIGIN + '/redirect')
            self.assertIn('external.invalid:443', self.services.denied[denied_before:])
            page.close()
            page = context.new_page()
            with self.assertRaises(Error):
                page.goto('https://portal.example.invalid.evil.invalid/')
            self.assertEqual(set(self.blocked), {'https://external.invalid/', 'https://external.invalid/data', 'https://portal.example.invalid.evil.invalid/'})
        # Remove routing in a separate empty context: the proxy itself still denies.
        with self.browser.new_context() as context:
            with self.assertRaises(Error):
                context.new_page().goto('https://external.invalid/', timeout=5000)
        self.assertIn('external.invalid:443', self.services.denied)
        self.assertFalse(self.services.submissions)

    def test_upload_mail_complement_and_next_day_uncertain_resume(self):
        fx = journey.ProcessJourneyTests('test_login_uncertain_submission_resume_and_mail_coverage')
        self.addCleanup(fx.doCleanups)
        fx.setUp()
        fx.network.stop()  # CLI subprocess retains its own offline guard.
        clock = datetime.now(timezone.utc)
        # Inject Workflow's supported clock in the CLI subprocess only, without product edits.
        with (fx.guard / 'sitecustomize.py').open('a') as guard:
            guard.write('\nfrom datetime import datetime\nfrom scripts.job.workflow import Workflow\n_original_init = Workflow.__init__\ndef _test_init(self, root, **kwargs):\n    kwargs["clock"] = lambda: datetime.fromisoformat(os.environ["BROWSER_TEST_CLOCK"])\n    _original_init(self, root, **kwargs)\nWorkflow.__init__ = _test_init\n')
        fx.env['BROWSER_TEST_CLOCK'] = clock.isoformat()
        def check(action):
            return fx.call('action', 'check', action['action_id'], data={'owner': 'chat:simulacao', 'generation': fx.generation})
        def complete(action, receipt, **extra):
            return fx.complete(action, evidence=receipt, checked_at=fx.env['BROWSER_TEST_CLOCK'], **extra)
        def refresh():
            for provider, account, kind in [('chrome', 'portal-a', 'browser'), ('gmail', 'principal', 'mail')]:
                fx.call('capability', data={'kind': kind, 'provider': provider, 'account': account, 'status': 'ready', 'checked_at': fx.env['BROWSER_TEST_CLOCK'], 'evidence': 'Fictional destination observed in managed Chromium'})
        job = fx.vacancy('browser')['opportunity_id']
        pdf = fx.root / fx.resume['paths']['pdf']
        expected_pdf = pdf.read_bytes()
        self.assertTrue(expected_pdf.startswith(b'%PDF'))
        with self.context() as context:
            page = context.new_page()
            page.goto(ORIGIN + '/mail')
            self.assertEqual(page.locator('#empty').inner_text(), 'empty')
            fill = fx.authorize('fill', opportunity_id=job)
            check(fill)
            page.goto(ORIGIN)
            page.locator('[name=name]').fill('Marina Exemplo')
            page.locator('[name=cv]').set_input_files(pdf)
            self.assertEqual(page.locator('[name=name]').input_value(), 'Marina Exemplo')
            self.assertEqual(page.locator('[name=cv]').evaluate('(el) => el.files[0].size'), len(expected_pdf))
            complete(fill, 'Managed Chromium fields and approved PDF selection observed')
            action = fx.authorize('apply', opportunity_id=job)
            check(action)
            page.locator('button').click()
            receipt = page.locator('#receipt').inner_text()
            self.assertEqual(receipt, 'application-1')
            self.assertEqual(self.services.submissions, [{'name': 'Marina Exemplo', 'filename': pdf.name, 'cv': expected_pdf}])
            fx.complete(action, 'uncertain', evidence='Interrupted before receipt reconciliation', evidence_source='agent_report')
            stopped = fx.call('stop')
        clock += timedelta(days=1)
        fx.env['BROWSER_TEST_CLOCK'] = clock.isoformat()
        fx.generation = fx.call('resume-work')['control']['generation']
        self.assertGreater(clock, datetime.fromisoformat(stopped['stopped_at']) + timedelta(hours=23))
        with self.context() as context:
            page = context.new_page()
            page.goto(ORIGIN + '/receipts')
            receipt = page.locator('#receipt').inner_text()
            refresh()
            fx.authorize('apply', opportunity_id=job, success=False)
            complete(action, receipt)
            fx.authorize('apply', opportunity_id=job, success=False)
            read = fx.authorize('email_read', channel={'provider': 'gmail', 'account': 'principal'}, scope_key='browser-inbox')
            check(read)
            page.goto(ORIGIN + '/mail')
            message_id = page.locator('article').get_attribute('data-message-id')
            sender = page.locator('#sender').inner_text()
            content = page.locator('#message').inner_text()
            self.assertEqual((message_id, sender), ('mail-1', 'recruiter@company.invalid'))
            message = fx.call('email', data={'provider': 'gmail', 'account': 'principal', 'message_id': message_id, 'category': 'recruiter_contact', 'received_at': clock.isoformat(), 'summary': content, 'opportunity_id': job, 'link_evidence': receipt, 'step_key': 'browser-reply', 'step_kind': 'email_reply'})
            complete(read, message_id + ': verified fictional sender: ' + content, evidence_source='destination_email')
            text = 'Disponível amanhã'
            args = {'channel': {'provider': 'gmail', 'account': 'principal'}, 'message': fx.ref(message), 'reply': {'recipient': 'message_sender', 'content_sha256': hashlib.sha256(text.encode()).hexdigest(), 'summary': text}}
            reply = fx.authorize('email_reply', **args)
            check(reply)
            page.locator('[name=reply]').fill(text)
            page.locator('button').click()
            reply_receipt = page.locator('#receipt').inner_text()
            self.assertEqual(reply_receipt, 'reply-mail-1')
            complete(reply, reply_receipt, evidence_source='destination_email')
            fx.authorize('email_reply', success=False, **args)
            fx.call('step', data={'job_id': job, 'step_key': 'browser-complement', 'kind': 'form', 'summary': 'Confirmar disponibilidade'})
            complement = fx.authorize('fill', opportunity_id=job, step_key='browser-complement')
            check(complement)
            page.goto(ORIGIN + '/complement')
            page.locator('[name=availability]').fill(text)
            page.locator('button').click()
            observed = page.locator('#receipt').inner_text()
            self.assertEqual(observed, 'complement-1')
            complete(complement, observed)
            steps = fx.call('steps')
            self.assertEqual(next(s for s in steps if s['step_key'] == 'browser-complement')['state'], 'completed')
            self.assertEqual(next(s for s in steps if s['step_key'] == 'browser-reply')['state'], 'completed')
            self.assertEqual(fx.call('status')['ledger']['confirmed'], 1)
            persisted = fx.call('action', 'show', action['action_id'])
            self.assertEqual(persisted['status'], 'confirmed')
            self.assertEqual(persisted['checked_at'], clock.isoformat())
            with sqlite3.connect(fx.root / '.job' / 'control.sqlite3') as database:
                evidence = database.execute('SELECT evidence FROM wf_actions WHERE id=?', (action['action_id'],)).fetchone()[0]
            self.assertEqual(evidence, 'application-1')
            self.assertEqual(self.services.replies, [text])
            self.assertEqual(self.services.complements, [text])
            self.assertEqual(len(self.services.submissions), 1)
