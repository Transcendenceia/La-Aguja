# LA AGUJA IoT — Nodos Microcontrolador Nativos de Tailnet

[English](IOT.md) · [README del módulo IoT](../iot/README.es.md) · [Especificación IoT en Flash Imager](design/iot-imager-integration.md) · [Registro de placas](../iot/boards.json)

**LA AGUJA IoT** traslada la filosofía de LA AGUJA — entrada pequeña, control real, sin relay propietario — a microcontroladores de bolsillo. Una placa ESP32 compatible se conecta a Wi-Fi, entra directamente en tu **Tailscale o Headscale propio** por WireGuard/DERP y ofrece un centro móvil de operaciones controlable por agentes IA u operadores.

## Capacidades de cada nodo

- **Conectividad Tailnet (MicroLink v2.3.0):** protocolo de control ts2021 Noise sobre TLS, plano de datos WireGuard en lwIP, STUN, DISCO NAT traversal y respaldo por DERP. Compatible con Tailscale y Headscale autohospedado (incluyendo DERP embebido).
- **Exit node + Subnet router dinámico:** anuncia `0.0.0.0/0` y `::/0` (exit node con lwIP NAPT/NAT66), la subred Wi-Fi upstream detectada dinámicamente por DHCP, la subred local del SoftAP NAT (`192.168.4.0/24`) y rutas CIDR personalizadas en NVS. Incluye un **DNS relay UDP 53** escuchando en la IP VPN para clientes que usen el nodo como salida.
- **Wi-Fi STA multi-SSID + SoftAP NAT:** hasta 8 perfiles Wi-Fi ordenados en NVS con conmutación automática, control de potencia TX y ahorro energético, más SoftAP NAT activable en caliente (`aguja-iot-ap`).
- **Control de hardware al nanómetro (Seeed Studio XIAO ESP32-C6):**
  - Conmutador de antena RF (`GPIO3` enable + `GPIO14` cerámica interna vs u.FL externa) inicializado antes del Wi-Fi y conmutable en vivo.
  - LED de usuario (`GPIO15`, activo en LOW): estado automático, encendido, apagado, parpadeo o PWM.
  - Los 11 GPIOs de borde (`D0`–`D10`): modo (`in`/`out`/`od`), pull-up/down, lectura/escritura/pulso y presets de arranque en NVS.
  - PWM LEDC (5 canales), ADC1 calibrado en mV (`D0`–`D2`), sensor interno de temperatura y escalado dinámico de CPU (`40`/`80`/`160` MHz).
  - **I2C maestro** (`D4`/`D5`, escaneo y transacciones crudas), **puente UART1** (`D6`/`D7`) y **SPI maestro** (`D8`–`D10`) para operar sensores, displays o módems externos sin recompilar.
- **Caja de herramientas NetOps:** ping ICMP remoto, sondeo TCP de puertos, resolución DNS, Wake-on-LAN, escaneo Wi-Fi 2.4 GHz, listado de clientes SoftAP y beacons UDP periódicos hacia el host del agente.
- **Motor de reglas local:** hasta 8 reglas en NVS (`gpio_high`/`gpio_low`/`adc_gt`/`adc_lt`/`temp_gt` → `gpio_set`/`led`/`udp_alert`).
- **OTA dual-slot con rollback automático:** particionado de 4 MB (`ota_0` 1920 KB + `ota_1` 1920 KB). Una imagen subida sobre Tailscale solo se confirma tras alcanzar `CONNECTED`; si falla, el bootloader revierte automáticamente a la anterior.

## API REST para agentes (`/api/v1/*`)

Accesible solo por la IP WireGuard de la tailnet (`http://<hostname>/`) por defecto (`http_allow_lan=false`). Todos los endpoints excepto `/api/v1/health` exigen `Authorization: Bearer <token>`, `X-Aguja-Token: <token>` o HTTP Basic (`admin:<token>`).

| Grupo | Endpoints |
| --- | --- |
| Sistema y telemetría | `GET /` (Web UI oscura), `GET /api/v1/health`, `GET /api/v1/status`, `GET /api/v1/peers`, `POST /api/v1/system/cpu`, `POST /api/v1/system/sleep`, `POST /api/v1/system/restart-tailnet`, `POST /api/v1/system/reboot`, `POST /api/v1/system/factory-reset` |
| Config y reglas | `GET/PUT /api/v1/config`, `GET/PUT /api/v1/rules`, `GET/DELETE /api/v1/logs`, `POST /api/v1/logs/level` |
| Hardware (XIAO C6) | `POST /api/v1/hw/antenna`, `POST /api/v1/hw/led`, `GET/POST /api/v1/hw/gpio`, `POST /api/v1/hw/pwm`, `GET /api/v1/hw/adc`, `GET /api/v1/hw/i2c/scan`, `POST /api/v1/hw/i2c/config`, `POST /api/v1/hw/i2c/xfer`, `POST /api/v1/hw/uart/config`, `POST /api/v1/hw/uart/tx`, `GET /api/v1/hw/uart/rx`, `POST /api/v1/hw/spi/xfer` |
| Wi-Fi y NetOps | `GET /api/v1/wifi/scan`, `POST /api/v1/wifi/ap`, `POST /api/v1/wifi/rf`, `POST /api/v1/net/ping`, `POST /api/v1/net/probe`, `POST /api/v1/net/dns`, `POST /api/v1/net/wol`, `GET /api/v1/net/clients`, `POST /api/v1/net/beacon` |
| Firmware OTA | `POST /api/v1/ota` (cuerpo `.bin` crudo → slot OTA inactivo → reinicio con protección de rollback) |

## CLI USB-Serial (rescate local)

Conecta a `115200` baudios por USB-Serial/JTAG nativo (`/dev/ttyACM0`):

`help`, `status`, `token`, `config`, `scan`, `wifi <ssid> <pass>`, `authkey <key>`, `antenna <ceramic|ufl>`, `led <status|on|off|blink>`, `lan <on|off>`, `reboot`, `factory-reset`.

## Límites reales (ESP32-C6 sin PSRAM)

- WireGuard en espacio de usuario + NAPT sobre un RISC-V monocore de 160 MHz busca **alcance y operación remota** (~0.5–1.5 Mbps): ideal para control por agentes, saltos SSH/API, telemetría IoT, Wake-on-LAN y diagnóstico LAN; no para streaming de vídeo ni copias masivas.
- Para operar estable en 512 KB de SRAM sin PSRAM con tailnets Headscale multi-nodo (`MapResponse` de ~50 KB), `iot/firmware/esp32c6` usa `CONFIG_MBEDTLS_SSL_IN_CONTENT_LEN=16384` y parches de parseo JSON streaming + drenaje 0-RAM en reconexiones sobre MicroLink (detallados en [THIRD-PARTY-NOTICES.md](../iot/THIRD-PARTY-NOTICES.md)).
