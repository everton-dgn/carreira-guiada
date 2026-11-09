"""Client completion and tool results must be observed, never synthesized."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.maintainers.benchmark_trace import normalize


class TraceTests(unittest.TestCase):
    def test_persisted_result_is_not_reconstructed_from_a_private_file(self):
        """A client-truncated result cannot claim the model saw the full output."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'executor.json').write_text(json.dumps({'model':'fixture','effort':'high'}),encoding='utf-8')
            events = [
                {'type':'system','subtype':'init','session_id':'fixture'},
                {'type':'assistant','message':{'content':[{'type':'tool_use','id':'t1','name':'mcp__fictional__lab','input':{'request_json':'{"op":"next_case"}'}}]}},
                {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'t1','content':'<persisted-output>\nFull output saved to: /private/person/result.json\nPreview: incomplete'}]}},
                {'type':'result','subtype':'success','is_error':False,'result':'Parei.'}]
            (root/'client-events.json').write_text(json.dumps(events),encoding='utf-8')
            result=normalize(root,2)
            call=result['client_trace']['calls'][0]
            self.assertEqual(call['status'],'output_not_inlined')
            self.assertEqual(call['error'],'client_persisted_result')
            self.assertIsNone(call['output'])
            self.assertNotIn('/private/person',json.dumps(result))

    def test_claude_result_links_real_tool_id_and_requires_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'executor.json').write_text(json.dumps({'model':'fixture','effort':'high'}),encoding='utf-8')
            events = [
                {'type':'system','subtype':'init','session_id':'fictional-session'},
                {'type':'assistant','message':{'content':[{'type':'tool_use','id':'t1','name':'mcp__fictional__lab','input':{'op':'context'}}]}},
                {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'t1','content':[{'type':'text','text':'{"ok":true}'}]}]}},
                {'type':'result','subtype':'success','is_error':False,'result':'Terminei.'}]
            path=root/'client-events.json'
            path.write_text(json.dumps(events),encoding='utf-8')
            result=normalize(root,1)
            self.assertTrue(result['completed'])
            self.assertTrue(result['has_final'])
            self.assertEqual(result['client_trace']['calls'][0]['output'],{'ok':True})
            self.assertNotIn('fictional-session',json.dumps(result))
            events[-1]['is_error']=True
            path.write_text(json.dumps(events),encoding='utf-8')
            self.assertFalse(normalize(root,1)['completed'])

    def test_rpc_error_string_is_preserved_as_failed_call(self):
        """A provider error must not crash collection or become a completed action."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'executor.json').write_text(json.dumps({'model':'fixture','effort':'high'}),encoding='utf-8')
            events = [
                {'type':'system','subtype':'init','session_id':'fixture'},
                {'type':'assistant','message':{'content':[{'type':'tool_use','id':'t1','name':'mcp__fictional__lab','input':{'request_json':'broken'}}]}},
                {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'t1','content':'JSONDecodeError: laboratory request refused','is_error':True}]}},
                {'type':'result','subtype':'success','is_error':False,'result':'Parei.'}]
            (root/'client-events.json').write_text(json.dumps(events),encoding='utf-8')
            result = normalize(root,1)
            self.assertEqual(result['client_trace']['calls'][0]['status'],'failed')
            self.assertIsNone(result['client_trace']['calls'][0]['output'])
            self.assertIn('JSONDecodeError',result['client_trace']['calls'][0]['error'])

    def test_structured_security_rejection_remains_an_observed_action(self):
        """MCP isError does not erase a blocked attempt recorded by the laboratory."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'executor.json').write_text(json.dumps({'model':'fixture','effort':'high'}),encoding='utf-8')
            blocked={'ok':False,'rejected':True,'blocked':True,'reason':'unauthorized_action'}
            events=[
                {'type':'system','subtype':'init','session_id':'fixture'},
                {'type':'assistant','message':{'content':[{'type':'tool_use','id':'t1','name':'mcp__fictional__lab','input':{'op':'act','action':'send_files'}}]}},
                {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'t1','content':[{'type':'text','text':json.dumps(blocked)}],'is_error':True}]}},
                {'type':'result','subtype':'success','is_error':False,'result':'Parei.'}]
            (root/'client-events.json').write_text(json.dumps(events),encoding='utf-8')
            call=normalize(root,1)['client_trace']['calls'][0]
            self.assertEqual(call['status'],'completed')
            self.assertIsNone(call['error'])
            self.assertEqual(call['output'],blocked)


if __name__ == '__main__':
    unittest.main()
