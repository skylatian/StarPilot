I've verified the four key CAN claims from the helpers' reports—parser timeout logic, LKAS_HUD's source, radarUnavailable's definition, and the spoofed 0x201 gas sensor—all checking out against the code. Now I'll read the four section files in full and write up the report.

# StarPilot 7.0 alpha: retrofit research report

**Pinned commits.** All three branch heads matched their pins when cloned (2026-10-16), so no branch had moved.

| Repo | Branch | Commit |
|---|---|---|
| Alpha (`alpha:`) | firestar5683/StarPilot `SecretGoodStarPilot` | `01fd37fa7509174d71a626f66fa5567b4603b00e` ("Prebuilt runtime artifacts") |
| Our 6.7.8 fork (`fork:`) | skylatian/StarPilot `retrofit-dev-6.7.8-update-sandbox` | `38134a41cd3442bf9661da72a939f8f519f19f45` |
| Emulator (`emu:`) | skylatian/corolla_emulator `full-emulate` | `30ba722360f978490a8a0c3bd5956f6f8f2c0e5b` |

**Method.** I split the work across four helpers and re-checked the key claims myself. Those checks corrected three helper claims: the steer ratio (Q6), the policy `k_d` precedent (Q7), and the lane-centering line numbers (Q4). Citations are `repo:path:line`. Car paths are relative to `opendbc_repo/opendbc/car/toyota/` unless shown in full. Labels are **[C]** confirmed in code, **[I]** inferred (with the basis given) and **[NF]** not found.

---

## Summary

| # | Question | One-line answer | Confidence |
|---|---|---|---|
| 1 | CAN coverage | All 16 bus-0 (pt) messages the alpha reads are on our bus. The one gap is **LKAS_HUD 0x412, read from the bus-2 cam parser** (`carstate.py:189`), which no device sends. It is lazily added at 1 Hz with a 10 s timeout. Panda RX checks are all met. | [C], except the bus-2 topology [I] |
| 2 | Other `canValid=False` paths | All four card.py additions are Ioniq 6 only, so none can trip on our car. | [C] |
| 3 | Panda MCU | The C3 internal panda is DOS (STM32F4). F4 firmware **is still built and shipped**, and `STARPILOT_DEVELOPMENT.md` is wrong about that. A Toyota safety change can be built for F4. | MCU [I]; F4 build [C] |
| 4 | Lane centering | No Toyota is admitted. Admitting us needs one predicate clause plus a test change. | [C] |
| 5 | Auto Learn | `steerlearnerd` learns only ±3 % feed-forward / friction-threshold residuals at ≥ 15 m/s, and the centre objective is disabled. No brand allowlist exists, so a non-dashcam Toyota torque platform is eligible. It runs alongside torqued and does not override it. | [C] |
| 6 | Manual tuning | Production scope is Ioniq 6 and GM only. Toyota needs an allowlist entry, the production predicate and tests. Steer ratio can only be pinned through the GM-only geometry owner. | [C] |
| 7 | Vehicle policy | A policy owns `parent.pid` and can set `k_d`. **GV70 already does this as measurement damping.** | [C] |
| 8 | Settings migration | There is no supported import. Snapshots land in `/data/starpilot/snapshots/<sha>/`. Galaxy rejects 6.x backups. | [C] |
| 9 | Realtime inheritance | Nothing sets `SCHED_RESET_ON_FORK`. The confirmed realtime (SCHED_FIFO) spawners onroad are `selfdrived` (git, once) and `sensord` (sudo). `steerlearnerd` and its fit worker run SCHED_OTHER. | [C]; modeld/ui partly [I] |
| 10 | Odds and ends | radard: `radarUnavailable=False` with no radar leads to `commIssue`. door_locks: off. LKAS_HUD payload: zeroed sway fields. AOL: unreachable for us. | [C] |

---

## Q1. CAN message coverage

### Platform facts that decide the reads [C]

- **DBC.** `TOYOTA_COROLLA` and `TOYOTA_MATRIX_RETROFIT` have no static flags and use `dbc_dict('toyota_new_mc_pt_generated', 'toyota_adas')` (`values.py:206-215`). HYBRID, HAS_BSM, DISABLE_RADAR and LONG_FILTER can't be detected on our car (`interface.py:83-84, 117-118, 123-127, 147-153`).
- **Longitudinal.** `openpilotLongitudinalControl` is False for both platforms, which gives STOCK_LONGITUDINAL (`interface.py:134-135, 156, 165-166`).
  - safetyParam = 88 (EPS scale) | 256 (ALT_BRAKE) | 512 (stock long) = **856** (`values.py:609-611`, `interface.py:54-55`).
- **Steering.** Torque control, so the `LTA_STATE` reads are skipped (`carstate.py:135-137`).
- **Radar.** `radarUnavailable = Bus.radar not in DBC[candidate]` gives **False** for both platforms (`interface.py:120`).

### Alpha pt parser (bus 0), every frame [C]

At construction only `BLINKERS_STATE` is registered, and with NaN frequency (`carstate.py:238-249`). Every other message is added on first `vl[...]` access.

