"""Validated, public locale preferences; independent of private auth capsules."""
import json
import os
from pathlib import Path
import subprocess
import sys
from i18n import CATALOG, t
import profile

PREFERENCE = Path('/config/aguja-locale.json')


def select():
    import cockpit
    result = {}
    for key, items in [('language', CATALOG['languages']), ('keyboard', CATALOG['keyboards'])]:
        result[key] = cockpit.option_dialog(t('Idioma y teclado'), [(i['label'], i['value']) for i in items])
        if result[key] is None:
            return None
    variants = next(i['variants'] for i in CATALOG['keyboards'] if i['value'] == result['keyboard'])
    result['variant'] = cockpit.option_dialog(t('Variante del teclado'),
        [(t(CATALOG['variants'][v]), v) for v in variants]) if len(variants) > 1 else variants[0]
    return None if result['variant'] is None else profile.validate_locale(result)


def main(args):
    if args[:1] == ['apply']:
        if len(args) != 4:
            raise ValueError('locale apply idioma teclado variante')
        selection = profile.validate_locale(dict(zip(('language', 'keyboard', 'variant'), args[1:])))
        if os.geteuid() != 0:
            return subprocess.call(['sudo', '-n', '/usr/local/bin/aguja', 'locale', *args])
        # Apply first; don't claim persistence if the effective console map failed.
        profile.apply_locale({'locale': selection}, respect_override=False)
        if os.path.ismount('/config'):
            profile.private_write(PREFERENCE, json.dumps(selection).encode())
            PREFERENCE.chmod(0o644)
            print(t('Idioma y teclado aplicados y guardados para el próximo arranque.'))
        else:
            print(t('Idioma y teclado aplicados en esta sesión; este medio no permite guardarlos.'))
        return 0
    if args:
        raise ValueError('locale [apply idioma teclado variante]')
    selection = select()
    if selection is None:
        return 130
    return main(['apply', *[selection[k] for k in ('language', 'keyboard', 'variant')]])
