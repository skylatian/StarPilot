#pragma once

#include <QPainter>
#include <QMouseEvent>
#include <cmath>
#include <vector>

#include "starpilot/ui/qt/offroad/starpilot_settings.h"

class DraggableCurveWidget : public QWidget {
  Q_OBJECT

public:
  struct PointDef {
    float x;
    float y;
    float y_min;
    float y_max;
    QString param_key;
    QString label;
  };

  explicit DraggableCurveWidget(const QString &x_label, const QString &y_label,
                                float x_min, float x_max, float y_min, float y_max,
                                const std::vector<PointDef> &points,
                                QWidget *parent = nullptr)
      : QWidget(parent), m_x_label(x_label), m_y_label(y_label),
        m_x_min(x_min), m_x_max(x_max), m_y_min(y_min), m_y_max(y_max),
        m_points(points) {
    setFixedHeight(340);
    setContentsMargins(0, 0, 0, 0);
    setAttribute(Qt::WA_AcceptTouchEvents);
  }

  void reloadFromParams() {
    Params p;
    for (auto &pt : m_points) {
      pt.y = p.getFloat(pt.param_key.toStdString());
      if (pt.y == 0.0f && !pt.param_key.isEmpty()) {
        std::string val = p.get(pt.param_key.toStdString());
        if (!val.empty()) {
          pt.y = std::stof(val);
        }
      }
    }
    update();
  }

signals:
  void pointChanged(int index, float value);
  void pointCommitted(int index, float value);

protected:
  void paintEvent(QPaintEvent *) override {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const int w = width();
    const int h = height();
    const int pad_l = 65, pad_r = 25, pad_t = 25, pad_b = 45;
    const int plot_w = w - pad_l - pad_r;
    const int plot_h = h - pad_t - pad_b;

    p.fillRect(rect(), QColor(30, 30, 30));
    QRect plotRect(pad_l, pad_t, plot_w, plot_h);
    p.fillRect(plotRect, QColor(20, 20, 20));

    auto toScreenX = [&](float x) -> int {
      return pad_l + (int)((x - m_x_min) / (m_x_max - m_x_min) * plot_w);
    };
    auto toScreenY = [&](float y) -> int {
      return pad_t + (int)((m_y_max - y) / (m_y_max - m_y_min) * plot_h);
    };

    // grid lines
    p.setPen(QPen(QColor(60, 60, 60), 1));
    int n_x_grid = 6;
    for (int i = 0; i <= n_x_grid; i++) {
      float gx = m_x_min + (m_x_max - m_x_min) * i / n_x_grid;
      int sx = toScreenX(gx);
      p.drawLine(sx, pad_t, sx, pad_t + plot_h);
    }
    int n_y_grid = 5;
    for (int i = 0; i <= n_y_grid; i++) {
      float gy = m_y_min + (m_y_max - m_y_min) * i / n_y_grid;
      int sy = toScreenY(gy);
      p.drawLine(pad_l, sy, pad_l + plot_w, sy);
    }

    // axis labels
    p.setPen(QColor(150, 150, 150));
    p.setFont(QFont("sans-serif", 18));
    for (int i = 0; i <= n_x_grid; i++) {
      float gx = m_x_min + (m_x_max - m_x_min) * i / n_x_grid;
      QString txt = QString::number(gx, 'g', 3);
      p.drawText(toScreenX(gx) - 15, pad_t + plot_h + 28, txt);
    }
    p.drawText(pad_l + plot_w / 2 - 30, pad_t + plot_h + 42, m_x_label);

    for (int i = 0; i <= n_y_grid; i++) {
      float gy = m_y_min + (m_y_max - m_y_min) * i / n_y_grid;
      QString txt = QString::number(gy, 'g', 4);
      p.drawText(5, toScreenY(gy) + 5, txt);
    }

    // interpolated line between points
    QPen curvePen(QColor(0x58, 0xD6, 0x8D), 3);
    p.setPen(curvePen);
    for (int i = 1; i < (int)m_points.size(); i++) {
      p.drawLine(toScreenX(m_points[i - 1].x), toScreenY(m_points[i - 1].y),
                 toScreenX(m_points[i].x), toScreenY(m_points[i].y));
    }

    // control points
    for (int i = 0; i < (int)m_points.size(); i++) {
      int sx = toScreenX(m_points[i].x);
      int sy = toScreenY(m_points[i].y);
      int radius = (i == m_dragIndex && m_dragging) ? 16 : 12;

      p.setPen(Qt::NoPen);
      if (i == m_dragIndex && m_dragging) {
        p.setBrush(QColor(0xFF, 0xA5, 0x00));
      } else {
        p.setBrush(QColor(0x58, 0xD6, 0x8D));
      }
      p.drawEllipse(QPoint(sx, sy), radius, radius);

      // value label
      p.setPen(QColor(220, 220, 220));
      p.setFont(QFont("sans-serif", 16, QFont::Bold));
      QString valStr = QString::number(m_points[i].y, 'g', 4);
      int tw = p.fontMetrics().horizontalAdvance(valStr);
      int label_y = sy - radius - 6;
      if (label_y < pad_t + 15) label_y = sy + radius + 18;
      p.drawText(sx - tw / 2, label_y, valStr);
    }
  }

