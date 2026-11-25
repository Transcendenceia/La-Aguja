# Third-Party Notices — LA AGUJA IoT

LA AGUJA IoT application code (`iot/firmware/esp32c6/main/`, `iot/cli/`, `iot/boards.json`, and documentation) is licensed under **GPL-3.0-or-later** (see repository root `LICENSE`).

Third-party components bundled or linked by the firmware retain their original licenses:

| Component | Upstream | License | Notes |
| --- | --- | --- | --- |
| MicroLink | `https://github.com/CamM2325/microlink` (v2.3.0) | MIT | Tailscale/Headscale ts2021 control plane, DERP, STUN, DISCO, subnet router/exit node, OTA rollback. Vendored in `iot/firmware/esp32c6/components/microlink/`. |
| wireguard-lwip | Bundled inside MicroLink (`components/wireguard_lwip`) | BSD-3-Clause | Userspace WireGuard data plane on lwIP. |
| ESP-IDF | `https://github.com/espressif/esp-idf` (v5.5.x) | Apache-2.0 | Espressif IoT Development Framework, lwIP (BSD-3-Clause), FreeRTOS (MIT), mbedTLS (Apache-2.0 / GPL-2.0-or-later). |

## Local patches applied to vendored MicroLink (non-PSRAM ESP32-C6 support)

To run reliably inside the 512 KB internal SRAM of an ESP32-C6 without PSRAM on multi-node Headscale tailnets (~50 KB MapResponses):

1. `components/microlink/Kconfig`: lowered minimum `ML_H2_BUFFER_SIZE_KB` / `ML_JSON_BUFFER_SIZE_KB` range from `64` to `16`.
2. `components/microlink/src/ml_coord.c`:
   - Replaced doubling `malloc+memcpy+free` in `lp_reserve()` with 4 KB-aligned `realloc()` and exact single-shot preallocation using the 4-byte length prefix on stream 5 to eliminate heap fragmentation.
   - Added a low-RAM top-level JSON scanner (`lp_handle_large_message`) that parses `Node`, `DERPMap`, and `Peers` one object at a time (~3 KB cJSON peak instead of >90 KB).
   - Added a zero-RAM reconnect drainer (`lp.discard_rem`) for Headscale deployments that resend the full peer map on reconnect even when `OmitPeers=true`, keeping DERP and WireGuard live without exhausting SRAM.
