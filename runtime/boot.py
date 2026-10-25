#!/usr/bin/python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from config import load, wifi_keyfile, ssh_access


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def secure_write(path, value, mode=0o600):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    os.fchmod(fd, mode)
    with os.fdopen(fd, "w") as f:
        f.write(value)


def partition_view(partition, source):
    """The live ISO claims the whole disk. Map only the sibling's byte range.

    A loop view avoids claiming a child blockdev of an ISO-mounted whole disk.
    The partition was already located on our own boot disk, never on another disk.
    Linux sysfs start/size are always in 512-byte sectors.
    """
    device = Path(partition).name
    parent = subprocess.check_output(["lsblk", "-ndo", "PKNAME", source], text=True).strip()
    if parent:
        return partition  # Medium mounted through a partition: no whole-disk conflict.
    start = int(Path(f"/sys/class/block/{device}/start").read_text()) * 512
    size = int(Path(f"/sys/class/block/{device}/size").read_text()) * 512
    return subprocess.check_output(["losetup", "--find", "--show", "--offset", str(start),
                                    "--sizelimit", str(size), source], text=True).strip()



def prepare_auth_runtime(base='/run/aguja-auth'):
    # install -m applies the requested mode even under the boot service's 077 umask.
    import pwd
    run('install','-d','-m','755','-o','root','-g','root',str(base))
    run('install','-d','-m','700','-o','aguja','-g','aguja',str(Path(base)/str(pwd.getpwnam('aguja').pw_uid)))


def configure_owner_access(c, home, locked=False):
    """Keep a protected profile inaccessible over SSH until owner unlock."""
    password, auth_mode = ssh_access(c)
    if locked:
        secure_write(home / '.ssh/authorized_keys', '')
        run('passwd', '-l', 'aguja', stdout=subprocess.DEVNULL)
        return 'locked'
    secure_write(home / '.ssh/authorized_keys', c['ssh_public_key'] + '\n')
    if password is not None:
        run('chpasswd', input='aguja:' + password + '\n', text=True)
    else:
        run('passwd', '-l', 'aguja', stdout=subprocess.DEVNULL)
    return auth_mode


