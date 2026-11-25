#!/usr/bin/env python3
"""LA AGUJA IoT — Linux/Cross-platform ESP microcontroller flasher & boot verifier.

Protocol:
  Reads one JSON job object from stdin (never puts secrets in argv), emits JSONL
  progress events on stdout, and ends with a single JSON receipt object:
    {"ok": true, "verified": true, "chip": "...", "mac": "...", ...}
"""

import hashlib
import io
import json
import os
import re
import sys
import time


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def progress(stage, message, percent=None):
    ev = {"type": "progress", "stage": stage, "message": message}
    if percent is not None:
        ev["percent"] = max(0, min(100, int(percent)))
    emit(ev)


def fail(message):
    emit({"ok": False, "error": str(message)[:300]})
    sys.exit(1)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def ensure_deps():
    try:
        import esptool  # noqa: F401
    except ImportError:
        fail("Falta esptool en Python. Instala esptool y pyserial (por ejemplo: pip install esptool pyserial).")
    try:
        import serial  # noqa: F401
    except ImportError:
        fail("Falta pyserial en Python. Instala pyserial (por ejemplo: pip install pyserial).")


class ProgressCapture(io.TextIOBase):
    """Captures esptool stdout and translates percentage lines into JSONL progress."""

    def __init__(self, stage, label):
        self.stage = stage
        self.label = label
        self.buf = ""
        self.lines = []
        self.last_pct = -1

    def write(self, s):
        self.buf += s
        while "\n" in self.buf or "\r" in self.buf:
            sep_n = self.buf.find("\n")
            sep_r = self.buf.find("\r")
            idxs = [i for i in (sep_n, sep_r) if i >= 0]
            cut = min(idxs)
            line = self.buf[:cut].strip()
            self.buf = self.buf[cut + 1:]
            if not line:
                continue
            self.lines.append(line)
            m = re.search(r"\((\d{1,3})\s*%\)", line)
            if m:
                pct = int(m.group(1))
                if pct != self.last_pct:
                    self.last_pct = pct
                    progress(self.stage, f"{self.label} ({pct}%)", pct)
        return len(s)

    def flush(self):
        pass


def run_esptool(argv, stage, label):
    import esptool

    cap = ProgressCapture(stage, label)
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    err_buf = io.StringIO()
    sys.stdout = cap
    sys.stderr = err_buf
    try:
        esptool.main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code != 0:
            detail = " ".join(cap.lines[-5:] + [err_buf.getvalue().strip()])
            raise RuntimeError(detail.strip() or f"esptool exit {code}")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return cap.lines


def normalize_chip(raw_chip):
    s = str(raw_chip or "").upper()
    for key in ("ESP32-S3", "ESP32-C6", "ESP32-C3", "ESP32-S2", "ESP32-C2", "ESP32-H2"):
        if key in s:
            return key.replace("-", "").lower()
    if "ESP32" in s:
        return "esp32"
    return ""


def parse_chip_info(lines):
    info = {
        "chip": "",
        "chip_normalized": "",
        "features": "",
        "mac": "",
        "flash_size": "",
        "flash_mb": 0,
        "psram_mb": 0,
    }
    for line in lines:
        m = re.search(r"Chip type:\s*(.+)$", line)
        if m:
            info["chip"] = m.group(1).strip()
            info["chip_normalized"] = normalize_chip(info["chip"])
        m = re.search(r"Features:\s*(.+)$", line)
        if m:
            feat = m.group(1).strip()
            info["features"] = feat
            mp = re.search(r"PSRAM\s*(\d+)\s*MB", feat, re.I)
            if mp:
                info["psram_mb"] = int(mp.group(1))
            elif "PSRAM" in feat.upper():
                info["psram_mb"] = 2
        m = re.search(r"MAC:\s*([0-9a-fA-F:]{17})", line)
        if m:
            info["mac"] = m.group(1).lower()
        m = re.search(r"Detected flash size:\s*(\S+)", line)
        if m:
            info["flash_size"] = m.group(1).strip()
            mf = re.match(r"^(\d+)\s*MB$", info["flash_size"], re.I)
            if mf:
                info["flash_mb"] = int(mf.group(1))
    return info


def flash_size_bytes(label):
    m = re.match(r"^(\d+)\s*MB$", str(label or "").strip(), re.I)
    if not m:
        return 4 * 1024 * 1024
    return int(m.group(1)) * 1024 * 1024


