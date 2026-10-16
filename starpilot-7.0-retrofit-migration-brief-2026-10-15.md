# StarPilot 6.7.8 → 7.0 Retrofit Migration Brief

**Audience:** an engineering agent porting the `TOYOTA_COROLLA_RETROFIT` research car from our 6.7.8 fork to the StarPilot 7.0 alpha.
**Status:** read-only research. Nothing was built, run, or modified. Every claim is cited and labeled.
**Date of research:** 2026-10-16.

---

## 0. How to use this document

- **Citation format:** `repo:path:line`. Repo prefixes:
  - `alpha:` is firestar5683/StarPilot.
  - `fork:` is skylatian/StarPilot.
  - `emu:` is skylatian/corolla_emulator.
- **Car-code paths.** Unless shown in full, car-code paths are relative to `opendbc_repo/opendbc/car/toyota/`. In the alpha, openpilot code lives under `openpilot/`. In the fork, openpilot code sits at the repo root, except `opendbc_repo/` and `panda/`.
- **Labels:**
  - **[C]** confirmed in code.
  - **[I]** inferred, with the basis stated.
  - **[NF]** searched for and not found.
- **Re-verify before acting.** Line numbers are only valid at the pinned commits. If the alpha has moved, re-grep each anchor before editing.
- Section 2 is the porting map, section 3 is the step-by-step plan, and section 4 is the verification checklist. Sections 5–14 hold the evidence behind them.

### Pinned commits

All three branch heads matched their pins when cloned on 2026-10-16.

| Repo | Branch | Commit |
|---|---|---|
| Alpha 7.0 | `firestar5683/StarPilot` `SecretGoodStarPilot` | `01fd37fa7509174d71a626f66fa5567b4603b00e` ("Prebuilt runtime artifacts") |
| Our fork 6.7.8 | `skylatian/StarPilot` `retrofit-dev-6.7.8-update-sandbox` | `38134a41cd3442bf9661da72a939f8f519f19f45` |
| CAN emulator | `skylatian/corolla_emulator` `full-emulate` | `30ba722360f978490a8a0c3bd5956f6f8f2c0e5b` |

Clone with `git clone --filter=blob:none --single-branch -b <branch> <url>` and then `git checkout <commit>`. The alpha vendors everything in-tree and has no submodules.

---

## 1. System context

### 1.1 The car

- **Vehicle.** A stripped 2005 Toyota Corolla/Matrix running openpilot on a **comma 3** (tici, not 3X) with the internal panda. It is used for campus research only.
- **Lateral.**
  - A junkyard 2016 Corolla EPS motor sends real **0x260** STEER_TORQUE_SENSOR and **0x262** EPS_STATUS frames.
  - A real steering-angle sensor sends **0x25**.
  - Both sit on the car's own hydraulic rack, which has weak self-centering.
- **Absent hardware.** No camera, no radar, no DSU. The gas interceptor (Comma Pedal) is not installed and is on hold.
- **Emulated ECUs.** Three custom Arduino ECUs sit on bus 0:

| Device | Sketch | Owns |
|---|---|---|
| Main emulator (PCM stand-in) | `emu:fakeecu/corolla_emulator/corolla_emulator.ino` | 0x1D2/0x1D3 cruise, EPS-init and background traffic, 0x500/0x503 diagnostics |
| VSS device | `emu:vss_speed/vss_speed.ino` | 0xAA, 0xB4, 0x3BC, 0x502, 0x505 |
| Cruise stalk | `emu:cruise_stalk/cruise_stalk.ino` | 0x69, 0x614, 0x501, 0x504 |

- **Production compile flags** (`emu:corolla_emulator.ino:50-91`):
  - `VSS_DEVICE_INSTALLED=true`
  - `REAL_EPS_CONNECTED=true`
  - `REAL_SAS_CONNECTED=true`
  - `REAL_PEDAL_CONNECTED=false`
  - `SEND_ACC_CONTROL=false`
  - `FORCE_BRAKE_OFF=true`
  - `SEND_BACKGROUND_MSGS=true`
- **Bus 2 mirrors bus 0.** The panda forwards everything from 0 to 2, and from 2 to 0 except relay-checked IDs. Devices must never send the relay-checked IDs **0x2E4, 0x412 or 0x191**.

### 1.2 What our 6.7.8 fork does today

Platform `TOYOTA_COROLLA_RETROFIT` (`fork:…/toyota/values.py:209-213`):
- Specs are `steerRatio=18.27` (same as TOYOTA_COROLLA). The only bus is `{Bus.pt: 'toyota_new_mc_pt_generated'}`, with no cam or radar bus.
- **Runtime tune:**
  - stock StarPilot `LatControlTorque`;
  - manual friction 0.15, lat accel factor 4.05, steer ratio 17.4 (via params);
  - learning forced off;
  - `LaneCentering` on about half the time;
  - openpilot longitudinal on (alpha long).

| Gate | Fork location |
|---|---|
| Fingerprint forced and FW query skipped | `fork:launch_env.sh:33-35` (`FINGERPRINT="TOYOTA_COROLLA_RETROFIT"`, `SKIP_FW_QUERY="1"`) |
| Fingerprint table entry | `fork:opendbc_repo/opendbc/car/fingerprints.py:307`; `fork:…/toyota/fingerprints.py:449` |
| Safety param 88 | `fork:…/toyota/values.py:607` |
| Torque data | `fork:opendbc_repo/opendbc/car/torque_data/override.toml:27`: `[4.05, 1.84, 0.06]` |
| Skip Bus.cam parser | `fork:…/toyota/carstate.py:332-336` |
| DSU-bypass detection disabled | `fork:…/toyota/interface.py:176-183` (comment explains the 0x4CB mirror) |
| `steerFaultTemporary` cleared at `LKA_STATE` 0 | `fork:…/toyota/carstate.py:24, 171-175` |
| `radarUnavailable=True` | `fork:…/toyota/interface.py:243-244` |
| Center deadzone from `RetrofitSteerAngleDeadzone` (default 0.3°, frozen into CarParams) | `fork:…/toyota/interface.py:30, 246-254`; `fork:common/params_keys.h:643` |
| SAS offset param `RetrofitSASOffset` | `fork:…/toyota/carstate.py:141-142`; `fork:common/params_keys.h:642` |
| ±300° steer-angle kill | `fork:…/toyota/carcontroller.py:57, 362-364` |
| Nonlinear torque map (`RetrofitNonlinear*`) | `fork:…/toyota/interface.py:~88-115` (`torque_from_lateral_accel` / `lateral_accel_from_torque` overrides) |
| openpilot long via alpha long | `fork:…/toyota/interface.py:280-285` |
| Gas interceptor auto-enable (`0x201 in fingerprint[0]` and op long) | `fork:…/toyota/interface.py:287-290` |
| Retrofit pedal shaping | `fork:…/toyota/carcontroller.py:295-302` |
| Diagnostics frames 0x69 and 0x500–0x505 | `fork:opendbc_repo/opendbc/dbc/generator/toyota/_community.dbc`, `fork:…/toyota/retrofit_diag.py:1-161`, `carstate.py:97, 301-302, 325-326` |
| Diagnostics cereal field | `fork:cereal/custom.capnp:113` (`retrofitDiag @31 :RetrofitDiag`) |
| ECU alerts from diagnostics | `fork:selfdrive/selfdrived/events.py:464-501`; `fork:selfdrive/selfdrived/selfdrived.py:178-183, 295, 550-551` |
| Retrofit lateral tunes and NNFF | `fork:selfdrive/controls/lib/latcontrol_vehicle_tunes.py:182-183`; `fork:selfdrive/controls/lib/latcontrol_torque.py:82`; `fork:starpilot/assets/nnff_models/retrofit/` |
| Helper scripts | `fork:scripts/carstate_check.py`, `launch_retrofit_offroad.sh`, `launch_retrofit_onroad.sh`, `seed_retrofit_params.py` |

---

## 2. Porting map: what exists in 7.0 and where each fork feature has to go

The alpha already has a `TOYOTA_MATRIX_RETROFIT` platform (`alpha:…/toyota/values.py:211-215`). It **cannot be used as-is** on our car:

| Property of alpha `TOYOTA_MATRIX_RETROFIT` | Evidence | Effect on our car |
|---|---|---|
| Uses `dbc_dict("toyota_new_mc_pt_generated", "toyota_adas")` | `alpha:…/toyota/values.py:211-215` | It has a radar bus, so `radarUnavailable=False` (`alpha:…/toyota/interface.py:120`), which leads to `commIssue` (§12.1). |
| `bypass = 0x343 in camera_fp or 0x4CB in camera_fp`, so `takeover` makes it `dashcamOnly=True` | `alpha:…/toyota/interface.py:137-157` | The emulator's 0x4CB EPS-init frame shows up in fingerprint[2], so the car goes **dashcam-only**. That fails every admission path. |
| Forces `openpilotLongitudinalControl = smart_dsu` (False) and `alphaLongitudinalAvailable=False` | `interface.py:156-157` | Stock longitudinal only, safetyParam 856 (§5.1). |
| Cam parser reads `LKAS_HUD` from bus 2 | `alpha:…/toyota/carstate.py:188-189` | Missing message, so `canError` or `canBusMissing` (§5.5). |
| `TEMP_STEER_FAULTS` includes LKA_STATE 0, with no bypass | `alpha:…/toyota/carstate.py:23, 132` | `steerFaultTemporary` whenever the EPS reports 0. |
| Torque data `[4.05, 1.84, 0.10]` (legend `LAT_ACCEL_FACTOR, MAX_LAT_ACCEL_MEASURED, FRICTION`) | `alpha:opendbc_repo/opendbc/car/torque_data/override.toml:1, 167` | Lat accel factor matches ours. Friction 0.10 differs from our 0.15, and from the fork's override value 0.06. |
| Specs = `TOYOTA_COROLLA.specs` (steerRatio 18.27) | `alpha:…/toyota/values.py:206-213` | Same as the fork's CarSpecs. Our live 17.4 comes from a param that doesn't exist in 7.0. |
| Listed in `openpilot/starpilot/validation/required-platforms.json:1536` as `source_only` | file | A new platform probably needs an entry here [I]. |