| Message | ID | Line(s) | Condition |
|---|---|---|---|
| VSC1S07 | 0x320 | 72 | not SECOC |
| BODY_CONTROL_STATE | 0x620 | 74-77 | always |
| BRAKE_MODULE | 0x224 | 79 | always |
| ESP_CONTROL | 0x3B7 | 80, 182 | always |
| PCM_CRUISE | 0x1D2 | 87, 175, 178 | always |
| GEAR_PACKET | 0x3BC | 88 | not SECOC |
| PRE_COLLISION (`cp_acc` = `cp` on non-TSS2) | 0x283 | 90 | not SECOC and not DISABLE_RADAR |
| WHEEL_SPEEDS, including the 4 FAULT bits | 0xAA | 93-96, 102-103 | always |
| STEER_ANGLE_SENSOR | 0x25 | 105-106 | always |
| STEER_TORQUE_SENSOR | 0x260 | 107, 110, 126-127 | always |
| BLINKERS_STATE (NaN, so it never affects validity) | 0x614 | 123-124 | always |
| EPS_STATUS.LKA_STATE | 0x262 | 132-133 | always |
| PCM_CRUISE_2 | 0x1D3 | 150, 152-153, 192 | not UNSUPPORTED_DSU. LOW_SPEED_LOCKOUT (173) is read only with openpilot long, so not for us. |
| PCM_CRUISE_SM | 0x399 | 151, 154 | not UNSUPPORTED_DSU |
| BODY_CONTROL_STATE_2 | 0x610 | 157 | always |
| LIGHT_STALK | 0x622 | 181 | always |

These are **not read** on our platforms:
- SECOC messages (83-85).
- DSU_CRUISE / PCM_CRUISE_ALT (146-148).
- ACC_CONTROL / PCS_HUD (TSS2 or LONG_FILTER).
- BSM.
- SDSU / PCM_CRUISE_4.

There are no StarPilot-side Toyota CAN readers: a full `\.vl\[` grep found none. `openpilot/starpilot/car/toyota/aol.py` makes no CAN reads [C].

### Alpha cam parser (bus 2) [C]

| Message | ID | Line | Registration |
|---|---|---|---|
| RSA1 | 0x489 | 224-227, 235 | NaN (`ignore_alive`). The `parser_expiry` read uses `.get` and never lazily adds it (`dashboard_speed_limit.py:55-61`). |
| **LKAS_HUD** | **0x412** | **189** | Read on every car except the Prius V, so **always** for us. **Lazy add, default 1 Hz.** |

### 6.7.8 `TOYOTA_COROLLA_RETROFIT` [C]

- There is **no cam parser** (`fork:…/toyota/carstate.py:332-336`), so LKAS_HUD and RSA1 are skipped (234, 277).
- The pt reads are the same 16 messages, plus ECON_ON/SPORT_ON from GEAR_PACKET (280-281). 6.7.8 does not read the 0xAA FAULT bits.
- **Extra read:** GAS_SENSOR 0x201 at 50 Hz (313-314) **if `enableGasInterceptorDEPRECATED`**. That flag is `0x201 in fingerprint[0] and openpilotLongitudinalControl` (`fork:…/toyota/interface.py:288`), and the retrofit turns openpilot long on with alpha long (282-285).
- `retrofit_diag` reads 0x69 and 0x500–0x505 with NaN frequency (`fork:retrofit_diag.py:23-27`).

### Production bus contents [C]

The main emulator's production flags are at `emu:fakeecu/corolla_emulator/corolla_emulator.ino:50-91`. They include FORCE_BRAKE_OFF and SEND_BACKGROUND_MSGS, both true.

| Source | ID | Rate | Gate / line |
|---|---|---|---|
| emulator | 0x1D2 PCM_CRUISE (with checksum) | 33 Hz | 1150-1152 |
| emulator | 0x1D3 PCM_CRUISE_2 | 33 Hz | 1154-1156 |
| emulator | 0x283 PRE_COLLISION | 33 Hz | 1158-1160 |
| emulator | 0x224 BRAKE_MODULE (always 0) | 40 Hz | 1141-1143 |
| emulator | 0x1C4, 0x4CB (EPS init), 0x320 | 50 Hz | 1124-1134 |
| emulator | **0x201 GAS_SENSOR (spoofed)** | 50 Hz | **`#if !REAL_PEDAL_CONNECTED`, 1115-1117** |
| emulator | 0x620 | 3 Hz | 1185-1187 |
| emulator | 0x500 / 0x503 | 2 Hz, plus on each cruise transition | 1216-1221 |
| emulator | 69 background IDs, zero payload (includes 0x3B7, 0x399, 0x610, 0x622, 0x489, 0x7E0–0x7E8) | ~10 Hz each | 665-702, 1173-1179 |
| emulator, not sent in production | 0xAA, 0xB4, 0x3BC, 0x25, 0x260, 0x262, 0x343 | — | 1097, 1101, 1111, 1120, 1167, 1195, 685 |
| VSS | 0xAA (raw = kph·100 + 6767) | 83 Hz | `emu:vss_speed/vss_speed.ino:237-245` |
| VSS | 0xB4 | 50 Hz | 247-255 |
| VSS | 0x3BC (FORCE_DRIVE, always D) | 10 Hz | 78, 257-270 |
| VSS | 0x502 / 0x505 | 2 Hz | 119-120 |
| stalk | 0x69 | 20 Hz | `emu:cruise_stalk/cruise_stalk.ino:390-396` |
| stalk | 0x614 | 20 Hz | 401-405 |
| stalk | 0x501 / 0x504 | 2 Hz | 175, 73 |
| real EPS | 0x260, 0x262 (0x262 is 5 bytes in the new_mc DBC) | not in code | — |
| real SAS | 0x25 | not in code | — |

The emulator never sends 0x2E4, 0x412 or 0x191 (emu 659-660; they are not in the background list) [C].

### Coverage table

