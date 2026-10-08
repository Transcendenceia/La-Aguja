#!/usr/bin/python3
"""Bounded DNS checks; recover broken DHCP via the local gateway, in RAM only.

No public fallback, stored profile changes, route changes or manual DNS overrides.
The gateway must answer before it is used and the system resolver must work after
the change. NetworkManager discards device modifications on disconnect/reboot.
"""
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import time

STATUS = Path('/run/aguja-network-health.json')
PROBE = 'example.com'


def command(argv, timeout=3):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env=dict(os.environ, LC_ALL='C'))
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(argv, 1, '', '')


def resolves():
    result = command(['getent', 'ahosts', PROBE])
    return result.returncode == 0 and bool(result.stdout.strip())


def gateway_resolves(gateway):
    for name in (PROBE, 'api.openai.com'):
        result = command(['dig', '@' + gateway, name, 'A', '+time=1', '+tries=1',
                          '+noall', '+answer', '+comments'], timeout=2)
        if result.returncode or 'status: NOERROR' not in result.stdout:
            return False
        if not any(len(row.split()) >= 5 and row.split()[3] == 'A'
                   for row in result.stdout.splitlines() if not row.startswith(';')):
            return False
    return True


def candidates():
    response = command(['ip', '-j', '-4', 'route', 'show', 'default'])
    try:
        routes = json.loads(response.stdout)
    except (ValueError, TypeError):
        return []
    result = []
    for route in sorted(routes, key=lambda row: row.get('metric', 0)):
        device, gateway = route.get('dev'), route.get('gateway')
        if not device or not gateway:
            continue
        try:
            address = ipaddress.IPv4Address(gateway)
        except ipaddress.AddressValueError:
            continue
        if address.is_unspecified or address.is_loopback or address.is_multicast:
            continue
        kind = command(['nmcli', '-g', 'GENERAL.TYPE', 'device', 'show', device]).stdout.strip()
        if kind not in ('ethernet', 'wifi'):
            continue  # Never rewrite a VPN/tailnet link.
        connection = command(['nmcli', '-g', 'GENERAL.CON-UUID', 'device', 'show', device]).stdout.strip()
        if not connection or connection == '--':
            continue
        settings = command(['nmcli', '-g', 'ipv4.method,ipv4.dns,ipv4.ignore-auto-dns',
                            'connection', 'show', 'uuid', connection])
        # A stored manual DNS/method is the owner's authority. Empty lines matter.
        if settings.returncode or settings.stdout.splitlines() != ['auto', '', 'no']:
            continue
        result.append((device, str(address)))
    return result[:4]


def tailnet_dns():
    try:
        # MagicDNS and custom stub resolvers must keep their own split-DNS policy.
        servers = [line.split()[1] for line in Path('/etc/resolv.conf').read_text().splitlines()
                   if line.startswith('nameserver ') and len(line.split()) > 1]
        return any(value == '100.100.100.100' or ipaddress.ip_address(value).is_loopback
                   for value in servers)
    except (OSError, ValueError):
        return True


def record(state, healthy, **metadata):
    value = {'state': state, 'dns_ok': healthy, 'checked_at': time.time(), **metadata}
    from profile import private_write
    private_write(STATUS, json.dumps(value))
    STATUS.chmod(0o644)
    return value


def check(recover=False):
    if resolves():
        # Preserve which device was recovered while it still has that DNS.
        try:
            previous = json.loads(STATUS.read_text())
            if previous.get('state') == 'recovered':
                active = command(['nmcli', '-g', 'IP4.DNS', 'device', 'show', previous['device']])
                if previous['gateway'] in active.stdout.splitlines():
                    return record('recovered', True, device=previous['device'], gateway=previous['gateway'])
        except (OSError, ValueError, KeyError):
            pass
        return record('ok', True)
    if not recover or tailnet_dns():
        return record('unresolved', False)
    for device, gateway in candidates():
        if not gateway_resolves(gateway):
            continue
        change = command(['nmcli', 'device', 'modify', device, 'ipv4.ignore-auto-dns', 'yes',
                          'ipv4.dns', gateway], timeout=5)
        if change.returncode:
            continue
        # NM's D-Bus reply can precede the atomic resolv.conf update. Give its
        # DNS plugin time to settle, then retry once before reverting the link.
        time.sleep(0.2)
        if resolves():
            return record('recovered', True, device=device, gateway=gateway)
        time.sleep(0.2)
        if resolves():
            return record('recovered', True, device=device, gateway=gateway)
        # Reapply the unmodified stored connection instead of leaving bad DNS.
        command(['nmcli', 'device', 'reapply', device], timeout=5)
    return record('unresolved', False)


if __name__ == '__main__':
    try:
        value = check(recover=True)
        print('[LA AGUJA Red] DNS: ' + value['state'], flush=True)
    except Exception:
        # No credentials or raw command errors in the journal.
        print('[LA AGUJA Red] comprobación pendiente', flush=True)
