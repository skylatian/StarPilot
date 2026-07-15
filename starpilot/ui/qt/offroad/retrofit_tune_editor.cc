#include "starpilot/ui/qt/offroad/retrofit_tune_editor.h"

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
    emit openSubSubPanel();
  });
  if (forceOpen) kpButton->showDescription();
  tableList->addItem(kpButton);

  ButtonControl *ffButton = new ButtonControl(
      tr("FF Window (live)"),
      tr("EDIT"),
      tr("<b>Extra steering effort in mid-range turns.</b> Adds a boost to steering "
         "commands during moderate curves, tapering off for gentle and sharp turns. "
         "Takes effect immediately."));
  QObject::connect(ffButton, &ButtonControl::clicked, [tuneLayout, ffPanel, this]() {
    tuneLayout->setCurrentWidget(ffPanel);
    emit openSubSubPanel();
  });
  if (forceOpen) ffButton->showDescription();
  tableList->addItem(ffButton);

  ButtonControl *turnButton = new ButtonControl(
      tr("Turn Dynamics (live)"),
      tr("EDIT"),
      tr("<b>How steering behaves entering and exiting turns.</b> Adjusts how much "
         "extra effort is added when turning in, how much is removed when straightening out, "
         "and how the wheel resists small movements. Takes effect immediately."));
  QObject::connect(turnButton, &ButtonControl::clicked, [tuneLayout, turnPanel, this]() {
    tuneLayout->setCurrentWidget(turnPanel);
    emit openSubSubPanel();
  });
  if (forceOpen) turnButton->showDescription();
  tableList->addItem(turnButton);

  ButtonControl *centerButton = new ButtonControl(
      tr("Center Taper (live)"),
      tr("EDIT"),
      tr("<b>Calms steering on straight highways.</b> Reduces steering output when "
         "driving mostly straight at higher speeds. Fixes the small left-right jitter "
         "you might see on long straight roads. Takes effect immediately."));
  QObject::connect(centerButton, &ButtonControl::clicked, [tuneLayout, centerPanel, this]() {
    tuneLayout->setCurrentWidget(centerPanel);
    emit openSubSubPanel();
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
  // FF WINDOW EDITOR (Panel 2) — all FLM-backed
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
      params.getFloat("RetrofitTuneFFOnset"),
      params.getFloat("RetrofitTuneFFOnsetWidth"),
      params.getFloat("RetrofitTuneFFCutoff"),
      params.getFloat("RetrofitTuneFFCutoffWidth"));
  ffList->addItem(ffPreview);

  TuneParam ffParams[] = {
    {"RetrofitTuneFFGain", tr("FF Gain"), 0.04f, 0.0f, 0.30f, 0.01f,
     tr("How much extra steering effort to add in the boost zone (see curve above). "
        "Higher = more aggressive mid-corner steering. 0 = no boost at all.")},
    {"RetrofitTuneFFOnset", tr("FF Onset"), 0.18f, 0.0f, 2.0f, 0.02f,
     tr("How hard you need to be turning before the boost kicks in. "
        "Lower = boost starts in gentler curves. Higher = only boosts in sharper turns.")},
    {"RetrofitTuneFFOnsetWidth", tr("Onset Width"), 0.08f, 0.01f, 1.0f, 0.01f,
     tr("How gradually the boost ramps in. "
        "Smaller = snaps on quickly. Larger = fades in smoothly over a wider range of turning.")},
    {"RetrofitTuneFFCutoff", tr("FF Cutoff"), 1.10f, 0.1f, 3.0f, 0.05f,
     tr("How hard you need to be turning before the boost starts fading out. "
        "Lower = boost drops off in moderate turns. Higher = boost stays active into sharper turns.")},
    {"RetrofitTuneFFCutoffWidth", tr("Cutoff Width"), 0.30f, 0.01f, 2.0f, 0.05f,
     tr("How gradually the boost fades at the cutoff. "
        "Smaller = drops off abruptly. Larger = tapers out gradually.")},
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
            params.getFloat("RetrofitTuneFFOnset"),
            params.getFloat("RetrofitTuneFFOnsetWidth"),
            params.getFloat("RetrofitTuneFFCutoff"),
            params.getFloat("RetrofitTuneFFCutoffWidth"));
      }
    });

    QObject::connect(toggle, &StarPilotParamValueButtonControl::valueChanged, [key, ffPreview, this](float value) {
      auto it = s_flmKnobMap.find(key);
      if (it != s_flmKnobMap.end()) {
        writeFlmKnob(it->second, value);
        ensureFlmActive();
      }
      ffPreview->setFFParams(
          params.getFloat("RetrofitTuneFFGain"),
          params.getFloat("RetrofitTuneFFOnset"),
          params.getFloat("RetrofitTuneFFOnsetWidth"),
          params.getFloat("RetrofitTuneFFCutoff"),
          params.getFloat("RetrofitTuneFFCutoffWidth"));
    });
  }

  // ============================================================
  // TURN DYNAMICS (Panel 3) — all FLM-backed
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
        "0 = no reduction. Too high can make turn exits feel jerky.")},
    {"RetrofitTuneTurnInBoost", tr("Turn-In Boost"), 0.0f, -0.10f, 0.60f, 0.05f,
     tr("Extra steering effort when initiating a turn. "
        "0 = no extra push (default for dual PS, which already responds strongly). "
        "Negative = dampen turn-in.")},
    {"RetrofitTuneTransitionSpeed", tr("Transition Speed"), 10.0f, 1.0f, 30.0f, 1.0f,
     tr("Speed (m/s) below which the turn dynamics effects are strongest. "
        "At low speeds, the boost/taper are fully active. "
        "Above this speed, they gradually fade. 10 = ~22 mph.")},
    {"RetrofitTunePhaseScale", tr("Phase Scale"), 0.10f, 0.01f, 1.0f, 0.01f,
     tr("How quickly the system detects you're entering or exiting a turn. "
        "Smaller = reacts to smaller steering changes. "
        "Larger = needs a more obvious turn before applying boost/taper.")},
    {"RetrofitTuneFrictionLatRise", tr("Friction Lat Rise"), 0.20f, 0.01f, 2.0f, 0.02f,
     tr("How much turning activates the friction adjustments below. "
        "Smaller = friction changes happen even in gentle curves. "
        "Larger = only applies in harder turns.")},
    {"RetrofitTuneFrictionJerkRise", tr("Friction Jerk Rise"), 0.24f, 0.01f, 2.0f, 0.02f,
     tr("How much a sudden change in steering activates the friction adjustments. "
        "Smaller = quick flicks trigger friction changes. "
        "Larger = only sustained turning matters.")},
    {"RetrofitTuneTurnInThresholdReduction", tr("TI Thresh. Reduction"), 0.10f, 0.0f, 0.50f, 0.02f,
     tr("Adds extra resistance when entering a turn, helping the wheel hold its position. "
        "Higher = more holding force during turn-in. "
        "Useful if the wheel feels loose when starting to turn.")},
    {"RetrofitTuneUnwindThresholdIncrease", tr("UW Thresh. Increase"), 0.50f, 0.0f, 1.00f, 0.05f,
     tr("Reduces resistance when straightening out, letting the wheel return freely. "
        "Higher = less holding force during turn exit. "
        "Useful if the wheel feels sticky returning to center.")},
    {"RetrofitTuneTurnInFrictionBoost", tr("TI Friction Boost"), 0.04f, 0.0f, 0.20f, 0.01f,
     tr("Adds extra overall friction compensation when entering turns. "
        "Higher = more torque to overcome real steering friction during turn-in. "
        "Increase if the car understeers slightly at the start of turns.")},
    {"RetrofitTuneUnwindFrictionReduction", tr("UW Friction Reduction"), 0.30f, 0.0f, 0.60f, 0.05f,
     tr("Reduces friction compensation when straightening out. "
        "Higher = less torque fighting the wheel as it returns to center. "
        "Increase if the car overshoots when exiting turns.")},
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
  // CENTER TAPER (Panel 4) — all FLM-backed
  // ============================================================

  CenterTaperPreviewWidget *centerPreview = new CenterTaperPreviewWidget(this);
  centerPreview->setTaperParams(
      params.getFloat("RetrofitTuneCenterTaperMax"),
      params.getFloat("RetrofitTuneCenterTaperLat"),
      params.getFloat("RetrofitTuneCenterTaperLatWidth"),
      params.getFloat("RetrofitTuneCenterTaperSpeed"),
      params.getFloat("RetrofitTuneCenterTaperSpeedWidth"));
  centerList->addItem(centerPreview);

  TuneParam centerParams[] = {
    {"RetrofitTuneCenterTaperMax", tr("Taper Max"), 0.20f, 0.0f, 0.30f, 0.02f,
     tr("How much to reduce steering when going mostly straight. "
        "0 = disabled. 0.20 = 20% quieter. Increase if you see jitter on highways. "
        "Too high can make the car slow to respond to gentle lane changes.")},
    {"RetrofitTuneCenterTaperLat", tr("Lat Threshold"), 0.14f, 0.01f, 1.0f, 0.02f,
     tr("How far from perfectly straight the taper still applies. "
        "Higher = stays active during gentle curves (wider quiet zone). "
        "Lower = only active when almost perfectly straight.")},
    {"RetrofitTuneCenterTaperLatWidth", tr("Lat Width"), 0.04f, 0.01f, 0.5f, 0.01f,
     tr("How gradually the taper blends in/out as you start turning. "
        "Smaller = sharp cutoff (full taper then suddenly none). "
        "Larger = smooth transition between tapered and normal steering.")},
    {"RetrofitTuneCenterTaperSpeed", tr("Speed Threshold"), 14.0f, 1.0f, 35.0f, 1.0f,
     tr("Speed above which the taper activates (m/s). 14 = ~31 mph. "
        "Lower = taper kicks in at lower speeds. "
        "Higher = only active at highway speeds.")},
    {"RetrofitTuneCenterTaperSpeedWidth", tr("Speed Width"), 2.5f, 0.1f, 10.0f, 0.5f,
     tr("How gradually the taper ramps in as you speed up. "
        "Smaller = snaps on at the threshold speed. "
        "Larger = fades in over a wider speed range.")},
  };

  std::vector<StarPilotParamValueButtonControl *> centerToggles;
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
    centerToggles.push_back(toggle);

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
            params.getFloat("RetrofitTuneCenterTaperMax"),
            params.getFloat("RetrofitTuneCenterTaperLat"),
            params.getFloat("RetrofitTuneCenterTaperLatWidth"),
            params.getFloat("RetrofitTuneCenterTaperSpeed"),
            params.getFloat("RetrofitTuneCenterTaperSpeedWidth"));
      }
    });

    QObject::connect(toggle, &StarPilotParamValueButtonControl::valueChanged, [centerPreview, key, this](float) {
      auto it = s_flmKnobMap.find(key);
      if (it != s_flmKnobMap.end()) {
        writeFlmKnob(it->second, params.getFloat(key));
        ensureFlmActive();
      }
      centerPreview->setTaperParams(
          params.getFloat("RetrofitTuneCenterTaperMax"),
          params.getFloat("RetrofitTuneCenterTaperLat"),
          params.getFloat("RetrofitTuneCenterTaperLatWidth"),
          params.getFloat("RetrofitTuneCenterTaperSpeed"),
          params.getFloat("RetrofitTuneCenterTaperSpeedWidth"));
    });
  }

}
