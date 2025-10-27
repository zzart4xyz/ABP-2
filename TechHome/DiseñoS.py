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
    return w
