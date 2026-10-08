#!/usr/bin/python3
"""Exact-identity USB writer with optional verified backup. Must run as root."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def identify(device, serial):
    doc = json.loads(subprocess.check_output(["lsblk", "--tree", "-b", "-J", "-o", "PATH,TYPE,SERIAL,TRAN,RM,SIZE,MOUNTPOINTS", device]))
    d = doc["blockdevices"][0]
    if d["path"] != str(Path(device).resolve()) or d["type"] != "disk" or d["tran"] != "usb" or not d["rm"] or d["serial"] != serial:
        raise ValueError("El dispositivo no coincide con USB extraíble y serie exacta")
    def mounted(x):
        return any(x.get("mountpoints") or []) or any(mounted(c) for c in x.get("children", []))
    if mounted(d):
        raise ValueError("Desmonta todas las particiones del USB antes de grabar")
    return d


def hash_stream(f, limit=None):
    h = hashlib.sha256()
    n = 0
    while limit is None or n < limit:
        chunk = f.read(min(16 * 1024**2, limit - n) if limit else 16 * 1024**2)
        if not chunk:
            break
        h.update(chunk)
        n += len(chunk)
    if limit is not None and n != limit:
        raise ValueError("Lectura incompleta")
    return h.hexdigest()


def revalidate(device, serial, original):
    current = identify(device, serial)
    if current['size'] != original['size'] or current['path'] != original['path']:
        raise ValueError('El USB cambió durante la operación; no se continúa')
    return current


def verify_backup(backup, size, digest):
    proc = subprocess.Popen(['zstd', '-dc', str(backup)], stdout=subprocess.PIPE)
    try:
        recovered_hash = hash_stream(proc.stdout, size)
        # Drain explicitly: corrupt/oversized streams must not deadlock wait().
        extra = bool(proc.stdout.read(1))
        while proc.stdout.read(16 * 1024**2):
            extra = True
        if proc.wait() or extra or recovered_hash != digest:
            raise ValueError('Backup no verificado; no se escribe el USB')
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait()


class FilesystemCheckError(ValueError):
    def __init__(self, code):
        self.returncode = code
        super().__init__('No se amplía el USB: la comprobación del sistema de archivos requiere atención (e2fsck ' +
                         str(code) + '). La imagen ya está grabada y verificada; no vuelvas a grabarla por este aviso.')


def check_data_filesystem(partition):
    # e2fsck is a bitmask, not a generic success/failure status. 1 means repaired
    # successfully; reboot-required (2) or any error bit must stop expansion.
    result = subprocess.run(['e2fsck', '-f', '-y', partition], check=False)
    if result.returncode not in (0, 1):
        raise FilesystemCheckError(result.returncode)
    return result.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image", type=Path)
    p.add_argument("device")
    p.add_argument("--serial", required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--backup-dir", type=Path, help="Opcional: respaldar y verificar antes de escribir")
    p.add_argument("--report-dir", type=Path, help="Carpeta para el informe, sin copia del disco")
    p.add_argument("--confirm", required=True)
    a = p.parse_args()
    if os.geteuid() != 0 or a.confirm != "FLASH:" + a.serial:
        p.error("Se requiere root y --confirm FLASH:SERIE")
    image = a.image.resolve(strict=True)
    if not image.is_file():
        raise ValueError('La imagen debe ser un archivo regular')
    disk = identify(a.device, a.serial)
    if image.stat().st_size > disk["size"]:
        raise ValueError("Imagen mayor que USB")
    print(json.dumps({"type": "progress", "stage": "verify"}), flush=True)
    with image.open("rb") as f:
        if hash_stream(f) != a.sha256:
            raise ValueError("SHA256 de imagen incorrecto")
    report_dir = a.report_dir or a.backup_dir or Path('/var/tmp/aguja-flash-reports')
    report_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename_serial = re.sub(r'[^A-Za-z0-9._-]', '_', a.serial)
    report_path = report_dir / f"flash-{filename_serial}-{stamp}-{os.getpid()}.json"
    report = {"serial": a.serial, "device": a.device, "size": disk["size"],
              "image_sha256": a.sha256, "backup_requested": a.backup_dir is not None,
              "backup_verified": False, "stage": "validated"}
    def save_report():
        with report_path.open('w') as stream:
            os.fchmod(stream.fileno(), 0o600)
            os.fchown(stream.fileno(), report_dir.stat().st_uid, report_dir.stat().st_gid)
            json.dump(report, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
    if a.backup_dir:
        a.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Backup destination must not be on the disk that is about to be overwritten.
        backing = subprocess.check_output(["findmnt", "-n", "-o", "SOURCE", "--target", str(a.backup_dir)], text=True).strip()
        if backing.startswith(a.device):
            raise ValueError("El backup no puede estar en el USB objetivo")
        free = os.statvfs(a.backup_dir)
        if free.f_bavail * free.f_frsize < disk["size"]:
            raise ValueError("Necesitas espacio para un backup completo en el peor caso")
        backup = a.backup_dir / f"usb-{filename_serial}-{stamp}.img.zst"
        report["backup"] = str(backup)
        print(json.dumps({"type": "progress", "stage": "backup"}), flush=True)
        h = hashlib.sha256()
        with backup.open("xb") as out:
            os.fchmod(out.fileno(), 0o600)
            proc = subprocess.Popen(["zstd", "-T2", "-3", "-q", "-c"], stdin=subprocess.PIPE, stdout=out)
            try:
                with open(a.device, "rb", buffering=0) as source:
                    while chunk := source.read(16 * 1024**2):
                        h.update(chunk)
                        proc.stdin.write(chunk)
                proc.stdin.close()
                if proc.wait() != 0:
                    raise ValueError("Falló compresión de backup")
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
            out.flush()
            os.fsync(out.fileno())
        directory = os.open(a.backup_dir, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        report["original_sha256"] = h.hexdigest()
        print("Verificando backup recuperable…", flush=True)
        verify_backup(backup, disk['size'], h.hexdigest())
        report["backup_verified"] = True
        report['stage'] = 'backup_verified'
    save_report()
    revalidate(a.device, a.serial, disk)
    # Confirm source contents again after the long backup phase; it may have
    # been replaced/modified while the owner waited for the backup to finish.
    with image.open('rb') as source:
        if hash_stream(source) != a.sha256:
            raise ValueError('La imagen cambió antes de grabar; no se escribe el USB')
    print(json.dumps({"type": "progress", "stage": "write"}), flush=True)
    run("dd", "if=" + str(image), "of=" + a.device, "bs=16M", "conv=fsync", "status=progress")
    run("blockdev", "--flushbufs", a.device)
    print(json.dumps({"type": "progress", "stage": "readback"}), flush=True)
    with open(a.device, "rb", buffering=0) as source:
        if hash_stream(source, image.stat().st_size) != a.sha256:
            raise ValueError("Lectura de USB no coincide con imagen")
    report["image_readback_verified"] = True
    report['stage'] = 'image_verified'
    save_report()
    # Move backup GPT to real USB end. Expand only the DATA partition.
    revalidate(a.device, a.serial, disk)
    print(json.dumps({"type": "progress", "stage": "expand"}), flush=True)
    run("sgdisk", "-e", a.device)
    info = subprocess.check_output(["sgdisk", "-i", "5", a.device], text=True)
    start = next(line.split(":", 1)[1].split()[0] for line in info.splitlines() if line.startswith("First sector:"))
    run("sgdisk", "-d", "5", "-n", f"5:{start}:0", "-t", "5:8300", "-c", "5:AGUJA_DATA", a.device)
    run("partprobe", a.device)
    run("udevadm", "settle")
    partition = a.device + ("p5" if a.device[-1].isdigit() else "5")
    revalidate(a.device, a.serial, disk)
    report['stage'] = 'data_checking'
    save_report()
    try:
        report['e2fsck_exit_code'] = check_data_filesystem(partition)
    except FilesystemCheckError as error:
        report['e2fsck_exit_code'] = error.returncode
        report['stage'] = 'data_check_failed'
        save_report()
        raise
    report['stage'] = 'data_expanding'
    save_report()
    run("resize2fs", partition)
    run('blockdev', '--flushbufs', a.device)
    run("sgdisk", "-v", a.device)
    report["data_expanded"] = True
    report['stage'] = 'complete'
    save_report()
    print(json.dumps({"ok": True, "verified": True, "backup_verified": report["backup_verified"], "report": str(report_path)}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        error = str(e) if isinstance(e, ValueError) else "No se pudo grabar el USB. Comprueba permisos, herramientas y conexión del dispositivo."
        print(json.dumps({"ok": False, "error": error}), flush=True)
        sys.exit(1)