def verify_serial_boot(port, timeout_s=24):
    import serial

    progress("boot", "Verificando arranque y conexión a la red…", 5)
    result = {
        "booted": False,
        "provisioned_from_nvs": False,
        "wifi_ip": "",
        "tailnet_state": "",
        "vpn_ip": "",
        "hostname": "",
        "fw_version": "",
        "board": "",
        "chip": "",
    }
    deadline = time.monotonic() + timeout_s
    last_status_poll = 0.0
    buf = ""
    try:
        ser = serial.Serial(port, 115200, timeout=0.35)
    except Exception as exc:
        result["warning"] = f"No se pudo abrir el puerto serie tras grabar: {exc}"
        return result

    try:
        # Release reset cleanly (RTS/DTR low-inactive)
        ser.dtr = False
        ser.rts = False
        while time.monotonic() < deadline:
            chunk = ser.read(1024)
            if chunk:
                buf += chunk.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if "AGUJA-IOT Mobile Ops Center" in line or "Boot complete" in line:
                        result["booted"] = True
                    if "Provisioned config from NVS init_json" in line:
                        result["provisioned_from_nvs"] = True
                    m_ip = re.search(r"got ip:(\d+\.\d+\.\d+\.\d+)", line, re.I)
                    if m_ip:
                        result["wifi_ip"] = m_ip.group(1)
                    if "Tailscale CONNECTED" in line or "tailnet=CONNECTED" in line:
                        result["tailnet_state"] = "CONNECTED"
                    m_vpn = re.search(r"vpn=(\d+\.\d+\.\d+\.\d+)", line)
                    if m_vpn and m_vpn.group(1) != "0.0.0.0":
                        result["vpn_ip"] = m_vpn.group(1)
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict) and (
                                "wifi" in obj or "tailnet" in obj or "tailnet_state" in obj or "wifi_ip" in obj
                            ):
                                result["booted"] = True
                                wifi_obj = obj.get("wifi") if isinstance(obj.get("wifi"), dict) else {}
                                tn_obj = obj.get("tailnet") if isinstance(obj.get("tailnet"), dict) else {}
                                wifi_ip = obj.get("wifi_ip") or wifi_obj.get("ip") or ""
                                if wifi_ip and wifi_ip != "0.0.0.0":
                                    result["wifi_ip"] = str(wifi_ip)
                                vpn_ip = obj.get("vpn_ip") or tn_obj.get("vpn_ip") or ""
                                if vpn_ip and vpn_ip != "0.0.0.0":
                                    result["vpn_ip"] = str(vpn_ip)
                                if obj.get("tailnet_state"):
                                    result["tailnet_state"] = str(obj["tailnet_state"])
                                elif "connected" in tn_obj:
                                    result["tailnet_state"] = "CONNECTED" if tn_obj.get("connected") else "CONNECTING"
                                host = obj.get("hostname") or tn_obj.get("hostname") or ""
                                if host:
                                    result["hostname"] = str(host)
                                if obj.get("board"):
                                    result["board"] = str(obj["board"])
                                if obj.get("chip"):
                                    result["chip"] = str(obj["chip"])
                        except Exception:
                            pass

            now = time.monotonic()
            elapsed = timeout_s - (deadline - now)
            if elapsed >= 3.5 and (now - last_status_poll) >= 2.5:
                last_status_poll = now
                try:
                    ser.write(b"status\n")
                    ser.flush()
                except Exception:
                    pass
                pct = min(95, int(10 + (elapsed / timeout_s) * 85))
                if result["vpn_ip"] and result["tailnet_state"] == "CONNECTED":
                    progress("boot", f"Nodo en línea en tailnet ({result['vpn_ip']})…", 100)
                    break
                elif result["wifi_ip"]:
                    progress("boot", f"Wi-Fi conectado ({result['wifi_ip']}), esperando tailnet…", pct)
                elif result["booted"]:
                    progress("boot", "Firmware arrancado, conectando a Wi-Fi…", pct)
    finally:
        try:
            ser.close()
        except Exception:
            pass

    return result


def handle_probe(job):
    port = job.get("port")
    if not port:
        fail("Falta el puerto serie para comprobar la placa.")
    progress("probe", "Sondeando silicio en " + port + "…", 25)
    lines = run_esptool(["--port", port, "flash_id"], "probe", "Sondeando chip")
    info = parse_chip_info(lines)
    progress("probe", f"Detectado {info.get('chip') or 'ESP32'} ({info.get('flash_size') or '?'})", 100)
    emit({"ok": True, "port": port, **info})


