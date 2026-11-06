"""Comparação privada de propostas com premissas informadas pela pessoa."""
import ipaddress
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_EVEN, localcontext
from functools import wraps
from urllib.parse import urlsplit
from uuid import uuid4

from .profile import Profile
from .resumes import _text

REGIMES = ('CLT', 'PJ', 'MEI', 'cooperado', 'internacional')
AMOUNTS = ('gross_monthly', 'guaranteed_extra_annual', 'variable_annual',
           'benefits_annual', 'restricted_funds_annual', 'taxes_annual',
           'costs_annual', 'reserve_annual')
MATERIAL = AMOUNTS + ('paid_months',)
OPTIONAL = ('hours_week', 'weeks_year')
FIELDS = ('label', 'regime', 'currency') + MATERIAL + OPTIONAL + ('notes', 'assumptions', 'estimated_fields')


def _precision(function):
    @wraps(function)
    def calculate(*args, **kwargs):
        with localcontext() as context:
            context.prec = 80
            context.rounding = ROUND_HALF_EVEN
            return function(*args, **kwargs)
    return calculate


def _number(value, field, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f'{field}: informe um número válido.')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f'{field}: informe um número válido.') from None
    if (not number.is_finite() or number < 0 or (positive and number == 0)
            or number.adjusted() > 18 or number.as_tuple().exponent < -12):
        raise ValueError(f'{field}: informe um número finito e válido.')
    return number


def _currency(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z]{3}', value):
        raise ValueError('Informe a moeda como código de três letras maiúsculas, por exemplo BRL.')
    return value


def _validate(data):
    if not isinstance(data, dict) or set(data) - set(FIELDS):
        raise ValueError('Confira os campos da proposta.')
    for field in ('label', 'regime', 'currency') + MATERIAL:
        if field not in data:
            raise ValueError(f'Informe {field} ou null quando desconhecido.')
    if not isinstance(data['label'], str) or not data['label'].strip() or len(data['label']) > 200:
        raise ValueError('Informe um nome para a proposta.')
    if data['regime'] not in REGIMES:
        raise ValueError('Regime desconhecido.')
    _currency(data['currency'])
    result = dict(data)
    result['label'] = _text(result['label'], 'o nome da proposta', 200)
    for field in AMOUNTS + OPTIONAL:
        if result.get(field) is not None:
            result[field] = str(_number(result[field], field, field in OPTIONAL))
    months = result['paid_months']
    if months is not None and (type(months) is not int or not 1 <= months <= 12):
        raise ValueError('Meses pagos devem ser inteiros entre 1 e 12, ou null.')
    if result.get('hours_week') is not None and Decimal(result['hours_week']) > 168:
        raise ValueError('Horas semanais não podem superar 168.')
    if result.get('weeks_year') is not None and Decimal(result['weeks_year']) > 53:
        raise ValueError('Semanas anuais não podem superar 53.')
    for field in ('notes', 'assumptions'):
        value = result.get(field)
        if value is not None and (not isinstance(value, str) or len(value) > 10000):
            raise ValueError(f'{field}: informe texto ou null.')
        if value:
            result[field] = _text(value, field, 10000)
    estimates = result.get('estimated_fields', [])
    if (not isinstance(estimates, list) or any(not isinstance(k, str) or k not in MATERIAL + OPTIONAL
                                                or result.get(k) is None for k in estimates)
            or len(estimates) != len(set(estimates))):
        raise ValueError('estimated_fields deve listar campos numéricos informados, sem duplicatas.')
    return result


def _sum(*values):
    return sum(values, Decimal(0)) if all(v is not None for v in values) else None


def _str(value):
    return str(value) if value is not None else None