  void mousePressEvent(QMouseEvent *e) override {
    const int pad_l = 65, pad_r = 25, pad_t = 25, pad_b = 45;
    const int plot_w = width() - pad_l - pad_r;
    const int plot_h = height() - pad_t - pad_b;

    int best = -1;
    float bestDist = 50.0f * 50.0f;
    for (int i = 0; i < (int)m_points.size(); i++) {
      float sx = pad_l + (m_points[i].x - m_x_min) / (m_x_max - m_x_min) * plot_w;
      float sy = pad_t + (m_y_max - m_points[i].y) / (m_y_max - m_y_min) * plot_h;
      float dx = e->pos().x() - sx;
      float dy = e->pos().y() - sy;
      float d2 = dx * dx + dy * dy;
      if (d2 < bestDist) {
        bestDist = d2;
        best = i;
      }
    }

    if (best >= 0) {
      m_dragIndex = best;
      m_dragging = true;
      e->accept();
    } else {
      e->ignore();
    }
  }

  void mouseMoveEvent(QMouseEvent *e) override {
    if (!m_dragging || m_dragIndex < 0) return;

    const int pad_t = 25, pad_b = 45;
    const int plot_h = height() - pad_t - pad_b;

    float y = m_y_max - (float)(e->pos().y() - pad_t) / plot_h * (m_y_max - m_y_min);
    y = std::max(m_points[m_dragIndex].y_min, std::min(m_points[m_dragIndex].y_max, y));
    m_points[m_dragIndex].y = y;

    emit pointChanged(m_dragIndex, y);
    update();
    e->accept();
  }

  void mouseReleaseEvent(QMouseEvent *e) override {
    if (m_dragging && m_dragIndex >= 0) {
      Params p;
      p.putFloat(m_points[m_dragIndex].param_key.toStdString(), m_points[m_dragIndex].y);
      emit pointCommitted(m_dragIndex, m_points[m_dragIndex].y);
      m_dragging = false;
      m_dragIndex = -1;
      update();
    }
    e->accept();
  }

private:
  QString m_x_label, m_y_label;
  float m_x_min, m_x_max, m_y_min, m_y_max;
  std::vector<PointDef> m_points;
  int m_dragIndex = -1;
  bool m_dragging = false;
};

class CenterTaperPreviewWidget : public QWidget {
  Q_OBJECT

public:
  explicit CenterTaperPreviewWidget(QWidget *parent = nullptr) : QWidget(parent) {
    setFixedHeight(220);
    setContentsMargins(0, 0, 0, 0);
  }