| Message | ID | Alpha reads | 6.7.8 reads | On our bus | Rate |
|---|---|---|---|---|---|
| VSC1S07 | 0x320 | pt | pt | yes | 50 Hz |
| BODY_CONTROL_STATE | 0x620 | pt | pt | yes | 3 Hz |
| BRAKE_MODULE | 0x224 | pt | pt | yes | 40 Hz |
| ESP_CONTROL | 0x3B7 | pt | pt | yes (background) | ~10 Hz |
| PCM_CRUISE | 0x1D2 | pt | pt | yes | 33 Hz |
| GEAR_PACKET | 0x3BC | pt | pt | yes (VSS) | 10 Hz |
| PRE_COLLISION | 0x283 | pt | pt | yes | 33 Hz |
| WHEEL_SPEEDS | 0xAA | pt (+FAULT bits) | pt | yes (VSS) | 83 Hz |
| STEER_ANGLE_SENSOR | 0x25 | pt | pt | yes (real) | not in code |
| STEER_TORQUE_SENSOR | 0x260 | pt | pt | yes (real) | not in code |
| BLINKERS_STATE | 0x614 | pt (NaN) | pt (NaN) | yes (stalk) | 20 Hz |
| EPS_STATUS | 0x262 | pt | pt | yes (real) | not in code |
| PCM_CRUISE_2 | 0x1D3 | pt | pt | yes | 33 Hz |
| PCM_CRUISE_SM | 0x399 | pt | pt | yes (background) | ~10 Hz |
| BODY_CONTROL_STATE_2 | 0x610 | pt | pt | yes (background) | ~10 Hz |
| LIGHT_STALK | 0x622 | pt | pt | yes (background) | ~10 Hz |
| **LKAS_HUD** | **0x412** | **cam, lazy 1 Hz** | no | **no device sends it** (only openpilot's own TX on bus 0) | — |
| RSA1 | 0x489 | cam (NaN) | no | background, bus 0 | ~10 Hz |
| GAS_SENSOR | 0x201 | no | pt, if the interceptor is on | **yes (spoofed)** | 50 Hz |
| CRUISE_STALK, 0x500–0x505 | | no | pt (NaN) | yes | 20 / 2 Hz |

**Flagged:** LKAS_HUD 0x412 on bus 2 is the only message the alpha reads that our devices don't produce [C].

### Parser rules (`alpha:opendbc_repo/opendbc/can/parser.py`) [C, verified]

- **Lazy add.** `VLDict.__getitem__` adds the message on first access (103-111). `.get` does not add. Frames for a message that hasn't been added yet are skipped (219-221).
- **Default timeout.** With no frequency given, the parser assumes 1 Hz, so the timeout is 10 s (167-172).
- **Learned rate.** After 3 or more frames spanning over 1 s, it sets `frequency = min(n/dt, 100)` and the timeout to 10 periods, once (78-82).
- **NaN frequency** means `ignore_alive`, so the message never affects validity (93-95).
- **Never-received messages fail at once.** `valid()` returns False when there are no timestamps (96-97). `can_invalid_cnt` starts at 5 (`CAN_INVALID_CNT`, 12 and 138). So `can_valid` is False from the very first frame until every registered non-NaN message has a fresh timestamp, with no grace period. After that, it takes 5 consecutive invalid evaluations to go False again (199-200).
- **DBC messages that are never accessed have no effect** on `can_valid` or `bus_timeout` [C].
- **Bus timeout.** `bus_timeout` trips after `min(500 ms, smallest timeout)` with no frames on that parser's bus (177-183).
- **Aggregation.** `canValid = all(...)` and `canTimeout = any(...)` across both the pt and cam parsers (`interfaces.py:239-240`). selfdrived raises `canBusMissing` when `canTimeout` is set and `canError` otherwise (`selfdrived.py:590-593`). Both are IMMEDIATE_DISABLE (`events.py:929-945`).
- **Counter checks** apply only to signals named `COUNTER`, and none of the read messages has one (`dbc.py:309-310`).
- **Toyota checksum** applies to the 0x1D2, 0x1D3, 0x283, 0x260 and 0x262 reads (`dbc.py:261-262, 303-308`). The emulator, VSS and stalk checksums match opendbc and panda (`toyotacan.py:190-198`; `emu corolla_emulator.ino:406-414`; `vss_speed.ino:212-219`), and so do the frame lengths [C].

### The LKAS_HUD / bus-2 mechanism [rule C; topology I]

The established finding is that 0x4CB shows up on bus 2 during fingerprinting. Here is what the code says about how bus-2 frames reach the parser:
- The panda's 0→2 forwarding retransmits frames with `returned=1` (`panda/board/drivers/fdcan.h:129-139, 199-213`). pandad then adds `CAN_RETURNED_BUS_OFFSET`, so they arrive as src 130 (`openpilot/selfdrive/pandad/panda.cc:322-328`).
- `CANParser` keeps only `src == bus` (`parser.py:215-217`), and fingerprinting drops src ≥ 128 (`car_helpers.py:62`).

**Inference:** the bus-2 0x4CB therefore comes from the harness relay leaving buses 0 and 2 physically joined in NOOUTPUT/ELM327 mode (`panda/board/main.c:55-76`), not from the forwarding.

Onroad, the result depends on wiring the code can't show:
- **Bus 2 not physically joined to bus 0.** The cam parser times out after 500 ms, giving `canBusMissing`.
- **Bus 2 physically joined.** openpilot's own 5 Hz 0x412 TX might come back as src 2 and satisfy the read.

6.7.8 avoids both cases by not having the cam parser at all (`fork:…/toyota/carstate.py:332-336`).

### Panda safety RX (alpha; built from `opendbc_repo/opendbc/safety`, the only `toyota.h`) [C]

Our param 856 selects `TOYOTA_ALT_BRAKE_RX_CHECKS(false)` (`toyota.h:50-62, 553-565`):

| ID | Rate | Checks | Our source |
|---|---|---|---|
| 0xAA | 83 Hz | FAULT quality bits (bit 7 of bytes 0, 2, 4, 6) | VSS. Its raw formula keeps them at 0 below ~260 kph (`vss_speed.ino:237-245`). |
| 0x260 | 50 Hz | checksum | real EPS |
| 0x1D2 | 33 Hz | checksum | emulator, correct checksum |
| 0x224 | 40 Hz | none | emulator |

- **Lag rule.** A check counts as lagging when the gap exceeds `max(10×period, 1 s)`, which is 1 s for all four. Lagging, frequency below 10, or an invalid frame clears `controls_allowed` (`safety.h:173-185, 394-417`).
- **Relay check.** 0x191, 0x412 and 0x2E4 are relay-checked (`toyota.h:7-14`), and our devices send none of them.
- **Differences from 6.7.8** (`fork:…/safety/modes/toyota.h:53-85, 122-130`): the fork ignores the 0xAA quality bits, *requires* 0x1D3, and adds 0x201 when the interceptor is on. The alpha drops the 0x1D3 requirement and adds the FAULT-bit check. Our devices satisfy both versions.

---

## Q2. Other `canValid=False` paths [C]

These are every `canValid = False` write in the alpha (whole-tree grep, tests excluded):

| Location | Condition | Reaches us? |
|---|---|---|
| `openpilot/selfdrive/car/card.py:1134` | `ioniq6_long_selected and ioniq6_long_lost` | No. Set only for `HYUNDAI_IONIQ_6` (`card.py:247-275`). |
| `card.py:1146` | `ioniq6_long_prearmed` and lost | No (returns early at 1135). |
| `card.py:1393` | Ioniq 6 handoff not CONFIRMED | No (`ioniq6_long_pending` only for Ioniq 6). |
| `card.py:1430` | selected and not prearmed | No. |
| `opendbc_repo/opendbc/car/gm/interface.py:130` | GM CC-source taint | No. |

- **Vehicle-startup owner.** Its gates (`card.py:1273, 1423, 1477`) stay inactive: `startup_owner` exists only in Hyundai files (`starpilot/vehicle_startup.py:11-24`).
- **Only real source.** For us, `canValid` comes only from the parser aggregate (Q1).
- **ControlsReady.** A permanent `canValid=False` before init blocks `ControlsReady` and safety-mode switching (`card.py:1361`).
- **6.7.8 comparison.** `fork:selfdrive/car/card.py` has no `canValid` or `canTimeout` writes at all (its reads are at :418, 424, 437 and 478).

---

## Q3. Panda MCU

- **Hardware type [I].** The alpha's hardware types are `F4_DEVICES=[DOS]` and `H7_DEVICES=[RED_PANDA, TRES, CUATRO, BODY]` (`panda/python/__init__.py:130-134, 153-157`). `dos.h:6` reads "Dos (STM32F4)". The only line tying the C3 to DOS is the comment "The original comma 3 … Its DOS Panda" (`openpilot/selfdrive/pandad/pandad.cc:318-319`). No device-to-panda-type table exists [NF].
- **F4 firmware is built and shipped [C, verified]:**
  - The `build` help text says "--panda builds signed panda (C3), panda_h7 and body_h7" (`build:14-15`). Its shortcut targets include `panda/board/obj/panda.bin.signed` (`build:76`).
  - `tools/STARPILOT_DEVELOPMENT.md:62` says `./build --panda` builds only H7 targets. **The doc contradicts the code.**
  - `panda/SConscript` builds `panda` (STM32F413) plus all its variants.
  - The tree ships `panda.bin.signed` plus F4 `_remote`, `_hkg_remote`, `_tesla_wake` and `_can_ignition_only` images and bootstubs (`git ls-files panda/board/obj`). They are DEBUG-cert builds, version `DEV-39689cd6-…`. That commit isn't in the clone, so I couldn't confirm the binaries match the source.
- **What pandad flashes [C].** For DOS it flashes `panda.bin.signed` (`selfdrive/pandad/pandad.py:20-47`; `pandad.cc:139-143`). The variant choice is in `starpilot/panda_wake.py`, which I didn't read.
- **Building Toyota safety for F4 [C, not executed].** Toyota safety is compiled with no MCU guard (`opendbc/safety/safety.h:12, 469`). A Toyota change builds for F4 with `./build --panda` (or `scons panda/board/obj/panda.bin.signed`) using `arm-none-eabi-gcc` (`SConscript:9`; `tools/laptop_device_build/Dockerfile:23-24`). I did not verify that it compiles under `-Werror`.

---

## Q4. Lane centering [C]

- **Gate.** `runtime_supported` (`openpilot/starpilot/lateral/lane_runtime.py:45-50`) admits only:
  - the `LANE_CENTERING_REPLAY_RUNTIME=1` environment variable;
  - Ioniq 6 long eligibility;
  - the Bolt policy;
  - GM (`opendbc/car/gm/lateral.py:11-23`, `brand == 'gm'` plus finite tuning and not dashcam-only).
- **No Toyota is admitted.** `tests/test_lane_runtime.py:308` asserts that Corolla TSS2 is not.
- **Consumption.** `controlsd.py:96` creates the host only if the gate passes. With no host, the `LaneCentering` param does nothing (`controlsd.py:297-305`).
- **Host requirements.** `REQUIRED` services (`lane_runtime.py:56`), `carState.canValid and not canTimeout` (`:75`), and freshness checks.

To admit a retrofit platform:
1. Add a clause to `runtime_supported`. Mirroring the GM predicate would mean brand toyota, exact fingerprint, torque control, not dashcam-only and not passive.
2. Update `test_lane_runtime.py:308`.
3. Nothing else for the UI or params: the strength row is gated by the same function (`starpilot/ui/feature_settings_owner.py:966-983`), and the keys already exist (`common/params_keys.h:98-102`).
4. `lane_centering.py` has no vehicle gate that I found, but I only read its imports and call site.

---

## Q5. Auto Learn (`openpilot/starpilot/flm/`)

### What runs [C]

- **Learner process.** `steerlearnerd` runs onroad only (`system/manager/process_config.py:151`), at SCHED_OTHER nice 10 (`steerlearnerd.py:226-231`).
  - It subscribes to deviceMotion, extrinsicsCalibration, carState, carControl, pandaStates, lateralDelay, vehicleParameters, driverMonitoringState, onroadEvents and aolSafetyWire (:238-250).
  - It also reads the full-rate sockets `starpilotLateralState.learningEvidence` and `starpilotCarState.appliedEvidence` (:251-252).
  - It publishes `autoSteeringLearning` at 4 Hz.
  - Fits run in a `fit_worker` child limited to 8 MiB input, 2 GiB address space and 20 s CPU (`fit_worker.py:14-31`).
- **What it learns.** Multiplicative residuals on the feed-forward and friction-threshold stages, at most ±0.03 and slewed at 0.005/s.
  - The residuals are keyed `feedforward.{low|high}.{left|right}.{steady|turn_in|unwind}` (`torque_adapter.py:33-34`; `torque_stages.py:312-316`).
  - The speed bands split at 25 m/s, and the application gate blends between 10 and 25 m/s.
  - It writes no factor, PID or table values (`torque_stages.py:1-6`).
- **Not learned.** The centre objective is defined (`centre_objective.py`: deadband ≤ 0.01°) but **disabled in this alpha** (`learner_factory.py:179-182, 272-273`; `global_runtime.py:238-239`). The friction stage isn't learned either (`torque_adapter.py:64-67`).
- **Dormant path.** A scalar `latAccelFactor` learner (`automatic.py`, `learning_source.py`, `learning_producer.py`) has no production caller (`controlsd.py:97-98`) [C for no reference; I for dormant].

### Gates [C]

1. **Preference.** Learning stops if the preference is off (`SteeringLearningPreferences`, or `ForceAutoTuneOff`, alpha default `"0"`, `params_keys.h:109`), a saved document is invalid, a manual FLM surface exists, extrinsics are uncalibrated, or the VIN is invalid (`runtime_adapter_registry.py:240-300`).
2. **Descriptor** (`runtime_adapter_registry.py:315-349`). Requires:
   - not notCar, passive or dashcamOnly;
   - the fingerprint in `interfaces`, with CarParams matching;
   - `LatControlTorque`, torque steer control and torque tuning.
   **There is no brand or fingerprint allowlist.**
3. **Collector.** Requires:
   - **≥ 15 m/s** and |roll| < 0.3 rad (`learner_factory.py:150-151`);
   - panda safety configs matching CarParams with `controlsAllowed` (`runtime_adapter_registry.py:118-169`);
   - freshness, engagement and override windows (`fullrate_collector.py:23-26`; `global_runtime.py:149-196`).
4. **Fit** (`adaptive_profile.py:95-163`). Ridge regression with 8–24 blocks of 40–240 samples. Every cohort needs held-out improvement with a t-quantile lower bound above 0.
5. **Replay validation** (`adaptive_profile.py:166-180`). No saturation or slew regression, with a TTL and slew applied on the controller side (`:194-221`). Any failure falls back to the baseline.

### `AutomaticSteeringProfiles` [C]

- **Format.** JSON v1, at most 32 KiB and 32 profiles (`learned_lifecycle.py:8-72`).
- **Row contents.** `identity`, `reset`, `policy="passive_stage_ridge_v1"`, `parameters`, `coefficients` and `validation`.
- **Use.** Stored rows serve only as a ridge prior; a fresh fit and replay are always required (`learned_lifecycle.py:240-244`).
- **Identity.** It hashes the CarParams digest, the baseline tune and the VIN or session, so any CarParams or baseline change orphans the stored rows (`runtime_adapter_registry.py:66-86, 352-367`).

### Retrofit eligibility [C]

A new Toyota retrofit platform is eligible if it:
- is in `interfaces`;
- is not dashcam-only (the alpha's `MATRIX_RETROFIT` bypass logic makes it dashcam-only on our bus);
- uses torque control with a `torque_data` entry (`opendbc/car/interfaces.py:221-227`);
- uses `LatControlTorque`;
- has the learning preference on.

The explicit linear-torque-map check (`learning_source.conversion_identity`, :56-70) sits only on the dormant path, and Toyota would pass it anyway because no Toyota file overrides `torque_from_lateral_accel`.

### Interaction with torqued [C, verified]

- Auto Learn doesn't override, feed or disable torqued.
- `controlsd.py:178-182` pushes torqued's filtered factor, offset and friction into `LatControlTorque` whenever `torque_host is None and torque_learning_allowed`, which is the case for a Toyota retrofit.
- The ±3 % residual is applied on top of that (`latcontrol_torque.py:118-127`).
- When torqued changes the baseline, Auto Learn's identity resets (`global_runtime.py:137-145`).
- `ForceAutoTuneOff=1` turns off both torqued and steerlearnerd (`controlsd.py:68`; `torqued.py:270`; `steerlearnerd.py:77-78`).

---

## Q6. Manual tuning path [C]

### The gate chain

1. `controlsd.py:97-99` creates `TorqueHost` only if `runtime_enabled` (`torque_runtime.py:97`) passes.
2. `runtime_enabled` requires `manual_overrides_present` (:84).
3. `manual_overrides_present` requires `production_supported_cp` (:78), which is Ioniq 6 or GM only.
4. Toyota appears in `supported_cp` (:59) through `TOYOTA_VEHICLES`. That list has 38 IDs and excludes both retrofits (`torque_supported.py:3-14`). Two tests assert this (`tests/test_torque_family.py:48-52`; `tests/test_native_inferred_torque.py:63-69`).
5. Overrides take effect from the **next** drive, because the host is created at startup.

### Admitting a Toyota retrofit for manual friction and lat accel factor

- Add the platform to `TOYOTA_VEHICLES`.
- Add it to `production_supported_cp`. That also drives the UI capability (`starpilot/ui/feature_settings_owner.py:184-194`; `ui/torque_feature.py:69-148`).
- Update the tests above, plus `galaxy/tests/test_vehicle_configuration.py`.
- No new keys are needed. `SteerLatAccel`, `SteerFriction`, the `*Stock` keys and `TorqueOverrideDocument` already exist (`params_keys.h:109-114`).
- `supported_cp` itself requires not dashcam-only.

### Bounds

The bounds are 0.5–1.5× of the base factor, and friction 0 to `min(1, max(0.1, 2×base))` (`torque_settings.py:69-77`). The alpha's base for `MATRIX_RETROFIT` is `[4.05, 1.84, 0.10]`. I checked this against the legend `[LAT_ACCEL_FACTOR, MAX_LAT_ACCEL_MEASURED, FRICTION]` (`torque_data/override.toml:1, 167`). So our 4.05 equals the base, and friction 0.15 falls inside the 0–0.20 range.

### Steer ratio

- **Correction to a helper.** `MATRIX_RETROFIT` uses `TOYOTA_COROLLA.specs` with **steerRatio 18.27** (`values.py:206-215`, 208). The 17.4 at `values.py:261` belongs to a different platform.
- **Live estimate.** paramsd learns the ratio within 0.5–2.0× of the CarParams value (`selfdrive/locationd/paramsd.py:48, 167, 172`). controlsd reads it (`controlsd.py:169`).
- **Pinning.** The only pin is `GeometryPublicationOwner` (`starpilot/lateral/gm_geometry_runtime.py:60-75`, wired into `paramsd.py:261-272` and `lagd.py:401-402`). It is GM-only in three places (`gm_geometry_runtime.py:24-26`; `torque_settings.py:197-198, 348`) and in the UI (`torque_feature._geometry_rows`, :154-200).
- **Other routes [I].** Change `CarSpecs.steerRatio` in code, or extend the geometry owner to cover the retrofit. There is no `SteerRatio` key.

---

## Q7. Vehicle policy template [C]

### Selection (startup only)

1. `read_selection` (`controller_selection.py:214-225`).
2. `policy_for` (:77), an if-chain. The Toyota entries are `corolla_tss2` and `rav4_tss2`.
3. `KNOWN_POLICIES` (:17-63) validates the saved mode. A new platform must be added there.
4. `latcontrol_torque.py:49-64` calls `create_extension` (`torque_extension.py:25-83`), another if-chain on the policy name.

### Policy interface

- `__init__(parent, CP)`: guards with `supported_cp` and may replace `parent.pid`.
- `update(active, CS, VM, params, steer_limited_by_safety, desired_curvature, curvature_limited, lat_delay)` returns `(-torque, 0.0, pid_log)`. It is called from `latcontrol_torque.py:88-92`.
- Optional hooks: `FACTOR_MULT` (multiplies the factor) and `steer_ratio_scale(speed)` (consumed in `controlsd.py:172-174`).

### Shaping (Corolla TSS2 template, `corolla_tss2_policy.py:130-199`)

- Feed-forward scale for turn-in boost and unwind reduction (:74-87, :174).
- Friction threshold (:90-102) and jerk deadzone.
- `get_friction` with `torque_params.friction` (:180), so manual or torqued friction still applies.
- Centre output scale with a floor of 0.65 (:110, :187).

### Damping and `k_d`

- **A policy can set PID `k_d`.** `PIDController(k_p, k_i, k_d=0., …)` accepts a scalar or a table, and `d = k_d · error_rate` (`common/pid.py:7-10, 45`).
- **Correction to a helper:** there is already a precedent. `genesis_gv70_policy.py:66-68` passes `[GENESIS_GV70_MEASUREMENT_DAMPING_SPEED_BP, GENESIS_GV70_MEASUREMENT_DAMPING_V]` as `k_d`, with `error_rate = 0.0 if steeringPressed else -measurement_rate` (:146-148). This is derivative-on-measurement damping.
- Corolla already passes `error_rate=-measurement_rate` with `k_d=0` (`corolla_tss2_policy.py:184`).
- The STANDARD path never passes `error_rate` (`latcontrol_torque.py:137`), so it has no D term.

### Outline of a retrofit policy

1. Copy `supported_cp` (`corolla_tss2_policy.py:38-46`) with the exact retrofit fingerprint.
2. Add per-car feed-forward, friction-threshold, centre and `KD_INTERP` constants.
3. Build `PIDController(..., k_d=table)` following the GV70 pattern.
4. Write `update` from the Corolla flow.
5. Register it in `policy_for`, `KNOWN_POLICIES` and `create_extension`, and add tests.

Two things change automatically once a policy exists:
- `default_selection` would auto-pick STARPILOT mode (`controller_selection.py:150-155`).
- A STARPILOT policy gets `learning_allowed=False` unless it is `rav4_tss2` (:228-252).

---

## Q8. Settings migration and import [C]

- **`snapshot_settings`** (`starpilot/state_migration.py:172-181`) copies every Params file, at up to 256 MiB, into a manifest-verified archive.
- **`restore_snapshot`** (:198-217) restores exact bytes into a **new** namespace and refuses to overwrite one. It is offline recovery, "not an upgrade" (`README.md:31-33`).
- **`stage_settings`** (:220-292) writes `staged/<sha>.json` and activates nothing, and no consumer exists (grep found none; `README.md:77-78`).
- **The Dom handoff marker** (:346-371) only forces the wipe-and-archive migration to run again. It imports nothing.
- **First start** keeps only the 16 `OPERATIONAL_KEYS` (:25-29, 303-314). The 8-key preference allowlist is also dropped when `auto_migrate=True` (`system/manager/manager.py:30`; `state_migration.py:455-456`).
- **Snapshot location:** `/data/starpilot/snapshots/<sha256>/{values/<key>, manifest.json, migration.json}` (`starpilot/storage.py:12-29`; `state_migration.py:298, 319`).
- **Supported import: [NF].** Doing it by hand means reading `values/<key>` and re-entering the values in the UI [I].
- **Galaxy `toggle_backup.py`.** It requires exactly `{format:"galaxy-toggles", version:1, createdAt, metric, vehicle, settings, layout}` (:55-61), with string values validated row by row. A 6.x backup has `"starpilot-toggle-backup"` with a `data` blob (`fork:starpilot/system/the_galaxy/the_galaxy.py:1232-1233, 10321-10337`), so **it is rejected**. There is no shim.

### Fate of our keys

| Setting | 6.7.8 key | In alpha table? | Survives first start? |
|---|---|---|---|
| Friction 0.15 | `SteerFriction` | yes | no (and TorqueHost ignores it for Toyota) |
| Lat accel factor 4.05 | `SteerLatAccel` | yes | no (4.05 = alpha base) |
| Steer ratio 17.4 | `SteerRatio` | **no** | dropped |
| LaneCentering | `LaneCentering` | yes | no, reset to 0 |
| Learning off | `ForceAutoTuneOff` | yes, default `"0"` | **no, so learning comes back on** |
| SAS offset / deadzone | `RetrofitSASOffset`, `RetrofitSteerAngleDeadzone` | **no** | dropped |

For `ForceAutoTuneOff` in the fork, `fork:common/params_keys.h:385` reads `{PERSISTENT, BOOL, "1", "0", 2}`. Which of those values is the effective default depends on the fork's key format, which I didn't settle [I].

---

## Q9. Realtime inheritance audit

- **No reset flag [C].** No code anywhere sets `SCHED_RESET_ON_FORK`, so SCHED_FIFO passes across fork and exec unless the child drops it. This follows from Linux semantics.
- **Manager [C].** The manager isn't realtime, so every managed process starts SCHED_OTHER and raises itself.
- **Coverage.** 58 files contain spawn calls. I didn't read all of them; the table covers the files reachable from realtime processes.

| Process (when) | Scheduling class / priority (citation) | Spawns | Children inherit FIFO? |
|---|---|---|---|
| card (onroad) | FIFO 53, core 4 (`card.py:1546`) | none found | n/a |
| controlsd | FIFO 53, then 52, cores 4/5 (`controlsd.py:496-500`) | none found | n/a |
| **selfdrived** | FIFO 53, core 5 (`selfdrived.py:1898`) | `git rev-parse` through `get_short_branch` (`events.py:240`; `common/git.py:15-16`), cached so once | **yes**, a short-lived child [C path; I whether it fires] |
| plannerd, radard | FIFO 51 (`plannerd.py:336`; `radard.py:402`) | none | n/a |
| locationd, calibrationd, torqued, paramsd, lagd | FIFO 5, cores 0–3 | none | n/a |
| **steerlearnerd** | **SCHED_OTHER, nice 10** (`flm/steerlearnerd.py:226-231`) | `fit_worker` via Popen (`flm/fit_process.py:46-53`), which resets itself to SCHED_OTHER (`fit_worker.py:22-31`) | no |
| modeld | FIFO 54, core 7 (`modeld.py:389`) | possibly tinygrad worker pool or compiler subprocesses (`tinygrad/engine/worker.py:38-44`) | [I] only if spawned after :389; not traced |
| pandad (Python wrapper) | OTHER | `./pandad` (`pandad.py:147`), which sets its own FIFO 54 (`pandad/main.cc:13-15`) | no |
| encoderd | FIFO 52 (`encoderd.cc:214-216`) | none | n/a |
| loggerd | not FIFO (`loggerd.cc:351` commented out) | popen | no |
| ui | FIFO 50, then `drop_realtime` at the first frame on tici (`ui.py:35, 66-73`) | wifi, software, busctl, ffmpeg helpers | [I] mostly no; children started before the drop, or from worker threads created before it, would inherit |
| **sensord** | FIFO 1, core 1 (`sensord.py:97`) | `sudo` write via `subprocess.run` (`sensord.py:40`; `common/utils.py:39, 45`) | **yes**, FIFO 1 [I on call order] |
| hardwared, athenad, journald, uploader, galaxy, maps, etc. | OTHER | many | no |

---

## Q10. Odds and ends [C]

- **radard.**
  - With `radarUnavailable=False`, the Toyota RadarInterface waits for 0x22F on bus 1 and returns None (`radar_interface.py:53-60`). The base class's empty 20 Hz output is used only when no radar parser exists (`interfaces.py:88-92`).
  - So `radarTracks` is never published (`card.py:1070-1080`), and radard sets `radarState.valid=False` (`radard.py:331, 364-370`).
  - selfdrived doesn't ignore radarState (`selfdrived.py:186`). `all_checks` fails while the message is still alive and on frequency, so it raises **`commIssue`** (`selfdrived.py:598-606`; soft disable plus no entry, `events.py:854-857`).
  - 6.7.8 forces `radarUnavailable=True` (`fork:…/toyota/interface.py:243-244`).
- **door_locks (0x750).** Off by default: `LockDoors` and `UnlockDoors` default to `"0"` (`params_keys.h:290-291`; `starpilot/vehicle_preferences.py:86-89`).
  - A command also needs a P↔non-P gear transition at standstill (`door_locks.py:22-35`), and the VSS forces D (`vss_speed.ino:78`).
  - The panda allows only the two exact payloads (`safety/modes/toyota.h:449-462`).
- **LKAS_HUD from a zeroed copy.**
  - The zero-filled dict from `_add_message` (`parser.py:151-154`) overrides LANE_SWAY_FLD, BUZZER, WARNING, SENSITIVITY and TOGGLE with 0 (`toyotacan.py:145-185`). It goes out on bus 0 at 5 Hz and on alert transitions (`carcontroller.py:372-389`).
  - None of our devices accepts 0x412 (emulator RX filters `corolla_emulator.ino:909-922`, stalk `cruise_stalk.ino:96-97`, VSS has no RX).
  - Whether the real EPS or the 2005 cluster reads it can't be told from code [NF]. The bigger effect of 0x412 is the cam-parser timeout in Q1, not this payload.
- **AOL.**
  - `aol.py qualified()` requires a TSS2 car on its list (`starpilot/car/toyota/aol.py:9-59`).
  - The panda requires safetyParam in {73, 585, 4169, 4681} (`safety/modes/toyota_aol.h:95-100`), and our param is 856.
  - Even if admitted, AOL requires 0x262 to be **8 bytes** (`toyota_aol.h:51-66`), and our EPS_STATUS is 5 bytes (`toyota_new_mc_pt.dbc:8`).
  - **Our bus can't meet the AOL requirements.**

---

## New risks for the retrofit

1. **Bus-2 LKAS_HUD.** Any alpha Toyota platform that keeps the cam parser can sit at `canError` or `canBusMissing`, depending on bus-2 wiring (Q1). A `canValid` that stays False before init also blocks `ControlsReady` (`card.py:1361`).
2. **The emulator spoofs 0x201 GAS_SENSOR at 50 Hz in the production build** (`emu:corolla_emulator.ino:52, 1115-1117`). On 6.7.8 with openpilot long, that enables the gas-interceptor path and its safety flag (`fork:…/toyota/interface.py:288-290`), even though the interceptor is on hold. The alpha ignores 0x201.
3. **No radar.** `radarUnavailable=False` with no radar leads to `commIssue` on the alpha platforms (Q10).
4. **Stock longitudinal.** The alpha runs `TOYOTA_COROLLA` and `MATRIX_RETROFIT` with stock long (param 856). That differs from 6.7.8's alpha-long retrofit.
5. **LKA_STATE 0.** The alpha's `TEMP_STEER_FAULTS` includes LKA_STATE 0 with no bypass (`carstate.py:23, 132`).
6. **Dashcam-only cascade.** If a platform goes dashcam-only, every admission path fails: torque override, lane centering, vehicle policy and Auto Learn.
7. **Learning comes back on.** After first start, `ForceAutoTuneOff` reverts to `"0"`, so torqued and steerlearnerd run again, and none of our tuning keys survive.
8. **Steer ratio mismatch.** The alpha's base ratio for `MATRIX_RETROFIT` is 18.27, against our 17.4, and there is no non-GM pin.
9. **Auto Learn is unlikely to help at campus speeds.** It needs ≥ 15 m/s and road calibration, and its centre objective is disabled.
10. **Stale dev doc.** `STARPILOT_DEVELOPMENT.md` misstates the panda build scope. Confirm the F4 build compiles before relying on a safety change.
11. **Diagnostic IDs in background traffic.** The emulator sends zero-payload 0x7E0–0x7E8 at ~10 Hz, which could interfere with firmware queries. I didn't analyse this.

## Leads not finished

- Count src==2 frames, and 0x412 at src==2, in an onroad 6.7.8 rlog to settle the bus-2 topology question.
- The real EPS and SAS send rates aren't in any sketch. Measure them against the 50 Hz RX check and the 1 s lag rule.
- I didn't read `starpilot/panda_wake.py` (firmware variant choice) or confirm that the F4 build compiles.
- I didn't trace whether modeld's tinygrad pool spawns after the FIFO call. Worker threads in the ui are partly unverified.
- These files weren't read in full: `learning_preferences.py`, `controller_feature.py`, `lane_centering.py`, `controller_replay.py`, `learning_wire.py`, `test_controller_selection.py`, `test_torque_runtime.py`, the Galaxy `SettingsRecovery` route bodies, and `settings_retirement.py` / `legacy_cache_migration.py`.
- I only traced `learning_producer` statically; its dormancy hasn't been confirmed at runtime.
- I didn't trace the device path of the Params namespace (`Params.get_param_path()`).
- I didn't determine which of the two values in the fork's `ForceAutoTuneOff` entry is the effective default.