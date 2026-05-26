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

  StarPilotManageControl *pedalTuningToggle = new StarPilotManageControl(
      "RetrofitPedalTuning",
      tr("Pedal Tuning"),
      tr("<b>Interceptor pedal mapping for standstill launch and creep.</b>"),
      "../../starpilot/assets/toggle_icons/icon_vehicle.png");
  QObject::connect(pedalTuningToggle, &StarPilotManageControl::manageButtonClicked, [retrofitLayout, tuningPanel, this]() {
    retrofitLayout->setCurrentWidget(tuningPanel);
    emit openSubPanel();
  });
  if (forceOpenDescriptions) {
    pedalTuningToggle->showDescription();
  }
  retrofitList->addItem(pedalTuningToggle);

  QObject::connect(parent, &StarPilotSettingsWindow::closeSubPanel, [retrofitLayout, retrofitPanel]() {
    retrofitLayout->setCurrentWidget(retrofitPanel);
  });
}
