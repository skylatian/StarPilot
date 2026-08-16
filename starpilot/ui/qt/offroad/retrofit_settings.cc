#include "starpilot/ui/qt/offroad/retrofit_settings.h"

StarPilotRetrofitPanel::StarPilotRetrofitPanel(StarPilotSettingsWindow *parent, bool forceOpen)
    : StarPilotListWidget(parent), parent(parent) {
  forceOpenDescriptions = forceOpen;

  QStackedLayout *retrofitLayout = new QStackedLayout();
  addItem(retrofitLayout);

  StarPilotListWidget *retrofitList = new StarPilotListWidget(this);
  ScrollView *retrofitPanel = new ScrollView(retrofitList, this);
  retrofitLayout->addWidget(retrofitPanel);

  StarPilotListWidget *tuningList = new StarPilotListWidget(this);
  ScrollView *tuningPanel = new ScrollView(tuningList, this);
  retrofitLayout->addWidget(tuningPanel);

  StarPilotListWidget *steeringList = new StarPilotListWidget(this);
  ScrollView *steeringPanel = new ScrollView(steeringList, this);
  retrofitLayout->addWidget(steeringPanel);

  StarPilotListWidget *advancedSteeringList = new StarPilotListWidget(this);
  ScrollView *advancedSteeringPanel = new ScrollView(advancedSteeringList, this);
  retrofitLayout->addWidget(advancedSteeringPanel);

  RetrofitTuneTablePanel *tuneTableWidget = new RetrofitTuneTablePanel(parent, retrofitLayout, forceOpen);
  QObject::connect(tuneTableWidget, &RetrofitTuneTablePanel::openSubSubPanel, this, &StarPilotRetrofitPanel::openSubSubPanel);
  ScrollView *tuneTablePanel = new ScrollView(tuneTableWidget, this);
  retrofitLayout->addWidget(tuneTablePanel);

  // --- Main retrofit list ---

  ButtonControl *pedalTuningButton = new ButtonControl(
      tr("Pedal Tuning"),
      tr("MANAGE"),
      tr("<b>Interceptor pedal mapping for standstill launch and creep.</b>"));
  QObject::connect(pedalTuningButton, &ButtonControl::clicked, [retrofitLayout, tuningPanel, this]() {
    retrofitLayout->setCurrentWidget(tuningPanel);
    emit openSubPanel();
  });
  if (forceOpenDescriptions) {
    pedalTuningButton->showDescription();
  }
  retrofitList->addItem(pedalTuningButton);

  ButtonControl *steeringTuningButton = new ButtonControl(
      tr("Nonlinear Steering"),
      tr("MANAGE"),
      tr("<b>Sigmoid-linear torque model for dual power steering.</b> "
         "Caps torque at large corrections to prevent wind-up and oscillation."));
  QObject::connect(steeringTuningButton, &ButtonControl::clicked, [retrofitLayout, steeringPanel, this]() {
    retrofitLayout->setCurrentWidget(steeringPanel);
    emit openSubPanel();
  });
  if (forceOpenDescriptions) {
    steeringTuningButton->showDescription();
  }
  retrofitList->addItem(steeringTuningButton);

  ButtonControl *controllerTuneButton = new ButtonControl(
      tr("Controller Tune"),
      tr("MANAGE"),
      tr("<b>Vehicle-specific lateral tuning constants.</b> "
         "KP gain curve, FF window, turn dynamics, and center taper. "
         "Most values take effect immediately while driving."));
  QObject::connect(controllerTuneButton, &ButtonControl::clicked, [retrofitLayout, tuneTablePanel, this]() {
    retrofitLayout->setCurrentWidget(tuneTablePanel);
    emit openSubPanel();
  });
  if (forceOpenDescriptions) {
    controllerTuneButton->showDescription();
  }
  retrofitList->addItem(controllerTuneButton);

  ParamControl *pauseSteeringToggle = new ParamControl(
      "RetrofitPauseSteering",
      tr("Pause Steering"),
      tr("<b>Disable openpilot steering while driving.</b> Longitudinal (Comma Pedal) can stay active if engaged. Takes effect immediately."),
      "");
  if (forceOpenDescriptions) {
    pauseSteeringToggle->showDescription();
  }
  retrofitList->addItem(pauseSteeringToggle);

  const float defaultSASOffset = 0.0f;
  std::vector<QString> sasOffsetResetButton{tr("Reset")};
  sasOffsetToggle = new StarPilotParamValueButtonControl(
      "RetrofitSASOffset",
      tr("SAS Offset (Default: %1°)").arg(QString::number(defaultSASOffset, 'f', 0)),
      tr("<b>Corrects a physically misaligned steering angle sensor.</b> "
         "Set to the raw angle your SAS reports when wheels are straight. "
         "Takes effect immediately while driving."),
      "",
      -180.0f, 180.0f, QString("°"), std::map<float, QString>(), 1.0f,
      true, {}, sasOffsetResetButton, false, false, 150);
  if (forceOpenDescriptions) {
    sasOffsetToggle->showDescription();
  }
  retrofitList->addItem(sasOffsetToggle);

  QObject::connect(sasOffsetToggle, &StarPilotParamValueButtonControl::buttonClicked,
      [defaultSASOffset, this]() {
    if (StarPilotConfirmationDialog::yesorno(
        tr("Reset <b>SAS Offset</b> to default?"), this)) {
      params.putFloat("RetrofitSASOffset", defaultSASOffset);
      sasOffsetToggle->refresh();
    }
  });

  // --- Pedal tuning subpanel ---

  const float defaultPedalOffsetStandstill = -0.1f;
  std::vector<QString> pedalOffsetResetButton{tr("Reset")};
  pedalOffsetToggle = new StarPilotParamValueButtonControl(
      "RetrofitPedalOffsetStandstill",
      tr("Pedal Offset (Default: %1)").arg(QString::number(defaultPedalOffsetStandstill, 'f', 2)),
      tr("<b>Low-speed deadband subtracted from accel before pedal scaling.</b> Less negative values apply gas sooner from a stop. Takes effect immediately while driving."),
      "",
      -0.5f, 0.2f, QString(), std::map<float, QString>(), 0.05f, false, {}, pedalOffsetResetButton, false, false, 150);
  if (forceOpenDescriptions) {
    pedalOffsetToggle->showDescription();
  }
  tuningList->addItem(pedalOffsetToggle);

  QObject::connect(pedalOffsetToggle, &StarPilotParamValueButtonControl::buttonClicked, [defaultPedalOffsetStandstill, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Pedal Offset</b> to default?"), this)) {
      params.putFloat("RetrofitPedalOffsetStandstill", defaultPedalOffsetStandstill);
      pedalOffsetToggle->refresh();
    }
  });

  // --- Nonlinear steering subpanel ---

  ParamControl *nonlinearEnableToggle = new ParamControl(
      "RetrofitNonlinearSteering",
      tr("Enable Nonlinear Steering"),
      tr("<b>Replace the linear torque model with a sigmoid-linear curve.</b> "
         "Provides high response for small corrections while capping torque at large inputs. "
         "Requires offroad cycle to take effect."),
      "");
  if (forceOpenDescriptions) {
    nonlinearEnableToggle->showDescription();
  }
  steeringList->addItem(nonlinearEnableToggle);

  curveWidget = new SigmoidCurveWidget(this);
  curveWidget->setParams(
    params.getFloat("RetrofitNonlinearStrength"),
    params.getFloat("RetrofitNonlinearSaturation"),
    params.getFloat("RetrofitNonlinearBias"));
  steeringList->addItem(curveWidget);

  const float defaultStrength = 0.0f;
  std::vector<QString> strengthResetButton{tr("Reset")};
  strengthToggle = new StarPilotParamValueButtonControl(
      "RetrofitNonlinearStrength",
      tr("Sigmoid Strength (Def. %1)").arg(QString::number(defaultStrength, 'f', 2)),
      tr("<b>Blend between linear (0) and full sigmoid (1).</b> "
         "Increase if the wheel oscillates or whips back in turns. "
         "Decrease if steering feels sluggish entering corners. "
         "At 0, behavior is identical to stock linear."),
      "",
      0.0f, 1.0f, QString(), std::map<float, QString>(), 0.05f, false, {}, strengthResetButton, false, false, 150);
  if (forceOpenDescriptions) {
    strengthToggle->showDescription();
  }
  steeringList->addItem(strengthToggle);

  QObject::connect(strengthToggle, &StarPilotParamValueButtonControl::buttonClicked, [defaultStrength, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Strength</b> to default?"), this)) {
      params.putFloat("RetrofitNonlinearStrength", defaultStrength);
      strengthToggle->refresh();
      curveWidget->setStrength(defaultStrength);
    }
  });

  const float defaultSaturation = 2.5f;
  std::vector<QString> saturationResetButton{tr("Reset")};
  saturationToggle = new StarPilotParamValueButtonControl(
      "RetrofitNonlinearSaturation",
      tr("Saturation (Default: %1)").arg(QString::number(defaultSaturation, 'f', 1)),
      tr("<b>How quickly the torque curve flattens at large inputs.</b> "
         "Increase if oscillation only happens in sharp turns (caps torque sooner). "
         "Decrease if the car understeers mid-corner (allows more torque before capping)."),
      "",
      0.5f, 5.0f, QString(), std::map<float, QString>(), 0.1f, false, {}, saturationResetButton, false, false, 150);
  if (forceOpenDescriptions) {
    saturationToggle->showDescription();
  }
  steeringList->addItem(saturationToggle);

  QObject::connect(saturationToggle, &StarPilotParamValueButtonControl::buttonClicked, [defaultSaturation, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Saturation</b> to default?"), this)) {
      params.putFloat("RetrofitNonlinearSaturation", defaultSaturation);
      saturationToggle->refresh();
      curveWidget->setSaturation(defaultSaturation);
    }
  });

  const float defaultBias = 0.0f;
  std::vector<QString> biasResetButton{tr("Reset")};
  biasToggle = new StarPilotParamValueButtonControl(
      "RetrofitNonlinearBias",
      tr("L/R Bias (Default: %1)").arg(QString::number(defaultBias, 'f', 2)),
      tr("<b>Compensate for asymmetric EPS response.</b> "
         "Positive = more torque going left. Negative = more going right. "
         "Adjust if one direction overshoots more than the other."),
      "",
      -1.0f, 1.0f, QString(), std::map<float, QString>(), 0.05f, false, {}, biasResetButton, false, false, 150);
  if (forceOpenDescriptions) {
    biasToggle->showDescription();
  }
  steeringList->addItem(biasToggle);

  QObject::connect(biasToggle, &StarPilotParamValueButtonControl::buttonClicked, [defaultBias, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Left/Right Bias</b> to default?"), this)) {
      params.putFloat("RetrofitNonlinearBias", defaultBias);
      biasToggle->refresh();
      curveWidget->setBias(defaultBias);
    }
  });

  QObject::connect(strengthToggle, &StarPilotParamValueButtonControl::valueChanged, [this](float v) {
    strengthToggle->updateParam();
    curveWidget->setStrength(v);
  });
  QObject::connect(saturationToggle, &StarPilotParamValueButtonControl::valueChanged, [this](float v) {
    saturationToggle->updateParam();
    curveWidget->setSaturation(v);
  });
  QObject::connect(biasToggle, &StarPilotParamValueButtonControl::valueChanged, [this](float v) {
    biasToggle->updateParam();
    curveWidget->setBias(v);
  });

  ButtonControl *advancedButton = new ButtonControl(
      tr("Advanced (Raw ABCD)"),
      tr("CONFIGURE"),
      tr("<b>Direct control of sigmoid-linear parameters.</b> "
         "When enabled, overrides the Strength/Saturation/Bias controls above. "
         "Four parameters per side: a=steepness, b=amplitude, c=linear slope, d=offset."));
  QObject::connect(advancedButton, &ButtonControl::clicked, [retrofitLayout, advancedSteeringPanel, this]() {
    if (!params.getBool("RetrofitNonlinearAdvanced")) {
      float str = params.getFloat("RetrofitNonlinearStrength");
      float sat = params.getFloat("RetrofitNonlinearSaturation");
      float bias = params.getFloat("RetrofitNonlinearBias");
      float lin_slope = 1.0f / 4.05f;
      float c_floor = 0.05f;
      float b_base = 1.0f * str;
      float c_base = lin_slope * (1.0f - str) + c_floor * str;
      params.putFloat("RetrofitNonlinearLeftA", sat);
      params.putFloat("RetrofitNonlinearLeftB", b_base * (1.0f + bias * 0.3f));
      params.putFloat("RetrofitNonlinearLeftC", c_base);
      params.putFloat("RetrofitNonlinearLeftD", 0.0f);
      params.putFloat("RetrofitNonlinearRightA", sat);
      params.putFloat("RetrofitNonlinearRightB", b_base * (1.0f - bias * 0.3f));
      params.putFloat("RetrofitNonlinearRightC", c_base);
      params.putFloat("RetrofitNonlinearRightD", 0.0f);
    }
    retrofitLayout->setCurrentWidget(advancedSteeringPanel);
    emit openSubSubPanel();
  });
  if (forceOpenDescriptions) {
    advancedButton->showDescription();
  }
  steeringList->addItem(advancedButton);

  // --- Advanced ABCD subpanel ---

  ParamControl *advancedEnableToggle = new ParamControl(
      "RetrofitNonlinearAdvanced",
      tr("Use Raw ABCD Parameters"),
      tr("<b>Override Strength/Saturation/Bias with direct ABCD values.</b> "
         "When ON, the controls below define the torque curve. "
         "When OFF, the user-facing controls on the previous screen are used."),
      "");
  if (forceOpenDescriptions) {
    advancedEnableToggle->showDescription();
  }
  advancedSteeringList->addItem(advancedEnableToggle);

  struct AbcdParam {
    const char *key;
    QString label;
    float defaultVal;
    float min;
    float max;
    float step;
    QString desc;
  };

  AbcdParam abcdParams[] = {
    {"RetrofitNonlinearLeftA", tr("Left A (steepness)"), 2.5f, 0.1f, 8.0f, 0.1f,
     tr("Sigmoid steepness for left turns. Higher = saturates sooner.")},
    {"RetrofitNonlinearLeftB", tr("Left B (amplitude)"), 1.0f, 0.0f, 3.0f, 0.05f,
     tr("Sigmoid amplitude for left turns. Higher = more nonlinear contribution.")},
    {"RetrofitNonlinearLeftC", tr("Left C (linear)"), 0.2f, 0.0f, 1.0f, 0.01f,
     tr("Linear slope for left turns. This is the unsaturated floor of response.")},
    {"RetrofitNonlinearLeftD", tr("Left D (offset)"), 0.0f, -0.2f, 0.2f, 0.01f,
     tr("Constant offset for left turns. Usually 0.")},
    {"RetrofitNonlinearRightA", tr("Right A (steepness)"), 2.5f, 0.1f, 8.0f, 0.1f,
     tr("Sigmoid steepness for right turns. Higher = saturates sooner.")},
    {"RetrofitNonlinearRightB", tr("Right B (amplitude)"), 1.0f, 0.0f, 3.0f, 0.05f,
     tr("Sigmoid amplitude for right turns. Higher = more nonlinear contribution.")},
    {"RetrofitNonlinearRightC", tr("Right C (linear)"), 0.2f, 0.0f, 1.0f, 0.01f,
     tr("Linear slope for right turns. This is the unsaturated floor of response.")},
    {"RetrofitNonlinearRightD", tr("Right D (offset)"), 0.0f, -0.2f, 0.2f, 0.01f,
     tr("Constant offset for right turns. Usually 0.")},
  };

  for (auto &p : abcdParams) {
    std::vector<QString> resetBtn{tr("Reset")};
    auto *toggle = new StarPilotParamValueButtonControl(
        p.key,
        tr("%1 (Dflt: %2)").arg(p.label).arg(QString::number(p.defaultVal, 'f', 2)),
        tr("<b>%1</b>").arg(p.desc),
        "",
        p.min, p.max, QString(), std::map<float, QString>(), p.step,
        false, {}, resetBtn, false, false, 150);
    if (forceOpenDescriptions) {
      toggle->showDescription();
    }
    advancedSteeringList->addItem(toggle);

    float defVal = p.defaultVal;
    const char *key = p.key;
    QObject::connect(toggle, &StarPilotParamValueButtonControl::buttonClicked, [defVal, key, toggle, this]() {
      if (StarPilotConfirmationDialog::yesorno(tr("Reset to default value?"), this)) {
        params.putFloat(key, defVal);
        toggle->refresh();
      }
    });
  }

  // --- Navigation: close subpanels ---

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubSubPanel, [retrofitLayout, steeringPanel, advancedSteeringPanel, tuneTablePanel, tuneTableWidget]() {
    QWidget *current = retrofitLayout->currentWidget();
    if (current == advancedSteeringPanel) {
      retrofitLayout->setCurrentWidget(steeringPanel);
    } else if (current == tuneTablePanel) {
      tuneTableWidget->closeDetailPanel();
    }
  });

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubPanel, [retrofitLayout, retrofitPanel, tuneTableWidget]() {
    tuneTableWidget->closeDetailPanel();
    retrofitLayout->setCurrentWidget(retrofitPanel);
  });
}
