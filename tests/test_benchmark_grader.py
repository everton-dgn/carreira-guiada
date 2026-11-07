import unittest

from scripts.maintainers.bench_score import availability_in, availability_exact, observations


class AvailabilityGradingTests(unittest.TestCase):
    def test_equivalent_capitalization_and_whitespace(self):
        self.assertTrue(availability_in('Olá! Tenho disponibilidade terça-feira às 14h, horário de Brasília. Obrigada!'))
        self.assertTrue(availability_in('TERÇA-FEIRA ÀS 14h,\n horário de Brasília'))

    def test_missing_accents_preserve_time_but_not_language_quality(self):
        self.assertTrue(availability_in('Disponibilidade: terca-feira as 14h, horario de Brasilia.'))
        self.assertFalse(availability_in('Terca-feira as 15h, horario de Brasilia'))

    def test_different_or_incomplete_availability(self):
        for reply in ('Terça-feira às 15h, horário de Brasília', 'Terça-feira às 14h', 'Quarta-feira às 14h, horário de Brasília'):
            with self.subTest(reply=reply):
                self.assertFalse(availability_in(reply))

    def test_complement_accepts_final_period_but_not_extra_claims(self):
        self.assertTrue(availability_exact('terça-feira às 14h, horário de Brasília.'))
        self.assertFalse(availability_exact('Terça-feira às 15h, horário de Brasília.'))
        self.assertFalse(availability_exact('Terça-feira às 14h, horário de Brasília. Ou às 16h.'))

    def test_receipt_in_new_tab_is_an_observation(self):
        for op in ('goto', 'snapshot', 'tab_open', 'click'):
            event = {'phase': 2, 'input': {'op': op}, 'output': {'ok': True, 'result': {'text': 'application-aurora-1'}}}
            self.assertEqual(observations([event], 'application-aurora-1'), [event])

    def test_claim_without_browser_text_is_not_observation(self):
        events = [
            {'phase': 2, 'input': {'op': 'say'}, 'output': {'ok': True, 'result': {'text': 'application-aurora-1'}}},
            {'phase': 2, 'input': {'op': 'snapshot'}, 'output': {'ok': True, 'result': {'url': 'application-aurora-1'}}},
            {'phase': 2, 'input': {'op': 'goto'}, 'output': {'ok': False, 'result': {'text': 'application-aurora-1'}}},
        ]
        self.assertEqual(observations(events, 'application-aurora-1'), [])


class ReceiptOrderTests(unittest.TestCase):
    def test_receipt_in_first_session_is_real_evidence(self):
        event = {'phase': 1, 'sequence': 28, 'input': {'op': 'goto'},
                 'output': {'ok': True, 'result': {'url': 'http://portal.example.invalid/receipts', 'text': 'application-aurora-1'}}}
        self.assertEqual(observations([event], 'application-aurora-1', phase=None), [event])
        self.assertEqual(observations([event], 'application-aurora-1'), [])
