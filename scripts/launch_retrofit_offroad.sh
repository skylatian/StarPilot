#!/usr/bin/env bash
# Seed retrofit CarParams and launch the c3 UI offroad, for settings menus gated on the platform.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

FINGERPRINT_NAME="TOYOTA_COROLLA_RETROFIT"
SEED=1

usage() {
  cat <<EOF
Usage: scripts/launch_retrofit_offroad.sh [--fingerprint NAME] [--no-seed]

  --fingerprint NAME  Platform to impersonate (default: ${FINGERPRINT_NAME})
  --no-seed           Skip re-seeding params (faster; params persist in ~/.comma/params)

The Retrofit page gate ORs CarParamsPersistent.carFingerprint with getenv("FINGERPRINT"),
so both the seed and the env var are set here.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --fingerprint) FINGERPRINT_NAME="$2"; shift 2 ;;
    --no-seed) SEED=0; shift ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ "${SEED}" == "1" ]]; then
  echo "==> seeding params for ${FINGERPRINT_NAME}"
  ./dev python scripts/seed_retrofit_params.py --fingerprint "${FINGERPRINT_NAME}"
fi

echo "==> launching c3 UI offroad as ${FINGERPRINT_NAME}"
FINGERPRINT="${FINGERPRINT_NAME}" ./c3
