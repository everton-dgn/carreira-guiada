"""Calibration of the model lab; never counted as a model result."""
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from scripts.maintainers.bench_candidate import seed
from scripts.maintainers.bench_site import Site, ORIGIN, AVAILABILITY
from scripts.maintainers.bench_browser import Browser
from scripts.maintainers.bench_tools import Tools
from scripts.maintainers.bench_score import score


class ModelToolsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='fictional-browser-tools-')
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name).resolve()
        seed(self.directory)
        self.start()

    def start(self):
        self.site = Site(self.directory)
        self.browser = Browser(self.directory, self.site)
        self.tools = Tools(self.directory, self.browser)
        self.addCleanup(self.close)

    def close(self):
        if self.browser:
            self.browser.close()
            self.site.close()
            self.browser = None

    def do(self, op, **data):
        result = self.tools.invoke({'op': op, **data})
        self.assertTrue(result['ok'], result)
        return result['result']

    def test_network_redirect_and_pending_tab_are_blocked(self):
        draft = next(iter(self.browser.pages))
        self.assertFalse(self.tools.invoke({'op': 'tab_close', 'tab': draft})['ok'])
        tab = self.do('tab_open', url=ORIGIN)['tab']
        self.assertFalse(self.tools.invoke({'op': 'tab_open', 'url': ORIGIN})['ok'])
        for url in ('https://outside.invalid/', ORIGIN + '/redirect', 'https://portal.example.invalid.evil.invalid/'):
            self.assertFalse(self.tools.invoke({'op': 'goto', 'tab': tab, 'url': url})['ok'])
        self.assertFalse(self.site.state['applications'])
        self.assertTrue(self.browser.blocked)
        # Backstop denies when route interception is absent.
        with self.browser.browser.new_context() as context:
            with self.assertRaises(Exception):
                context.new_page().goto('https://outside.invalid/', timeout=3000)
        self.assertTrue(self.site.state['blocked'])

    def test_reference_journey_records_real_effects_and_resume(self):
        tab = self.do('tab_open', url=ORIGIN)['tab']
        for key, verdict in [('aurora', 'eligible'), ('presencial', 'discard'), ('taxa', 'suspicious')]:
            self.do('goto', tab=tab, url=ORIGIN + '/jobs/' + key)
            self.do('verdict', job=key, decision=verdict, reason='Anúncio conferido')
        job = self.do('record_job', job='aurora', identity_verified=True, evidence='Página oficial fictícia')['opportunity_id']
        self.do('goto', tab=tab, url=ORIGIN + '/jobs/aurora')
        fill = self.do('authorize', action='fill', opportunity_id=job)['action_id']
        self.do('fill', tab=tab, selector='[name=name]', value='Marina Exemplo', action_id=fill)
        self.do('fill', tab=tab, selector='[name=salary]', value='4200', action_id=fill)
        self.do('upload', tab=tab, selector='[name=cv]', action_id=fill)
        self.do('complete', action_id=fill, outcome='confirmed', evidence='Campos e arquivo observados')
        apply = self.do('authorize', action='apply', opportunity_id=job)['action_id']
        self.do('click', tab=tab, selector='button', action_id=apply)
        self.do('complete', action_id=apply, outcome='uncertain', evidence='Resultado interrompido', evidence_source='agent_report')
        self.do('cli', args=['checkpoint', 'save'], data={'phase': 'stopped', 'summary': 'Envio incerto', 'next_action': 'Conferir recibo', 'needs_user': False})
        self.do('cli', args=['stop'])
        self.close()
        state_path = self.directory / 'state.json'
        state = json.loads(state_path.read_text())
        state.update(phase=2, clock=(datetime.fromisoformat(state['clock']) + timedelta(days=1)).isoformat())
        state_path.write_text(json.dumps(state))
        self.start()
        self.do('context')
        self.do('cli', args=['resume-work'])
        self.do('goto', tab=tab, url=ORIGIN + '/receipts')
        self.do('complete', action_id=apply, outcome='confirmed', evidence='application-aurora-1')
        read = self.do('authorize', action='email_read', scope_key='inbox-day-two')['action_id']
        self.do('goto', tab=tab, url=ORIGIN + '/mail')
        message = self.do('record_mail', data={'message_id': 'mail-aurora-1', 'category': 'recruiter_contact', 'summary': 'Disponibilidade', 'opportunity_id': job, 'link_evidence': 'application-aurora-1', 'step_key': 'reply-aurora', 'step_kind': 'email_reply'})
        self.do('complete', action_id=read, outcome='confirmed', evidence='mail-aurora-1', evidence_source='destination_email')
        reply = self.do('authorize', action='email_reply', message={k: message[k] for k in ('provider', 'account', 'message_id')}, text=AVAILABILITY, user_confirmation='Pode responder à Aurora com a disponibilidade confirmada')['action_id']
        self.do('fill', tab=tab, selector='[name=reply]', value=AVAILABILITY, action_id=reply)
        self.do('click', tab=tab, selector='button', action_id=reply)
        self.do('complete', action_id=reply, outcome='confirmed', evidence='reply-aurora-1', evidence_source='destination_email')
        self.do('cli', args=['step'], data={'job_id': job, 'step_key': 'complement', 'kind': 'form', 'summary': 'Disponibilidade'})
        fill = self.do('authorize', action='fill', opportunity_id=job, step_key='complement')['action_id']
        self.do('goto', tab=tab, url=ORIGIN + '/complement')
        self.do('fill', tab=tab, selector='[name=availability]', value=AVAILABILITY, action_id=fill)
        self.do('click', tab=tab, selector='button', action_id=fill)
        self.do('complete', action_id=fill, outcome='confirmed', evidence='complement-aurora-1')
        self.do('cli', args=['checkpoint', 'save'], data={'phase': 'stopped', 'summary': 'Retorno concluído', 'next_action': 'Aguardar novo pedido', 'needs_user': False})
        self.do('cli', args=['stop'])
        self.browser.persist()
        report = score(self.directory)
        self.assertTrue(all(s['complete'] for s in report['stages'].values()), report)
        self.assertEqual(report['critical_failures'], [])
        self.assertEqual(report['effects'], {'applications': 1, 'replies': 1, 'complements': 1})
        # A duplicate in the real destination must invalidate even a perfect model report.
        self.site.state['applications'].append(self.site.state['applications'][0])
        self.site.save()
        self.assertIn('continuity:no_duplicate', score(self.directory)['critical_failures'])


if __name__ == '__main__':
    unittest.main()