  void setTaperParams(float taper_max, float taper_lat, float taper_lat_w, float taper_speed, float taper_speed_w) {
    m_max = taper_max; m_lat = taper_lat; m_lat_w = taper_lat_w;
    m_speed = taper_speed; m_speed_w = taper_speed_w;
    update();
  }

protected:
  void paintEvent(QPaintEvent *) override {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const int w = width(), h = height();
    const int pad_l = 65, pad_r = 25, pad_t = 20, pad_b = 40;
    const int plot_w = w - pad_l - pad_r;
    const int plot_h = h - pad_t - pad_b;

    p.fillRect(rect(), QColor(30, 30, 30));
    QRect plotRect(pad_l, pad_t, plot_w, plot_h);
    p.fillRect(plotRect, QColor(20, 20, 20));

    const float x_min = 0.0f, x_max = 0.5f;
    const float y_min = 0.70f, y_max = 1.02f;

    auto toSX = [&](float x) -> int { return pad_l + (int)((x - x_min) / (x_max - x_min) * plot_w); };
    auto toSY = [&](float y) -> int { return pad_t + (int)((y_max - y) / (y_max - y_min) * plot_h); };

    // grid
    p.setPen(QPen(QColor(60, 60, 60), 1));
    for (float gx : {0.0f, 0.1f, 0.2f, 0.3f, 0.4f, 0.5f})
      p.drawLine(toSX(gx), pad_t, toSX(gx), pad_t + plot_h);
    for (float gy : {0.75f, 0.80f, 0.85f, 0.90f, 0.95f, 1.0f})
      p.drawLine(pad_l, toSY(gy), pad_l + plot_w, toSY(gy));

    // axis labels
    p.setPen(QColor(150, 150, 150));
    p.setFont(QFont("sans-serif", 16));
    for (float gx : {0.0f, 0.1f, 0.2f, 0.3f, 0.4f, 0.5f})
      p.drawText(toSX(gx) - 10, pad_t + plot_h + 25, QString::number(gx, 'f', 1));
    p.drawText(pad_l + plot_w / 2 - 30, pad_t + plot_h + 38, "lat accel");
    for (float gy : {0.80f, 0.90f, 1.0f})
      p.drawText(5, toSY(gy) + 5, QString::number(gy, 'f', 2));

    auto sigmoid = [](float x) -> float {
      if (x >= 0) { float z = std::exp(-x); return 1.0f / (1.0f + z); }
      float z = std::exp(x); return z / (1.0f + z);
    };

    // draw curves at 3 speeds
    struct SpeedLine { float v; QColor color; QString label; };
    SpeedLine speeds[] = {
      {10.0f, QColor(100, 100, 200), "10 m/s"},
      {15.0f, QColor(200, 200, 100), "15 m/s"},
      {20.0f, QColor(0x58, 0xD6, 0x8D), "20 m/s"},
    };

    for (auto &sl : speeds) {
      float speed_weight = sigmoid((sl.v - m_speed) / std::max(m_speed_w, 0.1f));
      p.setPen(QPen(sl.color, 2));
      QPointF prev;
      bool has_prev = false;
      for (int i = 0; i <= plot_w; i++) {
        float la = x_min + (x_max - x_min) * i / plot_w;
        float center_weight = sigmoid((m_lat - la) / std::max(m_lat_w, 0.01f));
        float reduction = m_max * speed_weight * center_weight;
        float val = 1.0f - reduction;
        QPointF pt(toSX(la), toSY(val));
        if (has_prev) p.drawLine(prev, pt);
        prev = pt;
        has_prev = true;
      }
    }

    // legend
    p.setFont(QFont("sans-serif", 14));
    int lx = pad_l + 10;
    for (auto &sl : speeds) {
      p.setPen(QPen(sl.color, 2));
      p.drawLine(lx, pad_t + 12, lx + 25, pad_t + 12);
      p.setPen(QColor(180, 180, 180));
      p.drawText(lx + 30, pad_t + 17, sl.label);
      lx += 100;
    }
  }

private:
  float m_max = 0.20f, m_lat = 0.14f, m_lat_w = 0.04f;
  float m_speed = 14.0f, m_speed_w = 2.5f;
};

class RetrofitTuneTablePanel : public StarPilotListWidget {
  Q_OBJECT

public:
  explicit RetrofitTuneTablePanel(StarPilotSettingsWindow *parent, QStackedLayout *mainLayout, bool forceOpen = false);

  bool isShowingTableOverview() const { return m_tuneLayout && m_tuneLayout->currentIndex() == 0; }

signals:
  void openSubPanel();

private:
  QStackedLayout *m_tuneLayout = nullptr;
  Params params;
};
