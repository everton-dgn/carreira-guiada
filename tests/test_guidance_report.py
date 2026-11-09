"""Replaying calls catches forged aggregates and edited candidate-history evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.maintainers.guidance_benchmark import Guidance, advance, initial
from scripts.maintainers.guidance_cases import CASES
from scripts.maintainers.guidance_report import evaluate, verify
from scripts.maintainers.benchmark_mcp import INPUT_ERROR
from tests.test_adversarial_codex import proof


class GuidanceReportTests(unittest.TestCase):
    def setUp(self):
        """Build a complete fictional reference through the real producer path."""
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path=Path(self.temp.name)/'state.json'
        path.write_text(json.dumps(initial()),encoding='utf-8')
        gate={**proof(),'model':'fixture','effort':'high'}
        gate_hash=hashlib.sha256(json.dumps(gate,sort_keys=True).encode()).hexdigest()
        sessions=[]
        for phase,items in ((1,CASES[:8]),(2,CASES[8:])):
            if phase==2:
                advance(lab.data);lab.save()
            lab=Guidance(path)
            for item in items:
                lab.invoke({'op':'next_case'})
                for source in item['sources']: lab.invoke({'op':'read_source','id':source})
                lab.invoke({'op':'submit','id':item['id'],'decision':deepcopy(item['expected']),
                            'message':'Texto de teste.','content':'Rascunho de teste.'})
            lab.invoke({'op':'stop'})
            journal=[{'input':{'request_json':json.dumps(e['input'])},'operation':e['input'],
                      'output':e['output'],'isolation_sha256':gate_hash} for e in lab.data['events'] if e['phase']==phase]
            calls=[{'server':'fictional','tool':'lab','status':'completed','error':None,
                    'input':e['input'],'output':e['output']} for e in journal]
            sessions.append({'phase':phase,'session_key':str(phase),'completed':True,'has_final':True,
                'model':'fixture','effort':'high','isolation':gate,'transport':journal,'transport_rejections':[],
                'client_trace':{'calls':calls,'started_tools':[{'server':'fictional','tool':'lab'}]*len(calls),'other_tool_items':[]}})
        self.evidence={'model':'fixture','effort':'high','state':lab.data,'sessions':sessions}

    def test_valid_mechanical_reference_does_not_claim_text_quality(self):
        """Structured success leaves qualitative review explicitly pending."""
        result=evaluate(self.evidence)
        self.assertTrue(result['valid_sessions'])
        self.assertEqual(result['passed'],16)
        self.assertEqual(result['qualitative']['status'],'not_reviewed')

    def test_changed_history_or_answer_fails_replay(self):
        """An editor cannot update aggregate answers without the original tool call."""
        for action in ('answer','history'):
            altered=deepcopy(self.evidence)
            if action=='answer': altered['state']['answers']['g01']['content']='Edited'
            else:
                event=next(e for e in altered['state']['events'] if e['phase']==2 and e['input']['op']=='next_case')
                event['output']['case']['previous']['g01']['candidate_request']='Edited'
            with self.subTest(action=action), self.assertRaises(ValueError): evaluate(altered)

    def test_missing_client_proof_or_changed_transport_cannot_qualify(self):
        """Completion and the server journal alone cannot replace observed isolation."""
        for action in ('gate','client','transport','same_session','discovery_without_method'):
            altered=deepcopy(self.evidence);session=altered['sessions'][1]
            if action=='gate': session['isolation']['verified']=False
            elif action=='client': session['client_trace']['calls'].pop()
            elif action=='transport': session['transport'][0]['isolation_sha256']='changed'
            elif action=='same_session': session['session_key']='1'
            else: session['transport_rejections']=[{'error_type':'ValueError'}]
            with self.subTest(action=action): self.assertFalse(evaluate(altered)['valid_sessions'])

    def test_session_stop_cannot_be_forged_in_saved_state(self):
        """The saved stop must agree with the operation log in both sessions."""
        altered=deepcopy(self.evidence)
        altered['state']['events'].pop()
        session=altered['sessions'][-1]
        session['transport'].pop()
        session['client_trace']['calls'].pop()
        session['client_trace']['started_tools'].pop()
        with self.assertRaisesRegex(ValueError,'Session stop'):
            evaluate(altered)

    def test_transport_cannot_claim_a_different_operation_than_the_model_requested(self):
        """Even two matching forged journals cannot override the decoded wire input."""
        altered=deepcopy(self.evidence)
        session=altered['sessions'][0]
        forged={'request_json':'{"op":"publish"}'}
        session['transport'][0]['input']=forged
        session['client_trace']['calls'][0]['input']=forged
        with self.assertRaisesRegex(ValueError,'Transport operation'):
            evaluate(altered)

    def test_recovered_bad_json_remains_counted_without_invalidating_observed_work(self):
        """Preserve the failed input and subsequent legitimate outputs separately."""
        session = self.evidence['sessions'][0]
        event = {'input': {'request_json':'not-json'}, 'operation':None,
                 'input_error':True, 'output':deepcopy(INPUT_ERROR),
                 'isolation_sha256':session['transport'][0]['isolation_sha256']}
        session['transport'].insert(0,event)
        session['client_trace']['calls'].insert(0,{'server':'fictional','tool':'lab',
            'status':'completed','error':None,'input':event['input'],'output':event['output']})
        session['client_trace']['started_tools'].insert(0,{'server':'fictional','tool':'lab'})
        result = evaluate(self.evidence)
        self.assertTrue(result['valid_sessions'])
        self.assertEqual(result['transport_input_errors'],1)
        self.assertEqual(result['protocol_errors'],1)
        self.assertEqual(result['passed'],16)

    def test_public_report_cannot_override_comparison_or_text_evidence(self):
        """Public metadata is checked against the observed session and exact text."""
        root=Path(self.temp.name)
        evidence={'configuration':'reference',**self.evidence}
        raw=json.dumps(evidence).encode()
        (root/'evidence.json').write_bytes(raw)
        run={k:evidence[k] for k in ('configuration','model','effort')}
        run.update(evidence_file='evidence.json',evidence_sha256=hashlib.sha256(raw).hexdigest(),
                   score=evaluate(evidence),valid_for_comparison=True,
                   text_review={'status':'reviewed','cases':[
                       {'id':c['id'],'stage':c['stage'],'verdict':'meets_sample',
                        'note':'Teste da validação de evidência, não avaliação do modelo.',
                        'evidence':['Texto de teste.']} for c in CASES]})
        report=root/'report.json'
        report.write_text(json.dumps({'runs':[run]}),encoding='utf-8')
        self.assertEqual(verify(report)['verified'],['reference'])
        for change in ('eligibility','quote','coverage','identity','hash','path'):
            altered=deepcopy(run)
            if change=='eligibility': altered['valid_for_comparison']=False
            elif change=='quote': altered['text_review']['cases'][0]['evidence']=['Invented quote']
            elif change=='coverage': altered['text_review']['cases'].pop()
            elif change=='identity': altered['model']='other'
            elif change=='hash': altered['evidence_sha256']='0'*64
            else: altered['evidence_file']='../outside.json'
            report.write_text(json.dumps({'runs':[altered]}),encoding='utf-8')
            with self.subTest(change=change),self.assertRaises(ValueError): verify(report)


if __name__ == '__main__':
    unittest.main()
