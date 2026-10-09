#!/usr/bin/python3
"""Network state and interactive setup. Never expose stored credentials."""
import datetime
import getpass
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import uuid

from config import load, update


def output(*args, timeout=5):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                                env=dict(os.environ, LC_ALL="C"))
        return result.stdout.rstrip("\n")
    except (OSError, subprocess.TimeoutExpired):
        return ""


def fields(line):
    """Decode nmcli's escaped terse fields without splitting SSID colons."""
    parts, word, escaped = [], "", False
    for char in line:
        if escaped:
            word += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            parts.append(word)
            word = ""
        else:
            word += char
    parts.append(word)
    return parts


def session():
    try:
        return json.loads(Path("/run/aguja-session.json").read_text())
    except (OSError, ValueError):
        return {"ssh_port": "22", "ssh_auth_mode": "unknown", "default_harness": "menu"}


def state():
    try:
        interfaces = json.loads(output("ip", "-j", "address") or "[]")
    except ValueError:
        interfaces = []
    addresses = []
    for interface in interfaces:
        if interface.get("ifname") == "lo":
            continue
        for address in interface.get("addr_info", []):
            ip = address.get("local", "")
            if address.get("scope") == "global" and not ip.startswith("169.254."):
                addresses.append({"device": interface["ifname"], "ip": ip, "family": address.get("family")})
    addresses.sort(key=lambda a: (a["family"] != "inet", a["device"], a["ip"]))
    devices = []
    for line in output("nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status").splitlines():
        parts = fields(line)
        if len(parts) == 3:
            devices.append(dict(zip(("device", "type", "state"), parts)))
    services = output("systemctl", "is-active", "ssh", "avahi-daemon").splitlines()
    hostname = socket.gethostname()
    mdns = None
    if len(services) > 1 and services[1] == "active":
        response = output("busctl", "--json=short", "call", "org.freedesktop.Avahi", "/",
                          "org.freedesktop.Avahi.Server", "GetHostNameFqdn", timeout=2)
        try:
            mdns = json.loads(response)["data"][0]
        except (ValueError, KeyError, IndexError, TypeError):
            pass
    settings = session()
    ts_status = None
    ts_file = Path("/run/aguja-platform/tailscale-status.json")
    try:
        if ts_file.is_file():
            ts_status = json.loads(ts_file.read_text())
            # Service file is a snapshot; querying the daemon prevents stale IP
            # from presenting an offline or logged-out node as connected.
            if not isinstance(ts_status, dict):
                ts_status = None
            if ts_status and ts_status.get('enabled'):
                import tailscale_service
                binary = tailscale_service.find_binary('tailscale')
                fresh = tailscale_service.retrieve_status(binary, ts_status.get('login_server', '')) if binary else {'connected': False}
                ts_status.update(fresh)
    except (OSError, ValueError):
        # Before unlock the protected platform directory is root-private.
        # Missing/unreadable tailnet metadata must not prevent rescue/locale UI.
        pass
    return {"hostname": hostname, "addresses": addresses, "devices": devices,
            "connected": bool(addresses), "mdns": mdns,
            "ssh_active": bool(services and services[0] == "active"),
            "ssh_port": str(settings.get("ssh_port", "22")),
            "ssh_auth_mode": settings.get("ssh_auth_mode", "unknown"),
            "tailscale": ts_status,
            "workspace": "/data/workspace" if os.path.ismount("/data") else str(Path.home() / "workspace")}


def save_settings(changes):
    profile_path = Path('/config/aguja-profile.json')
    if profile_path.is_file():
        import profile
        # Protected settings stay in volatile runtime. Plain profiles are updated
        # themselves, rather than a legacy INI overwritten on the next boot.
        if json.loads(profile_path.read_bytes()).get('protection') == 'encrypted':
            return False
        before = profile_path.read_bytes()
        backup_dir = Path('/data/config-backups') if os.path.ismount('/data') else Path('/run/aguja-config-backups')
        backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(backup_dir, 0o700)
        profile.private_write(backup_dir / (uuid.uuid4().hex + '-profile.json'), before)
        return profile.update_plain_settings(profile_path, changes)
    target = Path("/config/aguja.conf")
    if not target.is_file():
        return False
    # Keep a private, recoverable previous configuration on this USB, never in Git.
    folder = Path("/data/config-backups") if os.path.ismount("/data") else Path("/run/aguja-config-backups")
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = folder / (stamp + "-" + uuid.uuid4().hex[:8] + ".conf")
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(target.read_bytes())
        f.flush()
        os.fsync(f.fileno())
    update(target, changes)
    return True


