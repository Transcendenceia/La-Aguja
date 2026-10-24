"""One unprivileged browser opener for browsing, native OAuth and file viewing.

Private redirect files keep URLs out of process arguments. Normal profiles are
in HOME (RAM until an explicit encrypted snapshot); OAuth remains transient.
Chromium remains an explicit alternative.
"""
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ASSETS = Path('/usr/share/aguja/desktop')


def redirect_document(url):
    """A visible same-tab handoff, even when startup navigation is cancelled."""
    target = json.dumps(url).replace('<', '\\u003c')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="referrer" content="no-referrer"><title>LA AGUJA · Open</title>'
            '<style>body{margin:0;background:#090b10;color:#f7f6f1;'
            'font:18px Inter,"Noto Sans",system-ui,sans-serif}'
            'main{max-width:560px;margin:15vh auto;padding:32px}'
            'small{color:#d9afff}h1{font-size:32px}p{color:#9a9da6;line-height:1.6}'
            'a{display:inline-block;background:#f7f6f1;color:#090b10;padding:14px 24px;'
            'border:2px solid #d9afff;border-radius:10px;text-decoration:none}'
            'a:focus-visible{outline:3px solid #ff9dcc;outline-offset:5px}</style>'
            '<body><main><small>LA AGUJA</small><h1 id="title">Opening your destination</h1>'
            '<p id="help">If this page stays open, select Continue.</p>'
            '<a id="continue" rel="noreferrer" href="' + html.escape(url, quote=True) + '">Continue</a>'
            '</main><script>const target=' + target + ';'
            'if(navigator.language.startsWith("es")){document.documentElement.lang="es";'
            'document.getElementById("title").textContent="Abriendo tu destino";'
            'document.getElementById("help").textContent="Si esta página sigue abierta, pulsa Continuar.";'
            'document.getElementById("continue").textContent="Continuar";}'
            # Do not navigate while the HTML parser is still constructing the
            # initial startup document. The real link also works without JS.
            'window.addEventListener("load",()=>setTimeout(()=>location.replace(target),0),{once:true});'
            '</script></body></html>')


def binary(choice=None):
    if choice is None:
        try:
            choice = (Path('/run/user') / str(os.getuid()) / 'aguja-browser').read_text().strip()
        except OSError:
            choice = 'helium'
    names = ('chromium',) if choice == 'chromium' else ('helium-browser', 'helium', 'chromium')
    return next((shutil.which(name) for name in names if shutil.which(name)), None)


def open_browser(url=None, directory=None, choice=None):
    if os.getuid() == 0:
        raise ValueError('The browser runs as the owner, never root')
    executable = binary(choice)
    if not executable or not os.environ.get('DISPLAY'):
        raise ValueError('Open the browser from the local Rescue Desk')
    if directory is None:
        runtime = Path('/run/user') / str(os.getuid())
        runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
        # HOME is RAM in a nonpersistent live. Explicit global snapshots can
        # now retain normal browsing state encrypted, unlike transient OAuth.
        directory = Path.home() / '.local/share/aguja/browser'
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if url:
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'http', 'file') or parsed.username or parsed.password:
            raise ValueError('Use an HTTP(S) address or local file')
        page = directory / 'open.html'
        page.write_text(redirect_document(url))
        page.chmod(0o600)
    else:
        page = ASSETS / 'home.html'
    profile = directory / 'profile'
    profile.mkdir(mode=0o700, exist_ok=True)
    preferences = profile / 'Default' / 'Preferences'
    if not preferences.exists():
        preferences.parent.mkdir(mode=0o700, exist_ok=True)
        preferences.write_text(json.dumps({
            'browser': {'check_default_browser': False, 'has_seen_welcome_page': True},
            'session': {'restore_on_startup': 4, 'startup_urls': [(ASSETS/'home.html').as_uri()]},
            'homepage': (ASSETS/'home.html').as_uri(), 'homepage_is_newtabpage': False,
            'credentials_enable_service': False, 'profile': {'password_manager_enabled': False},
            'download': {'default_directory': str(Path.home()/'Downloads'), 'prompt_for_download': True},
        }))
        preferences.chmod(0o600)
    return subprocess.Popen([
        executable, '--user-data-dir=' + str(profile), '--no-first-run',
        '--no-default-browser-check', '--disable-sync', '--ozone-platform=x11',
        '--password-store=basic', '--force-dark-mode', '--disk-cache-size=33554432',
        '--load-extension=' + str(ASSETS/'browser-theme'),
        '--start-maximized', '--window-size=1180,740', '--window-position=0,0', page.as_uri(),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main(args):
    url = args[0] if args else None
    if os.environ.get('DISPLAY'):
        open_browser(url)
        return 0
    import gui_session
    return gui_session.run('browser', url=url)


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError):
        print('LA AGUJA: open the browser from the local console.', file=sys.stderr)
        raise SystemExit(1)
