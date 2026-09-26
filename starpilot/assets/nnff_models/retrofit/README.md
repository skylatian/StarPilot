# TOYOTA_COROLLA_RETROFIT NNFF models

One file per trained version, loaded only for `TOYOTA_COROLLA_RETROFIT` with the NNFF toggle on.
The stock NNFF loader never looks in this folder (it lists `nnff_models/` non-recursively and
fuzzy-matches names, so versioned files there could load without being chosen).

**Choosing a model**: Settings → StarPilot → Retrofit Options → Retrofit Tuning → **NNFF Model**
(param `RetrofitNNFFModel`). Empty = newest version here; picking one pins it. A pinned name that no
longer exists falls back to the newest. Loaded when `controlsd` starts, so a change needs an
offroad cycle. The onroad "NNFF loaded with:" alert names the version that loaded.

**Adding a model**: copy the trainer's JSON in unchanged as `v<N>_<YYYY-MM-DD>[_label].json`, with N
one higher than the last, and add a row below. Never edit or reuse an existing file. Old versions
stay so they can be selected again. `selfdrive/controls/tests/test_retrofit_nnff_models.py` checks
every file here: naming, unique versions, 18 inputs in runtime order, and torque sign against the
shipped `TOYOTA_COROLLA` model. Run it before driving a new model.

| Version | Trained | Trainer (openpilot-nnlc-tools) | Data | Loss (train / test) | sha256 | Notes |
|---------|---------|--------------------------------|------|---------------------|--------|-------|
| v1_2026-09-23 | 2026-09-23 | `2ef5cae` (sign guard), no `--symmetrize` | Full device sync to 2026-09-23: 1,493,940 engaged frames (~4.15 h), `RetrofitSASOffset` −48, balanced to ~60k rows | 0.0272 / 0.0275 | `1daff41a…da80b14` | First model. ~65–70% of stock Corolla torque; learned L/R difference is mostly a leftward offset growing with speed. Not yet driven. |

Writeup: `project_docs/research-2026-09-21-nnlc-evaluation/` in the parent docs repo.
