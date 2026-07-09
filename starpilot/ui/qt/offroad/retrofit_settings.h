#pragma once

#include <QPainter>
#include <cmath>

#include "starpilot/ui/qt/offroad/starpilot_settings.h"

class SigmoidCurveWidget : public QWidget {
  Q_OBJECT

public:
  explicit SigmoidCurveWidget(QWidget *parent = nullptr) : QWidget(parent) {
    setFixedHeight(240);
    setContentsMargins(0, 0, 0, 0);
  }

  void setParams(float strength, float saturation, float bias) {
    m_strength = strength;
    m_saturation = saturation;
    m_bias = bias;
    update();
  }

  void setStrength(float v) { m_strength = v; update(); }
  void setSaturation(float v) { m_saturation = v; update(); }
  void setBias(float v) { m_bias = v; update(); }

protected:
  void paintEvent(QPaintEvent *) override {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const int w = width();
    const int h = height();
    const int pad_l = 60, pad_r = 20, pad_t = 20, pad_b = 40;
    const int plot_w = w - pad_l - pad_r;
    const int plot_h = h - pad_t - pad_b;

    // background
    p.fillRect(rect(), QColor(30, 30, 30));

    // plot area
    QRect plotRect(pad_l, pad_t, plot_w, plot_h);
    p.fillRect(plotRect, QColor(20, 20, 20));

    const float x_min = -3.0f, x_max = 3.0f;
    const float y_min = -0.8f, y_max = 0.8f;

    auto toScreenX = [&](float x) -> int {
      return pad_l + (int)((x - x_min) / (x_max - x_min) * plot_w);
    };
    auto toScreenY = [&](float y) -> int {
      return pad_t + (int)((y_max - y) / (y_max - y_min) * plot_h);
    };

    // grid lines
    p.setPen(QPen(QColor(60, 60, 60), 1));
    for (int i = -2; i <= 2; i++) {
      int sx = toScreenX(i);
      p.drawLine(sx, pad_t, sx, pad_t + plot_h);
    }
    for (float gy : {-0.5f, -0.25f, 0.0f, 0.25f, 0.5f}) {
      int sy = toScreenY(gy);
      p.drawLine(pad_l, sy, pad_l + plot_w, sy);
    }

    // axis labels
    p.setPen(QColor(150, 150, 150));
    p.setFont(QFont("sans-serif", 20));
    for (int i = -2; i <= 2; i++) {
      p.drawText(toScreenX(i) - 15, pad_t + plot_h + 30, QString::number(i));
    }
    p.drawText(pad_l + plot_w / 2 - 60, pad_t + plot_h + 38, "lat accel");
    p.save();
    p.translate(18, pad_t + plot_h / 2 + 30);
    p.rotate(-90);
    p.drawText(0, 0, "torque");
    p.restore();

    // stock linear reference (dashed)
    QPen dashedPen(QColor(100, 100, 100), 2, Qt::DashLine);
    p.setPen(dashedPen);
    float lin_slope = 1.0f / 4.05f;
    p.drawLine(toScreenX(x_min), toScreenY(x_min * lin_slope),
               toScreenX(x_max), toScreenY(x_max * lin_slope));

    // compute ABCD from user params
    float c_floor = 0.05f;
    float c_base = lin_slope * (1.0f - m_strength) + c_floor * m_strength;
    float b_base = 1.0f * m_strength;
    float left_a = m_saturation, left_b = b_base * (1.0f + m_bias * 0.3f), left_c = c_base;
    float right_a = m_saturation, right_b = b_base * (1.0f - m_bias * 0.3f), right_c = c_base;

    // draw sigmoid-linear curve
    QPen curvePen(QColor(0x58, 0xD6, 0x8D), 3);
    p.setPen(curvePen);
    QPointF prev;
    bool has_prev = false;
    const int steps = plot_w;
    for (int i = 0; i <= steps; i++) {
      float x = x_min + (x_max - x_min) * i / steps;
      float a = x >= 0 ? left_a : right_a;
      float b = x >= 0 ? left_b : right_b;
      float c = x >= 0 ? left_c : right_c;
      float ax = a * x;
      float sig;
      if (ax >= 0) {
        float z = std::exp(-ax);
        sig = 1.0f / (1.0f + z) - 0.5f;
      } else {
        float z = std::exp(ax);
        sig = -(1.0f / (1.0f + z) - 0.5f);
      }
      float torque = sig * b + x * c;
      QPointF pt(toScreenX(x), toScreenY(torque));
      if (has_prev) {
        p.drawLine(prev, pt);
      }
      prev = pt;
      has_prev = true;
    }

    // legend
    p.setPen(dashedPen);
    p.drawLine(pad_l + 10, pad_t + 15, pad_l + 40, pad_t + 15);
    p.setPen(QColor(150, 150, 150));
    p.setFont(QFont("sans-serif", 18));
    p.drawText(pad_l + 45, pad_t + 22, "stock");

    p.setPen(curvePen);
    p.drawLine(pad_l + 110, pad_t + 15, pad_l + 140, pad_t + 15);
    p.drawText(pad_l + 145, pad_t + 22, "sigmoid");
  }

private:
  float m_strength = 0.5f;
  float m_saturation = 2.5f;
  float m_bias = 0.0f;
};

class StarPilotRetrofitPanel : public StarPilotListWidget {
  Q_OBJECT

public:
  explicit StarPilotRetrofitPanel(StarPilotSettingsWindow *parent, bool forceOpen = false);

signals:
  void openSubPanel();

private:
  bool forceOpenDescriptions;

  StarPilotParamValueButtonControl *pedalOffsetToggle;
  StarPilotParamValueButtonControl *sasOffsetToggle;
  StarPilotParamValueButtonControl *strengthToggle;
  StarPilotParamValueButtonControl *saturationToggle;
  StarPilotParamValueButtonControl *biasToggle;

  SigmoidCurveWidget *curveWidget;

  StarPilotSettingsWindow *parent;

  Params params;
};
