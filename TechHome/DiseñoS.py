"""Construcción de la página de salud."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QEasingCurve
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

    def slide(target_getter, order: int, *, duration: int = 420, offset: float = 32.0, step: int = 110) -> dict[str, object]:
        return {
            'type': 'slide_fade',
            'target': target_getter,
            'delay': max(0, order) * step,
            'duration': duration,
            'offset': offset,
            'direction': 'down',
            'easing': QEasingCurve.OutCubic,
        }

    return [
        slide(lambda: getattr(app, 'health_gauge', None), 0, duration=380, offset=26.0),
        slide(lambda: getattr(app, 'health_metrics', None), 1, duration=420, offset=40.0),
    ]