@_precision
def _calculate(offer):
    n = {key: Decimal(offer[key]) if offer.get(key) is not None else None for key in AMOUNTS}
    months = offer['paid_months']
    salary = n['gross_monthly'] * months if n['gross_monthly'] is not None and months is not None else None
    gross = _sum(salary, n['guaranteed_extra_annual'])
    net = _sum(gross, -n['taxes_annual'] if n['taxes_annual'] is not None else None,
               -n['costs_annual'] if n['costs_annual'] is not None else None)
    available = _sum(net, -n['reserve_annual'] if n['reserve_annual'] is not None else None)
    comparable = _sum(available, n['benefits_annual'])
    hours = offer.get('hours_week') and offer.get('weeks_year')
    hourly = available / (Decimal(offer['hours_week']) * Decimal(offer['weeks_year'])) if hours and available is not None else None
    missing = [key for key in MATERIAL if offer.get(key) is None]
    return {'incomplete': bool(missing), 'missing': missing,
            'estimated_fields': offer.get('estimated_fields', []),
            'gross_guaranteed_annual': _str(gross), 'net_guaranteed_annual': _str(net),
            'available_annual': _str(available), 'available_monthly_average': _str((available / 12).quantize(Decimal('0.01')) if available is not None else None),
            'benefits_annual': _str(n['benefits_annual']), 'variable_annual': _str(n['variable_annual']),
            'restricted_funds_annual': _str(n['restricted_funds_annual']),
            'comparable_annual': _str(comparable), 'available_hourly': _str(hourly.quantize(Decimal('0.01')) if hourly is not None else None),
            'rounding': 'Médias mensal e por hora arredondadas a 0,01 unidade, com empate para o par.',
            'formulas': {'gross_guaranteed_annual': 'gross_monthly * paid_months + guaranteed_extra_annual',
                         'net_guaranteed_annual': 'gross_guaranteed_annual - taxes_annual - costs_annual',
                         'available_annual': 'net_guaranteed_annual - reserve_annual',
                         'comparable_annual': 'available_annual + benefits_annual',
                         'available_hourly': 'available_annual / (hours_week * weeks_year)'}}


def _rates(rates, base):
    if rates is None:
        return {}
    if not isinstance(rates, dict):
        raise ValueError('Informe taxas por moeda, com rate, date e source.')
    result = {}
    for currency, entry in rates.items():
        _currency(currency)
        if not isinstance(entry, dict) or set(entry) != {'rate', 'date', 'source'}:
            raise ValueError('Cada taxa exige rate, date e source.')
        rate = _number(entry['rate'], 'rate', True)
        try:
            if not isinstance(entry['date'], str) or date.fromisoformat(entry['date']).isoformat() != entry['date'] or date.fromisoformat(entry['date']) > date.today():
                raise ValueError
            url = urlsplit(entry['source'])
            host = url.hostname
            if (url.scheme != 'https' or not host or '.' not in host or url.username or url.password
                    or url.query or url.fragment or url.port not in (None, 443)
                    or host.lower().endswith(('.localhost', '.local', '.internal'))
                    or len(host) > 253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                                               for label in host.lower().split('.'))):
                raise ValueError
            try:
                ipaddress.ip_address(host)
            except ValueError:
                pass
            else:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise ValueError('Taxa exige data ISO e fonte pública HTTPS sem credenciais ou parâmetros.') from None
        if currency == base and rate != 1:
            raise ValueError('A taxa da moeda base deve ser 1.')
        result[currency] = {'rate': str(rate), 'date': entry['date'], 'source': entry['source']}
    return result


