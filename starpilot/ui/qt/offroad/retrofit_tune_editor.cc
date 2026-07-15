#include "starpilot/ui/qt/offroad/retrofit_tune_editor.h"

RetrofitTuneTablePanel::RetrofitTuneTablePanel(StarPilotSettingsWindow *parent, QStackedLayout *mainLayout, bool forceOpen)
    : StarPilotListWidget(parent) {

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

  // --- KP Curve group ---
  ButtonControl *kpButton = new ButtonControl(
      tr("KP Curve (offroad)"),
      tr("EDIT"),
      tr("<b>Speed-dependent proportional gain.</b> Lower values reduce steering authority. "
         "Requires offroad cycle to take effect."));
  QObject::connect(kpButton, &ButtonControl::clicked, [tuneLayout, kpPanel, this]() {
    tuneLayout->setCurrentWidget(kpPanel);
    emit openSubPanel();
  });
  if (forceOpen) kpButton->showDescription();
  tableList->addItem(kpButton);

  // --- FF Window group ---
  ButtonControl *ffButton = new ButtonControl(
      tr("FF Window (live)"),
      tr("EDIT"),
      tr("<b>Feedforward scaling bell curve.</b> Controls how FF boost varies "
         "with lateral acceleration magnitude. Takes effect immediately."));
  QObject::connect(ffButton, &ButtonControl::clicked, [tuneLayout, ffPanel, this]() {
    tuneLayout->setCurrentWidget(ffPanel);
    emit openSubPanel();
  });
  if (forceOpen) ffButton->showDescription();
  tableList->addItem(ffButton);

  // --- Turn Dynamics group ---
  ButtonControl *turnButton = new ButtonControl(
      tr("Turn Dynamics (live)"),
      tr("EDIT"),
      tr("<b>Turn-in boost, unwind taper, and friction shaping.</b> Controls "
         "how the controller behaves during turn entry and exit. Takes effect immediately."));
  QObject::connect(turnButton, &ButtonControl::clicked, [tuneLayout, turnPanel, this]() {
    tuneLayout->setCurrentWidget(turnPanel);
    emit openSubPanel();
  });
  if (forceOpen) turnButton->showDescription();
  tableList->addItem(turnButton);

  // --- Center Taper group ---
  ButtonControl *centerButton = new ButtonControl(
      tr("Center Taper (live)"),
      tr("EDIT"),
      tr("<b>Reduces output near straight-ahead at highway speed.</b> "
         "Fixes jitter/oscillation on straight roads. Takes effect immediately."));
  QObject::connect(centerButton, &ButtonControl::clicked, [tuneLayout, centerPanel, this]() {
    tuneLayout->setCurrentWidget(centerPanel);
    emit openSubPanel();
  });
  if (forceOpen) centerButton->showDescription();
  tableList->addItem(centerButton);

  // ============================================================
  // KP CURVE EDITOR (Panel 1)
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
  // FF WINDOW EDITOR (Panel 2)
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

  TuneParam ffParams[] = {
    {"RetrofitTuneFFGain", tr("FF Gain"), 0.04f, 0.0f, 0.5f, 0.01f,
     tr("Peak feedforward boost magnitude. Higher = more FF near the onset/cutoff window center.")},
    {"RetrofitTuneFFOnset", tr("FF Onset"), 0.18f, 0.0f, 2.0f, 0.02f,
     tr("Lateral accel where FF boost begins ramping up.")},
    {"RetrofitTuneFFOnsetWidth", tr("Onset Width"), 0.08f, 0.01f, 1.0f, 0.01f,
     tr("How sharp the onset transition is. Smaller = sharper.")},
    {"RetrofitTuneFFCutoff", tr("FF Cutoff"), 1.10f, 0.1f, 3.0f, 0.05f,
     tr("Lateral accel where FF boost begins ramping down.")},
    {"RetrofitTuneFFCutoffWidth", tr("Cutoff Width"), 0.30f, 0.01f, 2.0f, 0.05f,
     tr("How sharp the cutoff transition is. Smaller = sharper.")},
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
    QObject::connect(toggle, &StarPilotParamValueButtonControl::buttonClicked, [defVal, key, toggle, this]() {
      if (StarPilotConfirmationDialog::yesorno(tr("Reset to default?"), this)) {
        params.putFloat(key, defVal);
        toggle->refresh();
      }
    });
  }

  // ============================================================
  // TURN DYNAMICS (Panel 3)
  // ============================================================

  TuneParam turnParams[] = {
    {"RetrofitTuneUnwindTaper", tr("Unwind Taper"), 0.55f, 0.0f, 1.0f, 0.05f,
     tr("FF reduction during turn exit. 0=none, 1=full reduction. Prevents overshoot when straightening.")},
    {"RetrofitTuneTurnInBoost", tr("Turn-In Boost"), 0.0f, 0.0f, 1.0f, 0.05f,
     tr("Extra FF during turn entry. 0=none. With dual PS, turn entry is already strong; increase only if understeering into turns.")},
    {"RetrofitTuneTransitionSpeed", tr("Transition Speed"), 10.0f, 1.0f, 30.0f, 1.0f,
     tr("Speed below which low-speed scaling is most active (m/s). Lower = transitions happen at slower speeds only.")},
    {"RetrofitTunePhaseScale", tr("Phase Scale"), 0.10f, 0.01f, 1.0f, 0.01f,
     tr("Sensitivity of turn-in/unwind detection. Smaller = more sensitive phase detection.")},
    {"RetrofitTuneFrictionLatRise", tr("Friction Lat Rise"), 0.20f, 0.01f, 2.0f, 0.02f,
     tr("How quickly friction shaping ramps up with lateral acceleration.")},
    {"RetrofitTuneFrictionJerkRise", tr("Friction Jerk Rise"), 0.24f, 0.01f, 2.0f, 0.02f,
     tr("How quickly friction shaping ramps up with lateral jerk.")},
    {"RetrofitTuneTurnInThresholdReduction", tr("TI Thresh. Reduction"), 0.10f, 0.0f, 0.5f, 0.02f,
     tr("How much the friction threshold drops during turn-in. Lower threshold = more friction compensation.")},
    {"RetrofitTuneUnwindThresholdIncrease", tr("UW Thresh. Increase"), 0.50f, 0.0f, 1.0f, 0.05f,
     tr("How much the friction threshold rises during unwind. Higher threshold = less friction compensation when straightening.")},
    {"RetrofitTuneTurnInFrictionBoost", tr("TI Friction Boost"), 0.04f, 0.0f, 0.5f, 0.01f,
     tr("Extra friction scale factor applied during turn-in.")},
    {"RetrofitTuneUnwindFrictionReduction", tr("UW Friction Reduction"), 0.30f, 0.0f, 1.0f, 0.05f,
     tr("Friction scale reduction during unwind. Lets the wheel return more freely.")},
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
    QObject::connect(toggle, &StarPilotParamValueButtonControl::buttonClicked, [defVal, key, toggle, this]() {
      if (StarPilotConfirmationDialog::yesorno(tr("Reset to default?"), this)) {
        params.putFloat(key, defVal);
        toggle->refresh();
      }
    });
  }

  // ============================================================
  // CENTER TAPER (Panel 4)
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
    {"RetrofitTuneCenterTaperMax", tr("Taper Max"), 0.20f, 0.0f, 0.5f, 0.02f,
     tr("Maximum output reduction near straight-ahead. 0=disabled, 0.20=20% reduction.")},
    {"RetrofitTuneCenterTaperLat", tr("Lat Threshold"), 0.14f, 0.01f, 1.0f, 0.02f,
     tr("Lateral accel below which taper is active. Higher = taper affects wider range of steering.")},
    {"RetrofitTuneCenterTaperLatWidth", tr("Lat Width"), 0.04f, 0.01f, 0.5f, 0.01f,
     tr("Sharpness of lateral accel transition. Smaller = sharper on/off.")},
    {"RetrofitTuneCenterTaperSpeed", tr("Speed Threshold"), 14.0f, 1.0f, 35.0f, 1.0f,
     tr("Speed above which taper activates (m/s). ~14 m/s = 31 mph.")},
    {"RetrofitTuneCenterTaperSpeedWidth", tr("Speed Width"), 2.5f, 0.1f, 10.0f, 0.5f,
     tr("Sharpness of speed transition. Smaller = sharper on/off at the threshold.")},
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
        toggle->refresh();
        centerPreview->setTaperParams(
            params.getFloat("RetrofitTuneCenterTaperMax"),
            params.getFloat("RetrofitTuneCenterTaperLat"),
            params.getFloat("RetrofitTuneCenterTaperLatWidth"),
            params.getFloat("RetrofitTuneCenterTaperSpeed"),
            params.getFloat("RetrofitTuneCenterTaperSpeedWidth"));
      }
    });

    QObject::connect(toggle, &StarPilotParamValueButtonControl::valueChanged, [centerPreview, this](float) {
      centerPreview->setTaperParams(
          params.getFloat("RetrofitTuneCenterTaperMax"),
          params.getFloat("RetrofitTuneCenterTaperLat"),
          params.getFloat("RetrofitTuneCenterTaperLatWidth"),
          params.getFloat("RetrofitTuneCenterTaperSpeed"),
          params.getFloat("RetrofitTuneCenterTaperSpeedWidth"));
    });
  }

  // ============================================================
  // NAVIGATION
  // ============================================================

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubPanel, [tuneLayout, tablePanel, kpPanel, ffPanel, turnPanel, centerPanel]() {
    QWidget *current = tuneLayout->currentWidget();
    if (current == kpPanel || current == ffPanel || current == turnPanel || current == centerPanel) {
      tuneLayout->setCurrentWidget(tablePanel);
    }
  });
}
