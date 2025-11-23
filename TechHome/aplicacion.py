"""Punto de entrada y fachada principal para TechHome."""

from aplicacion_componentes import (
    MetricGauge,
    MetricSpec,
    MetricsDetailsDialog,
    NotificationsDetailsDialog,
    SlideFadeEffect,
    TimerPopupDialog,
    GraphWidget,
)
from aplicacion_background import AnimatedBackground
from aplicacion_main_window import MainWindow, run_app

__all__ = [
    "AnimatedBackground",
    "GraphWidget",
    "MainWindow",
    "MetricGauge",
    "MetricSpec",
    "MetricsDetailsDialog",
    "NotificationsDetailsDialog",
    "SlideFadeEffect",
    "TimerPopupDialog",
    "run_app",
]


if __name__ == "__main__":
    run_app()
