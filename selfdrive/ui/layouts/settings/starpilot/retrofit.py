from __future__ import annotations

from openpilot.system.ui.lib.multilang import tr_noop

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AetherSettingsView,
  SettingRow,
  SettingSection,
  panel_style_from_color,
)

PANEL_STYLE = panel_style_from_color("#F59E0B")


class StarPilotRetrofitTuningLayout(_SettingsPage):
  """Placeholder subpage for future retrofit tuning controls."""

  def __init__(self):
    super().__init__()
    self._build_view()

  def _build_view(self):
    self._manager_view = AetherSettingsView(
      self,
      [],
      header_title=tr_noop("Retrofit Tuning"),
      header_subtitle=tr_noop("Pedal and retrofit-specific adjustments."),
      panel_style=PANEL_STYLE,
    )


class StarPilotRetrofitLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._sub_panels = {
      "tuning": StarPilotRetrofitTuningLayout(),
    }
    self._wire_sub_panels()
    self._build_view()

  def _build_view(self):
    sections = [
      SettingSection(tr_noop("Longitudinal"), [
        SettingRow(
          "RetrofitTuningNav",
          "value",
          tr_noop("Pedal Tuning"),
          subtitle=tr_noop("Interceptor pedal mapping for standstill launch and creep."),
          get_value=lambda: tr_noop("Configure"),
          navigate_to="tuning",
        ),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self,
      sections,
      header_title=tr_noop("Retrofit Options"),
      header_subtitle=tr_noop("Comma Pedal and CAN emulator retrofit configurations."),
      panel_style=PANEL_STYLE,
    )
