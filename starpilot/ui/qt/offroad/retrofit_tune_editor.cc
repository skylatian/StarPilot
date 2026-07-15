#include "starpilot/ui/qt/offroad/retrofit_tune_editor.h"

static constexpr float FF_ONSET = 0.18f;
static constexpr float FF_ONSET_WIDTH = 0.08f;
static constexpr float FF_CUTOFF = 1.10f;
static constexpr float FF_CUTOFF_WIDTH = 0.30f;
static constexpr float CENTER_TAPER_LAT = 0.14f;
static constexpr float CENTER_TAPER_LAT_WIDTH = 0.04f;
static constexpr float CENTER_TAPER_SPEED = 14.0f;
static constexpr float CENTER_TAPER_SPEED_WIDTH = 2.5f;

RetrofitTuneTablePanel::RetrofitTuneTablePanel(StarPilotSettingsWindow *parent, QStackedLayout *mainLayout, bool forceOpen)
    : StarPilotListWidget(parent) {

  syncFlmToParams();

  m_tuneLayout = new QStackedLayout();
  QStackedLayout *tuneLayout = m_tuneLayout;
  addItem(tuneLayout);

  // --- Panel 0: Table overview ---
  StarPilotListWidget *tableList = new StarPilotListWidget(this);
  ScrollView *tablePanel = new ScrollView(tableList, this);
  tuneLayout->addWidget(tablePanel);

  // --- Panel 1: KP curve editor ---
  StarPilotListWidget *kpList = new StarPilotListWidget(this);
  ScrollView *kpPanel = new ScrollView(kpList, this);
  tuneLayout->addWidget(kpPanel);

  // --- Panel 2: FF window editor ---
  StarPilotListWidget *ffList = new StarPilotListWidget(this);
  ScrollView *ffPanel = new ScrollView(ffList, this);
  tuneLayout->addWidget(ffPanel);

  // --- Panel 3: Turn dynamics ---
  StarPilotListWidget *turnList = new StarPilotListWidget(this);
  ScrollView *turnPanel = new ScrollView(turnList, this);
  tuneLayout->addWidget(turnPanel);

  // --- Panel 4: Center taper ---
  StarPilotListWidget *centerList = new StarPilotListWidget(this);
  ScrollView *centerPanel = new ScrollView(centerList, this);
  tuneLayout->addWidget(centerPanel);

  // ============================================================
  // TABLE OVERVIEW (Panel 0)
  // ============================================================

  ButtonControl *kpButton = new ButtonControl(
      tr("KP Curve (offroad)"),
      tr("EDIT"),
      tr("<b>How aggressively the car corrects steering errors at each speed.</b> "
         "Lower values = gentler, slower corrections. Higher = snappier but can oscillate. "
         "Requires offroad cycle."));
  QObject::connect(kpButton, &ButtonControl::clicked, [tuneLayout, kpPanel, this]() {
    tuneLayout->setCurrentWidget(kpPanel);
    emit openSubPanel();
  });
  if (forceOpen) kpButton->showDescription();
  tableList->addItem(kpButton);

  ButtonControl *ffButton = new ButtonControl(
      tr("FF Gain (live, FLM)"),
      tr("EDIT"),
      tr("<b>Extra steering effort in mid-range turns.</b> Adds a boost to steering "
         "commands during moderate curves. Synced with FLM. "
         "Takes effect immediately."));
  QObject::connect(ffButton, &ButtonControl::clicked, [tuneLayout, ffPanel, this]() {
    tuneLayout->setCurrentWidget(ffPanel);
    emit openSubPanel();
  });
  if (forceOpen) ffButton->showDescription();
  tableList->addItem(ffButton);

  ButtonControl *turnButton = new ButtonControl(
      tr("Turn Dynamics (live, FLM)"),
      tr("EDIT"),
      tr("<b>How steering behaves entering and exiting turns.</b> Adjusts how much "
         "extra effort is added when turning in, how much is removed when straightening out, "
         "and how the wheel resists small movements. Synced with FLM. Takes effect immediately."));
  QObject::connect(turnButton, &ButtonControl::clicked, [tuneLayout, turnPanel, this]() {
    tuneLayout->setCurrentWidget(turnPanel);
    emit openSubPanel();
  });
  if (forceOpen) turnButton->showDescription();
  tableList->addItem(turnButton);

  ButtonControl *centerButton = new ButtonControl(
      tr("Center Taper (live, FLM)"),
      tr("EDIT"),
      tr("<b>Calms steering on straight highways.</b> Reduces steering output when "
         "driving mostly straight at higher speeds. Synced with FLM. "
         "Takes effect immediately."));
  QObject::connect(centerButton, &ButtonControl::clicked, [tuneLayout, centerPanel, this]() {
    tuneLayout->setCurrentWidget(centerPanel);
    emit openSubPanel();
  });
  if (forceOpen) centerButton->showDescription();
  tableList->addItem(centerButton);

  // ============================================================
  // KP CURVE EDITOR (Panel 1) — not FLM-backed
  // ============================================================

  std::vector<DraggableCurveWidget::PointDef> kpPoints = {
    {1.0f,  params.getFloat("RetrofitTuneKP1"),    0.1f, 300.0f, "RetrofitTuneKP1",   "1"},
    {1.5f,  params.getFloat("RetrofitTuneKP1_5"),  0.1f, 200.0f, "RetrofitTuneKP1_5", "1.5"},
    {2.0f,  params.getFloat("RetrofitTuneKP2"),    0.1f, 150.0f, "RetrofitTuneKP2",   "2"},
    {3.0f,  params.getFloat("RetrofitTuneKP3"),    0.1f, 100.0f, "RetrofitTuneKP3",   "3"},
    {5.0f,  params.getFloat("RetrofitTuneKP5"),    0.1f, 50.0f,  "RetrofitTuneKP5",   "5"},
    {7.5f,  params.getFloat("RetrofitTuneKP7_5"),  0.1f, 30.0f,  "RetrofitTuneKP7_5", "7.5"},
    {10.0f, params.getFloat("RetrofitTuneKP10"),   0.1f, 20.0f,  "RetrofitTuneKP10",  "10"},
    {15.0f, params.getFloat("RetrofitTuneKP15"),   0.1f, 10.0f,  "RetrofitTuneKP15",  "15"},
    {30.0f, params.getFloat("RetrofitTuneKP30"),   0.1f, 5.0f,   "RetrofitTuneKP30",  "30"},
  };

  DraggableCurveWidget *kpCurve = new DraggableCurveWidget(
      "speed (m/s)", "KP", 0.0f, 32.0f, 0.0f, 120.0f, kpPoints, this);
  kpList->addItem(kpCurve);

  QLabel *kpNote = new QLabel(tr("Drag points to adjust. Requires offroad cycle."));
  kpNote->setStyleSheet("color: #999; font-size: 28px; padding: 10px 20px;");
  kpNote->setWordWrap(true);
  kpList->addItem(kpNote);

  ButtonControl *kpResetButton = new ButtonControl(tr("Reset All KP"), tr("RESET"), "");
  QObject::connect(kpResetButton, &ButtonControl::clicked, [kpCurve, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset all KP values to defaults?"), this)) {
      float defaults[] = {100, 50, 30, 18, 8, 4.5f, 3.0f, 1.8f, 0.6f};
      const char *keys[] = {"RetrofitTuneKP1", "RetrofitTuneKP1_5", "RetrofitTuneKP2", "RetrofitTuneKP3",
                             "RetrofitTuneKP5", "RetrofitTuneKP7_5", "RetrofitTuneKP10", "RetrofitTuneKP15", "RetrofitTuneKP30"};
      for (int i = 0; i < 9; i++) {
        params.putFloat(keys[i], defaults[i]);
      }
      kpCurve->reloadFromParams();
    }
  });
  kpList->addItem(kpResetButton);

  // ============================================================
  // FF WINDOW EDITOR (Panel 2) — ff_gain is FLM-backed
  // ============================================================

  struct TuneParam {
    const char *key;
    QString label;
    float defaultVal;
    float min;
    float max;
    float step;
    QString desc;
  };

  FFWindowPreviewWidget *ffPreview = new FFWindowPreviewWidget(this);
  ffPreview->setFFParams(
      params.getFloat("RetrofitTuneFFGain"),
      FF_ONSET, FF_ONSET_WIDTH, FF_CUTOFF, FF_CUTOFF_WIDTH);
  ffList->addItem(ffPreview);

  TuneParam ffParams[] = {
    {"RetrofitTuneFFGain", tr("FF Gain"), 0.04f, 0.0f, 0.30f, 0.01f,
     tr("How much extra steering effort to add in the boost zone (see curve above). "
        "Higher = more aggressive mid-corner steering. 0 = no boost at all. "
        "Synced with FLM profile.")},
  };

  for (auto &fp : ffParams) {
    std::vector<QString> resetBtn{tr("Reset")};
    auto *toggle = new StarPilotParamValueButtonControl(
        fp.key,
        tr("%1 (Dflt: %2)").arg(fp.label).arg(QString::number(fp.defaultVal, 'f', 2)),
        tr("<b>%1</b>").arg(fp.desc), "",
        fp.min, fp.max, QString(), std::map<float, QString>(), fp.step,
        false, {}, resetBtn, false, false, 150);
    if (forceOpen) toggle->showDescription();
    ffList->addItem(toggle);

    float defVal = fp.defaultVal;
    const char *key = fp.key;
    QObject::connect(toggle, &StarPilotParamValueButtonControl::buttonClicked, [defVal, key, toggle, ffPreview, this]() {
      if (StarPilotConfirmationDialog::yesorno(tr("Reset to default?"), this)) {
        params.putFloat(key, defVal);
        auto it = s_flmKnobMap.find(key);
        if (it != s_flmKnobMap.end()) {
          writeFlmKnob(it->second, defVal);
          ensureFlmActive();
        }
        toggle->refresh();
        ffPreview->setFFParams(
            params.getFloat("RetrofitTuneFFGain"),
            FF_ONSET, FF_ONSET_WIDTH, FF_CUTOFF, FF_CUTOFF_WIDTH);
      }
    });

    QObject::connect(toggle, &StarPilotParamValueButtonControl::valueChanged, [key, ffPreview, this](float value) {
      auto it = s_flmKnobMap.find(key);
      if (it != s_flmKnobMap.end()) {
        writeFlmKnob(it->second, value);
        ensureFlmActive();
      }
      ffPreview->setFFParams(
          value,
          FF_ONSET, FF_ONSET_WIDTH, FF_CUTOFF, FF_CUTOFF_WIDTH);
    });
  }

  QLabel *ffNote = new QLabel(tr("Onset/cutoff shape is fixed. Only gain is FLM-tunable."));
  ffNote->setStyleSheet("color: #999; font-size: 28px; padding: 10px 20px;");
  ffNote->setWordWrap(true);
  ffList->addItem(ffNote);

  // ============================================================
  // TURN DYNAMICS (Panel 3) — 6 FLM-backed sliders
  // ============================================================

  TurnDynamicsPreviewWidget *turnPreview = new TurnDynamicsPreviewWidget(this);
  turnPreview->setDynamicsParams(
      params.getFloat("RetrofitTuneTurnInBoost"),
      params.getFloat("RetrofitTuneUnwindTaper"));
  turnList->addItem(turnPreview);

  TuneParam turnParams[] = {
    {"RetrofitTuneUnwindTaper", tr("Unwind Taper"), 0.55f, 0.0f, 1.20f, 0.05f,
     tr("How much to back off steering when exiting a turn (straightening out). "
        "Higher = pulls back more aggressively, preventing overshoot past center. "
        "0 = no reduction. Synced with FLM profile.")},
    {"RetrofitTuneTurnInBoost", tr("Turn-In Boost"), 0.0f, -0.10f, 0.60f, 0.05f,
     tr("Extra steering effort when initiating a turn. "
        "0 = no extra push (default for dual PS, which already responds strongly). "
        "Negative = dampen turn-in. Synced with FLM profile.")},
    {"RetrofitTuneTurnInThresholdReduction", tr("TI Thresh. Reduction"), 0.10f, 0.0f, 0.50f, 0.02f,
     tr("Adds extra resistance when entering a turn, helping the wheel hold its position. "
        "Higher = more holding force during turn-in. Synced with FLM profile.")},
    {"RetrofitTuneUnwindThresholdIncrease", tr("UW Thresh. Increase"), 0.50f, 0.0f, 1.00f, 0.05f,
     tr("Reduces resistance when straightening out, letting the wheel return freely. "
        "Higher = less holding force during turn exit. Synced with FLM profile.")},
    {"RetrofitTuneTurnInFrictionBoost", tr("TI Friction Boost"), 0.04f, 0.0f, 0.20f, 0.01f,
     tr("Adds extra overall friction compensation when entering turns. "
        "Higher = more torque to overcome real steering friction during turn-in. "
        "Synced with FLM profile.")},
    {"RetrofitTuneUnwindFrictionReduction", tr("UW Friction Reduction"), 0.30f, 0.0f, 0.60f, 0.05f,
     tr("Reduces friction compensation when straightening out. "
        "Higher = less torque fighting the wheel as it returns to center. "
        "Synced with FLM profile.")},
  };

  for (auto &tp : turnParams) {
    std::vector<QString> resetBtn{tr("Reset")};
    auto *toggle = new StarPilotParamValueButtonControl(
        tp.key,
        tr("%1 (Dflt: %2)").arg(tp.label).arg(QString::number(tp.defaultVal, 'g', 3)),
        tr("<b>%1</b>").arg(tp.desc), "",
        tp.min, tp.max, QString(), std::map<float, QString>(), tp.step,
        false, {}, resetBtn, false, false, 150);
    if (forceOpen) toggle->showDescription();
    turnList->addItem(toggle);

    float defVal = tp.defaultVal;
    const char *key = tp.key;
    QObject::connect(toggle, &StarPilotParamValueButtonControl::buttonClicked, [defVal, key, toggle, turnPreview, this]() {
      if (StarPilotConfirmationDialog::yesorno(tr("Reset to default?"), this)) {
        params.putFloat(key, defVal);
        auto it = s_flmKnobMap.find(key);
        if (it != s_flmKnobMap.end()) {
          writeFlmKnob(it->second, defVal);
          ensureFlmActive();
        }
        toggle->refresh();
        turnPreview->setDynamicsParams(
            params.getFloat("RetrofitTuneTurnInBoost"),
            params.getFloat("RetrofitTuneUnwindTaper"));
      }
    });

    QObject::connect(toggle, &StarPilotParamValueButtonControl::valueChanged, [key, turnPreview, this](float value) {
      auto it = s_flmKnobMap.find(key);
      if (it != s_flmKnobMap.end()) {
        writeFlmKnob(it->second, value);
        ensureFlmActive();
      }
      turnPreview->setDynamicsParams(
          params.getFloat("RetrofitTuneTurnInBoost"),
          params.getFloat("RetrofitTuneUnwindTaper"));
    });
  }

  // ============================================================
  // CENTER TAPER (Panel 4) — center_taper_max is FLM-backed
  // ============================================================

  CenterTaperPreviewWidget *centerPreview = new CenterTaperPreviewWidget(this);
  centerPreview->setTaperParams(
      params.getFloat("RetrofitTuneCenterTaperMax"),
      CENTER_TAPER_LAT, CENTER_TAPER_LAT_WIDTH,
      CENTER_TAPER_SPEED, CENTER_TAPER_SPEED_WIDTH);
  centerList->addItem(centerPreview);

  TuneParam centerParams[] = {
    {"RetrofitTuneCenterTaperMax", tr("Taper Max"), 0.20f, 0.0f, 0.30f, 0.02f,
     tr("How much to reduce steering when going mostly straight. "
        "0 = disabled. 0.20 = 20% quieter. Increase if you see jitter on highways. "
        "Synced with FLM profile.")},
  };

  for (auto &cp : centerParams) {
    std::vector<QString> resetBtn{tr("Reset")};
    auto *toggle = new StarPilotParamValueButtonControl(
        cp.key,
        tr("%1 (Dflt: %2)").arg(cp.label).arg(QString::number(cp.defaultVal, 'g', 3)),
        tr("<b>%1</b>").arg(cp.desc), "",
        cp.min, cp.max, QString(), std::map<float, QString>(), cp.step,
        false, {}, resetBtn, false, false, 150);
    if (forceOpen) toggle->showDescription();
    centerList->addItem(toggle);

    float defVal = cp.defaultVal;
    const char *key = cp.key;
    QObject::connect(toggle, &StarPilotParamValueButtonControl::buttonClicked, [defVal, key, toggle, centerPreview, this]() {
      if (StarPilotConfirmationDialog::yesorno(tr("Reset to default?"), this)) {
        params.putFloat(key, defVal);
        auto it = s_flmKnobMap.find(key);
        if (it != s_flmKnobMap.end()) {
          writeFlmKnob(it->second, defVal);
          ensureFlmActive();
        }
        toggle->refresh();
        centerPreview->setTaperParams(
            defVal,
            CENTER_TAPER_LAT, CENTER_TAPER_LAT_WIDTH,
            CENTER_TAPER_SPEED, CENTER_TAPER_SPEED_WIDTH);
      }
    });

    QObject::connect(toggle, &StarPilotParamValueButtonControl::valueChanged, [key, centerPreview, this](float value) {
      auto it = s_flmKnobMap.find(key);
      if (it != s_flmKnobMap.end()) {
        writeFlmKnob(it->second, value);
        ensureFlmActive();
      }
      centerPreview->setTaperParams(
          value,
          CENTER_TAPER_LAT, CENTER_TAPER_LAT_WIDTH,
          CENTER_TAPER_SPEED, CENTER_TAPER_SPEED_WIDTH);
    });
  }

  QLabel *centerNote = new QLabel(tr("Speed/lat thresholds are fixed. Only taper max is FLM-tunable."));
  centerNote->setStyleSheet("color: #999; font-size: 28px; padding: 10px 20px;");
  centerNote->setWordWrap(true);
  centerList->addItem(centerNote);

}
