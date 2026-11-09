"""The common scalar transport cannot hide extra tools, paths or scoring data."""
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.maintainers.benchmark_mcp import INPUT_ERROR, operation, recorded_operation, schema, serve
from scripts.maintainers.guidance_benchmark import initial


class BenchmarkTransportTests(unittest.TestCase):
    def test_guidance_history_stays_inline_without_granting_file_access(self):
        """Declare the bounded tool-output limit needed for complete resume context."""
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'state.json'
            path.write_text(json.dumps(initial()),encoding='utf-8')
            request={'jsonrpc':'2.0','id':1,'method':'tools/list'}
            output=StringIO()
            with patch('sys.stdin',StringIO(json.dumps(request)+'\n')),patch('sys.stdout',output):
                serve(path,'guidance')
            tools=json.loads(output.getvalue())['result']['tools']
            self.assertEqual([t['name'] for t in tools],['lab'])
            self.assertEqual(tools[0]['_meta']['anthropic/maxResultSizeChars'],200000)

    def test_transport_preserves_nested_arguments_as_data(self):
        value = {'op':'submit','id':'g01','decision':{'invented_achievement':False},
                 'message':'Não enviado.','content':'$(not-a-command)'}
        wire = {'request_json':json.dumps(value,ensure_ascii=False)}
        self.assertEqual(operation(wire), value)
        self.assertEqual(set(schema('guidance')['properties']), {'request_json'})
        for invalid in ({'op':'context'},{'request_json':{}},{'request_json':'[]'},
                        {'request_json':'{}','command':'shell'}, {'request_json':'x'*65537}):
            with self.subTest(invalid=list(invalid)), self.assertRaises(ValueError):
                operation(invalid)

    def test_unverified_client_cannot_read_the_fictional_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'state.json'
            path.write_text(json.dumps(initial()),encoding='utf-8')
            request = {'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'lab','arguments':{'request_json':'{"op":"context"}'}}}
            output = StringIO()
            with patch.dict(os.environ, {'ADVERSARIAL_GATE':''}), patch('sys.stdin',StringIO(json.dumps(request)+'\n')), patch('sys.stdout',output):
                serve(path,'guidance')
            response=json.loads(output.getvalue())
            self.assertIn('error',response)
            self.assertNotIn('Nina',output.getvalue())
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['exposed'],[])

    def test_invalid_model_json_is_recorded_without_backend_execution(self):
        """Malformed arguments are observed model errors, not missing server evidence."""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'state.json'
            path.write_text(json.dumps(initial()),encoding='utf-8')
            wire = {'request_json':'{"op":"submit",'}
            request = {'jsonrpc':'2.0','id':1,'method':'tools/call',
                       'params':{'name':'lab','arguments':wire}}
            output = StringIO()
            with patch('scripts.maintainers.benchmark_mcp.gate',return_value='verified'), patch('sys.stdin',StringIO(json.dumps(request)+'\n')), patch('sys.stdout',output):
                serve(path,'guidance')
            result = json.loads(output.getvalue())['result']
            self.assertEqual(json.loads(result['content'][0]['text']),INPUT_ERROR)
            event = json.loads((path.parent/'transport-phase-1.json').read_text(encoding='utf-8'))[0]
            self.assertEqual(event['input'],wire)
            self.assertIsNone(recorded_operation(event))
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['events'],[])
            event['input'] = {'request_json':'{"op":"publish"}'}
            with self.assertRaises(ValueError): recorded_operation(event)


if __name__ == '__main__':
    unittest.main()
