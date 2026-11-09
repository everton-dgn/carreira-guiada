"""Normalize private client events without exporting paths, IDs or credentials."""
import hashlib
import json
from pathlib import Path


def content_json(content):
    """Decode the single text result emitted by the fictional MCP server."""
    if not isinstance(content, list) or len(content) != 1 or content[0].get('type') != 'text':
        raise ValueError('Unexpected MCP result shape')
    return json.loads(content[0]['text'])


def normalize(client, phase):
    """Preserve actual calls, final text and completion; never infer missing proof."""
    client = Path(client)
    manifest = json.loads((client / 'executor.json').read_text(encoding='utf-8'))
    gate_path = client / 'isolation-gate.json'
    gate = json.loads(gate_path.read_text(encoding='utf-8')) if gate_path.exists() else {}
    path = client / 'client-events.json'
    events = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    calls, started, other, finals, identity = [], [], [], [], []
    completed = False
    usage = None
    pending = {}
    for event in events:
        params = event.get('params', {})
        method = event.get('method')
        item = params.get('item', {})
        if method == 'thread/started':
            identity.append(params.get('thread', {}).get('id', ''))
        if method == 'turn/completed':
            completed = params.get('turn', {}).get('status') == 'completed' and params.get('turn', {}).get('error') is None
        if method == 'thread/tokenUsage/updated':
            usage = params.get('tokenUsage', {}).get('last')
        if method == 'item/started' and item.get('type') == 'mcpToolCall':
            started.append({'server': item.get('server'), 'tool': item.get('tool')})
        if method == 'item/completed':
            kind = item.get('type')
            if kind == 'mcpToolCall':
                output = (None if item.get('error') or item.get('status') != 'completed'
                          else content_json((item.get('result') or {}).get('content', [])))
                calls.append({'server': item.get('server'), 'tool': item.get('tool'),
                              'status': item.get('status'), 'error': item.get('error'),
                              'input': item.get('arguments'), 'output': output})
            elif kind == 'agentMessage':
                if item.get('phase') == 'final_answer':
                    finals.append(item.get('text', ''))
            elif kind not in ('userMessage', 'reasoning'):
                other.append({'type': kind})
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            identity.append(event.get('session_id', ''))
        if event.get('type') == 'assistant':
            for block in event.get('message', {}).get('content', []):
                if block.get('type') == 'tool_use':
                    name = block.get('name')
                    if name != 'mcp__fictional__lab':
                        other.append({'type': 'tool_use', 'name': name})
                    else:
                        started.append({'server': 'fictional', 'tool': 'lab'})
                        call = {'server': 'fictional', 'tool': 'lab', 'status': 'started',
                                'error': None, 'input': block.get('input'), 'output': None}
                        calls.append(call)
                        pending[block['id']] = call
        if event.get('type') == 'user':
            for block in event.get('message', {}).get('content', []):
                if block.get('type') == 'tool_result' and block.get('tool_use_id') in pending:
                    call = pending.pop(block['tool_use_id'])
                    if block.get('is_error') and isinstance(block.get('content'), str):
                        call.update(status='failed', error=str(block.get('content')), output=None)
                    elif isinstance(block.get('content'), str) and block['content'].startswith('<persisted-output>'):
                        # The client replaced the real result with a preview and a
                        # private path. Do not read it or claim complete exposure.
                        call.update(status='output_not_inlined', error='client_persisted_result', output=None)
                    else:
                        call['output'] = content_json(block['content'])
                        call['status'] = 'completed'
                    # A rejected model action is still a completed tool call.
                    # Its error/block remains in output, not a transport failure.
        if event.get('type') == 'result':
            completed = event.get('subtype') == 'success' and not event.get('is_error')
            if event.get('result'):
                finals.append(event['result'])
            usage = event.get('usage')
    if not identity or not all(identity):
        completed = False
    return {'phase': phase, 'session_key': hashlib.sha256(json.dumps(identity).encode()).hexdigest(),
            'model': manifest['model'], 'effort': manifest['effort'], 'completed': completed,
            'has_final': bool(finals), 'final_text': '\n'.join(finals), 'isolation': gate,
            'client_trace': {'calls': calls, 'started_tools': started, 'other_tool_items': other},
            'usage': usage}