**Recommended direction [I, from the above].** Port a dedicated `TOYOTA_COROLLA_RETROFIT` platform into the alpha that mirrors the fork's gates. The alternative, reshaping `TOYOTA_MATRIX_RETROFIT`, is firestar's platform for a different setup with stock PCM longitudinal and possible takeover hardware. Changing it would alter behavior for its other users.

### 2.1 Feature-by-feature destination table

| Fork feature | Alpha destination | Notes |
|---|---|---|
| Platform definition | `alpha:…/toyota/values.py` (add a `PlatformConfig` with `{Bus.pt: 'toyota_new_mc_pt_generated'}`; add to the safety-param map at `values.py:610`) | Leaving out `Bus.radar` makes `radarUnavailable` True automatically (`interface.py:120`). |
| Torque data | `alpha:opendbc_repo/opendbc/car/torque_data/override.toml` | `configure_torque_tune` needs an entry (`alpha:opendbc_repo/opendbc/car/interfaces.py:221-227`). |
| Car selection | `VehicleSelection` param, or the `FINGERPRINT` env var (§3, step 2) | The alpha's `launch_env.sh` sets no FINGERPRINT. |
| Skip cam parser | `alpha:…/toyota/carstate.py` `get_can_parsers` (the cam parser is built near :238-249) and the `cp_cam` reads at :189 and :224-237 | Same idea as `fork:…/toyota/carstate.py:332-336`. |
| DSU bypass / takeover off | `alpha:…/toyota/interface.py:137-157`: don't add the new platform to that tuple | The alpha's DSU-bypass block for other cars sits near :130-170. Check that the new platform skips every `has_dsu_bypass`-style path. |
| LKA_STATE 0 bypass | `alpha:…/toyota/carstate.py:132-133` | Copy the fork's platform-scoped condition. |
| SAS offset | `alpha:…/toyota/carstate.py:105-106` (STEER_ANGLE_SENSOR read) plus a new param key in `alpha:openpilot/common/params_keys.h` | The key doesn't exist in 7.0 (§10.3). |
| Center deadzone | `configure_torque_tune(..., steering_angle_deadzone_deg=…)` in `alpha:…/toyota/interface.py` (the Prius retrofit does this at :93-95) | Matrix retrofit currently gets 0.0. |
| ±300° angle kill | `alpha:…/toyota/carcontroller.py` (`lat_active` computation) | [NF] no equivalent in the alpha. |
| openpilot longitudinal | `alpha:…/toyota/interface.py:134-170` | The alpha forces stock long for both retrofits. The panda must then run without `STOCK_LONGITUDINAL`. See §6 for relay and TX implications. |
| Diagnostics DBC frames | `alpha:opendbc_repo/opendbc/dbc/generator/toyota/_community.dbc` exists, but `toyota_new_mc_pt.dbc` imports only `_toyota_2017.dbc` and `_toyota_adas_standard.dbc` (`alpha:…/dbc/generator/toyota/toyota_new_mc_pt.dbc:1-2`) | Add the import or a new DBC. `_generated` DBCs aren't committed; the generator is `alpha:opendbc_repo/opendbc/dbc/generator/generator.py:18-31`. |
| `retrofitDiag` cereal field | `alpha:openpilot/cereal/custom.capnp` `StarPilotCarState`: `@31` is now `gps`, next free ordinal is **`@37`** | Renumbering breaks log compatibility with old 6.7.8 rlogs [I]. |
| ECU alerts | `alpha:openpilot/selfdrive/selfdrived/events.py`, `selfdrived.py` | [NF] no retrofit alerts in the alpha. |
| Manual friction / lat accel | TorqueHost production scope (§9) | Currently Ioniq 6 and GM only. |
| Pinned steer ratio | `GeometryPublicationOwner` (GM-only, §9.3), or CarSpecs | No `SteerRatio` key exists. |
| Lane centering | `alpha:openpilot/starpilot/lateral/lane_runtime.py:45-50` (§8) | No Toyota is admitted. |
| Retrofit lateral tunes and NNFF | The vehicle-policy framework (§11). NNFF is gone in 7.0. | A policy can carry feed-forward, friction and `k_d` shaping. |
| Nonlinear torque map | `CarInterface.torque_from_lateral_accel` override, as in the fork | **Check its interaction with Auto Learn (§10.4)** and with `TorqueHost`. |
| Learning off | `ForceAutoTuneOff=1`, or the per-vehicle `SteeringLearningPreferences` | The alpha default is `"0"`, so learning is on (§10.3). |
| Gas interceptor | **Removed** from the alpha's Toyota safety | Our emulator still spoofs 0x201 (§6.3). |

---

## 3. Suggested migration plan

Each step names its evidence section. These are proposals derived from code, not tested procedures.

1. **Back up the device first.**
   - Copy `/data/params` (or the active Params namespace) off the device.
   - Export a 6.7.8 Galaxy toggle backup. 7.0 can't restore it (§13.4), but it serves as a record of values.
   - Record these values by hand: `SteerFriction`, `SteerLatAccel`, `SteerRatio`, `RetrofitSASOffset`, `RetrofitSteerAngleDeadzone`, `ForceAutoTuneOff` and `LaneCentering`.
2. **Decide how the car will be selected.** The alpha resolves the car at `alpha:openpilot/starpilot/vehicle_selection.py:82-87`:
   - If the `FINGERPRINT` env var is set, `startup_candidate` returns None and opendbc uses the env var (`alpha:opendbc_repo/opendbc/car/car_helpers.py:101-102, 186`; `alpha:openpilot/selfdrive/car/card.py:283`).
   - Otherwise it reads the `VehicleSelection` param (JSON `{"version":1,"platform":<str|null>}`, at most 512 bytes, `vehicle_selection.py:13-15, 46-80`):
     - valid with a platform: that platform is forced;
     - valid with `null`: native fingerprinting ("Auto");
     - **unreadable or invalid: MOCK** (`:87`).
   - `VehicleSelection` isn't one of the 16 keys that survive first start (§13.2). Re-select the car after migrating, or carry `FINGERPRINT` and `SKIP_FW_QUERY` into the alpha's `launch_env.sh`.
   - What happens when the key is missing depends on `saved_source.read_saved`, which I didn't read [NF].
3. **Port the platform** (§2.1 rows 1–9) on a branch of the alpha. Keep everything scoped to the exact fingerprint. The alpha's convention is exact-platform predicates (§8, §9, §11).
4. **Port the DBC and diagnostics.**
   - Re-add the `_community.dbc` import, or a retrofit-specific DBC, and regenerate.
   - Add `retrofitDiag` at `@37`.
   - Port `retrofit_diag.py` and the alerts.
5. **Panda.**
   - If the Toyota safety mode needs changes (e.g. openpilot long without the interceptor, or any retrofit RX allowance), build F4 firmware with `./build --panda` (§7).
   - Confirm the C3 reports DOS before trusting the F4 path.
6. **Lateral admission.** Pick the gates the research needs:
   - lane centering (§8);
   - manual friction / lat accel / steer ratio (§9);
   - a retrofit vehicle policy with damping (§11).
   Update the tests that assert the allowlists; they are listed in each section.
7. **Learning.**
   - Set `ForceAutoTuneOff=1` after first start if learning must stay off (§10.3).
   - If Auto Learn is wanted, read §10 first: it needs ≥15 m/s and its centre objective is disabled.
8. **Emulator.**
   - Decide on 0x201: the alpha ignores it, while 6.7.8 auto-enables the interceptor from it (§6.3).
   - Make sure no device ever sends 0x2E4, 0x412 or 0x191.
9. **Build.**
   - The alpha ships a `prebuilt` marker. Compiled changes need `prebuilt` removed, or `./build`. `prebuilt.json` is a receipt over the non-UI files.
   - First boot reflashes AGNOS to 19.8.1. First start archives and wipes params (§13).
10. **Verify** with section 4.

---

## 4. Verification checklist (after porting, before driving)

- [ ] `carParams.carFingerprint` is the retrofit platform, not MOCK. `dashcamOnly == False`.
- [ ] `carParams.radarUnavailable == True`. `radarState.valid` doesn't block `selfdrived` (no `commIssue`) (§12.1).
- [ ] `carState.canValid == True` and `canTimeout == False` within about 1 s of onroad (§5.6 rules). No `canError` or `canBusMissing` events.
- [ ] No cam parser, or no bus-2 messages read (§5.5).
- [ ] `steerFaultTemporary` doesn't latch at `LKA_STATE == 0`.
- [ ] Panda `controlsAllowed` engages on 0x1D2 cruise rising edge. No relay malfunction. RX checks aren't lagging (§6.1).
- [ ] The real EPS really sends **0x260 at ≥ 10 Hz** and within 1 s gaps (RX check declared 50 Hz) (§6.1). Rate not in code, so measure it.
- [ ] `pandaStates[].pandaType` is DOS, and the flashed firmware is `panda.bin.signed` (§7).
- [ ] `ForceAutoTuneOff` matches the intended learning state, and `lateralTorqueParameters.useParams` agrees (§10.5).
- [ ] If TorqueHost was admitted, the host is created on the *second* drive after editing (§9.1).
- [ ] If lane centering was admitted, the host isn't None and `LaneCenteringStrength` shows in the UI (§8).
- [ ] `starpilotCarState.retrofitDiag` is populated, if ported.
- [ ] Logged steer ratio (`liveParameters` / `vehicleParameters.steerRatio`) matches the intended pin.

---

## 5. CAN message coverage (highest priority)

### 5.1 Platform facts that decide which messages are read (alpha) [C]

- **DBC and flags.** `TOYOTA_COROLLA` and `TOYOTA_MATRIX_RETROFIT` use `dbc_dict('toyota_new_mc_pt_generated', 'toyota_adas')` with no static flags (`values.py:206-215`).
- **Undetectable flags.** HYBRID (`interface.py:83-84`), HAS_BSM (TSS2 only, :117-118), DISABLE_RADAR (RADAR_ACC only, :123-127) and LONG_FILTER (Prius-retrofit smart DSU, :147-153) can't be detected on our car.
- **Longitudinal.** `openpilotLongitudinalControl` is False (:134-135, :156), so STOCK_LONGITUDINAL is set (:165-166).
- **safetyParam = 856.** That is 88 EPS scale (`values.py:609-611`) + 256 ALT_BRAKE (`interface.py:54-55`, new_mc DBC) + 512 stock long.
- **Steering.** Torque control, so `LTA_STATE` reads are skipped (`carstate.py:135-137`).
- **Radar.** `radarUnavailable = Bus.radar not in DBC[candidate]` (`interface.py:120`) gives **False** for both platforms. The only StarPilot override of `radarUnavailable` is Honda (`alpha:openpilot/starpilot/vehicle_preferences.py:103`).

