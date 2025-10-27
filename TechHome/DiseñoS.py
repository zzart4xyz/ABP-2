"""Construcción de la página de salud."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QEasingCurve, QPropertyAnimation
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QGraphicsOpacityEffect

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
    """Configurar animaciones suaves para la vista de salud."""

    animations: list[dict[str, object]] = []

    for idx, widget in enumerate(filter(None, [getattr(app, 'health_gauge', None), getattr(app, 'health_metrics', None)])):
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", app)
        anim.setDuration(500)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        try:
            anim.finished.connect(lambda eff=effect: eff.setOpacity(1.0))
        except Exception:
            pass
        animations.append(
            {
                "animation": anim,
                "prepare": (lambda eff=effect: eff.setOpacity(0.0)),
                "effect": effect,
                "widget": widget,
                "delay": idx * 120,
            }
        )

    return animations