def save_active_wifi():
    active = output("nmcli", "-t", "-f", "UUID,TYPE", "connection", "show", "--active")
    profiles = [fields(line)[0] for line in active.splitlines() if fields(line)[-1] == "802-11-wireless"]
    if len(profiles) != 1:
        return False
    profile = profiles[0]
    def field(name):
        return output("nmcli", "--show-secrets", "--escape", "no", "-g", name, "connection", "show", profile)
    security = field("802-11-wireless-security.key-mgmt")
    if security in ("", "--"):
        security = "open"
    if security not in ("wpa-psk", "sae", "open"):
        print("Red conectada para esta sesión. Los perfiles empresariales se gestionan con nmtui.")
        return False
    changes = {"wifi_ssid": field("802-11-wireless.ssid"),
               "wifi_password": field("802-11-wireless-security.psk") if security != "open" else "",
               "wifi_security": security,
               "wifi_hidden": "yes" if field("802-11-wireless.hidden") == "yes" else "no"}
    if not changes["wifi_ssid"] or (security != "open" and not changes["wifi_password"]):
        return False
    return save_settings(changes)


def privileged(command):
    if os.geteuid() != 0:
        return subprocess.call(["sudo", "-n", "/usr/local/bin/aguja", command])
    return None


def setup_wifi():
    result = privileged("wifi")
    if result is not None:
        return result
    print("LA AGUJA · Conectar a la red\n")
    print("Selecciona tu Wi-Fi y pulsa Enter; la clave se pide sin mostrarla.")
    print("También puedes conectar un cable. Esc / Atrás permite trabajar sin red.\n")
    subprocess.run(["rfkill", "unblock", "wifi"], capture_output=True)
    subprocess.run(["nmcli", "radio", "wifi", "on"], capture_output=True)
    if not shutil.which("nmtui-connect"):
        print("Asistente no disponible. Diagnóstico: aguja doctor")
        return 1
    subprocess.call(["nmtui-connect"])
    current = state()
    if not current["connected"]:
        print("Sin dirección de red por ahora. Puedes reintentar con aguja wifi o conectar Ethernet.")
        return 1
    try:
        saved = save_active_wifi()
    except (OSError, ValueError):
        saved = False
    print("Red conectada." + (" Wi-Fi guardado en el USB para próximos arranques." if saved else ""))
    print("IP: " + "  ".join(a["ip"] for a in current["addresses"]))
    return 0


def set_password():
    result = privileged("password")
    if result is not None:
        return result
    if session().get('ssh_auth_mode') == 'locked':
        print('Primero desbloquea el perfil protegido: aguja profile unlock.')
        return 1
    print("LA AGUJA · Contraseña SSH personalizada\nLa contraseña no se muestra ni se envía como argumento.")
    password = getpass.getpass("Nueva contraseña: ")
    confirm = getpass.getpass("Repite la contraseña: ")
    if not password or password != confirm or password != password.strip() or any(c in password for c in "\r\n\0"):
        print("No se cambió la contraseña: comprueba coincidencia y formato de una sola línea.")
        return 1
    # Save before applying, so a write error does not silently discard persistence.
    saved = save_settings({"ssh_password": password})
    subprocess.run(["chpasswd"], input="aguja:" + password + "\n", text=True, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    metadata = session()
    metadata["ssh_auth_mode"] = "default" if password == "aguja" else "custom"
    Path("/run/aguja-session.json").write_text(json.dumps(metadata))
    print("Contraseña aplicada." + (" Guardada en el USB para próximos arranques." if saved else " Solo para este arranque; cambia un perfil cifrado desde la aplicación."))
    return 0


def wait(timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        current = state()
        if current["connected"]:
            return current
        time.sleep(1)
    return state()
