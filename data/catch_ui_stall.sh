#!/bin/bash
# Auto-capture UI stall diagnostics
# Install: copy to /data/catch_ui_stall.sh && chmod +x /data/catch_ui_stall.sh
#
# Manual: /data/catch_ui_stall.sh
# Auto:   /data/catch_ui_stall.sh --watch
#   Polls every 2s, captures when stall log appears in /data/log/

set -euo pipefail

capture() {
  local UI_PID="$1"
  local TRIGGER="$2"
  local TS=$(date +%Y%m%d_%H%M%S)
  local OUT="/data/log/ui_stall_capture_${TS}"
  mkdir -p "$OUT"

  echo "=== UI stall capture: PID=$UI_PID trigger=$TRIGGER ===" | tee "$OUT/summary.txt"
  echo "timestamp: $(date -Iseconds)" >> "$OUT/summary.txt"
  echo "trigger: $TRIGGER" >> "$OUT/summary.txt"

  # Thread states
  for t in /proc/$UI_PID/task/*/; do
    tid=$(basename "$t")
    {
      echo "=== $tid ==="
      echo -n "comm: "; cat "$t/comm" 2>/dev/null || echo "?"
      echo -n "wchan: "; cat "$t/wchan" 2>/dev/null || echo "?"
      echo -n "state: "; awk '{print $3}' "$t/stat" 2>/dev/null || echo "?"
      echo -n "syscall: "; cat "$t/syscall" 2>/dev/null || echo "?"
      echo
    } >> "$OUT/threads.txt"
  done 2>/dev/null

  # Memory map (for mapping futex addresses to libraries)
  cat /proc/$UI_PID/maps > "$OUT/maps.txt" 2>/dev/null || true

  # Process status
  cat /proc/$UI_PID/status > "$OUT/proc_status.txt" 2>/dev/null || true

  # File descriptors (leak check)
  ls -la /proc/$UI_PID/fd 2>/dev/null | wc -l > "$OUT/fd_count.txt"

  # GPU state
  {
    echo "=== GPU ==="
    echo -n "gpubusy: "; cat /sys/class/kgsl/kgsl-3d0/gpubusy 2>/dev/null || echo "n/a"
    echo -n "gpu_clock: "; cat /sys/class/kgsl/kgsl-3d0/gpuclk 2>/dev/null || echo "n/a"
    echo -n "gpu_busy_pct: "; cat /sys/class/kgsl/kgsl-3d0/gpu_busy_percentage 2>/dev/null || echo "n/a"
    echo -n "devfreq_cur: "; cat /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq 2>/dev/null || echo "n/a"
    echo -n "power_state: "; cat /sys/class/kgsl/kgsl-3d0/power_state 2>/dev/null || echo "n/a"
  } > "$OUT/gpu.txt"

  # Kernel messages (last 100 lines around crash time)
  dmesg | tail -100 > "$OUT/dmesg.txt" 2>/dev/null || true

  # Weston compositor state
  {
    local WESTON_PID=$(pgrep -x weston 2>/dev/null || echo "")
    if [ -n "$WESTON_PID" ]; then
      echo "weston_pid: $WESTON_PID"
      echo -n "weston_state: "; cat /proc/$WESTON_PID/status 2>/dev/null | grep State || echo "?"
      echo -n "weston_fd_count: "; ls /proc/$WESTON_PID/fd 2>/dev/null | wc -l
    fi
  } > "$OUT/weston.txt" 2>/dev/null || true

  # System memory
  cat /proc/meminfo > "$OUT/meminfo.txt" 2>/dev/null || true

  echo "Captured to $OUT" | tee -a "$OUT/summary.txt"
}

if [ "${1:-}" = "--watch" ]; then
  echo "Watching for UI stalls (checking every 2s)..."
  LAST_STALL=""
  while true; do
    # Look for new stall logs
    NEWEST=$(ls -t /data/log/qt_ui_stall_*.log 2>/dev/null | head -1 || true)
    if [ -n "$NEWEST" ] && [ "$NEWEST" != "$LAST_STALL" ]; then
      LAST_STALL="$NEWEST"
      UI_PID=$(pgrep -x ui 2>/dev/null || echo "")
      if [ -n "$UI_PID" ]; then
        echo "Stall detected: $NEWEST"
        capture "$UI_PID" "auto:$NEWEST"
      fi
    fi
    sleep 2
  done
else
  # Manual capture
  UI_PID=$(pgrep -x ui 2>/dev/null || echo "")
  if [ -z "$UI_PID" ]; then
    echo "No ui process found"
    exit 1
  fi
  capture "$UI_PID" "manual"
fi
