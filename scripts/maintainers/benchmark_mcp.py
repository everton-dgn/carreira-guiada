"""One fixed MCP tool bridging only the executor-selected fictional laboratory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from .adversarial_isolation import valid_gate
from .guidance_benchmark import Guidance


def browser_guide():
    """Keep operation semantics while replacing the historical shell transport."""
    guide = (Path(__file__).resolve().parents[2] / 'docs/BENCHMARK-FERRAMENTAS.md').read_text(encoding='utf-8')
    start = guide.index('Na pasta fornecida')
    end = guide.index('Pode enviar até')
    return guide[:start] + 'Use somente a ferramenta MCP lab. O argumento request_json contém uma string JSON da operação, por exemplo {"op":"context"}. Não use shell nem leia arquivos.\n' + guide[end:]


def gate():
    """Require the observed executor inventory before any task data is exposed."""
    path = os.environ.get('ADVERSARIAL_GATE')
    if not path:
        raise ValueError('Missing executor attestation')
    proof = json.loads(Path(path).read_text(encoding='utf-8'))
    if not valid_gate(proof):
        raise ValueError('Executor not verified')
    return hashlib.sha256(json.dumps(proof, sort_keys=True).encode()).hexdigest()


def schema(kind):
    """Use the same explicit scalar transport on every supported provider."""
    return {'type': 'object', 'properties': {'request_json': {'type': 'string',
            'description': 'String JSON da operação, por exemplo {"op":"context"}. Os outros campos são descritos no guia/contexto.'}},
            'required': ['request_json'], 'additionalProperties': False}


def operation(wire):
    """Decode data only; the string can never select a subprocess or file."""
    if not isinstance(wire, dict) or set(wire) != {'request_json'} or not isinstance(wire['request_json'], str):
        raise ValueError('Use request_json com uma string JSON da operação')
    if len(wire['request_json']) > 65536:
        raise ValueError('Operation too large')
    args = json.loads(wire['request_json'])
    if not isinstance(args, dict):
        raise ValueError('Operation must be an object')
    return args


INPUT_ERROR = {'ok': False, 'input_error': 'invalid_operation',
               'message': 'Use request_json com uma string JSON válida de um objeto de operação.'}


def recorded_operation(event):
    """Verify rejected model input without mistaking it for a server failure."""
    try:
        args = operation(event['input'])
    except (ValueError, TypeError):
        if (event.get('input_error') is True and event.get('operation') is None
                and event.get('output') == INPUT_ERROR):
            return None
        raise ValueError('Unproven input rejection')
    if event.get('input_error') or event.get('operation') != args:
        raise ValueError('Transport operation differs from the client arguments')
    return args


def serve(state, kind):
    """Accept no model-selected paths, subprocesses, credentials or destinations."""
    guidance = Guidance(state) if kind == 'guidance' else None
    journal = state.parent / ('transport-phase-' + str(json.loads(state.read_text(encoding='utf-8')).get('phase', 1)) + '.json')
    if journal.exists():
        raise ValueError('A phase transport journal already exists; preserve the original session')
    events = []
    for line in sys.stdin:
        request = None
        try:
            if len(line) > 131072:
                raise ValueError('RPC message too large')
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError('Invalid MCP request')
            if 'id' not in request:
                continue
            method = request.get('method')
            if method == 'initialize':
                result = {'protocolVersion': request.get('params', {}).get('protocolVersion', '2024-11-05'),
                          'capabilities': {'tools': {}}, 'serverInfo': {'name': 'fictional-career-lab', 'version': '1.0'}}
            elif method == 'tools/list':
                description = ('Laboratório fictício. Passe a operação como string JSON no argumento request_json. ' + ('Use context, next_case, read_source, submit e stop.' if kind == 'guidance' else
                    'Use guide para consultar as operações do navegador e do controle local. Sem shell.'))
                result = {'tools': [{'name': 'lab', 'description': description,
                    'inputSchema': schema(kind)}]}
                if kind == 'guidance':
                    # Resume context must reach the model; a saved-file fallback
                    # is unusable in a client without native file tools.
                    result['tools'][0]['_meta'] = {'anthropic/maxResultSizeChars': 200000}
            elif method == 'tools/call' and request.get('params', {}).get('name') == 'lab':
                attestation = gate()
                wire = request['params'].get('arguments', {})
                try:
                    args = operation(wire)
                except (ValueError, TypeError):
                    args = None
                if args is None:
                    output = dict(INPUT_ERROR)
                elif kind == 'guidance':
                    output = guidance.invoke(args)
                elif kind == 'browser':
                    if args == {'op': 'guide'}:
                        guide = browser_guide()
                        output = {'guide': guide, 'transport': 'Use lab com request_json contendo uma string JSON da operação; não use shell, ./tools ou leitura de arquivos.'}
                    else:
                        from .browser_benchmark import request as call
                        output = call(state.parent / 'connection.json', args)
                else:
                    output = {'error': 'Este recorte pede resposta direta sem ferramentas.'}
                events.append({'seq': len(events) + 1, 'input': wire, 'operation': args, 'output': output, 'isolation_sha256': attestation})
                if args is None:
                    events[-1]['input_error'] = True
                journal.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding='utf-8')
                result = {'content': [{'type': 'text', 'text': json.dumps(output, ensure_ascii=False)}]}
            elif method == 'ping':
                result = {}
            elif method in ('resources/list', 'resources/templates/list', 'prompts/list'):
                key = {'resources/list': 'resources', 'resources/templates/list': 'resourceTemplates',
                       'prompts/list': 'prompts'}[method]
                result = {key: []}
            else:
                raise ValueError('Unsupported method')
            response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
        except (KeyError, ValueError, TypeError, OSError) as exc:
            rejection_path = state.parent / ('transport-rejections-' + str(json.loads(state.read_text(encoding='utf-8')).get('phase', 1)) + '.json')
            rejections = json.loads(rejection_path.read_text(encoding='utf-8')) if rejection_path.exists() else []
            rejections.append({'request_sha256': hashlib.sha256(line.encode()).hexdigest(), 'error_type': type(exc).__name__,
                               'method': request.get('method') if isinstance(request, dict) else None})
            rejection_path.write_text(json.dumps(rejections), encoding='utf-8')
            response = {'jsonrpc': '2.0', 'id': request.get('id') if isinstance(request, dict) else None,
                        'error': {'code': -32602, 'message': type(exc).__name__ + ': laboratory request refused'}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


def main():
    """Select a lab in host configuration; never accept selection from the model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('serve',))
    parser.add_argument('--kind', choices=('guidance', 'browser', 'preparation'), required=True)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    serve(args.state.resolve(), args.kind)


if __name__ == '__main__':
    main()
