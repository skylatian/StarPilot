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
      true, {}, sasOffsetResetButton, false, false);
  if (forceOpenDescriptions) {
    sasOffsetToggle->showDescription();
  }
  retrofitList->addItem(sasOffsetToggle);

  QObject::connect(sasOffsetToggle, &StarPilotParamValueButtonControl::buttonClicked,
      [defaultSASOffset, this]() {
    if (StarPilotConfirmationDialog::yesorno(
        tr("Reset <b>SAS Offset</b> to its default value?"), this)) {
      params.putFloat("RetrofitSASOffset", defaultSASOffset);
      sasOffsetToggle->refresh();
    }
  });

  const float defaultPedalOffsetStandstill = -0.1f;
  std::vector<QString> pedalOffsetResetButton{tr("Reset")};
  // Match advanced lateral Actuator Delay: no icon, Reset after +/-, default label width.
  pedalOffsetToggle = new StarPilotParamValueButtonControl(
      "RetrofitPedalOffsetStandstill",
      tr("Pedal Offset (Default: %1)").arg(QString::number(defaultPedalOffsetStandstill, 'f', 2)),
      tr("<b>Low-speed deadband subtracted from accel before pedal scaling.</b> Less negative values apply gas sooner from a stop. Takes effect immediately while driving."),
      "",
      -0.5f, 0.2f, QString(), std::map<float, QString>(), 0.05f, false, {}, pedalOffsetResetButton, false, false);
  if (forceOpenDescriptions) {
    pedalOffsetToggle->showDescription();
  }
  tuningList->addItem(pedalOffsetToggle);

  QObject::connect(pedalOffsetToggle, &StarPilotParamValueButtonControl::buttonClicked, [defaultPedalOffsetStandstill, this]() {
    if (StarPilotConfirmationDialog::yesorno(tr("Reset <b>Pedal Offset</b> to its default value?"), this)) {
      params.putFloat("RetrofitPedalOffsetStandstill", defaultPedalOffsetStandstill);
      pedalOffsetToggle->refresh();
    }
  });

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubPanel, [retrofitLayout, retrofitPanel]() {
    retrofitLayout->setCurrentWidget(retrofitPanel);
  });
}
