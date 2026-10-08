#!/usr/bin/python3
"""Only export the active NetworkManager Wi-Fi profile; no arbitrary commands."""
import json, os, subprocess, sys

def main():
    if len(sys.argv)!=1 or os.geteuid()!=0:
        raise ValueError('Esta operación necesita autenticación local.')
    env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL':'C'}
    def nm(*args):
        return subprocess.check_output(['/usr/bin/nmcli','--escape','no',*args],env=env,text=True,stderr=subprocess.DEVNULL,timeout=20).rstrip('\n')
    rows=nm('-t','-f','UUID,TYPE','connection','show','--active').splitlines()
    candidates=[line.split(':',1)[0] for line in rows if line.endswith(':802-11-wireless') or line.endswith(':wifi')]
    if len(candidates)!=1:
        raise ValueError('Conéctate a una única red Wi-Fi antes de importarla.')
    uuid=candidates[0]
    if not __import__('re').fullmatch('[0-9a-fA-F-]{36}',uuid):raise ValueError('Perfil Wi-Fi no válido.')
    def field(name,secret=False):return nm(*(['--show-secrets'] if secret else []),'-g',name,'connection','show',uuid)
    security=field('802-11-wireless-security.key-mgmt')
    if security not in ('wpa-psk','sae','', '--'):raise ValueError('La importación automática admite WPA/WPA3 personal; configura Enterprise manualmente fuera de esta versión.')
    ssid=field('802-11-wireless.ssid')
    password=field('802-11-wireless-security.psk',True) if security in ('wpa-psk','sae') else ''
    if not ssid or len(ssid.encode())>32 or '\n' in ssid:
        raise ValueError('El nombre de la red Wi-Fi activa no es válido.')
    if security in ('wpa-psk','sae') and password in ('','--','<hidden>'):
        raise ValueError('NetworkManager no pudo leer la contraseña Wi-Fi. Puede estar en el llavero del usuario; introdúcela manualmente sin cambiar los permisos de la red.')
    data={'ssid':ssid,'password':password, 'security':security if security in ('wpa-psk','sae') else 'open','hidden':field('802-11-wireless.hidden')=='yes'}
    sys.stdout.write(json.dumps(data))
if __name__=='__main__':
    try:main()
    except Exception as error:
        # Only our literal validation messages are public. Never emit nmcli
        # output, a traceback, UUID, SSID or a password on failure.
        message=str(error) if isinstance(error,ValueError) else 'No se pudo consultar NetworkManager. Comprueba que nmcli esté instalado y que el servicio esté activo.'
        sys.stdout.write(json.dumps({'ok':False,'error':message}));sys.exit(1)