### 5.2 Alpha pt parser (bus 0) reads [C]

- **Registration.** At construction only `BLINKERS_STATE` is registered, with NaN frequency (`carstate.py:238-249`). Every other message is added lazily on its first `vl[...]` access.

| # | Message | ID | carstate.py line(s) | Condition | Read on our platform? |
|---|---|---|---|---|---|
| 1 | VSC1S07 | 0x320 | 72 | not SECOC | yes |
| 2 | BODY_CONTROL_STATE | 0x620 | 74-77 | always | yes |
| 3 | BRAKE_MODULE | 0x224 | 79 | always | yes |
| 4 | ESP_CONTROL | 0x3B7 | 80, 182 | always | yes |
| 5 | PCM_CRUISE | 0x1D2 | 87, 175, 178 | always | yes |
| 6 | GEAR_PACKET | 0x3BC | 88 | not SECOC | yes |
| 7 | PRE_COLLISION (`cp_acc` = `cp` on non-TSS2, :69) | 0x283 | 90 | not SECOC and not DISABLE_RADAR | yes |
| 8 | WHEEL_SPEEDS + 4 FAULT bits | 0xAA | 93-96, 102-103 | always | yes |
| 9 | STEER_ANGLE_SENSOR | 0x25 | 105-106 | always | yes |
| 10 | STEER_TORQUE_SENSOR | 0x260 | 107, 110, 126-127 | always | yes |
| 11 | BLINKERS_STATE (NaN) | 0x614 | 123-124 | always | yes |
| 12 | EPS_STATUS.LKA_STATE | 0x262 | 132-133 | always (LTA_STATE only for angle control, 136-137) | yes |
| 13 | PCM_CRUISE_2 | 0x1D3 | 150, 152-153, 192 | not UNSUPPORTED_DSU. LOW_SPEED_LOCKOUT (173) only with op long. | yes (LOW_SPEED_LOCKOUT only if op long is ported) |
| 14 | PCM_CRUISE_SM | 0x399 | 151, 154 | not UNSUPPORTED_DSU | yes |
| 15 | BODY_CONTROL_STATE_2 | 0x610 | 157 | always | yes |
| 16 | LIGHT_STALK | 0x622 | 181 | always | yes |
| – | SECOC_SYNCHRONIZATION / GAS_PEDAL / GEAR_PACKET_HYBRID | – | 83-85 | SECOC | no |
| – | DSU_CRUISE / PCM_CRUISE_ALT | 0x365 / 0x3F1 | 146-148 | UNSUPPORTED_DSU | no |
| – | ACC_CONTROL / PCS_HUD | 0x343 / 0x411 | 163-164, 208, 215 | TSS2 or Prius / LONG_FILTER | no |
| – | BSM | 0x3F6 | 185-186 | HAS_BSM | no |
| – | SDSU / PCM_CRUISE_4 | – | 214, 220 | LONG_FILTER / SIENNA_4TH_GEN | no |

**StarPilot-side readers [C]:**
- A full grep of `\.vl\[` (tests excluded) finds no other Toyota readers.
- `alpha:openpilot/starpilot/car/toyota/aol.py` has no CAN reads (:1-106).
- The other hits are not Toyota: GM AOL (`starpilot/car/gm/aol.py:154-166`); offline replay (`flm/torque_emission_replay.py:406, 424`); `opendbc/car/gps.py:235, 246` (gm, ford and vw only, :198-210); and a Honda `.get` at `card.py:790-796`.

### 5.3 Alpha cam parser (bus 2) reads [C]

| Message | ID | Line | Condition | Registration |
|---|---|---|---|---|
| RSA1 | 0x489 | 224-227, 235 | in DBC (`_toyota_2017.dbc:323`) | NaN (`ignore_alive`). The `parser_expiry` read uses `.get` and never lazily adds it (`alpha:opendbc_repo/opendbc/car/dashboard_speed_limit.py:55-61`). |
| **LKAS_HUD** | **0x412** | **189** | every car except the Prius V, so always | **lazy, default 1 Hz** |
| LKAS_HUD.LDA_ON_MESSAGE | 0x412 | 198 | TSS2 / LONG_FILTER / PRIUS_RETROFIT | not ours |
| PRE_COLLISION_2 | 0x344 | 66, 236-237 | AUTO_BRAKE_HOLD | not ours |

### 5.4 Production bus contents [C]

| Source | ID | Name / payload | Rate | Gate / line |
|---|---|---|---|---|
| emulator | 0x1D2 | PCM_CRUISE (GAS_RELEASED=1, CRUISE_ACTIVE, checksum) | 33 Hz | `corolla_emulator.ino:1150-1152, 503-515` |
| emulator | 0x1D3 | PCM_CRUISE_2 (MAIN_ON byte 1 bit 7, SET_SPEED, LSL=0, checksum) | 33 Hz | 1154-1156, 521-530 |
| emulator | 0x283 | PRE_COLLISION (7 bytes of zeros + checksum) | 33 Hz | 1158-1160, 628-632 |
| emulator | 0x224 | BRAKE_MODULE (always 0) | 40 Hz | 1141-1143, 1085-1086 |
| emulator | 0x1C4 | ENGINE_RPM | 50 Hz | 1124-1126 |
| emulator | 0x4CB | EPS init | 50 Hz | 1128-1130 |
| emulator | 0x320 | VSC1S07 zeros | 50 Hz | 1132-1134 |
| emulator | **0x201** | **GAS_SENSOR spoof** | 50 Hz | **`#if !REAL_PEDAL_CONNECTED` 1115-1117**, 589-611; flag false at :52 |
| emulator | 0x620 | BODY_CONTROL_STATE zeros | 3 Hz | 1185-1187 |
| emulator | 0x500 / 0x503 | diagnostics / version | 2 Hz + on cruise transitions | 1216-1221 |
| emulator | 69 background IDs, zero payload (includes 0x24, 0x344, 0x365, 0x366, 0x399, 0x3B7, 0x411, 0x489, 0x610, 0x622, 0x7E0–0x7E8) | | ~10 Hz each (7 per 10 ms slot) | 665-702, 1173-1179 |
| emulator, **not sent in production** | 0xAA, 0xB4, 0x3BC (VSS gate), 0x25 (SAS), 0x260/0x262 (EPS), 0x343 | | | 1097, 1101, 1111, 1120, 1167, 1195, 685 |
| VSS | 0xAA | WHEEL_SPEEDS, 4 identical values, raw = kph·100 + 6767 | 83 Hz | `vss_speed.ino:237-245, 507-510` |
| VSS | 0xB4 | SPEED + checksum | 50 Hz | 247-255, 513-516 |
| VSS | 0x3BC | GEAR_PACKET (FORCE_DRIVE=true, always D) | 10 Hz | 78, 257-270, 519-522 |
| VSS | 0x502 / 0x505 | diagnostics / version | 2 Hz | 119-120, 532-536 |
| stalk | 0x69 | CRUISE_STALK, 3 bytes + checksum | 20 Hz | `cruise_stalk.ino:390-396, 823-829` |
| stalk | 0x614 | BLINKERS_STATE | 20 Hz | 401-405, 828 |
| stalk | 0x501 / 0x504 | diagnostics / version | 2 Hz | 175, 73 |
| real EPS | 0x260, 0x262 | STEER_TORQUE_SENSOR, EPS_STATUS (5 bytes in new_mc DBC) | **not in code** (bench spoof: 50 / 25 Hz, emu 109, 112) | — |
| real SAS | 0x25 | STEER_ANGLE_SENSOR | **not in code** (bench spoof: 83 Hz, emu 108) | — |

The emulator never sends 0x2E4, 0x412 or 0x191 (emu 659-660; none are in the background list at 665-688) [C].

### 5.5 Coverage table and the one gap

| Message | ID | Alpha reads | 6.7.8 reads | On our bus | Rate |
|---|---|---|---|---|---|
| VSC1S07 | 0x320 | pt | pt | yes | 50 Hz |
| BODY_CONTROL_STATE | 0x620 | pt | pt | yes | 3 Hz |
| BRAKE_MODULE | 0x224 | pt | pt | yes | 40 Hz |
| ESP_CONTROL | 0x3B7 | pt | pt | yes (background) | ~10 Hz |
| PCM_CRUISE | 0x1D2 | pt | pt | yes | 33 Hz |
| GEAR_PACKET | 0x3BC | pt | pt (+ECON/SPORT, fork 280-281) | yes (VSS) | 10 Hz |
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
| **LKAS_HUD** | **0x412** | **cam (bus 2), lazy 1 Hz** | no (no cam parser) | **no device sends it**; only openpilot's own TX on bus 0 (`alpha:…/toyota/carcontroller.py:386-389`) | — |
| RSA1 | 0x489 | cam (NaN) | no | background on bus 0 | ~10 Hz |
| GAS_SENSOR | 0x201 | no (removed) | pt @50 Hz if interceptor enabled (fork carstate 46, 313-314) | **yes (spoofed)** | 50 Hz |
| CRUISE_STALK, 0x500–0x505 | | no | pt (NaN) (`fork:retrofit_diag.py:23-27`) | yes | 20 / 2 Hz |

**The 16 pt messages are all on our bus.** The one message the alpha reads that our devices don't produce is **LKAS_HUD 0x412 on bus 2** (`alpha:…/toyota/carstate.py:189`) [C]. Skipping the cam parser for the retrofit platform removes it.

### 5.6 Parser rules (`alpha:opendbc_repo/opendbc/can/parser.py`) [C]

