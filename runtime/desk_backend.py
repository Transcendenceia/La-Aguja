"""Private stdin/stdout IPC for the owner desktop. Never log inputs/native errors."""
import configparser
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


def run(argv, **kwargs):
    return subprocess.run(argv, capture_output=True, timeout=kwargs.pop('timeout',30), check=True, **kwargs)


def cloud_parser():
    import storage
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    path = storage.configuration()
    if path.exists(): parser.read_string(path.read_text())
    return parser


def save_cloud(parser):
    import storage
    from profile import private_write
    stream = io.StringIO(); parser.write(stream)
    private_write(storage.configuration(), stream.getvalue())


def cloud_status():
    import storage
    result = storage.status()
    parser = cloud_parser()
    result['remotes'] = [{'name':name,'type':parser[name].get('type','unknown'),
                          'fields':list(parser[name])} for name in parser.sections()]
    return result


CLOUD_FIELDS = {
    'drive': {'client_id','client_secret','token','scope','service_account_file','root_folder_id'},
    'onedrive': {'client_id','client_secret','token','drive_id','drive_type'},
    'dropbox': {'client_id','client_secret','token'},
    's3': {'provider','access_key_id','secret_access_key','region','endpoint'},
    'sftp': {'host','user','port','pass','key_file','key_file_pass','known_hosts_file'},
    'smb': {'host','user','pass','domain','port'},
    'webdav': {'url','vendor','user','pass','bearer_token'},
}


def cloud_save(data):
    kind, name = data['type'], data['name']
    if kind not in CLOUD_FIELDS or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,63}',name):
        raise ValueError('Invalid remote name/type')
    fields = data['fields']
    if not isinstance(fields,dict) or set(fields)-CLOUD_FIELDS[kind]: raise ValueError('Invalid remote fields')
    parser = cloud_parser()
    if parser.has_section(name) and parser[name].get('type') != kind:
        raise ValueError('Use a new name for a different provider')
    if not parser.has_section(name): parser.add_section(name)
    parser[name]['type'] = kind
    for key,value in fields.items():
        if not isinstance(value,str) or len(value)>65536 or '\0' in value or '\n' in value or '\r' in value:
            raise ValueError('Invalid field')
        if not value: continue  # blank fields preserve existing credentials
        if key in ('pass','key_file_pass'):
            value = run(['rclone','obscure','-'],input=value.encode()).stdout.decode().strip()
        if key == 'token':
            if not isinstance(json.loads(value),dict): raise ValueError('Invalid token JSON')
        if key in ('service_account_file','key_file','known_hosts_file'):
            source = Path(value)
            if not source.is_file() or source.stat().st_size > 2*1024**2: raise ValueError('Invalid credential file')
            import storage
            from profile import private_write
            destination = storage.configuration().parent/'files'/(name+'-'+key)
            private_write(destination, source.read_bytes())
            value = str(destination)
        parser[name][key] = value
    save_cloud(parser)
    return {'ok':True, **cloud_status()}


def cloud_import(data):
    source = Path(data['path'])
    if source.is_dir():
        candidates = (source/'rclone.conf',source/'.config/rclone/rclone.conf',source/'config/rclone/rclone.conf')
        source = next((path for path in candidates if path.is_file()), source/'rclone.conf')
    if not source.is_file() or source.stat().st_size > 2*1024**2: raise ValueError('Invalid import file')
    incoming = configparser.ConfigParser(interpolation=None)
    incoming.optionxform = str
    incoming.read_string(source.read_text())
    if not incoming.sections(): raise ValueError('No remotes in configuration')
    parser = cloud_parser()
    for name in incoming.sections():
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,63}',name) or 'type' not in incoming[name]:
            raise ValueError('Invalid remote configuration')
        if not parser.has_section(name): parser.add_section(name)
        for key,value in incoming[name].items():
            if key in ('service_account_file','key_file','known_hosts_file') and value:
                asset=Path(os.path.expanduser(value))
                if not asset.is_absolute():asset=source.parent/asset
                if not asset.is_file() or asset.stat().st_size>2*1024**2:raise ValueError('Missing imported credential file')
                import storage
                from profile import private_write
                destination=storage.configuration().parent/'files'/(name+'-'+key)
                private_write(destination,asset.read_bytes());value=str(destination)
            parser[name][key] = value
    save_cloud(parser)
    return {'ok':True, **cloud_status()}


