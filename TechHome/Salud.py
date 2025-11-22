"""Construcción de la página de salud."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from animaciones import SlideSpec, slide_fade
from health import BPMGauge, MetricsPanel


def build_health_page(app):
    w = QWidget()
    l = QVBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(10)
    gauge = BPMGauge()
    metrics = MetricsPanel()
    gauge.calculationFinished.connect(metrics.update_values)
    gauge.calculationFinished.connect(app._record_health_history)
    l.addStretch(1)
    l.addWidget(gauge, alignment=Qt.AlignHCenter)
    l.addWidget(metrics, alignment=Qt.AlignHCenter)
    l.addStretch(1)
    app.health_gauge = gauge
    app.health_metrics = metrics
    return w


# ------------------------------------------------------------------
# Animaciones
# ------------------------------------------------------------------

def create_health_animations(app) -> list[dict[str, object]]:
    """Animaciones suaves para el medidor y el panel de métricas."""

    base_duration = 220

    specs = [
        SlideSpec(
            target_getter=lambda: getattr(app, 'health_gauge', None),
            order=0,
            duration=base_duration,
            offset=16.0,
            direction='down',
            step=30,
        ),
        SlideSpec(
            target_getter=lambda: getattr(app, 'health_metrics', None),
            order=1,
            duration=base_duration,
            offset=22.0,
            direction='down',
            step=30,
        ),
    ]

    return [slide_fade(spec) for spec in specs]
