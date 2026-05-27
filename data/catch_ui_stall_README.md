# catch_ui_stall.sh

Diagnostic capture script for UI stall events on the C3. Captures thread
states, memory maps, GPU state, Weston compositor info, and dmesg when the
UI watchdog fires.

## Deploy

```bash
scp data/catch_ui_stall.sh comma@<ip>:/data/catch_ui_stall.sh
ssh comma@<ip> chmod +x /data/catch_ui_stall.sh
```

## Usage

**Manual** — SSH in during a stall (you have ~5s before watchdog kills UI):
```bash
/data/catch_ui_stall.sh
```

**Auto-watch** — run in background, captures automatically when stall logs appear:
```bash
nohup /data/catch_ui_stall.sh --watch > /data/log/stall_watcher.log 2>&1 &
```

Output goes to `/data/log/ui_stall_capture_<timestamp>/`:
- `threads.txt` — wchan, syscall, state per thread
- `maps.txt` — memory map (for resolving futex addresses to libraries)
- `gpu.txt` — Adreno 630 busy/clock/power state
- `weston.txt` — compositor state and fd count
- `dmesg.txt` — last 100 kernel messages
- `meminfo.txt` — system memory
- `proc_status.txt` — full process status
- `fd_count.txt` — open file descriptor count (leak check)

## Background

The UI stall manifests as `futex_wait_queue_me` on the main thread after extended
idle onroad periods. Root cause is not yet identified — suspected Qt/Wayland/GPU
interaction. See `project_docs/phase2-starpilot-2026-05-27-ui-stall-investigation.md`.
