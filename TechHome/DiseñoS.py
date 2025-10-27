"""Construcción de la página de salud."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget

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

    def fade(target_getter, *, delay: int = 0, duration: int = 420) -> dict[str, object]:
        return {
            'type': 'fade',
            'target': target_getter,
            'delay': delay,
            'duration': duration,
            'start': 0.0,
            'end': 1.0,
        }

    return [
        fade(lambda: getattr(app, 'health_gauge', None), delay=0, duration=380),
        fade(lambda: getattr(app, 'health_metrics', None), delay=140, duration=420),
    ]
