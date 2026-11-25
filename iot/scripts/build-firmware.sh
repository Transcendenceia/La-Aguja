#!/usr/bin/env bash
set -euo pipefail

# Build sanitized generic firmware bundles for the entire ESP32 family
# (ESP32-C6, ESP32-S3 Octal PSRAM, ESP32-S3 Standard, ESP32-C3, ESP32, ESP32-S2)
# into iot/prebuilt/<firmware_profile>/ with SHA-256 manifests for LA AGUJA Flash Imager.

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

build_profile() {
  local TARGET="$1"
  local PROFILE="$2"
  local EXTRA_DEFAULTS="${3:-}"
  local BDIR
  BDIR="$(mktemp -d "/tmp/aguja-iot-build-${PROFILE}-XXXXXX")"
  local ODIR="${OUT_ROOT}/${PROFILE}"
  rm -rf "${FW_DIR}/sdkconfig" "${FW_DIR}/sdkconfig.old" "${FW_DIR}/dependencies.lock"
  mkdir -p "${ODIR}"

  echo "=== Building target=${TARGET} profile=${PROFILE} ==="
  local DEFAULTS_ARG="sdkconfig.defaults;sdkconfig.defaults.${TARGET}"
  if [[ -n "${EXTRA_DEFAULTS}" ]]; then
    DEFAULTS_ARG="${DEFAULTS_ARG};${EXTRA_DEFAULTS}"
  fi
  idf.py -C "${FW_DIR}" -B "${BDIR}" -D IDF_TARGET="${TARGET}" -D "SDKCONFIG_DEFAULTS=${DEFAULTS_ARG}" build

  cp "${BDIR}/bootloader/bootloader.bin" "${ODIR}/bootloader.bin"
  cp "${BDIR}/partition_table/partition-table.bin" "${ODIR}/partition-table.bin"
  cp "${BDIR}/ota_data_initial.bin" "${ODIR}/ota_data_initial.bin"
  cp "${BDIR}/aguja_iot.bin" "${ODIR}/aguja_iot.bin"
  cp "${BDIR}/flasher_args.json" "${ODIR}/flasher_args.json"

  python3 - "${ODIR}" "${PROFILE}" "${TARGET}" <<'PY'
import hashlib, json, os, sys
odir, profile, target = sys.argv[1:4]
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
    "profile": profile,
    "chip": target,
    "version": "1.4.0",
    "flash_mode": fa["flash_settings"]["flash_mode"],
    "flash_size": "detect",
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

build_profile esp32c6 esp32c6
build_profile esp32s3 esp32s3-oct
build_profile esp32s3 esp32s3-std sdkconfig.defaults.esp32s3.std
build_profile esp32c3 esp32c3
build_profile esp32   esp32
build_profile esp32s2 esp32s2

echo "=== ALL ESP32 FAMILY FIRMWARE BUNDLES READY ==="
ls -lh "${OUT_ROOT}"/*/aguja_iot.bin
