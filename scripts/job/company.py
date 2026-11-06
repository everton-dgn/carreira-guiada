"""Versioned company dossiers, without aggregate employer scores.

Dimensions are identity, management, workload, equipment, salary, culture,
stability, career_growth and consumer_reputation. Observations preserve their
original audience, origin and statistical meaning; unknown is not clean.
"""
import math
from uuid import uuid4
from .research_scope import Revisions, ResearchScopes, fields, text, positive, table_exists
from .due_diligence import _url, _date, _texts

DIMENSIONS = ('identity','management','workload','equipment','salary','culture','stability','career_growth','consumer_reputation')
EDITABLE = ('evidence','salary_observations','contradictions','interview_questions','opportunity_link')


def sequence(value):
    if not isinstance(value, list) or len(value) > 100:
        raise ValueError('Lista inválida.')
    return value


def dimensions(value):
    values = sequence(value)
    if not values or any(type(item) is not str or item not in DIMENSIONS for item in values):
        raise ValueError('Informe os temas que deseja investigar.')
    return list(dict.fromkeys(['identity', *values]))


class CompanyDossiers(Revisions):
    table = 'job_company_dossiers'

    def _validate(self, r):
        fields(r, ('id','version','entity','question','dimensions','message') + EDITABLE)
        text(r['id']); positive(r['version']); text(r['question']); text(r['message'])
        fields(r['entity'], ('name','country','domain','relationship'))
        for k in ('name','country'): text(r['entity'][k])
        if r['entity']['domain'] is not None: _url(r['entity']['domain'])
        if r['entity']['relationship'] not in ('employer','consultancy','end_client'):
            raise ValueError('Relação empresarial inválida.')
        if not sequence(r['dimensions']) or any(d not in DIMENSIONS for d in r['dimensions']):
            raise ValueError('Dimensão desconhecida.')
        ids = set()
        for e in sequence(r['evidence']):
            fields(e, ('id','dimension','nature','statement','url','checked_at','published_at','context','origin_group','limitations','scope_id','scope_version'), ('basis_evidence_ids',))
            for k in ('id','statement','origin_group','scope_id'): text(e[k])
            positive(e['scope_version']); _url(e['url']); _date(e['checked_at'])
            if e['published_at'] is not None: _date(e['published_at'])
            if e['id'] in ids: raise ValueError('Evidência duplicada.')
            ids.add(e['id'])
            if e['dimension'] not in r['dimensions'] or e['nature'] not in ('fact','report','inference'):
                raise ValueError('Evidência inválida.')
            fields(e['context'], ('audience','role','location','period'))
            if e['context']['audience'] not in ('employee','candidate','consumer','employer','unknown'): raise ValueError('Público inválido.')
            for k in ('role','location','period'):
                if e['context'][k] is not None: text(e['context'][k])
            _texts(e['limitations'], 'limitações')
            if e['nature'] != 'inference' and 'basis_evidence_ids' in e: raise ValueError('Base exclusiva de inferência.')
        evidence = {e['id']: e for e in r['evidence']}
        for e in r['evidence']:
            if e['nature'] == 'inference':
                basis = _texts(e.get('basis_evidence_ids'), 'base', 1)
                if any(b not in ids or b == e['id'] or evidence[b]['nature'] == 'inference' for b in basis):
                    raise ValueError('Base de inferência inválida.')
        for s in sequence(r['salary_observations']):
            common = ('evidence_id','kind','currency','period','role','seniority','location','contract','sample_size')
            kind = s.get('kind') if isinstance(s, dict) else None
            extra = ('minimum','maximum') if kind == 'range' else ('metric','value','methodology')
            fields(s, common + extra)
            if kind not in ('range','statistic') or s['evidence_id'] not in ids or evidence[s['evidence_id']]['dimension'] != 'salary':
                raise ValueError('A observação salarial precisa de uma evidência do tema salário.')
            for k in ('currency','period'): text(s[k])
            for k in ('role','seniority','location','contract'):
                if s[k] is not None: text(s[k])
            if s['sample_size'] is not None: positive(s['sample_size'])
            for k in (('minimum','maximum') if kind == 'range' else ('value',)):
                if type(s[k]) not in (int,float) or not math.isfinite(s[k]) or s[k] < 0: raise ValueError('Valor salarial inválido.')
            if kind == 'range' and s['minimum'] > s['maximum']: raise ValueError('Faixa invertida.')
            if kind == 'statistic':
                if s['metric'] not in ('mean','median'): raise ValueError('Estatística inválida.')
                text(s['methodology'])
        for c in sequence(r['contradictions']):
            fields(c, ('evidence_ids','explanation'))
            references = _texts(c['evidence_ids'], 'evidências', 2)
            if len(set(references)) < 2 or set(references) - ids: raise ValueError('Contradição sem base.')
            text(c['explanation'])
        _texts(r['interview_questions'], 'perguntas')
        if r['opportunity_link'] is not None:
            link = r['opportunity_link']
            fields(link, ('opportunity_id','evidence','url'))
            positive(link['opportunity_id']); text(link['evidence']); _url(link['url'])

    def create(self, data):
        fields(data, ('entity','question','dimensions'))
        r = dict(data, dimensions=dimensions(data['dimensions']), id=str(uuid4()), version=1, evidence=[], salary_observations=[], contradictions=[], interview_questions=[], opportunity_link=None, message='Dossiê criado; condições ainda desconhecidas.')
        self._validate(r)
        with self.profile._db(True) as db: return self._save(db, r)

    def revise(self, data):
        fields(data, ('id','expected_version') + EDITABLE, ('dimensions',))
        with self.profile._db(True) as db:
            current = self._current(db, data)
            r = dict(current, **{k: data[k] for k in EDITABLE})
            if 'dimensions' in data:
                r['dimensions'] = dimensions(data['dimensions'])
            r.update(version=current['version'] + 1, message='Dossiê atualizado; consulte as limitações de cada evidência.')
            self._validate(r)
            scopes = ResearchScopes(self.profile.root)
            previous_evidence = {e['id']: e for e in current['evidence']}
            for e in r['evidence']:
                if previous_evidence.get(e['id']) == e:
                    continue  # Preserve history without granting another external consultation.
                result = scopes.check(dict(scope_id=e['scope_id'], expected_version=e['scope_version'], purpose='company_dossier', target={'kind':'company','id':r['id']}, url=e['url']), db=db)
                if not result['allowed']: raise ValueError('Autorização da evidência inválida: ' + result['reason'])
            link = r['opportunity_link']
            if link and (not table_exists(db, 'jobs') or not db.execute('SELECT 1 FROM jobs WHERE id=?', (link['opportunity_id'],)).fetchone()):
                raise ValueError('Oportunidade inexistente.')
            return self._save(db, r)

    def summary(self, identifier):
        r = self.get(identifier)
        if r is None: return None
        groups = {d: [e for e in r['evidence'] if e['dimension'] == d] for d in r['dimensions']}
        unknown = [d for d, es in groups.items() if not any(e['nature'] != 'inference' and (e['context']['audience'] != 'consumer' or d == 'consumer_reputation') for e in es)]
        limitations = ['Ausência de evidência não comprova boas condições.', 'Origens distintas não comprovam independência editorial.', 'Relatos de consumidores não comprovam condições de trabalho.']
        if any(s['sample_size'] is None for s in r['salary_observations']): limitations.append('Há observações salariais sem tamanho de amostra conhecido.')
        if any(s[k] is None for s in r['salary_observations'] for k in ('role','seniority','location','contract')):
            limitations.append('Há observações salariais com contexto incompleto de cargo, nível, localidade ou regime.')
        limitations.extend(l for e in r['evidence'] for l in e['limitations'])
        message = (f"{r['entity']['name']}: há registros em {len(groups) - len(unknown)} tema(s) e faltam evidências pertinentes em {len(unknown)}. "
                   'Ter registros não confirma as condições da empresa; confira fontes, datas e limitações.')
        return dict(r, grouped_evidence=groups, unknown_dimensions=unknown, independent_origin_counts={d:len({e['origin_group'] for e in es if e['nature'] != 'inference'}) for d,es in groups.items()}, limitations=list(dict.fromkeys(limitations)), message=message)
