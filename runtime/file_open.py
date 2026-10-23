"""Explicit owner file opening. Never execute a selected script or binary."""
import os
from pathlib import Path
import subprocess
import sys


def terminal(argv, title='LA AGUJA · Files'):
    return subprocess.Popen(['xterm','-T',title,'-fa','DejaVu Sans Mono','-fs','12',
                             '-bg','#090b10','-fg','#f7f6f1','-cr','#ff9dcc',
                             '-geometry','120x34','-e',*argv],
                            env=dict(os.environ,YAZI_CONFIG_HOME='/usr/share/aguja/desktop/yazi'),
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def open_file(path):
    path=Path(path).absolute()
    if path.is_dir(): return terminal(['yazi',str(path)])
    if not path.is_file(): raise ValueError('Choose a regular file')
    result=subprocess.run(['file','--brief','--mime-type','--',str(path)],capture_output=True,text=True,check=True)
    kind=result.stdout.strip()
    if kind.startswith('image/'): argv=['feh','--auto-zoom','--scale-down','--',str(path)]
    elif kind=='application/pdf': argv=['zathura',str(path)]
    elif kind.startswith(('audio/','video/')): argv=['mpv','--',str(path)]
    elif kind.startswith('text/') or kind in ('application/json','application/xml','application/x-shellscript','application/javascript'):
        argv=['mousepad','--',str(path)]
    elif kind in ('application/zip','application/x-tar','application/x-7z-compressed','application/gzip','application/x-xz'):
        return terminal(['yazi',str(path)])
    else:
        return terminal(['sh','-c','xxd -- "$1" | less','aguja-file',str(path)],'LA AGUJA · Hex preview · read only')
    return subprocess.Popen(argv,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


if __name__=='__main__':
    try:
        for path in sys.argv[1:]:open_file(path)
    except (OSError,ValueError,subprocess.SubprocessError):
        print('LA AGUJA: file cannot be opened with the available viewers.',file=sys.stderr)
        raise SystemExit(1)