def cloud_probe(data):
    import storage
    parser = cloud_parser(); name = data['name']
    if name not in parser: raise ValueError('Unknown remote')
    result = run(['rclone','--config',str(storage.configuration()),'lsf',name+':',
                  '--max-depth','1','--contimeout','10s','--timeout','20s'],timeout=35)
    return {'ok':True,'items':result.stdout.decode(errors='replace').splitlines()[:200]}


def cloud_mount(data):
    import storage
    name=data['name'];parser=cloud_parser()
    if name not in parser:raise ValueError('Unknown remote')
    uid=int(os.environ.get('SUDO_UID','0'))
    if not uid:raise ValueError('Owner session required')
    import pwd
    user=pwd.getpwuid(uid)
    import hashlib
    target=Path('/mnt/aguja-remotes')/hashlib.sha256(name.encode()).hexdigest()[:16]
    target.mkdir(mode=0o700,parents=True,exist_ok=True)
    if target.is_symlink():raise ValueError('Invalid mountpoint')
    if subprocess.run(['mountpoint','-q',str(target)],capture_output=True).returncode:
        if any(target.iterdir()):raise ValueError('Mountpoint not empty')
        os.chown(target,uid,user.pw_gid)
        run(['rclone','--config',str(storage.configuration()),'mount',name+':',str(target),
             '--read-only','--allow-other','--default-permissions','--uid',str(uid),'--gid',str(user.pw_gid),
             '--umask','077','--vfs-cache-mode','off','--daemon','--daemon-timeout','20s',
             '--log-level','OFF','--log-file','/dev/null'],timeout=30)
    return {'ok':True,'mountpoint':str(target),'read_only':True}


def cloud_wizard(data):
    """Seed/import native rclone config in an owner-only temporary RAM directory."""
    from profile import private_write
    import storage
    uid = int(os.environ.get('SUDO_UID','0'))
    target = Path(data['path'])
    parent = target.parent
    if uid==0 or parent.is_symlink() or parent.parent!=Path('/tmp') or not parent.name.startswith('aguja-rclone-'):
        raise ValueError('Invalid native wizard directory')
    meta=parent.stat()
    if meta.st_uid!=uid or stat.S_IMODE(meta.st_mode)!=0o700 or target.name!='rclone.conf':
        raise ValueError('Invalid native wizard directory')
    if data.get('import'):
        result = cloud_import({'path':str(target)})
        return result
    path=storage.configuration()
    private_write(target,path.read_bytes() if path.exists() else '')
    os.chown(target,uid,meta.st_gid)
    return {'ok':True}


def volumes():
    result = json.loads(run(['lsblk','-J','-b','-o','PATH,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,PKNAME']).stdout)
    return {'ok':True,'devices':result.get('blockdevices',[])}


def mount_volume(data):
    device = Path(data['device']).resolve()
    if not str(device).startswith('/dev/') or not device.is_block_device(): raise ValueError('Choose a block partition')
    # Protect the actual live disk and its siblings, not just a /dev/sdX guess.
    own=set()
    for target in ('/run/live/medium','/config','/data'):
        mounted=subprocess.run(['findmnt','-nr','-o','SOURCE','--mountpoint',target],capture_output=True,text=True)
        source=mounted.stdout.strip().split('[',1)[0]
        if source.startswith('/dev/'):
            parents=subprocess.run(['lsblk','-s','-nr','-o','PATH',source],capture_output=True,text=True)
            own.update(parents.stdout.split())
    parents=run(['lsblk','-s','-nr','-o','PATH',str(device)]).stdout.decode().split()
    if own.intersection(parents): raise ValueError('The live boot disk is not a target')
    if subprocess.run(['findmnt','-nr','-S',str(device)],capture_output=True).returncode==0:
        raise ValueError('Already mounted: browse its current mountpoint')
    fs=run(['lsblk','-dnro','FSTYPE',str(device)]).stdout.decode().strip()
    writable=data.get('writable') is True
    options=('rw' if writable else 'ro')+',nosuid,nodev,noexec'
    if not writable and fs=='ext4':options+=',noload'
    if not writable and fs=='xfs':options+=',norecovery'
    target=Path('/mnt/aguja-targets')/device.name
    target.mkdir(mode=0o755,parents=True,exist_ok=True)
    if target.is_symlink() or any(target.iterdir()):raise ValueError('Mountpoint not empty')
    run(['mount','-o',options,str(device),str(target)])
    return {'ok':True,'mountpoint':str(target),'read_only':not writable}


