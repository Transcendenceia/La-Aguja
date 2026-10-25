"""Portable Imager settings; values are data, never shell fragments."""
import base64
import configparser
import io
import ipaddress
import json
import re
from pathlib import Path

FLAGS = {'accept_dns': False, 'exit_node_allow_lan_access': False,
         'advertise_exit_node': False, 'shields_up': False,
         'snat_subnet_routes': True, 'forwarding': False}
TEXT = ('exit_node', 'advertise_routes', 'advertise_tags', 'netfilter_mode')
CLOUD_FIELDS = {
    'drive': {'client_id','client_secret','token','scope','root_folder_id','service_account_file'},
    'onedrive': {'client_id','client_secret','token','drive_id','drive_type'},
    'dropbox': {'client_id','client_secret','token'},
    's3': {'provider','access_key_id','secret_access_key','region','endpoint'},
    'sftp': {'host','user','port','pass','key_file','key_file_pass','known_hosts_file'},
    'smb': {'host','user','pass','domain','port'},
    'webdav': {'url','vendor','user','pass','bearer_token'},
}
FILE_FIELDS = {'key_file', 'known_hosts_file', 'service_account_file'}


def literal(value, size=8192):
    if not isinstance(value, str) or len(value.encode()) > size or any(c in value for c in '\0\r\n'):
        raise ValueError('Invalid private profile value')
    return value


def environment(value):
    if not isinstance(value, dict) or len(value) > 128:
        raise ValueError('Invalid custom environment')
    for key, item in value.items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', key):
            raise ValueError('Invalid environment name')
        literal(item, 32768)
    return dict(value)


def validate(data):
    if not isinstance(data, dict) or set(data)-{'wifi_profiles','environment','storage','tailscale'}:
        raise ValueError('Invalid profile extensions')
    result = {}
    if 'wifi_profiles' in data:
        rows = data['wifi_profiles']
        if not isinstance(rows, list) or len(rows) > 16:
            raise ValueError('Invalid Wi-Fi profiles')
        names = set()
        for wifi in rows:
            from config import DEFAULTS, parse
            if not isinstance(wifi, dict) or set(wifi)-{'ssid','password','security','country','hidden'}:
                raise ValueError('Invalid Wi-Fi profile')
            if not wifi.get('ssid') or wifi['ssid'] in names or not isinstance(wifi.get('hidden'), bool):
                raise ValueError('Invalid or duplicate Wi-Fi network')
            names.add(wifi['ssid'])
            values = DEFAULTS | {'wifi_'+key: literal(wifi[key], 64 if key=='password' else 32)
                                 for key in ('ssid','password','security','country')}
            values['wifi_hidden'] = 'yes' if wifi['hidden'] else 'no'
            if any(v != v.strip() for v in values.values()):
                raise ValueError('Wi-Fi values cannot preserve leading/trailing whitespace')
            parse('[aguja]\n'+''.join(k+' = '+v+'\n' for k,v in values.items()))
        if rows: result['wifi_profiles'] = rows
    if data.get('environment'): result['environment'] = environment(data['environment'])
    if 'tailscale' in data:
        value = data['tailscale']
        if not isinstance(value, dict) or set(value)-set(FLAGS)-set(TEXT):
            raise ValueError('Invalid extended tailnet')
        if any(not isinstance(value.get(key, default), bool) for key, default in FLAGS.items()):
            raise ValueError('Invalid extended tailnet switch')
        import tailnet_config
        settings = tailnet_config.validate(value)
        result['tailscale'] = {key:settings[key] for key in (*FLAGS, *TEXT)}
        result['tailscale']['advertise_routes'] = ','.join(route.strip() for route in value.get('advertise_routes','').split(',') if route.strip())
    if 'storage' in data:
        rows = data['storage']
        if not isinstance(rows, list) or len(rows) > 32:
            raise ValueError('Invalid storage profiles')
        names = set()
        for remote in rows:
            if not isinstance(remote, dict) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,63}', remote.get('name','')):
                raise ValueError('Invalid storage name')
            if remote['name'] in names: raise ValueError('Duplicate storage name')
            names.add(remote['name'])
            kind, fields, files = remote.get('type'), remote.get('fields'), remote.get('files',{})
            if kind not in CLOUD_FIELDS or not isinstance(fields,dict) or set(fields)-CLOUD_FIELDS[kind]:
                raise ValueError('Invalid storage fields')
            if not isinstance(files,dict) or set(files)-FILE_FIELDS or set(files)-set(fields):
                raise ValueError('Invalid storage files')
            for key,value in fields.items():
                literal(value,65536)
                if key in FILE_FIELDS and value:
                    raw = base64.b64decode(files.get(key,''), validate=True)
                    if not raw or len(raw)>256*1024: raise ValueError('Invalid portable storage file')
                if key=='token' and value and not isinstance(json.loads(value),dict):
                    raise ValueError('Invalid OAuth token data')
            if kind in ('smb','sftp') and not fields.get('host'):
                raise ValueError('Storage host required')
            if fields.get('port') and (not re.fullmatch(r'\d+', fields['port']) or not 1 <= int(fields['port']) <= 65535):
                raise ValueError('Invalid storage port')
            if kind == 'webdav' and not fields.get('url'):
                raise ValueError('Storage URL required')
            from urllib.parse import urlsplit
            for key in ('url','endpoint'):
                if fields.get(key):
                    url=urlsplit(fields[key])
                    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password:
                        raise ValueError('Invalid storage URL')
            if 'obscured' in remote and not isinstance(remote['obscured'],bool):
                raise ValueError('Invalid storage password format')
        if rows: result['storage'] = rows
    if len(json.dumps(result).encode()) > 768*1024:
        raise ValueError('Profile extensions too large')
    return result