- **Lazy add.** `VLDict.__getitem__` calls `_add_message` for a missing key (103-111). `dict.get` and `ts_nanos.get` don't add. Frames for a message not yet added are skipped (219-221).
- **Default timeout.** With no frequency given, the parser assumes 1 Hz, so the timeout is `(1e9/1)·10` = **10 s** (167-172).
- **Learned rate.** After ≥3 frames spanning >1 s: `frequency = min(n/dt, 100)` and timeout = 10 periods. This is learned once (78-82).
  - Examples: 0xAA (83 Hz) gives 120 ms; 0x1D2 (33 Hz) gives 303 ms; 0x620 (3 Hz) gives 3.33 s; background (10 Hz) gives 1 s.
- **NaN frequency** sets `ignore_alive`, so the message never affects validity (93-95).
- **Never-received messages fail at once.** `valid()` returns False when there are no timestamps (96-97). `can_invalid_cnt` starts at `CAN_INVALID_CNT=5` (12, 138), so `can_valid` is False from the first frame with no grace period. After one all-valid evaluation the count resets, and it takes 5 consecutive invalid evaluations to go False again (199-200).
- **DBC messages that are never accessed** have no effect on `can_valid` or `bus_timeout` (176-200).
- **Bus timeout.** `bus_timeout` trips after `min(500 ms, smallest timeout_threshold)` with no frames on that bus, unless every message is `ignore_alive` (177-183). `last_nonempty_nanos` starts at 0 (139).
- **Aggregation.** `canValid = all(cp.can_valid)` and `canTimeout = any(cp.bus_timeout)` across **all** parsers (`alpha:opendbc_repo/opendbc/car/interfaces.py:239-240`).
- **Events.** selfdrived raises `canBusMissing` when `canTimeout` is set, else `canError` when `canValid` is False (`alpha:openpilot/selfdrive/selfdrived/selfdrived.py:590-593`). Both are IMMEDIATE_DISABLE (`events.py:929-945`).
- **Counter checks** apply only to signals named `COUNTER` (`alpha:opendbc_repo/opendbc/can/dbc.py:309-310`). None of the read messages has one. VSC1S07's `S07CNT` doesn't match.
- **Toyota checksum** applies to signals named exactly `CHECKSUM` in `toyota_*` DBCs (`dbc.py:261-262, 303-308`). That covers 0x1D2, 0x1D3, 0x283, 0x260 and 0x262.

### 5.7 Checksums and lengths [C]

- **opendbc formula.** `len + addr_lo + addr_hi + sum(d[:-1]) & 0xFF` (`alpha:…/toyota/toyotacan.py:190-198`). The panda uses the same formula (`alpha:opendbc_repo/opendbc/safety/modes/toyota.h:113-125`).
- **Our devices match.** The emulator, VSS and stalk use the same formula (`emu corolla_emulator.ino:406-414`, `vss_speed.ino:212-219`).
- **Lengths match the DBC.** 0x283 has 7 bytes with the checksum at d[6]; 0x1D2/0x1D3 have 8 bytes with d[7]. The parser doesn't check length (`parser.py:220`).
- **Unverifiable.** The real EPS's 0x260/0x262 checksums can't be checked from code.

### 5.8 Bus-2 topology [rule C; topology I]

- **Why forwarding alone doesn't feed bus 2.** The panda's 0→2 forwarding retransmits frames with `returned=1` (`alpha:panda/board/drivers/fdcan.h:129-139, 199-213`). pandad adds `CAN_RETURNED_BUS_OFFSET` (`alpha:openpilot/selfdrive/pandad/panda.cc:322-328`), so these arrive as src 130.
- **Filtering.** `CANParser` keeps only `src == bus` (`parser.py:215-217`). Fingerprinting drops src ≥ 128 (`alpha:opendbc_repo/opendbc/car/car_helpers.py:62`).
- **Inference.** The 0x4CB seen in fingerprint[2] most likely comes from the harness relay leaving buses 0 and 2 physically joined in NOOUTPUT/ELM327 mode (`alpha:panda/board/main.c:55-76`; `harness.h:8-33`), not from forwarding.
- **Onroad, two possible cases:**
  - bus 2 isn't physically joined: the cam parser trips `bus_timeout` after 500 ms, giving `canBusMissing`;
  - bus 2 is physically joined: openpilot's own 5 Hz 0x412 TX may appear as src 2 and satisfy the read.
- **Not determinable from code.** 6.7.8 sidesteps it (`fork:…/toyota/carstate.py:332-336`).
- **Porting rule:** don't build a cam parser for the retrofit platform.

---

## 6. Panda safety (Toyota RX/TX) [C]

The alpha panda includes `opendbc.INCLUDE_PATH` (`alpha:panda/SConscript:4, 105`; `alpha:opendbc_repo/opendbc/__init__.py:6`). Only one `toyota.h` exists in the alpha: `opendbc_repo/opendbc/safety/modes/toyota.h`, plus `toyota_aol.h`.

### 6.1 RX checks under param 856 (`TOYOTA_ALT_BRAKE_RX_CHECKS(false)`, `toyota.h:50-62, 553-565`)

| ID | Length | Rate | Checks | Our source / status |
|---|---|---|---|---|
| 0xAA | 8 | 83 Hz | **Quality bits:** any FAULT bit (bit 7 of bytes 0, 2, 4, 6) set makes it invalid (`toyota.h:127-144, 51`). Checksum and counter ignored. | VSS. raw = kph·100 + 6767, so bit 15 stays 0 below ~260 kph. The VSS clamps at 655 kph (`vss_speed.ino:200-201`), where the uint16 would wrap. |
| 0x260 | 8 | 50 Hz | checksum | real EPS, rate unknown |
| 0x1D2 | 8 | 33 Hz | checksum | emulator, correct |
| 0x224 | 8 | 40 Hz | none | emulator |

- **Not RX-checked in the alpha.** 0x1D3 and 0x262 are not RX checks. They appear only in the AOL hook (`toyota.h:146-153`).
- **Lag rule.** A check counts as lagging when the gap exceeds `max(10×period, 1 s)`, which is **1 s** for all four (`alpha:opendbc_repo/opendbc/safety/safety.h:394-417`). Lagging, frequency below 10, or an invalid frame clears `controls_allowed` (`safety.h:173-185, 410-414`).
- **Engagement.** Rising edge of 0x1D2 bit 5. `gas_pressed = !bit4`. Brake is 0x224 bit 5 (`toyota.h:233-243`).
- **Relay check.** 0x191, 0x412 and 0x2E4 are relay-checked on bus 0 (`toyota.h:7-14`). Receiving one sets `relay_malfunction` (`safety.h:286-293, 442-448`). 0x343 is not relay-checked in the stock-long list (`toyota.h:14`).

### 6.2 6.7.8 differences (`fork:opendbc_repo/opendbc/safety/modes/toyota.h:53-85, 122-130`)

| Topic | 6.7.8 | Alpha |
|---|---|---|
| 0xAA quality bits | ignored | checked |
| 0x1D3 | **required** (8 bytes, 33 Hz) | not required |
| 0x201 | RX check at 50 Hz when the interceptor is on | interceptor removed |

Our devices meet both versions.

### 6.3 0x201 gas interceptor hazard

- **Emulator.** It sends a spoofed 0x201 at 50 Hz in the production build (`emu:corolla_emulator.ino:52, 1115-1117`).
- **6.7.8.** `enableGasInterceptorDEPRECATED = 0x201 in fingerprint[0] and openpilotLongitudinalControl`, which also adds the `GAS_INTERCEPTOR` safety flag (`fork:…/toyota/interface.py:287-290`). So with alpha long on, today's fork **enables the interceptor path** even though the pedal isn't installed [C].
- **Alpha.** Ignores 0x201 [C].
- **Porting.** Decide whether the retrofit platform should ever look at 0x201.

### 6.4 Openpilot longitudinal in the alpha

The alpha forces stock long on both retrofit platforms. Porting op long means:
- not setting `STOCK_LONGITUDINAL`;
- the panda TX list changes, which includes 0x343 ACC_CONTROL with relay semantics (`toyota.h:7-14`);
- `LOW_SPEED_LOCKOUT` becomes a read (`carstate.py:173`).

I didn't analyze longitudinal TX safety beyond this [NF].

---

## 7. Panda MCU and firmware

- **C3 internal panda = DOS (STM32F4) [I].**
  - Code facts: `HW_TYPE_DOS=0x06`, `TRES=0x09` (`alpha:panda/python/__init__.py:130-134`); `F4_DEVICES=[DOS]`, `H7_DEVICES=[RED_PANDA, TRES, CUATRO, BODY]` (:153-157); `get_mcu_type` (:646-652); `alpha:panda/board/boards/dos.h:6` "Dos (STM32F4)".
  - The only code linking the comma 3 to DOS is the comment at `alpha:openpilot/selfdrive/pandad/pandad.cc:318-319`.
  - [NF] No device-to-panda-type table exists. Check `pandaStates.pandaType` on the device.
- **F4 firmware is built and shipped [C].**
  - `alpha:build:14-15` help text: "--panda builds signed panda (C3), panda_h7 and body_h7". `build:76` targets `panda/board/obj/panda.bin.signed`, `panda_h7.bin.signed` and `body_h7.bin.signed`.
  - **`alpha:tools/STARPILOT_DEVELOPMENT.md:62` says it builds only `panda_h7` and `body_h7`.** That is wrong; trust the code.
  - `panda/SConscript` builds `panda` (STM32F413, base_project_f4) plus the remote, hkg_remote, tesla_wake and can_ignition_only variants.
  - Committed in `panda/board/obj/` (`git ls-files`):
    - F4: `panda.bin.signed`, `panda_{remote,hkg_remote,tesla_wake,can_ignition_only,…}.bin.signed`, and `bootstub.panda*.bin`;
    - H7: `panda_h7*` images and bootstubs;
    - Body: `body_h7.bin.signed`.
  - Version files read `DEV-39689cd6-P92eb5651-DEBUG`, which are debug-cert builds. Commit `39689cd6` isn't in the clone, so I couldn't confirm the binaries match the source.
