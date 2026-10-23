"""Live tailnet preferences from the local Desk; LUKS persistence or RAM only."""
import ipaddress
import json
from pathlib import Path
import re
import subprocess

FLAGS = {'ssh': False, 'accept_routes': False, 'accept_dns': False,
         'exit_node_allow_lan_access': False, 'advertise_exit_node': False,
         'shields_up': False, 'snat_subnet_routes': True}
TEXT = ('login_server','hostname','exit_node','advertise_routes','advertise_tags','netfilter_mode')


def location():
    from profile_vault import private_root
    return (private_root() or Path('/run/aguja-storage'))/'tailnet'/'preferences.json'


def validate(data):
    from profile import endpoint, text
    if not isinstance(data, dict) or set(data)-set(FLAGS)-set(TEXT)-{'enabled','auth_key','auth_key_file','forwarding'}:
        raise ValueError('Unknown tailnet preference')
    result = {'enabled': bool(data.get('enabled', True))}
    for key, default in FLAGS.items():
        value = data.get(key, default)
        if not isinstance(value, bool): raise ValueError('Invalid tailnet switch')
        result[key] = value
    for key in TEXT:
        result[key] = text(data.get(key, ''), 2048)
    if result['login_server']:
        endpoint(result['login_server'])
        if not result['login_server'].startswith('https://'): raise ValueError('HTTPS login server required')
    if result['hostname'] and not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', result['hostname']):
        raise ValueError('Invalid node hostname')
    if result['exit_node'] and not re.fullmatch(r'[A-Za-z0-9.:_-]{1,253}', result['exit_node']):
        raise ValueError('Invalid exit node')
    result['advertise_routes'] = ','.join(str(ipaddress.ip_network(route.strip(), strict=False))
                                          for route in result['advertise_routes'].split(',') if route.strip())
    result['advertise_tags']=','.join(tag.strip() for tag in result['advertise_tags'].split(',') if tag.strip())
    if any(not re.fullmatch(r'tag:[a-zA-Z0-9-]+', tag) for tag in result['advertise_tags'].split(',') if tag):
        raise ValueError('Invalid advertised tags')
    if result['netfilter_mode'] not in ('','on','off','nodivert'):
        raise ValueError('Invalid netfilter mode')
    result['auth_key'] = text(data.get('auth_key', ''), 2048)
    if data.get('auth_key_file'):
        path=Path(data['auth_key_file'])
        if not path.is_file() or path.stat().st_size>4096:raise ValueError('Invalid auth key file')
        result['auth_key']=text(path.read_text().strip(),2048)
    result['forwarding'] = bool(data.get('forwarding', False))
    return result


def saved():
    path = location()
    return validate(json.loads(path.read_text())) if path.exists() else None


def metadata():
    data = saved() or validate({})
    data.pop('auth_key', None)
    data['persistent'] = str(location()).startswith('/config/private/')
    data['configured'] = location().exists()
    return data


def options(data):
    return ['--'+key.replace('_','-')+'='+str(data[key]).lower() for key in FLAGS] + [
        '--'+key.replace('_','-')+'='+data[key] for key in TEXT
        if key not in ('login_server',) and (data[key] or key in ('exit_node','advertise_routes','advertise_tags'))]


def boot_apply():
    """Called after the ordinary capsule path; no changes without saved Desk settings."""
    data = saved()
    if data is None: return False
    import profile
    import tailnet_identity
    profile.apply_tailnet({key:data[key] for key in ('enabled','auth_key','login_server','hostname','ssh','accept_routes')})
    # Extended options stay in their root-private preferences file. Native daemon
    # state is inside the vault when present; without one it remains RAM-only.
    from profile_vault import private_root
    if private_root():
        binding = {key:data[key] for key in ('enabled','auth_key','login_server','hostname')}
        tailnet_identity.configure({'tailscale':binding}, b'{"protection":"plain"}')
    else:
        tailnet_identity.SETTINGS.unlink(missing_ok=True)
    if data['forwarding']:
        subprocess.run(['sysctl','-w','net.ipv4.ip_forward=1','net.ipv6.conf.all.forwarding=1'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return True


def apply(data):
    from profile import private_write
    previous = saved()
    data = validate(data)
    if not data['auth_key'] and previous and data['login_server']==previous['login_server']:
        data['auth_key'] = previous.get('auth_key','')
    private_write(location(), json.dumps(data))
    boot_apply()
    if previous and previous['forwarding'] and not data['forwarding']:
        subprocess.run(['sysctl','-w','net.ipv4.ip_forward=0','net.ipv6.conf.all.forwarding=0'],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    import tailscale_service as service
    if not data['enabled']:
        service.disable()
        return {'ok': True, 'connected': False, 'persistent': metadata()['persistent']}
    binary, daemon = service.ensure_binaries()
    if not binary or not daemon or not service.ensure_tailscaled(daemon):
        raise ValueError('Tailnet daemon unavailable')
    current = service.retrieve_status(binary, data['login_server'])
    changed_server=bool(previous and previous['login_server']!=data['login_server'])
    if changed_server:
        result=subprocess.run(service.cli(binary)+['logout'],capture_output=True,timeout=12)
        if result.returncode:raise ValueError('Cannot switch control server')
    # `set` does not support advertise-tags in the bundled CLI. `up` accepts
    # the full reviewed set and also performs browser enrollment when needed.
    command = service.cli(binary)+['up','--reset','--timeout=12s']+options(data)
    if data['login_server']: command += ['--login-server='+data['login_server']]
    if service.KEY_FILE.exists() and (not current['connected'] or changed_server):
        command += ['--auth-key=file:'+str(service.KEY_FILE)]
    try:
        applied=subprocess.run(command, capture_output=True, timeout=18)
        if applied.returncode and current['connected'] and not changed_server:
            raise ValueError('Tailnet settings not applied')
    except subprocess.TimeoutExpired: pass
    current = service.retrieve_status(binary, data['login_server'])
    service.write_status(current)
    auth_url = ''
    if not current['connected']:
        result = subprocess.run(service.cli(binary)+['status','--json'], capture_output=True, timeout=8)
        if result.returncode == 0:
            candidate = json.loads(result.stdout).get('AuthURL','')
            if isinstance(candidate,str) and candidate.startswith('https://'): auth_url = candidate
    if current['connected']:
        service.KEY_FILE.unlink(missing_ok=True)
        try:
            import tailnet_identity
            tailnet_identity.request_save()
        except (OSError,ValueError): pass
    # URL is IPC to the same local owner UI, never emitted as an activity/log line.
    return {'ok': True, 'connected': current['connected'], 'auth_url': auth_url,
            'persistent': metadata()['persistent'], 'status': current}
