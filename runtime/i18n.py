"""Shared literal locale catalog and UI translation; never interprets profile data.

Only application-owned source strings are passed to t(). Credentials, commands,
URLs and peer output must not be translated. Unsupported UI languages fall back
explicitly to English; the operating system locale remains independently selected.
"""
import json
import os
from functools import lru_cache
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name('locale-catalog.json').read_text(encoding='utf-8'))
LANGUAGES = tuple(item['value'] for item in CATALOG['languages'])
KEYBOARDS = tuple(item['value'] for item in CATALOG['keyboards'])
KEYBOARD_VARIANTS = {item['value']: tuple(item['variants']) for item in CATALOG['keyboards']}
DEFAULT_LOCALE = dict(CATALOG['default'])


@lru_cache(maxsize=8)
def _system_language(stamp, inherited):
    try:
        return next(line[5:] for line in Path('/etc/default/locale').read_text().splitlines()
                    if line.startswith('LANG=') and line[5:] in LANGUAGES)
    except (OSError, StopIteration):
        return inherited


def ui_language(value=None):
    if value is None:
        # Owner-selected locale wins over forwarded SSH language. Cache file
        # contents but track mtime so profile unlock refreshes an open panel.
        inherited=os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG', 'es')
        try:
            stamp=Path('/etc/default/locale').stat().st_mtime_ns
        except OSError:
            stamp=None
        value=_system_language(stamp, inherited)
    language = str(value).replace('-', '_').split('_')[0].split('.')[0].lower()
    return language if language in ('es', *CATALOG['translations']) else 'en'


def t(source, *, language=None, **values):
    language = ui_language(language)
    message = source if language == 'es' else CATALOG['translations'].get(language, {}).get(source, source)
    return message.format(**values) if values else message


def result_text(value):
    """Translate only monitor-generated metadata, never terminal output/labels."""
    import re
    if value == 'Completado':
        return t('COMPLETADO')
    if value == 'Conexión finalizada · resultado no recibido':
        return t('SIN RESULTADO')
    if isinstance(value,str):
        match=re.fullmatch(r'Interrumpido · (SIG[A-Z0-9]+|[0-9]+)',value)
        if match:
            return t('INTERRUMPIDO')+' · '+match[1]
        match=re.fullmatch(r'Finalizado · código (-?[0-9]+)',value)
        if match:
            return t('FINALIZADO')+' · '+match[1]
        match=re.fullmatch(r'Sondeo Git · carpeta sin repositorio \(código ([0-9]+)\)',value)
        if match:
            return t('SONDEO GIT')+' · '+match[1]
    return value


def event_text(event):
    value=event.get('text','')
    if not isinstance(value,str):
        return value
    if event.get('kind')=='session_start' and value.startswith('Conexión SSH · '):
        return t('SSH CONECTADO · ')+value[len('Conexión SSH · '):]
    if event.get('kind')=='session_end' and value.startswith('SSH finalizado · '):
        return t('SSH DESCONECTADO · ')+result_text(value[len('SSH finalizado · '):])
    for source in ('Túnel conectado · ','Túnel finalizado · ','Consola iniciada · ','Consola finalizada · '):
        if event.get('kind') in ('session_start','session_end') and value.startswith(source):
            return t(source)+result_text(value[len(source):])
    if event.get('kind')=='command_end' and value.startswith('Comando terminado · código '):
        code=value[len('Comando terminado · código '):]
        if code.lstrip('-').isdigit():
            return t('FINALIZADO')+' · '+code
    return value


if __name__ == '__main__':
    # Shell only exports a checked literal. No config is sourced/evaluated.
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == '--system-locale':
        try:
            for line in Path('/etc/default/locale').read_text().splitlines():
                if line.startswith('LANG=') and line[5:] in LANGUAGES:
                    print(line[5:])
                    break
        except OSError:
            pass
