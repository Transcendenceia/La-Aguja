#!/usr/bin/python3
"""Literal configuration: never source/eval user text, never echo secrets."""
import configparser
import os
import re
import tempfile
from pathlib import Path

DEFAULTS = dict(hostname="aguja", wifi_ssid="", wifi_password="",
                wifi_security="wpa-psk", wifi_country="ES", wifi_hidden="no", ssh_password="aguja",
                ssh_public_key="", ssh_port="22", persistent_home="no",
                default_harness="menu", agent_mode="full")


def load(path):
    return parse(Path(path).read_text(encoding="utf-8-sig"))


def parse(content):
    """One literal parser for files and in-memory provisioning validation."""
    p = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=None)
    p.read_string(content)
    if p.sections() != ["aguja"] or p.defaults():
        raise ValueError("Se requiere únicamente la sección [aguja]")
    unknown = set(p["aguja"]) - set(DEFAULTS)
    if unknown:
        raise ValueError("Clave de configuración desconocida")
    c = DEFAULTS | dict(p["aguja"])
    if any("\n" in v or "\r" in v or "\0" in v for v in c.values()):
        raise ValueError("No se admiten valores multilínea")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", c["hostname"]):
        raise ValueError("hostname no válido")
    if not c["ssh_port"].isdigit() or not 1 <= int(c["ssh_port"]) <= 65535:
        raise ValueError("Puerto SSH no válido")
    if c["persistent_home"] not in ("yes", "no") or c["agent_mode"] not in ("full", "ask"):
        raise ValueError("Modo no válido")
    if c["default_harness"] not in ("menu", "shell", "codex", "antigravity", "claude", "opencode"):
        raise ValueError("Arnés no válido")
    if not re.fullmatch(r"[A-Z]{2}", c["wifi_country"]):
        raise ValueError("País Wi-Fi no válido")
    if len(c["wifi_ssid"].encode()) > 32:
        raise ValueError("SSID demasiado largo")
    if c["wifi_security"] not in ("wpa-psk", "sae", "open"):
        raise ValueError("Seguridad Wi-Fi no válida")
    if c["wifi_hidden"] not in ("yes", "no"):
        raise ValueError("Red oculta no válida")
    if c["wifi_ssid"] and c["wifi_security"] == "wpa-psk":
        pw = c["wifi_password"]
        if not (8 <= len(pw.encode()) <= 63 or re.fullmatch(r"[0-9a-fA-F]{64}", pw)):
            raise ValueError("La clave WPA necesita 8–63 bytes o 64 dígitos hex")
    if c["wifi_ssid"] and c["wifi_security"] == "sae" and not c["wifi_password"]:
        raise ValueError("WPA3 requiere contraseña")
    key = c["ssh_public_key"]
    if key and not re.fullmatch(r"(?:ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)) [A-Za-z0-9+/=]+(?: .*)?", key):
        raise ValueError("Clave pública SSH no válida")
    return c


def nm_escape(value):
    return value.replace("\\", "\\\\").replace("\t", "\\t").replace(";", "\\;").replace(" ", "\\s")


def wifi_keyfile(c):
    out = ("[connection]\nid=aguja-wifi\ntype=wifi\nautoconnect=true\n"
           "[wifi]\nmode=infrastructure\nssid=" + nm_escape(c["wifi_ssid"]) + "\n"
           "hidden=" + ("true" if c["wifi_hidden"] == "yes" else "false") + "\n")
    if c["wifi_security"] != "open":
        out += ("[wifi-security]\nkey-mgmt=" + c["wifi_security"] +
                "\npsk=" + nm_escape(c["wifi_password"]) + "\n")
    return out + "[ipv4]\nmethod=auto\n[ipv6]\nmethod=auto\n"


def ssh_access(c):
    """An explicit empty password with a key retains key-only access."""
    password = c["ssh_password"]
    if not password and c["ssh_public_key"]:
        return None, "key"
    if not password or password == "aguja":
        return "aguja", "default"
    return password, "custom"


def update(path, changes):
    """Validate, preserve unrelated fields/comments, replace atomically; no secret output."""
    target = Path(path)
    original = target.read_bytes()
    before = load(target)
    if set(changes) - set(DEFAULTS):
        raise ValueError("Clave de configuración desconocida")
    text = original.decode("utf-8-sig")
    for key, value in changes.items():
        if not isinstance(value, str) or value != value.strip() or any(ch in value for ch in "\r\n\0"):
            raise ValueError("Valor no representable sin pérdida")
        pattern = r"^" + re.escape(key) + r"\s*=.*$"
        if re.search(pattern, text, re.M):
            text = re.sub(pattern, lambda match: key + " = " + value, text, flags=re.M)
        else:
            text = text.rstrip() + "\n" + key + " = " + value + "\n"
    fd, filename = tempfile.mkstemp(prefix=".aguja-", dir=target.parent)
    temporary = Path(filename)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        candidate = load(temporary)
        if any(candidate[k] != v for k, v in changes.items()) or any(candidate[k] != v for k, v in before.items() if k not in changes):
            raise ValueError("La configuración no conserva sus valores")
        if target.read_bytes() != original:
            raise ValueError("La configuración cambió durante la operación")
        os.replace(temporary, target)
        os.sync()
        if target.read_bytes() != text.encode("utf-8"):
            raise OSError("Lectura de configuración no coincide")
        return candidate
    finally:
        if temporary.exists():
            temporary.unlink()
