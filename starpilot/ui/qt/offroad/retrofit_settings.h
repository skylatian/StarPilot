#pragma once

#include "starpilot/ui/qt/offroad/starpilot_settings.h"

class StarPilotRetrofitPanel : public StarPilotListWidget {
  Q_OBJECT

public:
  explicit StarPilotRetrofitPanel(StarPilotSettingsWindow *parent, bool forceOpen = false);

signals:
  void openSubPanel();

private:
  bool forceOpenDescriptions;

  StarPilotParamValueButtonControl *pedalOffsetToggle;

  StarPilotSettingsWindow *parent;

  Params params;
};
