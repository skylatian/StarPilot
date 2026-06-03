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
    sections = [
      SettingSection(tr_noop("Pedal"), [
        SettingRow(
          "RetrofitPedalOffsetStandstill",
          "value",
          tr_noop("Standstill Pedal Offset"),
          subtitle=tr_noop(
            "Low-speed deadband before pedal scaling. Less negative = gas sooner from a stop."
          ),
          get_value=lambda: f"{self._params.get_float('RetrofitPedalOffsetStandstill'):.2f}m/s²",
          on_click=lambda: self._show_slider(
            "RetrofitPedalOffsetStandstill",
            -0.5,
            0.2,
            step=0.05,
            unit="m/s²",
            value_type="float",
          ),
        ),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self,
      sections,
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
      SettingSection(tr_noop("Controls"), [
        SettingRow(
          "RetrofitPauseSteering",
          "toggle",
          tr_noop("Pause Steering"),
          subtitle=tr_noop(
            "Disable openpilot steering while driving. Longitudinal can stay active if engaged."
          ),
          get_state=lambda: self._params.get_bool("RetrofitPauseSteering"),
          set_state=lambda s: self._params.put_bool("RetrofitPauseSteering", s),
        ),
      ]),
      SettingSection(tr_noop("Steering"), [
        SettingRow(
          "RetrofitSASOffset",
          "value",
          tr_noop("SAS Offset"),
          subtitle=tr_noop(
            "Corrects a physically misaligned steering angle sensor. "
            "Set to the raw angle your SAS reports when wheels are straight."
          ),
          get_value=lambda: f"{self._params.get_float('RetrofitSASOffset'):.0f}°",
          on_click=lambda: self._show_slider(
            "RetrofitSASOffset",
            -180,
            180,
            step=1,
            unit="°",
            value_type="float",
          ),
        ),
      ]),
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