- **What gets flashed [C].** pandad flashes `panda.bin.signed` for DOS (`alpha:openpilot/selfdrive/pandad/pandad.py:20-47`; `pandad.cc:139-143`). Variants are chosen by `alpha:openpilot/starpilot/panda_wake.py`, which I didn't read.
- **Building Toyota safety for F4 [C, not executed].**
  - Toyota safety is compiled with no MCU guard (`safety.h:12, 469`).
  - Use `./build --panda [jobs]`, or `scons panda/board/obj/panda.bin.signed`. Add `RELEASE=1 CERT=…` for signed release images (`build:15-18, 41`).
  - Toolchain `arm-none-eabi-gcc` (`SConscript:9`; `tools/laptop_device_build/Dockerfile:23-24`). On device the build goes through `scripts/native_device_build.sh` (`build:57-60`).
  - I didn't verify that it compiles under `-Werror`.

---

## 8. Lane centering [C]

- **Gate.** `runtime_supported` (`alpha:openpilot/starpilot/lateral/lane_runtime.py:45-50`) admits only:
  - `LANE_CENTERING_REPLAY_RUNTIME=1`;
  - `ioniq6_long_eligible(CP)`;
  - `bolt_policy.supported_cp(CP)`;
  - `gm.lateral.lane_centering_supported(CP)` (`alpha:opendbc_repo/opendbc/car/gm/lateral.py:11-23`: brand gm, finite tuning, not dashcam-only).
- **No Toyota.** `tests/test_lane_runtime.py:308` asserts Corolla TSS2 is not supported.
- **Consumption.** `alpha:openpilot/selfdrive/controls/controlsd.py:96` builds `LaneCenteringHost` only if the gate passes. With no host, the `LaneCentering` toggle does nothing (`controlsd.py:297-305`).
- **Host requirements.** `REQUIRED = ('carState', 'selfdriveState', 'modelV2', 'vehicleParameters')` (`lane_runtime.py:56`), plus `carState.canValid and not canTimeout` (:75), plus freshness `2.5e9 / SERVICE_LIST[name].frequency`.
- **Settings.** Offset ±0.3 and E2E authority 0..1 (`lane_runtime.py:15-37`).

**To admit the retrofit platform:**
1. Add an exact-fingerprint clause to `runtime_supported`, mirroring the GM predicate: brand, fingerprint, torque control, not dashcam-only, not passive.
2. Update `test_lane_runtime.py:308`. Check `test_volt_lane_runtime.py:44-52` and `test_bolt_lane_runtime.py`.
3. Nothing else for the UI: the strength row is gated by the same function (`alpha:openpilot/starpilot/ui/feature_settings_owner.py:966-983`). No new keys either (`alpha:openpilot/common/params_keys.h:98-102`).
4. `lane_centering.py`: I found no vehicle gate, but only read its imports and call site.

---

## 9. Manual tuning path (friction, lat accel factor, steer ratio) [C]

### 9.1 Runtime chain

1. `controlsd.py:97-99`: `TorqueHost(...)` is created only if `runtime_enabled(CP, params)` passes (`alpha:openpilot/starpilot/lateral/torque_runtime.py:97`).
2. `runtime_enabled` requires `supported_cp` (:59), then `manual_overrides_present` (:84) or the env var `TORQUE_REPLAY_RUNTIME=1`.
3. `manual_overrides_present` requires `production_supported_cp` (:78), which is `supported_cp` + fingerprint in `IONIQ6_VEHICLES | GM_VEHICLES` + not passive + not notCar.
4. **The host is created at startup, so an edit takes effect on the next drive.**
5. `read_settings` prefers the `TorqueOverrideDocument` JSON (`torque_settings.py:13`). It falls back to the legacy `SteerLatAccel`/`SteerFriction` keys and their `*Stock` markers.
6. `TorqueHost.apply` calls `LatControlTorque.update_torque_parameters` (`alpha:openpilot/selfdrive/controls/lib/latcontrol_torque.py:68-74`).

### 9.2 Admitting a Toyota retrofit for manual friction and factor

- `alpha:openpilot/starpilot/lateral/torque_supported.py:3-14`: add the fingerprint to `TOYOTA_VEHICLES`. It currently has 38 IDs and excludes both retrofits.
- `torque_runtime.py:78`: add the fingerprint to `production_supported_cp`. That also drives the UI capability (`feature_settings_owner.py:184-194`; `ui/torque_feature.py:69-148`).
- `supported_cp` requirements (`torque_runtime.py:59-76`): brand toyota, torque control, **not dashcam-only**, torque tuning, finite values.
- **Tests to update:**
  - `lateral/tests/test_torque_family.py:48-52` (count 38; retrofits excluded);
  - `lateral/tests/test_native_inferred_torque.py:63-69` (Toyota not production);
  - `galaxy/tests/test_vehicle_configuration.py:9, 27`;
  - `test_torque_runtime.py`, `test_torque_settings.py` and `test_gm_manual_torque.py` (not read).
- **No new keys** (`params_keys.h:109-114`: `ForceAutoTuneOff`, `SteerLatAccel`, `SteerLatAccelStock`, `SteerFriction`, `SteerFrictionStock`, `TorqueOverrideDocument`).
- **Bounds** (`torque_settings.py:69-77`): factor 0.5–1.5× base; friction `0..min(1.0, max(0.1, 2×base))`. With the alpha's base `[4.05, 1.84, 0.10]`, our 4.05 / 0.15 fit. With the fork's base friction 0.06, the cap would be 0.12 and **0.15 would fall outside it** [C from formula].
- **Clamp on learned values.** When a host exists, learned values are clamped to 0.7–1.3× factor and friction 0.5×..max(0.1, 1.5×) (`torque_runtime.py:211-215, 281-285`).

### 9.3 Steer ratio

- **Static.** `CP.steerRatio` comes from `CarSpecs` (`alpha:opendbc_repo/opendbc/car/interfaces.py:138`). That is 18.27 for Corolla specs (`values.py:208`).
- **Live.** paramsd's Kalman estimate (`alpha:openpilot/selfdrive/locationd/paramsd.py:167`) is bounded to 0.5–2.0× (:48, 172). It is seeded from the `LiveParametersV2` cache when the fingerprint matches (:204-233), and written once per minute (:276-277). controlsd reads it (`controlsd.py:169`).
- **The only existing pin is `GeometryPublicationOwner`** (`alpha:openpilot/starpilot/lateral/gm_geometry_runtime.py:60-75`, wired into `paramsd.py:261-272` and `lagd.py:401-402`). It rewrites `vehicleParameters.steerRatio` to a custom value from `TorqueOverrideDocument.vehicles[fp].geometry` (schema ≥ 3, `torque_settings.py:42, 331-343`; 0.5–1.5× basis). It is **GM-only** in:
  - `read_geometry` (`gm_geometry_runtime.py:24-26`);
  - `parse_document` (`torque_settings.py:197-198`);
  - `replace_geometry` (`:348`);
  - the UI `_geometry_rows` (`torque_feature.py:154-200`).
  - Basis check: `(CP.steerRatio, CP.steerActuatorDelay + 0.2)` (`gm_geometry_runtime.py:19-20, 33-36`).
- **Porting options [I]:**
  - (a) extend the geometry owner to cover the retrofit by relaxing the four GM checks;
  - (b) set `CarSpecs.steerRatio=17.4`, though paramsd would still learn unless that is pinned too.
- [NF] No `SteerRatio`, `SteerKP` or `SteerDelay` key.

---

## 10. Auto Learn (`alpha:openpilot/starpilot/flm/`)

### 10.1 What runs [C]

- **Process.** `steerlearnerd` is onroad only (`alpha:openpilot/system/manager/process_config.py:151`), SCHED_OTHER nice 10 (`steerlearnerd.py:226-231`).
  - Subscribes to deviceMotion, extrinsicsCalibration, carState, carControl, pandaStates, lateralDelay, vehicleParameters, driverMonitoringState, onroadEvents and aolSafetyWire (:238-250).
  - Full-rate sockets `starpilotLateralState.learningEvidence` and `starpilotCarState.appliedEvidence` (:251-252).
  - Publishes `autoSteeringLearning` at 4 Hz (:182-205).
- **Fit worker.** `fit_worker` runs as a separate child: 8 MiB input, 64 KiB output, 2 GiB address space, 20 s CPU (`fit_worker.py:14-31`).
- **Controller attachment.** `GlobalRuntime` (`controlsd.py:124`) attaches stage hooks when a torque descriptor is selected (`global_runtime.py:90-99`). `latcontrol_torque.py:125` applies the stages after the baseline feed-forward and threshold, and before friction.
- **What it learns.** Multiplicative residuals `ff *= (1+δ)` and `threshold *= (1+δ)`, with |δ| ≤ 0.03 and slew 0.005/s (`torque_stages.py:312-316`; `torque_adapter.py:33-34`).
  - Keyed `feedforward.{low|high}.{left|right}.{steady|turn_in|unwind}`.
  - Speed bands split at 25 m/s (`learner_factory.py:32`); the application gate blends 10–25 m/s (`torque_adapter.py:44-45`).
  - |setpoint| ≥ 0.25 m/s² (`learner_factory.py:169`).
  - It writes no params, PID, factor or table values (`torque_stages.py:1-6`).
- **Centre objective: disabled in this alpha.** Defined in `centre_objective.py` (deadband ≤ 0.01°), but rejected at `learner_factory.py:179-182, 272-273` and `global_runtime.py:238-239`.
- **Friction stage: not learned** (`torque_adapter.py:64-67`).
- **Scalar latAccelFactor learner** (`automatic.py`, `learning_source.py`, `learning_producer.py`, ±30 %): no production caller, since `controlsd.py:97-98` builds TorqueHost without `automatic_interface` [C no reference; I dormant].

### 10.2 Gates [C]

1. **Source / preference** (`runtime_adapter_registry.py:240-300`; `learning_preferences.py:63-77`). Learning is disabled by any of:
   - preference off (`SteeringLearningPreferences`, else legacy `ForceAutoTuneOff`);
   - an invalid document or `LateralControllerSelection`;
   - a bad reset generation;
   - out-of-bounds legacy `SteerLatAccel`/`SteerFriction`;
   - a `TorqueOverrideDocument` basis mismatch;
   - a manual FLM surface (:272);
   - uncalibrated extrinsics (:285-287);
   - an invalid VIN with no session (:288-296).
2. **Descriptor** (`:315-349`). Requires:
   - not notCar, passive or dashcamOnly;
   - fingerprint in `interfaces`, `type(ci) is interfaces[fp]`, and CarParams dict equality;
   - `LatControlTorque`, torque steer control and torque tuning.
   **There is no brand or fingerprint allowlist.**
