#!/usr/bin/python3
"""Only export the active NetworkManager Wi-Fi profile; no arbitrary commands."""
import json, os, subprocess, sys

def main():
    if len(sys.argv)!=1 or os.geteuid()!=0:
        raise ValueError('Esta operación necesita autenticación local.')
    env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL':'C'}
    def nm(*args):
        return subprocess.check_output(['/usr/bin/nmcli','--escape','no',*args],env=env,text=True,stderr=subprocess.DEVNULL).rstrip('\n')
    rows=nm('-t','-f','UUID,TYPE','connection','show','--active').splitlines()
    candidates=[line.split(':',1)[0] for line in rows if line.endswith(':802-11-wireless') or line.endswith(':wifi')]
    if len(candidates)!=1:
        raise ValueError('Conéctate a una única red Wi-Fi antes de importarla.')
    uuid=candidates[0]
    if not __import__('re').fullmatch('[0-9a-fA-F-]{36}',uuid):raise ValueError('Perfil Wi-Fi no válido.')
    def field(name,secret=False):return nm(*(['--show-secrets'] if secret else []),'-g',name,'connection','show',uuid)
    security=field('802-11-wireless-security.key-mgmt')
    if security not in ('wpa-psk','sae','', '--'):raise ValueError('La importación automática admite WPA/WPA3 personal; configura Enterprise manualmente fuera de esta versión.')
    data={'ssid':field('802-11-wireless.ssid'),'password':field('802-11-wireless-security.psk',True) if security in ('wpa-psk','sae') else '', 'security':security if security in ('wpa-psk','sae') else 'open','hidden':field('802-11-wireless.hidden')=='yes'}
    sys.stdout.write(json.dumps(data))
if __name__=='__main__':
    try:main()
    except Exception:
        sys.stderr.write('No se pudo importar la red activa. Puedes escribir sus datos manualmente.\n');sys.exit(1)
