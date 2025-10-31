"""Construcción de la página de inicio."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, QEasingCurve
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

from constants import (
    CLR_TITLE,
    CLR_TEXT_IDLE,
    FONT_FAM,
    HOME_RECENT_COUNT,
)
from ui_helpers import create_card, create_header, create_row, init_page
from widgets import QuickAccessButton


def build_home_page(app, metric_gauge_cls, load_icon_pixmap, tint_pixmap):
    """Crear la página de inicio usando el nuevo sistema de tarjetas."""

    page, root = init_page("home_page")

    hero, hero_layout = create_card(role="hero", orientation="h", margins=(22, 18, 22, 18))
    hero_layout.setSpacing(16)
    greeting = QLabel(f"Hola, {app.username or 'Usuario'}")
    greeting.setStyleSheet(f"color:{CLR_TITLE}; font:700 26px '{FONT_FAM}';")
    hero_layout.addWidget(greeting)
    hero_layout.addStretch(1)
    time_label = QLabel(app.current_time())
    time_label.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 20px '{FONT_FAM}';")
    time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    hero_layout.addWidget(time_label)
    QTimer(time_label, timeout=lambda: time_label.setText(app.current_time())).start(1000)
    app.home_time_label = time_label
    app.home_greeting_card = hero
    root.addWidget(hero)

    grid = QGridLayout()
    grid.setHorizontalSpacing(20)
    grid.setVerticalSpacing(20)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    root.addLayout(grid)

    notif_card, notif_layout = create_card()
    notif_header, _, _ = create_header(
        "Notificaciones",
        icon_name="Información.svg",
        callback=app._open_notifications_details,
    )
    notif_layout.addWidget(notif_header)
    app.home_notifications_header = notif_header

    notif_body = QVBoxLayout()
    notif_body.setContentsMargins(0, 0, 0, 0)
    notif_body.setSpacing(8)
    notif_layout.addLayout(notif_body)
    app.home_notif_rows = []
    for _ in range(HOME_RECENT_COUNT):
        row, row_layout = create_row()
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(34, 34)
        icon_lbl.setScaledContents(True)
        icon_lbl.setStyleSheet("border:none;")
        text_lbl = QLabel("--")
        text_lbl.setProperty("class", "value")
        text_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        row_layout.addWidget(icon_lbl)
        row_layout.addWidget(text_lbl, 1)
        notif_body.addWidget(row)
        app.home_notif_rows.append((icon_lbl, text_lbl))
    notif_layout.addStretch(1)
    app.home_notifications_container = notif_card
    grid.addWidget(notif_card, 0, 0, 2, 1)

    metrics_card, metrics_layout = create_card()
    metrics_header, _, _ = create_header(
        "Resumen de Métricas",
        icon_name="Información.svg",
        callback=app._open_metrics_details,
    )
    metrics_layout.addWidget(metrics_header)
    app.home_metrics_header = metrics_header
    gauges_grid = QGridLayout()
    gauges_grid.setContentsMargins(0, 0, 0, 0)
    gauges_grid.setHorizontalSpacing(16)
    gauges_grid.setVerticalSpacing(16)
    gauge_specs = [
        ("devices", "Móvil.svg"),
        ("temp", "Calentador Agua.svg"),
        ("energy", "Energía.svg"),
        ("water", "Agua.svg"),
    ]
    app.home_metric_gauges = {}
    for idx, (key, icon_name) in enumerate(gauge_specs):
        gauge = metric_gauge_cls(icon_name)
        gauge.setToolTip(key)
        gauges_grid.addWidget(gauge, idx // 2, idx % 2)
        app.home_metric_gauges[key] = gauge
    metrics_layout.addLayout(gauges_grid)
    app.home_metrics_container = metrics_card
    grid.addWidget(metrics_card, 0, 1, 2, 1)

    quick_card, quick_layout = create_card()
    quick_header, quick_label, _ = create_header("Accesos rápidos")
    quick_layout.addWidget(quick_header)
    slots = QHBoxLayout()
    slots.setContentsMargins(0, 0, 0, 0)
    slots.setSpacing(16)
    quick_layout.addLayout(slots)
    app.quick_access_buttons = []
    quick_actions = [
        ("Historial De Salud", "Historial De Salud.svg", "Historial De Salud"),
        ("Cámaras", "Cámaras.svg", "Cámaras"),
        ("Notificaciones", "Notificaciones.svg", "Notificaciones"),
        ("Cuenta", "Cuenta.svg", "Cuenta"),
    ]
    for label, icon_name, page_name in quick_actions:
        btn = QuickAccessButton(label, icon_name)
        btn.clicked.connect(lambda _, page=page_name: app._open_more_section(page, True))
        slots.addWidget(btn)
        app.quick_access_buttons.append(btn)
    slots.addStretch(1)
    app.home_quick_access_card = quick_card
    grid.addWidget(quick_card, 2, 0, 1, 2)

    return page


# ------------------------------------------------------------------
# Animaciones
# ------------------------------------------------------------------

def create_home_animations(app) -> list[dict[str, object]]:
    """Definir animaciones verticales para la página de inicio."""

    base_duration = 320

    def slide(target_getter, order: int, *, offset: float = 26.0, step: int = 40) -> dict[str, object]:
        return {
            "type": "slide_fade",
            "target": target_getter,
            "delay": max(0, order) * step,
            "duration": base_duration,
            "offset": offset,
            "direction": "down",
            "easing": QEasingCurve.OutCubic,
        }

    specs = [
        slide(lambda: getattr(app, "home_greeting_card", None), 0, offset=22.0),
        slide(lambda: getattr(app, "home_notifications_header", None), 1),
        slide(lambda: getattr(app, "home_notifications_container", None), 2),
        slide(lambda: getattr(app, "home_metrics_header", None), 3),
        slide(lambda: getattr(app, "home_metrics_container", None), 4),
        slide(lambda: getattr(app, "home_quick_access_card", None), 5, offset=32.0),
    ]

    for index, row in enumerate(getattr(app, "home_notif_rows", [])):
        specs.append(slide(lambda row=row: row[0].parentWidget(), 6 + index, offset=18.0))

    return specs
