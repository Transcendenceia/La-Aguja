#!/usr/bin/python3
"""Boot an isolated USB image, prove DHCP/SSH/sudo/harnesses; no AI inference."""
import argparse
import configparser
import json
import os
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image", type=Path)
    p.add_argument("--firmware", choices=["bios", "uefi"], default="bios")
    p.add_argument("--accelerator", choices=["kvm", "tcg"], default="tcg")
    p.add_argument("--workdir", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=360)
    p.add_argument("--memory", type=int, default=2048)
    p.add_argument("--config-mode", choices=["custom", "default", "key-only"], default="custom")
    p.add_argument("--screenshots", action="store_true", help="Capture real VGA frames over QMP during boot")
    p.add_argument("--activity", action="store_true", help="Verify live SSH activity, framebuffer, binary streams and file transfers")
    p.add_argument("--restart-check", action="store_true", help="Reboot the QA clone and verify all CLI remain available")
    a = p.parse_args()
    a.workdir.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = a.workdir / "test-key"
    if not key.exists():
        run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key))
    image = a.workdir / "vm.img"
    run("cp", "--sparse=always", "--reflink=auto", str(a.image.resolve()), str(image))
    info = subprocess.check_output([shutil.which("sgdisk") or "/usr/sbin/sgdisk", "-i", "4", str(image)], text=True)
    offset = 512 * int(next(line.split(":", 1)[1].split()[0] for line in info.splitlines() if line.startswith("First sector:")))
    password = secrets.token_urlsafe(24) + ":#%$;"
    conf = configparser.ConfigParser(interpolation=None)
    conf["aguja"] = {"ssh_public_key": Path(str(key) + ".pub").read_text().strip(),
                     "ssh_password": "" if a.config_mode == "key-only" else password,
                     "hostname": "aguja-test", "persistent_home": "yes"}
    config = a.workdir / "test.conf"
    with config.open("w") as f:
        conf.write(f)
    config.chmod(0o600)
    if a.config_mode != "default":
        run("mcopy", "-o", "-i", str(image) + "@@" + str(offset), str(config), "::aguja.conf")
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    serial = a.workdir / "serial.log"
    err = a.workdir / "qemu.log"
    cmd = ["qemu-system-x86_64", "-machine", "q35", "-accel", a.accelerator,
           "-cpu", "host" if a.accelerator == "kvm" else "max", "-smp", "2", "-m", str(a.memory),
           "-display", "none", "-monitor", "none", "-serial", "file:" + str(serial),
           "-drive", f"if=none,id=stick,file={image},format=raw", "-device", "qemu-xhci",
           "-device", "usb-storage,drive=stick,removable=true", "-boot", "order=c",
           "-netdev", f"user,id=net0,hostfwd=tcp:127.0.0.1:{port}-:22", "-device", "e1000,netdev=net0"]
    if a.firmware == "uefi":
        code = next((x for x in (Path("/usr/share/OVMF/OVMF_CODE_4M.fd"), Path("/usr/share/edk2-ovmf/x64/OVMF_CODE.4m.fd")) if x.exists()), None)
        varsrc = next((x for x in (Path("/usr/share/OVMF/OVMF_VARS_4M.fd"), Path("/usr/share/edk2-ovmf/x64/OVMF_VARS.4m.fd")) if x.exists()), None)
        if not code or not varsrc:
            raise ValueError("OVMF requerido")
        varfile = a.workdir / "OVMF_VARS.fd"
        shutil.copyfile(varsrc, varfile)
        cmd += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}", "-drive", f"if=pflash,format=raw,file={varfile}"]
    qmp_path = a.workdir / "qmp.sock"
    if a.screenshots:
        (a.workdir / "screenshots").mkdir(exist_ok=True)
        cmd += ["-vga", "std", "-qmp", f"unix:{qmp_path},server=on,wait=off"]
    known = a.workdir / "known_hosts"
    ssh = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "UserKnownHostsFile=" + str(known),
           "-o", "ConnectTimeout=3", "-o", "BatchMode=yes", "-i", str(key), "-p", str(port), "aguja@127.0.0.1"]
    remote = list(ssh)
    remote_env = dict(os.environ)
    if a.config_mode == "default":
        if not shutil.which("sshpass"):
            raise ValueError("sshpass requerido para comprobar la imagen de fábrica")
        remote[remote.index("BatchMode=yes")] = "BatchMode=no"
        host = remote.pop()
        remote += ["-o", "PubkeyAuthentication=no", "-o", "PreferredAuthentications=password", host]
        remote = ["sshpass", "-e"] + remote
        remote_env["SSHPASS"] = "aguja"
    with err.open("w") as log:
        proc = subprocess.Popen(cmd, stderr=log, stdout=log)
        start = time.monotonic()
        qmp = None
        qmp_file = None
        screenshot_count = 0
        def qmp_command(command, arguments=None):
            payload = {"execute": command}
            if arguments:
                payload["arguments"] = arguments
            qmp_file.write((json.dumps(payload) + "\n").encode())
            qmp_file.flush()
            while True:
                response = json.loads(qmp_file.readline())
                if "return" in response:
                    return response["return"]
                if "error" in response:
                    raise ValueError("QMP screenshot failed: " + response["error"]["desc"])

        def capture_screen():
            nonlocal qmp, qmp_file, screenshot_count
            if not a.screenshots:
                return
            if qmp is None:
                if not qmp_path.exists():
                    return
                qmp = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                qmp.settimeout(5)
                qmp.connect(str(qmp_path))
                qmp_file = qmp.makefile("rwb")
                json.loads(qmp_file.readline())
                qmp_command("qmp_capabilities")
            dest = (a.workdir / "screenshots" / f"{screenshot_count:03d}.png").resolve()
            qmp_command("screendump", {"filename": str(dest), "format": "png"})
            screenshot_count += 1
        try:
            while time.monotonic() - start < a.timeout:
                capture_screen()
                if proc.poll() is not None:
                    raise ValueError("QEMU terminó antes de SSH")
                if serial.exists() and any(marker in serial.read_text(errors="replace") for marker in ("Kernel panic", "Aguja: fallo de inicio", "Rescue Disk: fallo de inicio")):
                    raise ValueError("Arranque falló; consulta serial.log")
                result = subprocess.run(remote + ["test -f /run/aguja-ready"], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True, text=True)
                if result.returncode == 0:
                    break
                time.sleep(3)
            else:
                raise ValueError("SSH no disponible dentro del plazo; consulta serial.log")
            check = "set -e; id; sudo -n id; systemctl is-active NetworkManager ssh aguja-boot; mountpoint -q /config; mountpoint -q /data; ip -brief address; codex --version; agy --version; claude --version; test ! -e /usr/lib/aguja/tunnel.py; test ! -e /etc/systemd/system/aguja-tunnel.service; opencode --version; test -f /data/workspace/AGENTS.md; test -f /run/aguja-hostkey.pub; sudo -n test -f /data/ssh/ssh_host_ed25519_key; test $(stat -c %a /home/aguja/.ssh/authorized_keys) = 600; aguja doctor; test $(/usr/sbin/plymouth-set-default-theme) = aguja; test -f /usr/share/plymouth/themes/aguja/frame-095.png; cat /usr/share/aguja/VERSION"
            result = subprocess.run(remote + [check], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
            (a.workdir / "checks.txt").write_text(result.stdout)
            (a.workdir / "checks.err").write_text(result.stderr)
            if result.returncode:
                raise ValueError("Comprobaciones del guest fallaron; consulta checks.txt/checks.err")
            report = {"firmware": a.firmware, "accelerator": a.accelerator,
                      "boot_and_checks_seconds": round(time.monotonic() - start, 1),
                      "config_mode": a.config_mode,
                      "key_auth": a.config_mode != "default", "sudo_root": True, "harness_versions": True,
                      "dhcp": True, "configuration_partition": True, "data_partition": True}
            # Browser dependencies/private RAM handoff only; no provider login.
            browser_code = "import sys,stat,shutil;sys.path.insert(0,'/usr/lib/aguja');import auth,browser;u='https://claude.com/cai/oauth/authorize?client_id=aguja-fixture&response_type=code&code=true&state=synthetic-fixture&redirect_uri=http%3A%2F%2F127.0.0.1%3A8123%2Fcallback';s=auth.Session();assert s.offer(u);assert auth.current()['url']==u;assert stat.S_IMODE(s.directory.stat().st_mode)==0o700;assert stat.S_IMODE((s.directory/'request.json').stat().st_mode)==0o600;assert all(shutil.which(x) for x in ('chromium','Xorg','xterm','openbox','xdotool','xauth','aguja-browser-launch'));assert __import__('pathlib').Path('/usr/lib/aguja/browser-session').is_file();assert 'QR' not in ' '.join(auth.terminal_lines(auth.current(),80,24));s.close();assert auth.current() is None"
            browser_check = subprocess.run(remote + ["python3 -c " + shlex.quote(browser_code)], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
            (a.workdir / "browser-check.err").write_bytes(browser_check.stderr)
            if browser_check.returncode:
                raise ValueError("Navegador local o handoff privado falló")
            report.update(local_browser_dependencies=True, owner_only_volatile_auth=True,
                          native_loopback_callback_unchanged=True, synthetic_auth_fixture_only=True,
                          provider_consent_and_inference_tested=False)
            onboarding = "set -e; test $(getent passwd aguja | cut -d: -f7) = /bin/zsh; systemctl is-active avahi-daemon; aguja status --json; aguja tools; test -s /usr/share/aguja/QUICKSTART.md; test -s /usr/share/aguja/AGENT-CONTEXT.md; test -s /etc/avahi/services/aguja-ssh.service; zsh -ic '[[ ${_comps[aguja]} == _aguja ]] && whence _zsh_autosuggest_start && whence _zsh_highlight'; avahi-browse -kprt _ssh._tcp"
            result = subprocess.run(remote + [onboarding], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
            (a.workdir / "onboarding.txt").write_text(result.stdout)
            if result.returncode:
                raise ValueError("Onboarding falló; consulta onboarding.txt")
            report.update(zsh_login_shell=True, command_completion=True, shell_plugins=True,
                          mdns_daemon=True, agent_guide=True, quickstart=True)
            report["mdns_ssh_service_resolved"] = any(line.startswith("=;") and ";_ssh._tcp;" in line for line in result.stdout.splitlines())
            if not report["mdns_ssh_service_resolved"]:
                raise ValueError("No se resolvió el anuncio SSH mDNS dentro del guest")
            current = next(json.loads(line) for line in result.stdout.splitlines() if line.startswith('{"hostname"'))
            if not current["connected"] or not current["mdns"]:
                raise ValueError("El estado no refleja IP y nombre mDNS actuales")
            report["current_ip_and_mdns"] = True
            login = list(remote)
            login.insert(len(login) - 1, "-tt")
            greeted = subprocess.run(login, env=remote_env, input="exit\n", capture_output=True, text=True, timeout=30)
            if greeted.returncode or "Agente remoto: aguja context" not in greeted.stdout:
                raise ValueError("La bienvenida SSH interactiva no muestra handover al agente")
            report["ssh_interactive_handover"] = True
            if a.activity:
                from verify_activity import verify
                def activity_screen(name):
                    qmp_command("screendump", {"filename": str((a.workdir / "screenshots" / name).resolve()), "format": "png"})
                report["activity"] = verify(remote, remote_env, a.workdir, activity_screen if a.screenshots else None)
            if a.screenshots:
                # Allow the local autologin to reach the live dashboard after SSH comes up.
                time.sleep(4)
                capture_screen()
                qmp_command("screendump", {"filename": str((a.workdir / "screenshots/dashboard.png").resolve()), "format": "png"})
                qmp_command("send-key", {"keys": [{"type": "qcode", "data": "1"}]})
                time.sleep(2)
                for char in "aguja sta":
                    qmp_command("send-key", {"keys": [{"type": "qcode", "data": "spc" if char == " " else char}], "hold-time": 40})
                    time.sleep(0.08)
                qmp_command("send-key", {"keys": [{"type": "qcode", "data": "tab"}]})
                time.sleep(1)
                qmp_command("send-key", {"keys": [{"type": "qcode", "data": "ret"}]})
                time.sleep(3)
                qmp_command("screendump", {"filename": str((a.workdir / "screenshots/zsh-status.png").resolve()), "format": "png"})
                completion_deadline = time.monotonic()+30
                trace_check = "import sys;sys.path.insert(0,'/usr/lib/aguja');import activity;assert any(c.get('transport')=='local' and c.get('command')=='aguja status' and c.get('exit')==0 for c in activity.snapshot()['commands'])"
                while time.monotonic()<completion_deadline:
                    trace = subprocess.run(remote+["python3 -c "+shlex.quote(trace_check)],env=remote_env,capture_output=True,timeout=15)
                    if trace.returncode==0:break
                    time.sleep(1)
                else:raise ValueError("Local status command did not complete")
                # Return from the newly instrumented local shell to the panel.
                # This must retain the real VT, not silently fall back to curses
                # because the shell was nested behind an SSH-style PTY relay.
                for char in "aguja":
                    qmp_command("send-key", {"keys": [{"type": "qcode", "data": char}], "hold-time": 40})
                    time.sleep(.08)
                qmp_command("send-key", {"keys": [{"type": "qcode", "data": "ret"}]})
                time.sleep(5)
                local_check = "import sys,os,fcntl,array;sys.path.insert(0,'/usr/lib/aguja');import activity;s=activity.snapshot();assert any(x.get('transport')=='local' for x in s['sessions']);assert any(c.get('transport')=='local' and c.get('command')=='aguja status' and c.get('exit')==0 for c in s['commands']);f=os.open('/dev/tty1',os.O_RDONLY);a=array.array('i',[0]);fcntl.ioctl(f,0x4B3B,a);os.close(f);assert a[0]==1"
                local_result = subprocess.run(remote + ["sudo -n python3 -c " + shlex.quote(local_check)], env=remote_env, capture_output=True, timeout=15)
                (a.workdir / "local-panel-check.err").write_bytes(local_result.stderr)
                if local_result.returncode:
                    raise ValueError("Local shell trace or graphical panel reopening failed")
                qmp_command("screendump", {"filename": str((a.workdir / "screenshots/local-panel-reopened.png").resolve()), "format": "png"})
                report.update(local_console_command_trace=True, local_panel_reopens_graphically=True)
                report["screenshots_captured"] = screenshot_count
                report["plymouth_theme_installed"] = True
            if a.config_mode == "default":
                report["default_password_auth"] = True
            elif a.config_mode == "key-only":
                report["key_only_mode"] = True
                pwssh = list(ssh)
                pwssh[pwssh.index("BatchMode=yes")] = "BatchMode=no"
                host = pwssh.pop()
                pwssh += ["-o", "PubkeyAuthentication=no", "-o", "PreferredAuthentications=password", host, "true"]
                attempt = subprocess.run(["sshpass", "-e"] + pwssh, env=dict(os.environ, SSHPASS="aguja"), stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
                if attempt.returncode == 0:
                    raise ValueError("Modo clave-only aceptó la contraseña de fábrica")
                report["default_password_rejected"] = True
            elif shutil.which("sshpass"):
                # No credentials on argv or in test output.
                pwssh = [v for v in ssh]
                pwssh[pwssh.index("BatchMode=yes")] = "BatchMode=no"
                pwssh += ["-o", "PubkeyAuthentication=no", "-o", "PreferredAuthentications=password"]
                # SSH options must precede the host.
                host = pwssh.pop(pwssh.index("aguja@127.0.0.1"))
                run("sshpass", "-e", *(pwssh + [host, "true"]), env=dict(os.environ, SSHPASS=password), stdin=subprocess.DEVNULL, capture_output=True)
                report["password_auth"] = True
            else:
                report["password_auth"] = "not tested (sshpass missing)"
            offline = "sudo -n unshare -n runuser -u aguja -- env -i HOME=/home/aguja PATH=/usr/local/bin:/usr/bin:/bin TERM=dumb sh -c 'set -e; codex --version; agy --version; claude --version; opencode --version'"
            result = subprocess.run(remote + [offline], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
            (a.workdir / "offline-cli-versions.txt").write_text(result.stdout)
            if result.returncode:
                raise ValueError("Un CLI no ejecuta su versión sin red")
            report['all_four_clis_without_network'] = True
            if a.restart_check:
                old_boot = subprocess.check_output(remote + ['cat /proc/sys/kernel/random/boot_id'], env=remote_env, stdin=subprocess.DEVNULL, text=True).strip()
                subprocess.run(remote + ['sudo -n systemctl reboot'], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
                restart_deadline = time.monotonic() + a.timeout
                while time.monotonic() < restart_deadline:
                    if proc.poll() is not None:
                        raise ValueError('QEMU terminó antes de reiniciar el clon')
                    result = subprocess.run(remote + ['test -f /run/aguja-ready && cat /proc/sys/kernel/random/boot_id'], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and result.stdout.strip() != old_boot:
                        break
                    time.sleep(3)
                else:
                    raise ValueError('El clon no volvió tras el reinicio')
                result = subprocess.run(remote + [check + '; ' + offline], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
                (a.workdir / 'restart-checks.txt').write_text(result.stdout)
                (a.workdir / 'restart-checks.err').write_text(result.stderr)
                if result.returncode:
                    raise ValueError('Comprobaciones tras reiniciar fallaron')
                report['restart_and_cli_persistence'] = True
            (a.workdir / "result.json").write_text(json.dumps(report, indent=2))
            print(json.dumps(report), flush=True)
            subprocess.run(remote + ["sudo -n poweroff"], env=remote_env, stdin=subprocess.DEVNULL, capture_output=True)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=10)
        finally:
            if qmp_file is not None:
                qmp_file.close()
            if qmp is not None:
                qmp.close()
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        # Errors expose only command/paths, never the configuration or password.
        print("VM smoke no completado: " + str(e), file=sys.stderr)
        sys.exit(1)
