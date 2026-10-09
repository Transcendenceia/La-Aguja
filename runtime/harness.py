"""Explicit per-launch permissions; never change the user's sudo/access rights."""
import json
import os
from i18n import t

BINS = {'codex': 'codex', 'claude': 'claude', 'antigravity': 'agy', 'opencode': 'opencode'}
SAFE_INSTRUCTIONS = ('Before each rescue task, show the intended commands, target disks/files and expected '
                     'changes, then ask for explicit confirmation. Do not treat a previous approval as '
                     'approval for a new task. Keep command input, output and result visible. '
                     'Do not include credentials in the transcript. Full sudo remains available after approval.')


def choose_mode(name):
    import cockpit
    return cockpit.option_dialog(name + ' · ' + t('Modo de ejecución'),
        [(t('Seguro · confirmar las tareas'), 'safe'), (t('Inseguro · YOLO, sin confirmaciones'), 'unsafe')],
        t('Seguro es la opción inicial. Conservas sudo y todas las herramientas; cambia cuándo se pide permiso.'))


def invocation(name, mode, extras=()):
    if mode not in ('safe', 'unsafe') or name not in BINS:
        raise ValueError('Modo o arnés no válido')
    # Extra CLI flags must not silently undo the visible mode selection.
    if mode == 'safe' and any(str(arg).startswith(('--dangerously-', '--auto', '--permission-mode',
            '--settings', '--setting-sources', '--disable', '--enable', '--remote', '--ask-for-approval', '--sandbox', '--config', '--mode'))
            or str(arg) in ('-a', '-s', '-c') for arg in extras):
        raise ValueError('Selecciona Inseguro en el diálogo para omitir las confirmaciones')
    binary = BINS[name]
    args, env = [binary], {}
    if name == 'codex' and os.environ.get('TMUX') and os.environ.get('AGUJA_LOCAL_CONSOLE') == '1':
        args += ['--no-alt-screen']
    if mode == 'unsafe':
        args += {'codex': ['--dangerously-bypass-approvals-and-sandbox'],
                 'claude': ['--dangerously-skip-permissions'],
                 'antigravity': ['--dangerously-skip-permissions'], 'opencode': []}[name]
        if name == 'opencode':
            env['OPENCODE_CONFIG_CONTENT'] = json.dumps({'permission': 'allow'})
    elif name == 'codex':
        # This is the pinned rescue CLI policy, not a promise about future versions.
        args += ['--ask-for-approval', 'never', '--sandbox', 'danger-full-access',
                 '--dangerously-bypass-hook-trust',
                 '-c', 'hooks.PreToolUse=[{matcher=".*",hooks=[{type="command",command="/usr/bin/python3 /usr/lib/aguja/approval_hook.py",timeout=600}]}]',
                 '-c', 'developer_instructions=' + json.dumps(SAFE_INSTRUCTIONS)]
    elif name == 'claude':
        settings = {'permissions': {'defaultMode': 'default', 'ask':
            ['Bash', 'Read', 'Edit', 'Write', 'NotebookEdit', 'Skill', 'ToolSearch', 'Glob', 'Grep', 'WebFetch', 'WebSearch', 'Task', 'Agent', 'mcp__*']}}
        args += ['--permission-mode', 'default', '--settings', json.dumps(settings),
                 '--append-system-prompt', SAFE_INSTRUCTIONS]
    elif name == 'antigravity':
        args += ['--mode', 'plan', '--prompt-interactive', SAFE_INSTRUCTIONS]
    else:
        # Explicit catch-all, not OpenCode's permissive default.
        env['OPENCODE_CONFIG_CONTENT'] = json.dumps({'permission': {'*': 'ask'}})
    env['AGUJA_EXECUTION_MODE'] = mode
    return binary, args + list(extras), env


def configure(name, mode, home=None):
    if name != 'antigravity' or mode != 'safe':
        return
    from pathlib import Path
    from profile import private_write
    target = (Path(home) if home else Path.home()) / '.gemini/antigravity-cli/settings.json'
    settings = json.loads(target.read_text()) if target.is_file() else {}
    settings['permissions'] = {'ask': [action+'(*)' for action in
        ('command', 'unsandboxed', 'read_file', 'write_file', 'read_url', 'execute_url', 'mcp')]}
    private_write(target, json.dumps(settings).encode())