def handle_erase(job):
    port = job.get("port")
    chip = job.get("chip", "auto")
    if not port:
        fail("Selecciona un puerto serie USB válido para limpiar la flash.")
    progress("erase", "Conectando para borrar la memoria flash…", 15)
    cmd = ["--port", port]
    if chip and chip != "auto":
        cmd.extend(["--chip", chip])
    cmd.append("erase_flash")
    lines = run_esptool(cmd, "erase", "Borrando memoria flash")
    info = parse_chip_info(lines)
    progress("erase", "Memoria flash borrada completamente.", 100)
    emit({"ok": True, "erased": True, "port": port, **info})


def handle_flash(job):
    port = job.get("port")
    chip = job.get("chip", "auto")
    baud = str(job.get("baud", 460800))
    flash_mode = job.get("flash_mode", "dio")
    flash_freq = job.get("flash_freq", "80m")
    flash_size = job.get("flash_size", "detect")
    segments = job.get("segments") or []
    backup_path = job.get("backup_path")
    verify_boot = bool(job.get("verify_boot", True))
    boot_timeout_s = int(job.get("boot_timeout_s", 24))

    if not port:
        fail("Selecciona un puerto serie USB válido.")
    if not segments:
        fail("Faltan los binarios de firmware para grabar.")

    # Verify all segment files exist and match expected SHA-256 before touching flash
    progress("verify", "Comprobando integridad SHA-256 del firmware y NVS…", 10)
    write_args = []
    for seg in segments:
        offset = str(seg.get("offset", ""))
        fpath = seg.get("path", "")
        expected = seg.get("sha256", "")
        if not re.match(r"^0x[0-9a-fA-F]+$", offset):
            fail(f"Offset de flash inválido: {offset}")
        if not os.path.isfile(fpath):
            fail(f"Falta archivo de firmware: {os.path.basename(fpath)}")
        if expected:
            actual = sha256_file(fpath)
            if actual != expected.lower():
                fail(f"SHA-256 incorrecto para {os.path.basename(fpath)}.")
        write_args.extend([offset, fpath])

    # Step 1: Probe chip & flash size
    progress("probe", "Conectando con el microcontrolador…", 15)
    probe_cmd = ["--port", port]
    if chip and chip != "auto":
        probe_cmd.extend(["--chip", chip])
    probe_cmd.append("flash_id")
    probe_lines = run_esptool(probe_cmd, "probe", "Detectando placa")
    info = parse_chip_info(probe_lines)

    # Step 2: Optional full flash backup
    backup_receipt = None
    if backup_path:
        total_bytes = flash_size_bytes(info.get("flash_size") or flash_size)
        progress("backup", f"Respaldando flash completa ({total_bytes // (1024*1024)} MB)…", 0)
        os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
        run_esptool(
            [
                "--chip", chip,
                "--port", port,
                "--baud", baud,
                "read_flash", "0x0", hex(total_bytes), backup_path,
            ],
            "backup",
            "Respaldando flash",
        )
        backup_receipt = {
            "path": backup_path,
            "bytes": os.path.getsize(backup_path),
            "sha256": sha256_file(backup_path),
        }

    # Step 3: Write bootloader + partition table + NVS + otadata + app
    progress("write", "Grabando firmware y configuración privada NVS…", 0)
    cmd = [
        "--chip", chip,
        "--port", port,
        "--baud", baud,
        "--before", "default_reset",
        "--after", "hard_reset",
        "write_flash",
        "-z",
        "--flash_mode", flash_mode,
        "--flash_freq", flash_freq,
        "--flash_size", flash_size,
        *write_args,
    ]
    run_esptool(cmd, "write", "Grabando flash")
    progress("write", "Flash verificada por esptool.", 100)

    # Step 4: Optional live serial boot verification
    boot_info = None
    if verify_boot:
        time.sleep(0.8)
        boot_info = verify_serial_boot(port, timeout_s=boot_timeout_s)

    emit({
        "ok": True,
        "verified": True,
        "port": port,
        "chip": info.get("chip") or chip,
        "mac": info.get("mac") or "",
        "flash_size": info.get("flash_size") or flash_size,
        "backup": backup_receipt,
        "boot": boot_info,
    })


def main():
    ensure_deps()
    raw = sys.stdin.read()
    try:
        job = json.loads(raw) if raw.strip() else {}
    except Exception:
        fail("Entrada JSON no válida para iot-flash.")
    op = job.get("op", "flash")
    try:
        if op == "probe":
            handle_probe(job)
        elif op == "erase":
            handle_erase(job)
        elif op == "flash":
            handle_flash(job)
        else:
            fail(f"Operación no soportada: {op}")
    except Exception as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