def restart_tailnet():
    """Unlocked settings apply even if enrollment is offline/awaiting approval."""
    try:
        return subprocess.run(['systemctl', '--no-block', 'restart', 'aguja-tailscale'],
                              check=False, capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main(profile_override=None, profile_passphrase=None):
    # live-boot mounts only its boot medium. No probing/mounting internal filesystems.
    medium = Path("/run/live/medium")
    # DATA must belong to the same physical disk as our boot partition.
    data = None
    cfg = None
    source = subprocess.check_output(["findmnt", "-n", "-o", "SOURCE", "--target", str(medium)], text=True).strip()
    if source.startswith("/dev/"):
        parent = subprocess.check_output(["lsblk", "-ndo", "PKNAME", source], text=True).strip()
        disk = "/dev/" + parent if parent else source
        children = json.loads(subprocess.check_output(["lsblk", "--tree", "-J", "-o", "PATH,LABEL", disk]))
        for child in children["blockdevices"][0].get("children", []):
            if child.get("label") == "AGUJA_DATA":
                data = child["path"]
            if child.get("label") == "AGUJA_CFG":
                cfg = child["path"]
    Path("/config").mkdir(exist_ok=True)
    if cfg and not os.path.ismount("/config"):
        run("mount", "-o", "rw,umask=0077,nosuid,nodev,noexec", partition_view(cfg, source), "/config")
    import profile_vault
    import config_transaction
    if cfg:
        config_transaction.recover(Path('/config'))
    import profile as platform_profile
    # Public keyboard preferences are needed to type the private unlock phrase.
    platform_profile.apply_locale(None)
    capsule, capsule_path, unlock_password, protection = profile_vault.gate()
    if profile_override is not None:
        capsule = profile_override
    profile_passphrase = profile_passphrase or unlock_password
    conf = profile_vault.settings_root() / 'aguja.conf' if cfg else medium / 'aguja.conf'
    if not conf.is_file():
        conf = Path('/etc/aguja/aguja.conf')
    c = load(conf)
    locked = False  # gate must return successfully before access is configured
    if capsule:
        c = platform_profile.configuration(capsule, c)
    platform_profile.apply_locale(capsule)
    os.environ.update(platform_profile.locale_environment())
    if protection in ('luks2', 'legacy-aes'):
        # A protected profile must never silently spill decrypted native secrets
        # into a legacy persistent HOME on the unencrypted DATA filesystem.
        c['persistent_home'] = 'no'
    secure_write('/run/aguja-profile-status.json', json.dumps({'present': capsule_path.is_file() or protection == 'luks2', 'locked': locked, 'loaded': bool(capsule) or protection == 'luks2', 'protection': protection, 'early_gate': True}), 0o644)
    import recovery_state
    recovery_state.initialize()
    if profile_passphrase and recovery_state.status().get('locked'):
        try:
            recovery_state.unlock(profile_passphrase)
        except (ValueError, OSError, KeyError):
            pass  # independent recovery envelope may deliberately use another key
    run("hostnamectl", "set-hostname", c["hostname"])
    secure_write("/etc/hosts", "127.0.0.1 localhost\n127.0.1.1 " + c["hostname"] + "\n", 0o644)
    Path("/data").mkdir(exist_ok=True)
    initialized_data=None
    if data and cfg and source != data:
        import data_capacity
        initialized_data=data_capacity.initialize('/config',disk,data)
    if data:
        secure_write('/run/aguja-data-device',data,0o644)
    if data and not os.path.ismount("/data"):
        if source == data:
            run('mount','-o','remount,rw,nosuid,nodev',str(medium))
            run('mount','--bind',str(medium),'/data')
        else:
            run("mount", "-o", "nosuid,nodev", initialized_data or partition_view(data, source), "/data")
    workspace = Path("/data/workspace" if data else "/home/aguja/workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    if c["persistent_home"] == "yes" and data and not os.path.ismount("/home/aguja"):
        home = Path("/data/home")
        home.mkdir(exist_ok=True, mode=0o700)
        run("mount", "--bind", str(home), "/home/aguja")
    run("chown", "-R", "aguja:aguja", "/home/aguja", str(workspace))
    # Owner-only volatile handoff; never DATA/HOME or public activity snapshots.
    prepare_auth_runtime()
    home = Path("/home/aguja")
    for filename in (".zshrc", ".hushlogin"):
        if not (home / filename).exists():
            shutil.copyfile(Path("/etc/skel") / filename, home / filename)
    (home / ".ssh").mkdir(exist_ok=True, mode=0o700)
    auth_mode = configure_owner_access(c, home, locked)
    run('chown', '-R', 'aguja:aguja', str(home / '.ssh'))
    # Stable USB-specific host identity, never shipped in the public image.
    hostkeys = Path("/data/ssh") if data else Path("/etc/ssh")
    hostkeys.mkdir(exist_ok=True, mode=0o700)
    key = hostkeys / "ssh_host_ed25519_key"
    if not key.exists():
        run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key))
    secure_write("/run/aguja-hostkey.pub", Path(str(key) + ".pub").read_text(), 0o644)
    secure_write("/etc/ssh/sshd_config.d/00-aguja.conf",
                 f"Port {c['ssh_port']}\nHostKey {key}\nPermitRootLogin no\n"
                 f"PasswordAuthentication {'no' if locked else 'yes'}\nKbdInteractiveAuthentication no\n"
                 "PermitEmptyPasswords no\nAllowUsers aguja\n"
                 "Banner /usr/share/aguja/SSH-WELCOME.txt\n"
                 "ForceCommand /usr/lib/aguja/ssh_session.py\n", 0o644)
    metadata = {k: c[k] for k in ("default_harness", "agent_mode", "ssh_port", "persistent_home")}
    metadata["ssh_auth_mode"] = auth_mode
    metadata["wifi_configured"] = bool(c["wifi_ssid"])
    secure_write("/run/aguja-session.json", json.dumps(metadata), 0o644)
    secure_write("/etc/avahi/services/aguja-ssh.service",
                 '<?xml version="1.0"?><!DOCTYPE service-group SYSTEM "avahi-service.dtd">\n'
                 '<service-group><name replace-wildcards="yes">LA AGUJA Rescue Disk · %h</name>'
                 '<service><type>_ssh._tcp</type><port>' + c["ssh_port"] + '</port>'
                 '<txt-record>product=LA AGUJA Rescue Disk</txt-record><txt-record>user=aguja</txt-record>'
                 '</service></service-group>\n', 0o644)
    if c["wifi_ssid"]:
        secure_write("/etc/NetworkManager/system-connections/aguja-wifi.nmconnection", wifi_keyfile(c))
    if capsule:
        secure_write('/etc/NetworkManager/system-connections/aguja-ethernet.nmconnection',
                     platform_profile.ethernet_keyfile(capsule['network']['ethernet']))
        import persistence
        platform_profile.apply(capsule, tailnet_state='/run/aguja-tailnet-private', preserve_native=persistence.running_snapshot())
        from profile_extensions import system_apply
        system_apply(capsule)
        import tailnet_identity
        tailnet_identity.configure(capsule, capsule_path.read_bytes(), profile_passphrase)
        # Tailnet credentials live separately, never in this owner-writable tree.
        run('chown', '-R', 'aguja:aguja', '/run/aguja-platform')
    import persistence
    persistence.restore_state()
    import tailnet_config
    try:
        tailnet_config.boot_apply()
    except (OSError,ValueError,subprocess.SubprocessError):
        print('Tailnet Desk preferences unavailable; existing profile preserved.',flush=True)
    subprocess.run(["rfkill", "unblock", "wifi"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["nmcli", "radio", "wifi", "on"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["iw", "reg", "set", c["wifi_country"]], check=False)
    subprocess.run(["nmcli", "connection", "reload"], check=False)
    if c["wifi_ssid"]:
        subprocess.Popen(["nmcli", "--wait", "25", "connection", "up", "aguja-wifi"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if capsule:
        subprocess.Popen(['nmcli', '--wait', '25', 'connection', 'up', 'aguja-ethernet'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import hardware
    try:
        observed_hardware = hardware.snapshot()
    except (OSError, ValueError, KeyError):
        observed_hardware = {'schema': 1, 'read_only': True, 'error': 'Inventory unavailable; rerun aguja hardware'}
    secure_write('/run/aguja-hardware.json', json.dumps(observed_hardware), 0o644)
    import agent_context
    agent_context.ensure(workspace)
    quickstart = workspace / "QUICKSTART.md"
    if not quickstart.exists() and not quickstart.is_symlink():
        shutil.copyfile("/usr/share/aguja/QUICKSTART.md", quickstart)
    run("chown", "-R", "aguja:aguja", "/home/aguja", str(workspace))
    # A locked capsule must not activate a previously materialized tailnet.
    if locked:
        platform = Path('/run/aguja-platform')
        platform.mkdir(parents=True, exist_ok=True, mode=0o711)
        platform_profile.private_write(platform / 'tailscale.json', json.dumps({'enabled': False}))
        platform_profile.apply_tailnet({'enabled': False})
        import tailnet_identity
        tailnet_identity.configure(None, b'{}')
        (platform / 'tailscale.key').unlink(missing_ok=True)
    if profile_override:
        run('systemctl', 'restart', 'ssh')
        restart_tailnet()
    secure_write("/run/aguja-ready", "ready\n", 0o644)
    print("AGUJA_READY: configuración aplicada; SSH disponible; consulta aguja status")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never emit exception details that may contain a Wi-Fi/SSH credential.
        print("LA AGUJA Rescue Disk: fallo de inicio; revisa configuración con aguja doctor", file=sys.stderr)
        sys.exit(1)
