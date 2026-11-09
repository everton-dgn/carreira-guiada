"""Restrict a PolyHive-launched Claude-compatible client to one fictional MCP.

The caller supplies a private executor.json before launch. No provider secrets
are accepted as arguments or copied into evidence. The authenticated client
still accesses its provider; this restricts model tools, not the entire process.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
from scripts.maintainers.adversarial_codex import dump, system_instructions

BUILTIN_AGENTS = {'claude', 'Explore', 'general-purpose', 'Plan', 'statusline-setup'}
BUILTIN_PLUGINS = {'cc-plugin-agents-md', 'cc-plugin-privacy', 'cc-plugin-plugin-authoring'}


def arguments(manifest, client):
    """Build an allowlisted launch without inheriting SDK settings or tools."""
    kind = manifest.get('laboratory_kind', 'adversarial')
    if kind not in ('adversarial', 'browser', 'preparation', 'guidance'):
        raise ValueError('Unknown fictional laboratory')
    if manifest['effort'] not in ('low', 'medium', 'high', 'xhigh', 'max'):
        raise ValueError('Unsupported effort for this client')
    module = 'adversarial_lab' if kind == 'adversarial' else 'benchmark_mcp'
    args = ['-m', 'scripts.maintainers.' + module, 'serve', '--state', manifest['state']]
    if kind != 'adversarial':
        args += ['--kind', kind]
    mcp = {'mcpServers': {'fictional': {'type': 'stdio', 'command': manifest['python'],
        'args': args, 'env': {'PYTHONPATH': manifest['root'],
                            'ADVERSARIAL_GATE': str(client / 'isolation-gate.json')}}}}
    settings = {'disableAllHooks': True, 'autoMemoryEnabled': False,
                'enabledPlugins': {name + '@builtin': False for name in BUILTIN_PLUGINS}}
    return ['--print', '--input-format', 'stream-json', '--output-format', 'stream-json',
            '--verbose', '--include-partial-messages', '--permission-prompt-tool', 'stdio',
            '--permission-mode', 'bypassPermissions', '--model', manifest['model'],
            '--effort', manifest['effort'], '--tools', '', '--setting-sources', '',
            '--disable-slash-commands',
            '--strict-mcp-config', '--mcp-config', json.dumps(mcp),
            '--settings', json.dumps(settings), '--system-prompt', system_instructions(manifest)]


def attest(event, manifest):
    """Reject any initialization with extra tools, servers or a different model."""
    if event.get('type') != 'system' or event.get('subtype') != 'init':
        raise ValueError('Missing initialization event')
    if event.get('tools') != ['mcp__fictional__lab']:
        raise ValueError('Unexpected tools')
    servers = event.get('mcp_servers')
    if not isinstance(servers, list) or len(servers) != 1:
        raise ValueError('Unexpected server inventory')
    if servers[0].get('name') != 'fictional' or servers[0].get('status') != 'connected':
        raise ValueError('Fictional server unavailable')
    if event.get('model') != manifest['model']:
        raise ValueError('Effective model differs from requested model')
    # The init packet lists built-in definitions even when the Agent/Skill
    # tools are absent. They cannot be invoked through the sole MCP tool.
    plugins = event.get('plugins', [])
    if (event.get('skills') or not set(event.get('agents', [])).issubset(BUILTIN_AGENTS)
            or any(not isinstance(p, dict) or p.get('path') != 'builtin'
                   or p.get('name') not in BUILTIN_PLUGINS for p in plugins)):
        raise ValueError('Unexpected customization')
    return {'verified': True, 'kind': 'claude-restricted-v2',
            'tools': ['mcp__fictional__lab'],
            'servers': [{'name': 'fictional', 'status': 'connected', 'source': 'dynamic'}],
            'model': event['model'], 'effort': manifest['effort'],
            'effort_observation': 'explicit_cli_argument',
            'setting_sources': [], 'native_tools': [], 'strict_mcp': True,
            'hooks_disabled': True, 'memory_disabled': True, 'system_prompt_replaced': True,
            'builtin_definitions_not_callable': True,
            'instruction_directories_denied': True,
            'client_version': manifest['client_version']}


def main():
    """Proxy the client, attest initialization and terminate owned children."""
    binary = os.environ.get('BENCHMARK_CLAUDE_BINARY', 'claude')
    if sys.argv[1:] in (['--version'], ['-v'], ['--help']):
        os.execvp(binary, [binary, *sys.argv[1:]])
    client = Path.cwd().resolve()
    manifest = json.loads((client / 'executor.json').read_text(encoding='utf-8'))
    seconds = manifest.get('session_seconds', 300)
    if type(seconds) is not int or not 60 <= seconds <= 900:
        raise ValueError('Invalid deadline')
    env = dict(os.environ)
    env.update(CLAUDE_CODE_DISABLE_AUTO_MEMORY='1', CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
    # The SDK's original argv is intentionally discarded. Only this fixed launch
    # may select tools/settings; provider authentication remains in the environment.
    if sys.platform != 'darwin':
        raise ValueError('The instruction-file boundary requires macOS')
    config_dir = Path(env.get('CLAUDE_CONFIG_DIR', str(Path.home() / '.claude')))
    denied = {str(p / name) for p in (client, *client.parents, config_dir, Path.home() / '.claude')
              for name in ('CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md')}
    seatbelt = '(version 1)(allow default)' + ''.join(
        '(deny file-read-data (literal ' + json.dumps(p) + '))' for p in sorted(denied))
    for base in {config_dir, Path.home() / '.claude', client / '.claude'}:
        for name in ('agents', 'rules', 'skills', 'plugins'):
            seatbelt += '(deny file-read* (subpath ' + json.dumps(str(base / name)) + '))'
    child = subprocess.Popen(['/usr/bin/sandbox-exec', '-p', seatbelt,
                              binary, *arguments(manifest, client)], env=env,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    timer = threading.Timer(seconds + 30, child.terminate)
    timer.start()
    events = []

    def forward_input():
        try:
            for line in sys.stdin.buffer:
                child.stdin.write(line)
                child.stdin.flush()
        except (BrokenPipeError, ValueError):
            pass

    threading.Thread(target=forward_input, daemon=True).start()
    try:
        for line in child.stdout:
            event = json.loads(line)
            # Completed assistant/user events contain the full tool inputs and
            # outputs. Rewriting the entire log for every token causes quadratic
            # disk traffic; partial deltas still reach the orchestrator below.
            if event.get('type') != 'stream_event':
                events.append(event)
                dump(client / 'client-events.json', events)
            if event.get('type') == 'system' and event.get('subtype') == 'init':
                dump(client / 'isolation-gate.json', attest(event, manifest))
            if event.get('type') == 'assistant':
                for block in event.get('message', {}).get('content', []):
                    if block.get('type') == 'tool_use' and block.get('name') != 'mcp__fictional__lab':
                        raise ValueError('Tool call outside the laboratory')
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
    except Exception as exc:
        dump(client / 'adapter-error.json', {'error_type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        timer.cancel()
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


if __name__ == '__main__':
    main()