class Offers:
    def __init__(self, root):
        self.profile = Profile(root)

    @staticmethod
    def _read(db):
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='job_offers'").fetchone():
            return []
        row = db.execute('SELECT value FROM job_offers WHERE id=1').fetchone()
        return json.loads(row[0]) if row else []

    def save(self, data):
        offer = _validate(data)
        offer['id'] = uuid4().hex
        with self.profile._db(True) as db:
            entries = self._read(db)
            entries.append(offer)
            db.execute('CREATE TABLE IF NOT EXISTS job_offers (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO job_offers VALUES (1, ?)', (json.dumps(entries, ensure_ascii=False),))
        return {'offer': offer, 'calculation': _calculate(offer)}

    def list(self):
        with self.profile._db() as db:
            return self._read(db)

    def get(self, offer_id):
        for offer in self.list():
            if offer['id'] == offer_id:
                return {'offer': offer, 'calculation': _calculate(offer)}
        raise ValueError('Proposta não encontrada.')

    def status(self):
        offers = self.list()
        return {'count': len(offers), 'offers': [{'id': offer['id'], 'label': offer['label'],
                'incomplete': _calculate(offer)['incomplete'], 'missing': _calculate(offer)['missing']} for offer in offers]}

    @_precision
    def compare(self, ids, base_currency=None, rates=None):
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('Informe uma lista de IDs distintos.')
        entries = [self.get(i) for i in ids]
        currencies = {entry['offer']['currency'] for entry in entries}
        base = _currency(base_currency) if base_currency is not None else (next(iter(currencies)) if len(currencies) == 1 else None)
        if rates is not None and base is None:
            raise ValueError('Informe a moeda base para usar taxas.')
        valid_rates = _rates(rates, base)
        missing_rates = sorted(currency for currency in currencies if currency != base and currency not in valid_rates) if base else sorted(currencies)
        for entry in entries:
            currency = entry['offer']['currency']
            factor = Decimal(1) if currency == base else Decimal(valid_rates[currency]['rate']) if currency in valid_rates else None
            amount = entry['calculation']['comparable_annual']
            entry['converted_comparable_annual'] = _str(Decimal(amount) * factor if factor is not None and amount is not None else None)
        return {'base_currency': base, 'rates': valid_rates, 'missing_rates': missing_rates,
                'comparable': not missing_rates and all(not x['calculation']['incomplete'] for x in entries),
                'offers': entries, 'ranking': None}

    @_precision
    def equivalent(self, base_id, target_id, base_currency=None, rates=None):
        comparison = self.compare([base_id, target_id], base_currency, rates)
        base, target = comparison['offers']
        offer = target['offer']
        target_required = ('paid_months', 'guaranteed_extra_annual', 'taxes_annual', 'costs_annual', 'reserve_annual', 'benefits_annual')
        if comparison['missing_rates'] or base['converted_comparable_annual'] is None or any(offer[key] is None for key in target_required):
            raise ValueError('Complete o caixa e os benefícios da proposta base, os extras, impostos, custos, reserva, benefícios e meses pagos do alvo e as taxas de câmbio. O salário mensal do alvo pode ficar desconhecido.')
        currency = offer['currency']
        factor = Decimal(1) if currency == comparison['base_currency'] else Decimal(comparison['rates'][currency]['rate'])
        base_value = Decimal(base['converted_comparable_annual']) / factor
        extras, taxes, costs, reserve, benefits = (Decimal(offer[k]) for k in ('guaranteed_extra_annual', 'taxes_annual', 'costs_annual', 'reserve_annual', 'benefits_annual'))
        monthly = max(Decimal(0), (base_value - extras + taxes + costs + reserve - benefits) / offer['paid_months'])
        monthly = monthly.quantize(Decimal('0.01'), rounding=ROUND_CEILING)
        return {'currency': currency, 'gross_monthly_required': str(monthly),
                'unknown_fields_outside_formula': {'base': [k for k in base['calculation']['missing'] if k in ('variable_annual', 'restricted_funds_annual')],
                                                  'target': [k for k in target['calculation']['missing'] if k not in target_required]},
                'base_comparable_in_target_currency': str(base_value), 'target_offer': offer,
                'base_offer': base['offer'], 'rates': comparison['rates'],
                'formula': 'ceil_cent(max(0, (base_comparable_in_target_currency - guaranteed_extra_annual + taxes_annual + costs_annual + reserve_annual - benefits_annual) / paid_months))',
                'rounding': 'Bruto mensal arredondado para cima em 0,01 unidade da moeda.',
                'notice': 'Estimativa válida apenas para as premissas informadas. Impostos fixos não modelam progressividade; recalcule os tributos para o novo valor.'}
