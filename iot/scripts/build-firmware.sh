#!/usr/bin/env bash
set -euo pipefail

# Build sanitized generic firmware bundles (ESP32-C6 & ESP32-S3) into iot/prebuilt/<board_id>/
# with SHA-256 manifests ready for LA AGUJA Flash Imager (IoT tab).
# Requires ESP-IDF v5.5+ in $IDF_PATH (or ~/esp/esp-idf).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FW_DIR="${ROOT_DIR}/iot/firmware/esp32c6"
OUT_ROOT="${1:-${ROOT_DIR}/iot/prebuilt}"
IDF_PATH="${IDF_PATH:-$HOME/esp/esp-idf}"

if [[ ! -f "${IDF_PATH}/export.sh" ]]; then
  echo "ESP-IDF not found at ${IDF_PATH}. Set IDF_PATH and retry." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${IDF_PATH}/export.sh" >/dev/null
mkdir -p "${OUT_ROOT}"

build_target() {
  local TARGET="$1"
  local BOARD_ID="$2"
  local BDIR
  BDIR="$(mktemp -d "/tmp/aguja-iot-build-${TARGET}-XXXXXX")"
  local ODIR="${OUT_ROOT}/${BOARD_ID}"
  rm -rf "${FW_DIR}/sdkconfig" "${FW_DIR}/sdkconfig.old" "${FW_DIR}/dependencies.lock"
  mkdir -p "${ODIR}"

  echo "=== Building ${TARGET} -> ${BOARD_ID} ==="
  idf.py -C "${FW_DIR}" -B "${BDIR}" -D IDF_TARGET="${TARGET}" build

  cp "${BDIR}/bootloader/bootloader.bin" "${ODIR}/bootloader.bin"
  cp "${BDIR}/partition_table/partition-table.bin" "${ODIR}/partition-table.bin"
  cp "${BDIR}/ota_data_initial.bin" "${ODIR}/ota_data_initial.bin"
  cp "${BDIR}/aguja_iot.bin" "${ODIR}/aguja_iot.bin"
  cp "${BDIR}/flasher_args.json" "${ODIR}/flasher_args.json"

  python3 - "${ODIR}" "${BOARD_ID}" "${TARGET}" <<'PY'
import hashlib, json, os, sys
odir, board_id, target = sys.argv[1:4]
fa = json.load(open(os.path.join(odir, "flasher_args.json")))
files = {}
for name, offset in [
    ("bootloader.bin", fa["bootloader"]["offset"]),
    ("partition-table.bin", fa["partition-table"]["offset"]),
    ("ota_data_initial.bin", fa["otadata"]["offset"]),
    ("aguja_iot.bin", fa["app"]["offset"]),
]:
    p = os.path.join(odir, name)
    data = open(p, "rb").read()
    files[name] = {
        "offset": offset,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
manifest = {
    "schema": 1,
    "board_id": board_id,
    "chip": target,
    "version": "1.3.0",
    "flash_mode": fa["flash_settings"]["flash_mode"],
    "flash_size": fa["flash_settings"]["flash_size"],
    "flash_freq": fa["flash_settings"]["flash_freq"],
    "nvs_offset": "0x9000",
    "nvs_size": 49152,
    "files": files,
}
with open(os.path.join(odir, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
PY

  rm -rf "${BDIR}" "${FW_DIR}/sdkconfig" "${FW_DIR}/sdkconfig.old" "${FW_DIR}/dependencies.lock"
}

build_target esp32c6 seeed-xiao-esp32c6
build_target esp32s3 esp32s3-wroom-n16r8
echo "Built generic firmware bundles in ${OUT_ROOT}"