3. **Collector.**
   - ≥15 m/s and |roll| < 0.3 rad (`learner_factory.py:150-151`).
   - Panda safety configs match CarParams with `controlsAllowed` (`runtime_adapter_registry.py:118-169`).
   - Sample freshness 100 ms, engagement ≥2 s, override exclusion 1 s (`fullrate_collector.py:23-26`).
   - Service freshness and `sat_time == 0` (`global_runtime.py:149-196`).
4. **Fit** (`adaptive_profile.py:95-163`).
   - Ridge regression (0.01), with 1–8 parameters and 8–24 blocks of 40–240 clean samples.
   - Each cohort needs ≥2 training and ≥2 held-out blocks, and a held-out improvement lower bound (t = 12.707) above 0.
   - At least 16 blocks from the last 24 (`learner_factory.py:183-190`).
5. **Replay validation** (`adaptive_profile.py:166-180`): no saturation or slew regression.
   - `ProfileOwner.tick` adds ≥4 training / ≥4 held-out blocks, candidate loss below baseline, a 500 ms TTL, and slew limiting.
   - Any failure falls back to the baseline (:194-221).
6. **Physical model.** Prediction within max(0.01, 3× held-out RMSE), and the model must be less than 600 s old (`learner_factory.py:158-160, 278`).

### 10.3 Storage: `AutomaticSteeringProfiles` [C]

- **Key.** `{PERSISTENT | DONT_LOG, BYTES}` (`params_keys.h:108`).
- **Format.** JSON `{"version":1,"profiles":{<scopeSha256>:{identity, reset, policy:"passive_stage_ridge_v1", parameters, coefficients, validation}}}`. At most 32 KiB and 32 profiles (`learned_lifecycle.py:8-74`).
- **Writes.** At most once per second (`:176-203`).
- **Use.** Rows are a ridge **prior only**; a fresh fit and replay are always required (`:240-244`).
- **Identity.** It hashes the CarParams digest, the baseline tune and the VIN or session (`runtime_adapter_registry.py:66-86, 352-367`). **Any CarParams or baseline change orphans the rows.**

### 10.4 Eligibility of a ported retrofit platform

- **Eligible [C]** if it:
  - is in `interfaces`;
  - is not dashcam-only;
  - has torque control with a `torque_data` entry;
  - uses `LatControlTorque`;
  - has the learning preference on.
- **Linear torque map [I].** The explicit linearity check (`learning_source.conversion_identity`, :56-70) sits only on the dormant scalar path. The live path rebuilds the controller through replay (`controller_replay.py`, not read) and uses `controller.torque_from_lateral_accel` in the descriptor (`runtime_adapter_registry.py:334-338`).
  - **If the fork's nonlinear torque map (`fork:…/toyota/interface.py:~88-115`) is ported, check whether replay reproduces it faithfully.** Not verified.
  - Stock Toyota has no override, so it would pass either way.
- **Practical limits [C thresholds; I conclusion].** FF learning needs ≥15 m/s plus calibrated extrinsics, and torqued has the same 15 m/s floor (`alpha:openpilot/selfdrive/locationd/torqued.py:25`). On a low-speed campus course, little or no evidence would accumulate. The centre objective is off.

### 10.5 Interaction with torqued [C]

- Auto Learn doesn't override, feed or disable torqued (`steerlearnerd.py:1`; `torque_stages.py:5-6`).
- `controlsd.py:178-182`: when `LaC` is `LatControlTorque`, `torque_host is None` and `torque_learning_allowed`, it pushes `lateralTorqueParameters` (filtered factor, offset, friction) into the controller whenever `useParams` is set.
- `useParams = learning_allowed and brand in ALLOWED_CARS and torque tuning` (`torqued.py:40, 83`). Toyota is in `ALLOWED_CARS`.
- torqued changing the baseline resets Auto Learn's identity (`global_runtime.py:137-145`).
- **Kill switch.** `torque_learning_allowed = learning_allowed(...)` (`controlsd.py:68`; `controller_selection.py:233-252`). When it is False:
  - torqued runs with `allow_learning=False` (`torqued.py:270`);
  - steerlearnerd is `unavailable` (`runtime_adapter_registry.py:298`; `steerlearnerd.py:77-78`).
- **Order within a frame:** baseline FF, then the ±3 % residual, then friction (`latcontrol_torque.py:118-127`).
- **STARPILOT-mode policies.** `controller_uses_native_learning` is True only for STANDARD or `rav4_tss2` (`controller_selection.py:228-230`). A new STARPILOT-mode policy therefore gets `learning_allowed == False` (:252).

---

## 11. Vehicle policy framework (where retrofit lateral tuning lives in 7.0) [C]

### 11.1 Selection (startup only)

1. `controlsd.py:65` calls `read_selection` (`alpha:openpilot/starpilot/lateral/controller_selection.py:214-225`). It reads the `LateralControllerSelection` JSON (≤ 4096 bytes), and falls back to `default_selection` (:150-155).
2. `policy_for(CP)` (:77-135) is an if-chain of per-policy `supported_cp` checks. The Toyota entries are `corolla_tss2` (:116-117) and `rav4_tss2` (:118-120).
3. `default_selection` picks `STARPILOT` mode if a policy exists and it isn't in the HKG `PROFILES`. **A new policy would be auto-selected on the next boot.**
4. `KNOWN_POLICIES` maps fingerprint to brand (:17-63) and gates `parse_document` (:176-182) and `replace_mode` (:188). **A new platform must be added here.**
5. `LatControlTorque.__init__` (`latcontrol_torque.py:49-64`) raises if the mode is STARPILOT and there is no policy. It calls `create_extension` (`alpha:openpilot/starpilot/lateral/torque_extension.py:25-83`), an if-chain on the policy name that lazily imports the class (:50-53 for Corolla).

### 11.2 Policy interface

- `__init__(self, parent, CP)`:
  - `parent` is `LatControlTorque`. A policy may replace `parent.pid`, read `dt`, `torque_params` and `steer_max`, and call `update_limits()`, `torque_from_lateral_accel` and `_check_saturation`.
  - It must guard with `supported_cp` (`corolla_tss2_policy.py:115-116`).
- `update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature, curvature_limited, lat_delay)` returns `(-output_torque, 0.0, pid_log)`.
  - Called from `latcontrol_torque.py:88-92`; STANDARD mode uses `update_standard` (:96-158) instead.
  - Inactive: reset and return 0 (`corolla_tss2_policy.py:137-146`).
- **Optional hooks:**
  - `FACTOR_MULT` (`torque_extension.py:12-15`);
  - `steer_ratio_scale(speed)` (→ `controlsd.py:172-174`, via `torque_extension.py:17-18`);
  - `apply_turn_assist(...)` (`torque_extension.py:99-102`);
  - `auto_stages.apply_stages(...)` (`corolla_tss2_policy.py:178-179`).

### 11.3 Shaping in the Corolla TSS2 template (`alpha:openpilot/starpilot/lateral/corolla_tss2_policy.py:130-199`)

- **Feed-forward:** `ff = gravity_adjusted_future_lat_accel - latAccelOffset·roll_fade` (:173), times a sigmoid turn-in / unwind scale (:74-87, :174).
- **Friction threshold:** a calm-window raise of the standard 0.30 (:90-102; `torque_shaping.py:49-50`). Jerk deadzone from `torque_shaping.py:41-46`.
- **Friction:** `get_friction(error + JERK_GAIN·jerk, deadzone, threshold, parent.torque_params)` (:180). Manual or torqued friction still applies through `torque_params`.
- **Output:** a centre output scale with a 0.65 floor (:110, :187).
- **Shared constants:** `KP=0.6`, `KI=0.35`, `KP_INTERP`, `JERK_GAIN=0.22` (`torque_shaping.py:20-38`).

### 11.4 Damping (`k_d`)

- **`PIDController` accepts `k_d`** as a scalar or a `([bp],[v])` table, and computes `d = k_d · error_rate` (`alpha:openpilot/common/pid.py:7-10, 28-29, 45`).
- **Precedent:** `genesis_gv70_policy.py:66-68` passes `[GENESIS_GV70_MEASUREMENT_DAMPING_SPEED_BP, GENESIS_GV70_MEASUREMENT_DAMPING_V]` as `k_d`. Its `error_rate = 0.0 if CS.steeringPressed else -measurement_rate` (:146-148). That is damping on the measured lateral-accel rate.
- **Corolla** already passes `error_rate=-measurement_rate` with `k_d=0` (`corolla_tss2_policy.py:184`; filtered measurement rate :124, :165-167).
- **STANDARD mode has no D term,** because `update_standard` never passes `error_rate` (`latcontrol_torque.py:137`).
- **A custom `pid` survives TorqueHost updates [I].** `update_torque_parameters` only calls `update_limits()` on it (`latcontrol_torque.py:68-78`).

### 11.5 Retrofit policy file outline

Proposed file: `openpilot/starpilot/lateral/corolla_retrofit_policy.py`.

1. **Imports** as in Corolla TSS2: `torque_stages`, `apply_turn_assist`, `log`, `structs`, `get_friction`, `PIDController`, `FirstOrderFilter`, `torque_shaping`, `CAR`.
2. **`supported_cp(CP)`:** brand toyota, exact retrofit fingerprint, torque control, torque tuning, not dashcam-only, not passive (copy `corolla_tss2_policy.py:38-46`).
3. **Per-car constants:** FF boost / reduction, friction threshold, a `KD_INTERP` table, centre taper. These suit the weak-self-centering hydraulic rack and its stiction.
4. **Pure shaping functions** built on `torque_shaping.sigmoid`.
5. **Class:**
   - `__init__` builds `PIDController([speeds, kp], KI, [kd_bp, kd_v], rate=1/dt)`, calls `update_limits()`, and sets up the filters and `low_speed_reset_threshold = max(CP.minSteerSpeed, 0.3)`.
   - `update` follows the Corolla flow. Freeze `error_rate` while `steeringPressed`, as GV70 does.
6. **Registration:**
   - `policy_for` and `KNOWN_POLICIES` (`controller_selection.py`);
   - `create_extension` (`torque_extension.py`);
   - tests modeled on `lateral/tests/test_corolla_tss2_policy.py`;
   - update `test_controller_selection.py` (not read).
