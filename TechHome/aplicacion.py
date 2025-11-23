"""Punto de entrada de la aplicación TechHome.

Este módulo actúa como fachada ligera que reexporta las clases y helpers
principales desde ``app_core`` y expone ``run_app`` como función pública
para ser usada por ``main.py`` u otros lanzadores.
"""

from app_core import (
    AnimatedBackground,
    GraphWidget,
    MainWindow,
    MetricGauge,
    MetricSpec,
    MetricsDetailsDialog,
    NotificationsDetailsDialog,
    SlideFadeEffect,
    TimerPopupDialog,
    run_app,
)

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