def wifi_keyfiles(rows):
    from config import DEFAULTS, wifi_keyfile
    result = {}
    for index,wifi in enumerate(rows):
        values=DEFAULTS | {'wifi_'+key:wifi[key] for key in ('ssid','password','security','country')}
        values['wifi_hidden']='yes' if wifi['hidden'] else 'no'
        name='aguja-wifi' if index==0 else 'aguja-wifi-'+str(index+1)
        raw=wifi_keyfile(values).replace('id=aguja-wifi\n','id='+name+'\nautoconnect-priority='+str(100-index)+'\n')
        result[name+'.nmconnection']=raw
    return result


def storage_apply(rows, destination):
    """Prepare native rclone settings without contacting any remote."""
    from profile import private_write
    import subprocess
    destination=Path(destination)
    parser=configparser.ConfigParser(interpolation=None)
    parser.optionxform=str
    for remote in rows:
        name=remote['name']; parser[name]={'type':remote['type']}
        for key,value in remote['fields'].items():
            if key in FILE_FIELDS and value:
                target=destination.parent/'files'/(name+'-'+key)
                private_write(target,base64.b64decode(remote['files'][key],validate=True))
                value=str(target)
            elif key in ('pass','key_file_pass') and value and not remote.get('obscured'):
                value=subprocess.run(['rclone','obscure','-'],input=value.encode(),capture_output=True,
                                     check=True,timeout=10).stdout.decode().strip()
            parser[name][key]=value
    out=io.StringIO();parser.write(out);private_write(destination,out.getvalue())


def system_apply(capsule, nm_root='/etc/NetworkManager/system-connections'):
    from profile import private_write
    data=capsule.get('extensions',{})
    for name,raw in wifi_keyfiles(data.get('wifi_profiles',[])).items():
        private_write(Path(nm_root)/name,raw)
    import storage
    import hashlib
    source_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    marker = storage.configuration().parent / 'imager-profile.sha256'
    if marker.is_file() and marker.read_text() == source_hash:
        return  # Preserve newer Desk edits for this same provisioning profile.
    if data.get('storage'):
        import storage
        storage_apply(data['storage'],storage.configuration())
    if data.get('tailscale') and capsule.get('tailscale',{}).get('enabled'):
        import tailnet_config
        settings=tailnet_config.validate(capsule['tailscale'] | data['tailscale'])
        private_write(tailnet_config.location(),json.dumps(settings))
    if data:
        private_write(marker, source_hash)