7. **Consequences:** the policy is auto-selected (STARPILOT mode) and native learning is off.

### 11.6 Deadzone note

- The alpha applies `steering_angle_deadzone_deg=0.3` only for the Prius retrofit (`alpha:…/toyota/interface.py:93-95`). Matrix retrofit gets 0.0 (`alpha:opendbc_repo/opendbc/car/interfaces.py:221-228`).
- The policy reads `parent.steering_angle_deadzone_deg` (`corolla_tss2_policy.py:152`; `latcontrol_torque.py:58`).

---

## 12. Other runtime behaviors relevant to porting

### 12.1 radard when `radarUnavailable=False` but no radar exists [C]

- **Toyota RadarInterface.** It builds a bus-1 parser for 0x210–0x22F plus STATUS_MSG, and returns None until 0x22F arrives (`alpha:…/toyota/radar_interface.py:11-25, 46, 53-60`). The empty 20 Hz output is used only when no radar parser exists, which means `radarUnavailable=True` (`alpha:opendbc_repo/opendbc/car/interfaces.py:88-92`).
- **card** publishes `radarTracks` only when it has data (`card.py:1070-1080`), so it **never publishes**.
- **radard** subscribes to `modelV2`, `carState` and `radarTracks`, and sets `radar_state_valid = sm.all_checks()` (`alpha:openpilot/selfdrive/controls/radard.py:331, 364-370, 411`). So `radarState.valid` is always False. radarErrors stay all False, so there is no radarFault.
- **selfdrived** doesn't ignore radarState (`selfdrived.py:186`). `all_checks()` fails while the message is still alive and on frequency, so it raises **`commIssue`** (`selfdrived.py:598-606`; soft disable plus no entry, `events.py:854-857`).
- **Fix when porting:** omit `Bus.radar`.

### 12.2 Other `canValid=False` paths in card.py [C]

| Location | Condition | Reaches us? |
|---|---|---|
| `alpha:openpilot/selfdrive/car/card.py:1134` | `ioniq6_long_selected and ioniq6_long_lost` | No. Set only for `HYUNDAI_IONIQ_6` (:208, 247-275). |
| `card.py:1146` | prearmed and lost | No. Returns at :1135; prearmed only in the Ioniq 6 handoff (:1396). |
| `card.py:1393` | handoff not CONFIRMED (`ioniq6_long_pending`) | No (:273). |
| `card.py:1430` | selected and not prearmed | No. |
| `alpha:opendbc_repo/opendbc/car/gm/interface.py:130` | GM CC taint | No. |

- **Vehicle-startup owner.** Its gates (`card.py:1273, 1423, 1477`) stay inactive: `startup_owner` exists only in Hyundai files (`alpha:openpilot/starpilot/vehicle_startup.py:11-24`).
- **Pre-init gate.** `card.py:1361`: `not CS.canValid or CS.canTimeout` before init publishes empty sendcan and returns. This **blocks `ControlsReady`** and safety-mode switching.
- **Other consumers:** `controlsd.py:216, 248, 322, 339` (`latActive`); `selfdrived.py:592`; `plannerd.py:86, 97`.
- **6.7.8 comparison.** `fork:selfdrive/car/card.py` has no `canValid`/`canTimeout` writes.

### 12.3 door_locks (0x750) [C]

- **Off by default.** `LockDoors` and `UnlockDoors` default to `"0"` (`params_keys.h:290-291`; `alpha:openpilot/starpilot/vehicle_preferences.py:86-89, 192-194`; `door_locks.py:18-20`).
- **Needs a gear transition.** A command needs a P↔non-P transition at standstill (`door_locks.py:22-35`), and the VSS forces D.
- **Panda limits.** The panda allows only the two exact payloads, and only when stationary (`toyota.h:449-462`). Tester-present needs radar diagnostics, which are off under stock long (`toyota.h:517`; `carcontroller.py:395-396`).

### 12.4 LKAS_HUD TX built from a zeroed bus-2 copy [C]

- **Source.** `CS.lkas_hud = copy.copy(cp_cam.vl["LKAS_HUD"])` (`carstate.py:189`) gets the zero-filled dict (`parser.py:151-154`).
- **Effect.** `create_ui_command` overrides LANE_SWAY_FLD (default 7), BUZZER, WARNING, SENSITIVITY (default 2) and TOGGLE (default 1) with 0 (`toyotacan.py:145-185`). It is sent on bus 0 every 20 frames and on alert/cancel transitions (`carcontroller.py:372-389`). Allowed as TX with `check_relay` (`toyota.h:8`).
- **Consumers.** None of our devices accepts 0x412: emulator RX filters `corolla_emulator.ino:909-922`, stalk `cruise_stalk.ino:96-97, 429-438`, VSS has no RX. Whether the 2016 EPS or the 2005 cluster consumes it is [NF].
- **If the cam parser is dropped,** the port must give `lkas_hud` a default the way 6.7.8 does (`fork:…/toyota/carstate.py:234`) [I].

### 12.5 Toyota AOL [C]

- **openpilot side.** `aol.py qualified()` requires `CAMERA_TORQUE_CARS ∪ RADAR_TORQUE_CARS` (TSS2), the TSS2 flag, and `safetyParam == EPS_SCALE` (`alpha:openpilot/starpilot/car/toyota/aol.py:9-59`).
- **Panda side.** `toyota_aol_enabled` needs param ∈ {73, 585, 4169, 4681} and altExp 32/160/288 (`alpha:opendbc_repo/opendbc/safety/modes/toyota_aol.h:95-100`).
- **If it were enabled,** it would need these on bus 0, all **8 bytes** (`toyota_aol.h:51-93`; RX health `safety.h:81-101`):
  - 0x1D3 (MAIN_ON, ACC_FAULTED);
  - 0x3BC;
  - 0x620;
  - 0x262 (LKA_STATE ∉ {0, 3, 9, 11, 17, 21, 25}).
- **Our 0x262 is 5 bytes** (`toyota_new_mc_pt.dbc:8`), so AOL can't pass on our bus without EPS_STATUS length changes.

---

## 13. Settings migration (what happens to our params) [C]

### 13.1 Functions in `alpha:openpilot/starpilot/state_migration.py`

- **`snapshot_settings`** (:172-181) copies every Params file into an archive: ≤4096 keys, ≤32 MiB each, ≤256 MiB total, with a manifest (`starpilot-raw-settings` v1) and 0700/0600 permissions (:147-169).
- **`restore_snapshot`** (:198-217) restores exact bytes into a **new** namespace and refuses to overwrite one. "Offline recovery, not an upgrade" (`README.md:31-33`).
- **`validate_bundle` / `decode_bundle` / `stage_settings`** (:220-292): `{format:"starpilot-settings", version:1, source{…}, preferences, pending, omitted}`.
  - `preferences` is a subset of 8 booleans and must include `AlwaysOnLateral` (:16-19, 232).
  - `stage_settings` writes `staged/<sha>.json` and **activates nothing**. No consumer exists (grep; `README.md:77-78`).
- **Dom handoff marker** (:346-371): `<namespace.parent>/.starpilot-dom-handoff-<sha256(namespace)>.json` with a strict format, owner and mode. A new token forces the migration to run again (:405-409). **It imports nothing.**

### 13.2 First start

- `alpha:openpilot/system/manager/manager.py:30`: `prepare_manager_start(params, starpilot_storage_root(), auto_migrate=True)`.
- If the namespace is uninitialized and non-empty, the code snapshots it, then removes every key except the **16 `OPERATIONAL_KEYS`**: DongleId, HardwareSerial, GithubSshKeys, GithubUsername, SshEnabled, GsmApn, GsmMetered, GsmRoaming, NetworkMetered, BluetoothEnabled, ConnectProvider, PairingProvider, PairingEmail, PrimeType, AssistNowToken, SecOCKey (:25-29, 303-314).
- The 8-key preference allowlist is also dropped (:455-456). Receipt: `migration.json` (:316-342).
- Leftover unknown keys with `auto_migrate` off give `MigrationRequired` (:437-454). So restoring a 6.x namespace wholesale isn't a startup-safe route.

### 13.3 Locations on device

| Item | Path | Citation |
|---|---|---|
| StarPilot storage root | `/data/starpilot` (or `/data/starpilot-<OPENPILOT_PREFIX>`) | `alpha:openpilot/starpilot/storage.py:12-29` |
| Snapshots | `/data/starpilot/snapshots/<sha256>/values/<key>`, `manifest.json`, `migration.json` | `state_migration.py:151, 161, 298, 319` |
| Profile marker | `/data/starpilot/profiles/<sha256(namespace)>.json` | :378-383 |
| Staged bundles | `/data/starpilot/staged/<digest>.json` | :290 |
| Galaxy credentials | `/data/starpilot/galaxy` | `storage.py:32-34` |
| Params namespace | `params.get_param_path()` (native; not traced) [NF] | `state_migration.py:376` |

**Manual carry-over [I]:** read the key files under `snapshots/<id>/values/` and re-enter the values through the 7.0 UI or Galaxy, or through `VehicleSelection` / `TorqueOverrideDocument` where applicable.

### 13.4 Galaxy toggle backups

- **Expected format.** `alpha:openpilot/starpilot/galaxy/toggle_backup.py` accepts exactly `{format:"galaxy-toggles", version:1, createdAt, metric, vehicle, settings, layout}`, at most 256 KiB (:55-61). Each entry is exactly `{page, key, value:str≤128}` with no duplicates (:73-79).
- **Filtering.** Only available, eligible rows are kept (`analytics/settings.py:12-16, 54-60`). There are vehicle and unit checks, the car must be parked, and values are re-validated (:64-114).
- **A 6.x backup is rejected.** It has format `"starpilot-toggle-backup"` with a `data` blob (`fork:starpilot/system/the_galaxy/the_galaxy.py:1232-1233, 10321-10337`). There is no shim.
- **6.x automatic backups** live under `fork:starpilot/common/starpilot_variables.py:163` (`toggle_backups`). The alpha doesn't read them [I].

### 13.5 Fate of our keys

