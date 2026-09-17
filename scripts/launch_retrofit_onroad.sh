#!/usr/bin/env bash
# Stage a local route and launch the desktop UI onroad against it.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

LOG_DIR="${SP_RETROFIT_LOG_DIR:-${ROOT_DIR}/../logs}"
STAGE_DIR="${SP_RETROFIT_STAGE_DIR:-${TMPDIR:-/tmp}/starpilot_routes}"
# same pinned baseline route as scripts/carstate_check.py
DEFAULT_RLOG="b22b100698b34d9f_00000256--3472968bc9--1--rlog.zst"
RLOG=""
ONROAD_ARGS=()

usage() {
  cat <<EOF
Usage: scripts/launch_retrofit_onroad.sh [rlog] [-- <onroad args>]

  rlog    Path to an rlog (.zst/.bz2) from the route to replay.
          Defaults to the pinned baseline route ${DEFAULT_RLOG}
  --      Remaining args are passed to ./onroad (default: --c3)

Replay's loadFromLocal() only scans directories named <route>--<seg>/, so the flat
comma-explorer files in ${LOG_DIR} are staged as symlinks under ${STAGE_DIR} first.

The route's own initData params are seeded by ./onroad, so a retrofit route restores
CarParamsPersistent with carFingerprint=TOYOTA_COROLLA_RETROFIT automatically.

Examples:
  scripts/launch_retrofit_onroad.sh
  scripts/launch_retrofit_onroad.sh ../logs/b22b100698b34d9f_00000256--3472968bc9--1--rlog.zst
  scripts/launch_retrofit_onroad.sh -- --c3 --galaxy
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --) shift; ONROAD_ARGS+=("$@"); break ;;
    *)
      if [[ -z "${RLOG}" ]]; then RLOG="$1"; shift; else ONROAD_ARGS+=("$1"); shift; fi
      ;;
  esac
done

if [[ ${#ONROAD_ARGS[@]} -eq 0 ]]; then
  ONROAD_ARGS=(--c3)
fi

if [[ -z "${RLOG}" ]]; then
  RLOG="${LOG_DIR}/${DEFAULT_RLOG}"
  if [[ ! -f "${RLOG}" ]]; then
    echo "Baseline rlog not found: ${RLOG}" >&2
    echo "logs/ is not in git, so pass an rlog explicitly or set SP_RETROFIT_LOG_DIR." >&2
    exit 1
  fi
  echo "Using pinned baseline rlog: ${RLOG}"
fi

if [[ ! -f "${RLOG}" ]]; then
  echo "No such rlog: ${RLOG}" >&2
  exit 1
fi

base="$(basename "${RLOG}")"
log_dir="$(cd "$(dirname "${RLOG}")" && pwd)"

if [[ ! "${base}" =~ ^([A-Za-z0-9]+)_(.+)--([0-9]+)--rlog\.(zst|bz2)$ ]]; then
  echo "Cannot derive a route from '${base}' (expected <dongle>_<route>--<seg>--rlog.zst)." >&2
  exit 1
fi
dongle="${BASH_REMATCH[1]}"
route="${BASH_REMATCH[2]}"

rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"
for f in "${log_dir}/${dongle}_${route}"--*--rlog.*; do
  [[ -f "${f}" ]] || continue
  seg="$(basename "${f}" | sed -E 's/.*--([0-9]+)--rlog\..*/\1/')"
  mkdir -p "${STAGE_DIR}/${dongle}|${route}--${seg}"
  ln -sf "${f}" "${STAGE_DIR}/${dongle}|${route}--${seg}/rlog.${f##*.}"
done

echo "Staged ${dongle}|${route} ($(find "${STAGE_DIR}" -name 'rlog.*' | wc -l | tr -d ' ') segments) in ${STAGE_DIR}"
exec ./onroad "${ONROAD_ARGS[@]}" --data_dir "${STAGE_DIR}" "${dongle}|${route}"
