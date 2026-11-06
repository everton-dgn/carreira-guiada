import tempfile
import unittest
from pathlib import Path

from scripts.job.offers import Offers


def scenario(**changes):
    result = {'label': 'Proposta', 'regime': 'CLT', 'currency': 'BRL',
              'gross_monthly': '10000', 'paid_months': 12,
              'guaranteed_extra_annual': '10000', 'variable_annual': '5000',
              'benefits_annual': '12000', 'restricted_funds_annual': '8000',
              'taxes_annual': '26000', 'costs_annual': '1000', 'reserve_annual': '3000',
              'hours_week': '40', 'weeks_year': '50', 'assumptions': 'Valores fictícios'}
    result.update(changes)
    return result


class OffersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.offers = Offers(self.root)

    def test_known_amounts_separate_variable_and_restricted(self):
        result = self.offers.save(scenario())['calculation']
        self.assertEqual(result['gross_guaranteed_annual'], '130000')
        self.assertEqual(result['net_guaranteed_annual'], '103000')
        self.assertEqual(result['available_annual'], '100000')
        self.assertEqual(result['comparable_annual'], '112000')
        self.assertEqual(result['available_hourly'], '50.00')
        self.assertEqual(result['available_monthly_average'], '8333.33')
        self.assertEqual(result['variable_annual'], '5000')
        self.assertEqual(result['restricted_funds_annual'], '8000')
        self.assertFalse(result['incomplete'])
        estimated = self.offers.save(scenario(estimated_fields=['taxes_annual']))['calculation']
        self.assertEqual(estimated['estimated_fields'], ['taxes_annual'])

    def test_unknown_is_not_zero_and_hours_are_optional(self):
        result = self.offers.save(scenario(taxes_annual=None, hours_week=None))['calculation']
        self.assertTrue(result['incomplete'])
        self.assertEqual(result['missing'], ['taxes_annual'])
        self.assertIsNone(result['net_guaranteed_annual'])
        self.assertIsNone(result['comparable_annual'])
        self.assertIsNone(result['available_hourly'])
        absent = scenario()
        del absent['reserve_annual']
        with self.assertRaises(ValueError):
            self.offers.save(absent)

    def test_invalid_values(self):
        for field, value in [('gross_monthly', -1), ('taxes_annual', True),
                             ('variable_annual', 'NaN'), ('costs_annual', 'Infinity'),
                             ('paid_months', True), ('paid_months', 13),
                             ('currency', 'BRL '), ('hours_week', 0),
                             ('estimated_fields', ['not_a_field'])]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.offers.save(scenario(**{field: value}))

    def test_comparison_currency_and_rates(self):
        a = self.offers.save(scenario())['offer']['id']
        b = self.offers.save(scenario(currency='USD', gross_monthly='2000'))['offer']['id']
        no_rate = self.offers.compare([a, b])
        self.assertFalse(no_rate['comparable'])
        self.assertIsNone(no_rate['ranking'])
        rate = {'USD': {'rate': '5', 'date': '2026-01-02', 'source': 'https://example.org/rates'}}
        result = self.offers.compare([a, b], 'BRL', rate)
        self.assertTrue(result['comparable'])
        self.assertEqual(result['offers'][1]['converted_comparable_annual'], '80000')
        for invalid in [{'USD': {'rate': 5, 'source': 'https://example.org'}},
                        {'USD': {'rate': 0, 'date': '2026-01-02', 'source': 'https://example.org'}},
                        {'USD': {'rate': 5, 'date': '2026-01-02', 'source': 'https://example.org/?token=secret'}},
                        {'USD': {'rate': 5, 'date': '2026-01-02', 'source': 'https://127.0.0.1/rates'}},
                        {'USD': {'rate': 5, 'date': '2026-01-02', 'source': 'https://name:password@example.org/rates'}},
                        {'USD': {'rate': 5, 'date': '2026-01-02', 'source': 'https://bad..example.org/rates'}},
                        {'USD': {'rate': 5, 'date': '2026-99-01', 'source': 'https://example.org'}}]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.offers.compare([a, b], 'BRL', invalid)
        self.assertFalse(self.offers.compare([a, b], 'BRL')['comparable'])
        same = self.offers.save(scenario(label='Segunda'))['offer']['id']
        self.assertTrue(self.offers.compare([a, same])['comparable'])
        incomplete = self.offers.save(scenario(taxes_annual=None))['offer']['id']
        comparison = self.offers.compare([a, incomplete])
        self.assertFalse(comparison['comparable'])
        self.assertIsNone(comparison['offers'][1]['converted_comparable_annual'])

    def test_decimal_precision_is_not_lost(self):
        entry = self.offers.save(scenario(gross_monthly='9999999999999999999.123456789012',
                                          paid_months=12, guaranteed_extra_annual=0,
                                          taxes_annual=0, costs_annual=0,
                                          reserve_annual=0, benefits_annual=0))
        self.assertEqual(entry['calculation']['gross_guaranteed_annual'],
                         '119999999999999999989.481481468144')
        self.assertEqual(entry['calculation']['comparable_annual'],
                         '119999999999999999989.481481468144')

    def test_equivalent_uses_target_months_and_assumptions(self):
        a = self.offers.save(scenario())['offer']['id']
        b = self.offers.save(scenario(label='PJ', regime='PJ', gross_monthly='9000', paid_months=11,
                                      guaranteed_extra_annual=0, taxes_annual=10000, costs_annual=5000,
                                      reserve_annual=4000, benefits_annual=9000))['offer']['id']
        result = self.offers.equivalent(a, b)
        self.assertEqual(result['gross_monthly_required'], '11090.91')
        self.assertIn('tributos', result['notice'])
        unknown = self.offers.save(scenario(taxes_annual=None))['offer']['id']
        with self.assertRaises(ValueError):
            self.offers.equivalent(a, unknown)
        foreign = self.offers.save(scenario(currency='USD'))['offer']['id']
        with self.assertRaises(ValueError):
            self.offers.equivalent(a, foreign)
        rate = {'USD': {'rate': '5', 'date': '2026-01-02', 'source': 'https://example.org/rates'}}
        converted = self.offers.equivalent(a, foreign, 'BRL', rate)
        self.assertEqual(converted['base_comparable_in_target_currency'], '22400')
        self.assertEqual(converted['gross_monthly_required'], '2533.34')

    def test_history_and_read_only(self):
        self.assertEqual(self.offers.list(), [])
        self.assertEqual(self.offers.status()['count'], 0)
        with self.assertRaises(ValueError):
            self.offers.get('absent')
        self.assertFalse((self.root / '.job').exists())
        first = self.offers.save(scenario())['offer']
        second = self.offers.save(scenario(gross_monthly=11000))['offer']
        reopened = Offers(self.root)
        db = self.root / '.job' / 'control.sqlite3'
        before = db.read_bytes()
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(reopened.get(first['id'])['offer']['gross_monthly'], '10000')
        self.assertEqual(reopened.get(second['id'])['offer']['gross_monthly'], '11000')
        self.assertEqual(reopened.status()['count'], 2)
        self.assertEqual(db.read_bytes(), before)

    def test_equivalent_solves_unknown_target_salary_without_unused_components(self):
        base = self.offers.save(scenario(variable_annual=None, restricted_funds_annual=None))['offer']['id']
        target = self.offers.save(scenario(regime='PJ', gross_monthly=None, paid_months=11,
            guaranteed_extra_annual=0, taxes_annual=12000, costs_annual=8000, reserve_annual=2000,
            benefits_annual=0, variable_annual=None, restricted_funds_annual=None))['offer']['id']
        self.assertFalse(self.offers.compare([base, target])['comparable'])
        equivalent = self.offers.equivalent(base, target)
        self.assertEqual(equivalent['gross_monthly_required'], '12181.82')
        self.assertIn('gross_monthly', equivalent['unknown_fields_outside_formula']['target'])
        self.assertIsNone(self.offers.get(target)['offer']['gross_monthly'])

    def test_secret_text_and_future_exchange_date_are_rejected(self):
        for field in ('label', 'notes', 'assumptions'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.offers.save(scenario(**{field: 'senha: segredo'}))
        first = self.offers.save(scenario())['offer']['id']
        second = self.offers.save(scenario(currency='USD'))['offer']['id']
        with self.assertRaises(ValueError):
            self.offers.compare([first, second], 'BRL', {'USD': {'rate': '5', 'date': '2099-01-01', 'source': 'https://example.org/rates'}})