| Setting | 6.7.8 key (`fork:common/params_keys.h`) | In alpha table? | After first start | 7.0 equivalent |
|---|---|---|---|---|
| Friction 0.15 | `SteerFriction` (:759), `SteerFrictionStock` (:760) | yes (`alpha :112-113`) | dropped | TorqueHost; not admitted for Toyota (§9) |
| Lat accel factor 4.05 | `SteerLatAccel` (:763), `…Stock` (:764) | yes (`:110-111`) | dropped | equals the alpha Matrix base |
| Steer ratio 17.4 | `SteerRatio` (:767), `…Stock` (:768) | **no** | dropped | geometry owner (GM-only) or CarSpecs |
| LaneCentering | `LaneCentering` (:454) | yes (`:98`, default 0) | reset | admission required (§8) |
| Learning off | `ForceAutoTuneOff` (:385, entry `{PERSISTENT, BOOL, "1", "0", 2}`; which value is the effective default depends on the fork's key format [I]) | yes (`:109`, default `"0"`) | **reverts to learning on** | re-set to `1`, or `SteeringLearningPreferences` |
| `ForceAutoTune` | :384 | no | dropped | — |
| `AdvancedLateralTune` | :191 | yes (`:104`) | dropped | — |
| SAS offset | `RetrofitSASOffset` (:642) | **no** | dropped | must be ported |
| Center deadzone 0.3° | `RetrofitSteerAngleDeadzone` (:643) | **no** | dropped | `configure_torque_tune` argument |
| Other retrofit tunes | `RetrofitTune*`, `RetrofitNonlinear*`, `RetrofitNNFF*`, `RetrofitPauseSteering` (:624-674), `RetrofitPedalOffsetStandstill` | no | dropped | NNFF gone; policy framework |
| `SteerKP`, `SteerDelay`, `UseAutoSteerDelay` | :756, :761, :812 | no | dropped | — |
| Car selection | `FINGERPRINT` env in `launch_env.sh` | — | — | `VehicleSelection` key or env (§3, step 2) |

---

## 14. Realtime scheduling audit (for any new process or spawn added during the port) [C unless noted]

- **Inheritance.** No code sets `SCHED_RESET_ON_FORK`. Linux keeps SCHED_FIFO across fork, clone and exec, so any child of a FIFO thread inherits FIFO unless it drops it itself.
- **Helpers.** `alpha:openpilot/common/realtime.py:18-47`: `config_realtime_process` sets FIFO plus affinity; `drop_realtime` sets SCHED_OTHER. C++ uses `util::set_realtime_priority` (`common/util.cc:36-44`).
- **Manager.** The manager isn't realtime. Children are `multiprocessing.Process` or `Popen` (`system/manager/process.py:157, 208, 245`), so each starts SCHED_OTHER.

| Process (when) | Class / priority / cores | Spawns | Children inherit FIFO? |
|---|---|---|---|
| card (onroad) | FIFO 53, core 4 (`card.py:1546`) | none found | n/a |
| controlsd | FIFO 53, then 52; cores 4/5 (`controlsd.py:496-500`) | none found | n/a |
| selfdrived | FIFO 53, core 5 (`selfdrived.py:1898`) | `git rev-parse` once, via `get_short_branch` (`events.py:240`; `common/git.py:15-16`; `common/utils.py:149-156`) | **yes**, short-lived (path C; whether it fires is I) |
| plannerd | FIFO 51, core 5 (`plannerd.py:336`, affinity :411) | none | n/a |
| radard | FIFO 51 (`radard.py:402`, affinity :419) | none | n/a |
| locationd, calibrationd, torqued, paramsd, lagd | FIFO 5, cores 0–3 (`locationd.py:265`, `calibrationd.py:265`, `torqued.py:260`, `paramsd.py:248`, `lagd.py:390`) | none | n/a |
| steerlearnerd | **SCHED_OTHER nice 10** (`flm/steerlearnerd.py:226-231`) | `fit_worker` via Popen (`flm/fit_process.py:46-53`); the worker resets to OTHER (`fit_worker.py:22-31`) | no |
| modeld | FIFO 54, core 7 (`modeld.py:389`) | tinygrad worker pool / compilers (`tinygrad/engine/worker.py:38-44`); jetlink threads drop FIFO (`jetlink/transport/priority.py:36-47`) | [I] only if spawned after :389; not traced |
| dmonitoringmodeld, dmonitoringd | FIFO 5 | none | n/a |
| pandad (Python) | OTHER | `./pandad` (`pandad.py:147`), which sets FIFO 54, core 3 itself (`pandad/main.cc:13-15`) | no |
| encoderd | FIFO 52 (`encoderd.cc:214-216`) | none | n/a |
| loggerd | not FIFO (`loggerd.cc:351` commented out) | popen (`logger.cc:80`; `bootlog.cc:41`) | no |
| ui | FIFO 50, then `drop_realtime` at the first frame on tici (`ui.py:35, 66-73`) | wifi, software, busctl, ffmpeg helpers | [I] mostly no; children started before the drop, or from worker threads created before it, would inherit |
| sensord | FIFO 1, core 1 (`sensord.py:97`) | `sudo` writes (`sensord.py:40`; `common/utils.py:39, 45`) | **yes**, FIFO 1 [I on order] |
| hardwared, athenad, journald, uploader, timed, tombstoned, modem, galaxy, maps, flm owners | OTHER | many | no |

**Porting rule [I]:** any new retrofit daemon or helper that spawns subprocesses from a FIFO process should either spawn before `config_realtime_process` or drop realtime in the child, following the `steerlearnerd` / `fit_worker` pattern.

---

## 15. Risk register

| # | Risk | Evidence | Mitigation direction |
|---|---|---|---|
| R1 | Using alpha `TOYOTA_MATRIX_RETROFIT` as-is makes the car dashcam-only | `alpha:…/toyota/interface.py:137-157` | Dedicated retrofit platform |
| R2 | Cam parser reads LKAS_HUD on bus 2, giving `canError` or `canBusMissing` | `carstate.py:189`; `parser.py:96-97, 167-183` | Skip the cam parser |
| R3 | `radarUnavailable=False` with no radar gives `commIssue` | §12.1 | Omit `Bus.radar` |
| R4 | `canValid` False before init blocks `ControlsReady` | `card.py:1361` | Verify §4 |
| R5 | LKA_STATE 0 counts as a temporary steering fault | `alpha carstate.py:23, 132` | Port the fork's bypass |
| R6 | The emulator's spoofed 0x201 enables the interceptor path on 6.7.8 | `emu:…:52, 1115-1117`; `fork interface.py:287-290` | Decide on the 0x201 policy |
| R7 | The alpha forces stock long on retrofits; op long needs a port plus a panda TX review | `interface.py:134-170`; `toyota.h:7-14` | §6.4 |
| R8 | Every admission path requires not dashcam-only | §8, §9, §10, §11 | — |
| R9 | First start wipes all tuning; learning comes back on | §13 | Re-set keys, especially `ForceAutoTuneOff` |
| R10 | `VehicleSelection` invalid or unreadable leads to MOCK | `vehicle_selection.py:82-87` | Set the selection or `FINGERPRINT` |
| R11 | No steer-ratio pin outside GM | §9.3 | Extend the geometry owner or CarSpecs |
| R12 | Fork base friction 0.06 would cap manual friction at 0.12 (< 0.15) | `torque_settings.py:69-77`; `fork override.toml:27` | Pick the base deliberately |
| R13 | Auto Learn is unlikely to accumulate evidence at campus speeds; centre objective off | §10.4 | — |
| R14 | Auto Learn profiles orphan on any CarParams or baseline change | §10.3 | — |
| R15 | Nonlinear torque map vs Auto Learn replay: unverified | §10.4 | Read `controller_replay.py` |
| R16 | `STARPILOT_DEVELOPMENT.md` panda scope is wrong | §7 | Trust `build` / `SConscript` |
| R17 | F4 build under `-Werror` is unverified; shipped binaries can't be tied to source | §7 | Build before relying on it |
| R18 | Real EPS 0x260 rate is unknown against the 50 Hz RX check and 1 s lag rule | §6.1 | Measure |
| R19 | Emulator background sends zero-payload 0x7E0–0x7E8 (UDS/OBD IDs) | `emu:…:680` | Check FW-query interaction |
| R20 | AOL can't apply (0x262 is 5 bytes, param 856) | §12.5 | — |
| R21 | `retrofitDiag` must move from `@31` to `@37`; old logs won't decode the same | `alpha custom.capnp` | — |
| R22 | A new STARPILOT policy is auto-selected and forces learning off | §11.1, §10.5 | Intended; note it |

---

## 16. Open questions and unfinished leads

1. **Bus-2 topology.** In an onroad 6.7.8 rlog, count `src==2` frames and 0x412 at `src==2`.
2. **Real EPS / SAS rates.** Measure 0x25, 0x260 and 0x262 rates; they aren't in any sketch.
3. **Panda.** Read `alpha:openpilot/starpilot/panda_wake.py` (firmware variant choice) and confirm the F4 build compiles.
4. **`saved_source.read_saved`.** Find out what happens when `VehicleSelection` is missing (Auto or MOCK).
5. **`required-platforms.json`.** Find which test consumes it and whether a new platform must be listed.
6. **Auto Learn replay.** Read `controller_replay.py`, `learning_wire.py` and `fullrate_collector.py` for per-platform restrictions and nonlinear-map handling.
7. **Lateral UI and learning files.** Read `learning_preferences.py`, `controller_feature.py`, `lane_centering.py`, `test_controller_selection.py` and `test_torque_runtime.py` in full.
8. **modeld.** Trace when the tinygrad worker pool spawns relative to the FIFO call. Check whether ui worker threads drop realtime.
9. **Params path.** Trace the device path of the Params namespace (`Params.get_param_path()`).
10. **Galaxy recovery.** Read the `SettingsRecovery` route bodies (`galaxy/batch_routes.py:152-160`) and `settings_retirement.py` / `legacy_cache_migration.py`.
11. **Scalar learner.** Confirm at runtime that `learning_producer` is unused.
12. **Op long safety.** Analyze the panda TX/RX set for op long on a non-TSS2 Toyota without the interceptor.
13. **Fork `ForceAutoTuneOff` default.** Determine which of its two values is the effective default.

---

*Prepared from read-only inspection at the pinned commits. Nothing in this document has been run on hardware.*
