"""Fixed-location secret inventory; never read or emit credential values."""
import json
from pathlib import Path
import recovery_state

SOURCES = {
    'profile_capsule': '/config/aguja-profile.json',
    'luks_profile_vault': '/config/aguja-profile.luks',
    'storage_credentials': '/config/private/storage/rclone.conf',
    'volatile_storage_credentials': '/run/aguja-storage/storage/rclone.conf',
    'literal_configuration': '/config/aguja.conf',
    'legacy_bitlocker_backup': '/config/bitlocker.json',
    'provider_api_environment': '/home/aguja/.config/aguja/provider-env.json',
    'codex_native_login': '/home/aguja/.codex/auth.json',
    'claude_native_login': '/home/aguja/.claude/.credentials.json',
    'antigravity_native_login': '/home/aguja/.gemini/antigravity-cli/antigravity-oauth-token',
    'opencode_native_login': '/home/aguja/.local/share/opencode/auth.json',
    'tailnet_enrollment': '/run/aguja-tailnet-private/auth.key',
    'networkmanager_wifi': '/etc/NetworkManager/system-connections/aguja-wifi.nmconnection',
    'usb_host_identity': '/data/ssh/ssh_host_ed25519_key',
}


def inventory():
    rows = []
    for name, location in SOURCES.items():
        path = Path(location)
        try:
            present = not path.is_symlink() and path.is_file()
        except OSError:
            present = None
        rows.append({'kind': name, 'path': location, 'present': present})
    return {'schema': 1, 'values_displayed': False, 'recovery': recovery_state.status(),
            'sources': rows, 'guide': '/usr/share/aguja/SECRETS.md'}


def main(args):
    if args not in ([], ['--json']):
        raise ValueError('aguja secrets [--json]')
    print(json.dumps(inventory(), ensure_ascii=False))
    return 0