def wifi_connect(data):
    from config import DEFAULTS, parse, wifi_keyfile
    from profile import private_write
    import network
    changes={'wifi_ssid':data['ssid'],'wifi_password':data.get('password',''),
             'wifi_security':data.get('security','wpa-psk'),'wifi_hidden':'yes' if data.get('hidden') else 'no'}
    parser=configparser.ConfigParser(interpolation=None);parser['aguja']=DEFAULTS|changes
    content=io.StringIO();parser.write(content);config=parse(content.getvalue())
    private_write('/etc/NetworkManager/system-connections/aguja-wifi.nmconnection',wifi_keyfile(config))
    run(['rfkill','unblock','wifi']);run(['nmcli','radio','wifi','on'])
    run(['nmcli','connection','reload'])
    run(['nmcli','--wait','25','connection','up','id','aguja-wifi'],timeout=35)
    try: persistent=network.save_settings(changes)
    except (OSError,ValueError):persistent=False
    return {'ok':True,'persistent':persistent}


def operation(action,data):
    if action=='update-state':
        import update_jobs as jobs
        return {'ok':True,'job':jobs.status(),'inventory':jobs.cached_inventory()}
    if action=='update-submit':
        import update_jobs as jobs
        return {'ok':True,'job':jobs.submit(data['operation'],data.get('items'),data.get('choices'))}
    if action=='cloud-status':return {'ok':True, **cloud_status()}
    if action=='cloud-save':return cloud_save(data)
    if action=='cloud-import':return cloud_import(data)
    if action=='cloud-probe':return cloud_probe(data)
    if action=='cloud-mount':return cloud_mount(data)
    if action=='cloud-wizard':return cloud_wizard(data)
    if action=='volumes':return volumes()
    if action=='mount-volume':return mount_volume(data)
    if action=='network-status':
        import network
        return {'ok':True,**network.state()}
    if action=='wifi-scan':
        import network
        result=run(['nmcli','-t','-f','SSID,SIGNAL,SECURITY','device','wifi','list','--rescan','yes'])
        return {'ok':True,'networks':[network.fields(line) for line in result.stdout.decode(errors='replace').splitlines()][:100]}
    if action=='wifi-connect':return wifi_connect(data)
    if action=='wifi-save':
        import network
        return {'ok':True,'persistent':network.save_active_wifi()}
    if action=='ssh-password':
        password=data['password']
        if not isinstance(password,str) or not password or any(ch in password for ch in '\0\r\n') or password!=data['confirmation']:
            raise ValueError('Invalid password confirmation')
        run(['chpasswd'],input=('aguja:'+password+'\n').encode())
        import network
        try:persistent=network.save_settings({'ssh_password':password})
        except (OSError,ValueError):persistent=False
        from profile import private_write
        session=network.session();session['ssh_auth_mode']='custom'
        private_write('/run/aguja-session.json',json.dumps(session));Path('/run/aguja-session.json').chmod(0o644)
        return {'ok':True,'persistent':persistent}
    if action=='tailnet-status':
        import tailnet_config
        import tailscale_service
        binary,_=tailscale_service.ensure_binaries()
        return {'ok':True,'preferences':tailnet_config.metadata(),
                'status':tailscale_service.retrieve_status(binary) if binary else {'connected':False}}
    if action=='tailnet-apply':
        import tailnet_config
        return tailnet_config.apply(data)
    if action=='forwarding-status':
        return {'ok':True,'ipv4':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()=='1'}
    raise ValueError('Unknown desktop action')


if __name__=='__main__':
    try:
        if os.geteuid()!=0:raise ValueError('Owner sudo required')
        raw=sys.stdin.buffer.read(2*1024**2+1)
        if len(raw)>2*1024**2:raise ValueError('Oversized request')
        result=operation(sys.argv[1],json.loads(raw or '{}'))
    except (OSError,ValueError,KeyError,TypeError,configparser.Error,subprocess.SubprocessError):
        # Native stderr and parser errors may contain secrets. Never relay them.
        result={'ok':False,'error':'Operation not completed. Check the fields, connectivity and permissions.'}
    print(json.dumps(result,ensure_ascii=False))
    raise SystemExit(0 if result.get('ok') else 1)
