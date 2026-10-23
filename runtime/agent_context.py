"""Refresh only a managed context pointer, preserving owner instructions."""
from pathlib import Path
import os
import stat
import tempfile

BEGIN = '<!-- LA_AGUJA_CANONICAL_CONTEXT_BEGIN -->'
END = '<!-- LA_AGUJA_CANONICAL_CONTEXT_END -->'
POINTER = BEGIN + '\nRead the current live instructions in /usr/share/aguja/AGENT-CONTEXT.md and /usr/share/aguja/SECRETS.md before using credentials or disk recovery keys. Apply /usr/share/aguja/ODD.md. Canonical instructions are English; answer in the operator requested language or configured live locale. AI requires Internet and an authorized remote provider; no local models are included. First run aguja hardware --json and aguja plan --json; read /usr/share/aguja/MISSIONS.md and /usr/share/aguja/BACKUP.md before planning interventions. Run aguja secrets --json and sudo aguja recovery status --json; metadata only. Preserve the owner instructions elsewhere in this file. Never print, log or publish credential values.\n' + END + '\n'


def ensure(workspace, canonical=Path('/usr/share/aguja/AGENT-CONTEXT.md')):
    workspace = Path(workspace)
    if any(p.is_symlink() for p in (workspace, *workspace.parents)):
        raise ValueError('Unsafe workspace context')
    for name in ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md'):
        target = workspace / name
        if target.is_symlink():
            continue
        if not target.exists():
            with target.open('x', encoding='utf-8') as stream:
                stream.write(canonical.read_text() + '\n\n' + POINTER)
            continue
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'r', encoding='utf-8') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 128 * 1024:
                continue
            try:
                text = stream.read()
            except UnicodeError:
                continue
        if text.count('\n' + BEGIN + '\n') == 1 and text.count('\n' + END) == 1:
            start = text.index(BEGIN)
            end = text.index(END, start) + len(END)
            text = text[:start] + POINTER.rstrip('\n') + text[end:]
        else:
            text += '\n\n' + POINTER
        fd, temporary = tempfile.mkstemp(prefix='.aguja-context-', dir=workspace)
        try:
            os.fchmod(fd, stat.S_IMODE(info.st_mode))
            if os.geteuid() == 0:
                os.fchown(fd, info.st_uid, info.st_gid)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            current = target.lstat()
            if (current.st_ino, current.st_mtime_ns, current.st_size) != (info.st_ino, info.st_mtime_ns, info.st_size):
                continue  # An owner edit raced us: preserve it instead of replacing.
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
