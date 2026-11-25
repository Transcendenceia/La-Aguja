# LA AGUJA IoT (Experimental)

[English](README.md) · [Arquitectura IoT completa](../docs/IOT.es.md) · [Diseño de integración en Flash Imager](../docs/design/iot-imager-integration.md) · [Avisos de terceros](THIRD-PARTY-NOTICES.md)

**LA AGUJA IoT** amplía el ecosistema de LA AGUJA (junto a **Flash Imager** y **Rescue Disk**) hacia **nodos microcontrolador nativos de tailnet**, pensados como centros móviles de operaciones controlables al nanómetro por agentes IA y operadores humanos.

Al encender una placa compatible y conectarse a Wi-Fi, se registra automáticamente en tu **Tailscale o Headscale propio** con **exit node**, **subnet router dinámico**, **SoftAP NAT**, **control completo de hardware** (conmutador de antena RF, GPIO, PWM, ADC, I2C, UART, SPI, temperatura), **herramientas de red**, **configuración persistente en NVS editable en caliente** y **OTA dual-slot con rollback automático**.

## Estructura del módulo

| Ruta | Propósito |
| --- | --- |
| `iot/boards.json` | Manifiesto legible por máquina (USB VID/PID, offsets de flash, mapa de pines y esquema NVS) para el futuro apartado **IoT de Flash Imager**. |
| `iot/firmware/esp32c6/` | Firmware ESP-IDF v5.5 para **Seeed Studio XIAO ESP32-C6** (`ESP32-C6FH4`, 4 MB flash, 512 KB SRAM sin PSRAM) sobre MicroLink v2.3.0 parcheado. |
| `iot/cli/aguja-iot.py` | CLI en Python 3 sin dependencias externas para controlar cualquier nodo IoT desde un agente o terminal sobre la tailnet. |
| `iot/THIRD-PARTY-NOTICES.md` | Licencias y registro de parches no-PSRAM sobre MicroLink, wireguard-lwip y ESP-IDF. |

## Placas soportadas

| Placa | SoC | Estado | Flash / RAM |
| --- | --- | --- | --- |
| **Seeed Studio XIAO ESP32-C6** | ESP32-C6FH4 (RISC-V 160 MHz) | **Verificada en hardware real** (v1.2.0) | 4 MB Flash / 512 KB SRAM (sin PSRAM) |
| ESP32-S3 N16R8 | ESP32-S3 (Xtensa doble núcleo) | Planificada (`boards.json` preparado) | 16 MB Flash / 8 MB PSRAM |

## Compilación y flasheo rápido (ESP-IDF v5.5+)

```sh
cd iot/firmware/esp32c6
cp sdkconfig.secrets.example sdkconfig.secrets
# Edita sdkconfig.secrets con tu Wi-Fi, clave Headscale/Tailscale y token (nunca lo subas a Git)

. ~/esp/esp-idf/export.sh
idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.secrets" set-target esp32c6
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

Cuando el nodo entre a la tailnet, aprueba sus rutas (`0.0.0.0/0`, `::/0`, subred Wi-Fi upstream y `192.168.4.0/24`) en Tailscale/Headscale y contrólalo a distancia:

```sh
python3 iot/cli/aguja-iot.py --host aguja-iot --token "$AGUJA_IOT_TOKEN" status
python3 iot/cli/aguja-iot.py --host aguja-iot --token "$AGUJA_IOT_TOKEN" wifi-scan
python3 iot/cli/aguja-iot.py --host aguja-iot --token "$AGUJA_IOT_TOKEN" ota iot/firmware/esp32c6/build/aguja_iot.bin
```

## Seguridad e higiene pública

- El plano de control HTTP escucha **solo en la IP WireGuard de la tailnet** por defecto (`http_allow_lan=false`) y exige autenticación Bearer/Basic en todos los endpoints salvo `/api/v1/health`.
- Nunca subas `sdkconfig.secrets`, `sdkconfig` ni volcados de flash. Los binarios genéricos no llevan credenciales embebidas y se aprovisionan por NVS, CLI USB-Serial o mediante el futuro apartado **IoT de Flash Imager**.
