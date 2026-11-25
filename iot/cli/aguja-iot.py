#!/usr/bin/env python3
"""Aguja-IoT Agent CLI — Control Seeed XIAO ESP32-C6 over Tailscale/Headscale."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CFG_PATH = Path.home() / ".config" / "aguja-iot" / "cli.json"


def load_cli_cfg():
    if CFG_PATH.exists():
        try:
            return json.loads(CFG_PATH.read_text())
        except Exception:
            pass
    return {}


def req(host, token, method, path, body=None, raw_bytes=None, timeout=15):
    url = f"http://{host}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if raw_bytes is not None:
        data = raw_bytes
        headers["Content-Type"] = "application/octet-stream"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            txt = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(txt)
            except Exception:
                return {"raw": txt}
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request error ({url}): {e}", file=sys.stderr)
        sys.exit(1)


def main():
    saved = load_cli_cfg()
    p = argparse.ArgumentParser(prog="aguja-iot", description="Control aguja-iot ESP32-C6 over Tailnet")
    p.add_argument("--host", default=os.environ.get("AGUJA_IOT_HOST", saved.get("host", "aguja-iot")))
    p.add_argument("--token", default=os.environ.get("AGUJA_IOT_TOKEN", saved.get("token", "")))
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")
    sub.add_parser("status")
    sub.add_parser("peers")

    c_cfg = sub.add_parser("config")
    c_cfg.add_argument("action", choices=["get", "set"])
    c_cfg.add_argument("--json", dest="json_str", help="JSON patch string for 'set'")
    c_cfg.add_argument("--secrets", action="store_true")

    c_ant = sub.add_parser("antenna")
    c_ant.add_argument("mode", choices=["ceramic", "ufl"])
    c_ant.add_argument("--persist", action="store_true")

    c_led = sub.add_parser("led")
    c_led.add_argument("mode", choices=["status", "on", "off", "blink", "pwm"])
    c_led.add_argument("--pwm", type=int, default=50)
    c_led.add_argument("--ms", type=int, default=300)
    c_led.add_argument("--persist", action="store_true")

    c_gpio = sub.add_parser("gpio")
    c_gpio.add_argument("--pin", type=int)
    c_gpio.add_argument("--mode", choices=["in", "out", "od"])
    c_gpio.add_argument("--pull", choices=["none", "up", "down"])
    c_gpio.add_argument("--level", type=int, choices=[0, 1])
    c_gpio.add_argument("--pulse-ms", type=int)

    c_pwm = sub.add_parser("pwm")
    c_pwm.add_argument("--channel", type=int, default=0)
    c_pwm.add_argument("--pin", type=int, required=True)
    c_pwm.add_argument("--freq", type=int, default=1000)
    c_pwm.add_argument("--duty", type=float, default=50.0)
    c_pwm.add_argument("--stop", action="store_true")

    sub.add_parser("adc")
    sub.add_parser("i2c-scan")
    sub.add_parser("wifi-scan")
    sub.add_parser("clients")

    c_ping = sub.add_parser("ping")
    c_ping.add_argument("target")
    c_ping.add_argument("--count", type=int, default=3)

    c_probe = sub.add_parser("probe")
    c_probe.add_argument("target")
    c_probe.add_argument("port", type=int)

    c_wol = sub.add_parser("wol")
    c_wol.add_argument("mac")

    c_dns = sub.add_parser("dns")
    c_dns.add_argument("target")

    c_logs = sub.add_parser("logs")
    c_logs.add_argument("--clear", action="store_true")
    c_logs.add_argument("--tag")
    c_logs.add_argument("--level")

    c_ota = sub.add_parser("ota")
    c_ota.add_argument("bin_path")

    c_cpu = sub.add_parser("cpu")
    c_cpu.add_argument("mhz", type=int, choices=[40, 80, 160])
    c_cpu.add_argument("--persist", action="store_true")

    sub.add_parser("restart-tailnet")
    sub.add_parser("reboot")

    args = p.parse_args()
    if args.cmd != "health" and not args.token:
        print("Missing token: pass --token, set AGUJA_IOT_TOKEN, or save ~/.config/aguja-iot/cli.json", file=sys.stderr)
        sys.exit(2)

    if args.cmd == "health":
        res = req(args.host, args.token, "GET", "/api/v1/health")
    elif args.cmd == "status":
        res = req(args.host, args.token, "GET", "/api/v1/status")
    elif args.cmd == "peers":
        res = req(args.host, args.token, "GET", "/api/v1/peers")
    elif args.cmd == "config":
        if args.action == "get":
            res = req(args.host, args.token, "GET", "/api/v1/config" + ("?secrets=1" if args.secrets else ""))
        else:
            res = req(args.host, args.token, "PUT", "/api/v1/config", json.loads(args.json_str))
    elif args.cmd == "antenna":
        res = req(args.host, args.token, "POST", "/api/v1/hw/antenna", {"external": args.mode == "ufl", "persist": args.persist})
    elif args.cmd == "led":
        res = req(args.host, args.token, "POST", "/api/v1/hw/led", {"mode": args.mode, "pwm_pct": args.pwm, "blink_ms": args.ms, "persist": args.persist})
    elif args.cmd == "gpio":
        if args.pin is None:
            res = req(args.host, args.token, "GET", "/api/v1/hw/gpio")
        else:
            body = {"pin": args.pin}
            if args.mode: body["mode"] = args.mode
            if args.pull: body["pull"] = args.pull
            if args.level is not None: body["level"] = args.level
            if args.pulse_ms: body["pulse_ms"] = args.pulse_ms
            res = req(args.host, args.token, "POST", "/api/v1/hw/gpio", body)
    elif args.cmd == "pwm":
        res = req(args.host, args.token, "POST", "/api/v1/hw/pwm", {"channel": args.channel, "pin": args.pin, "freq_hz": args.freq, "duty_pct": args.duty, "stop": args.stop})
    elif args.cmd == "adc":
        res = req(args.host, args.token, "GET", "/api/v1/hw/adc")
    elif args.cmd == "i2c-scan":
        res = req(args.host, args.token, "GET", "/api/v1/hw/i2c/scan")
    elif args.cmd == "wifi-scan":
        res = req(args.host, args.token, "GET", "/api/v1/wifi/scan", timeout=25)
    elif args.cmd == "clients":
        res = req(args.host, args.token, "GET", "/api/v1/net/clients")
    elif args.cmd == "ping":
        res = req(args.host, args.token, "POST", "/api/v1/net/ping", {"host": args.target, "count": args.count}, timeout=20)
    elif args.cmd == "probe":
        res = req(args.host, args.token, "POST", "/api/v1/net/probe", {"host": args.target, "port": args.port})
    elif args.cmd == "wol":
        res = req(args.host, args.token, "POST", "/api/v1/net/wol", {"mac": args.mac})
    elif args.cmd == "dns":
        res = req(args.host, args.token, "POST", "/api/v1/net/dns", {"host": args.target})
    elif args.cmd == "logs":
        if args.clear:
            res = req(args.host, args.token, "DELETE", "/api/v1/logs")
        elif args.tag and args.level:
            res = req(args.host, args.token, "POST", "/api/v1/logs/level", {"tag": args.tag, "level": args.level})
        else:
            res = req(args.host, args.token, "GET", "/api/v1/logs")
            print(res.get("logs", ""))
            return
    elif args.cmd == "ota":
        data = Path(args.bin_path).read_bytes()
        print(f"Uploading {len(data)} bytes OTA to {args.host}...", file=sys.stderr)
        res = req(args.host, args.token, "POST", "/api/v1/ota", raw_bytes=data, timeout=180)
    elif args.cmd == "cpu":
        res = req(args.host, args.token, "POST", "/api/v1/system/cpu", {"mhz": args.mhz, "persist": args.persist})
    elif args.cmd == "restart-tailnet":
        res = req(args.host, args.token, "POST", "/api/v1/system/restart-tailnet", {})
    elif args.cmd == "reboot":
        res = req(args.host, args.token, "POST", "/api/v1/system/reboot", {})

    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
