"""Construcción de la página de inicio."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QSize, QTimer, QEasingCurve
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from constants import CLR_BG, CLR_PANEL, CLR_SURFACE, CLR_TITLE, CLR_TEXT_IDLE, CLR_HOVER, HOME_RECENT_COUNT, FONT_FAM
from widgets import QuickAccessButton


def build_home_page(app, metric_gauge_cls, load_icon_pixmap, tint_pixmap):
    """Crear la página de inicio para ``app`` usando utilidades proporcionadas."""

    w = QWidget()
    grid = QGridLayout(w)
    grid.setContentsMargins(0, 20, 0, 0)
    grid.setHorizontalSpacing(20)
    grid.setVerticalSpacing(20)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)

    greet = QFrame()
    greet.setFixedHeight(80)
    greet.setStyleSheet(f'background:{CLR_PANEL}; border-bottom-left-radius:5px; border-bottom-right-radius:5px;')
    hl = QHBoxLayout(greet)
    hl.setContentsMargins(16, 0, 16, 0)
    user_display = app.username if app.username else 'Usuario'
    lg = QLabel(f'¡Hola, {user_display}!')
    lg.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}';")
    hl.addWidget(lg)
    hl.addStretch(1)
    tim = QLabel(app.current_time())
    tim.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}';")
    tim.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    hl.addWidget(tim)
    app.home_time_label = tim
    QTimer(tim, timeout=lambda: tim.setText(app.current_time())).start(1000)
    grid.addWidget(greet, 0, 0, 1, 2)
    app.home_greeting_frame = greet

    notif_header = QFrame()
    notif_header.setStyleSheet(f'background:{CLR_PANEL}; padding:8px 12px; border-top-left-radius:5px; border-top-right-radius:5px;')
    notif_layout = QHBoxLayout(notif_header)
    notif_layout.setContentsMargins(0, 0, 0, 0)
    notif_layout.setSpacing(8)
    notif_title = QLabel('Notificaciones', notif_header)
    notif_title.setStyleSheet(f"color:{CLR_TITLE}; font:700 20px '{FONT_FAM}';")
    notif_layout.addWidget(notif_title)
    notif_layout.addStretch(1)
    notif_info_btn = QPushButton(notif_header)
    notif_info_btn.setCursor(Qt.PointingHandCursor)
    notif_info_btn.setFlat(True)
    try:
        pix = load_icon_pixmap('Información.svg', QSize(40, 40))
        pix = tint_pixmap(pix, QColor(CLR_TITLE))
        notif_info_btn.setIcon(QIcon(pix))
    except Exception:
        fallback_pix = load_icon_pixmap('Información.svg', QSize(40, 40))
        notif_info_btn.setIcon(QIcon(fallback_pix))
    notif_info_btn.setIconSize(QSize(40, 40))
    notif_info_btn.setStyleSheet('border:none; padding:0;')
    notif_info_btn.clicked.connect(app._open_notifications_details)
    notif_layout.addWidget(notif_info_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)
    grid.addWidget(notif_header, 1, 0)
    app.home_notifications_header = notif_header

    nc = QFrame()
    nc.setStyleSheet(f'background:{CLR_BG}; border:none; border-radius:5px;')
    nc.setMinimumSize(300, 300)
    nv = QVBoxLayout(nc)
    nv.setContentsMargins(0, 0, 0, 0)
    nv.setSpacing(0)
    app.home_notif_rows = []
    notif_inner = QFrame()
    notif_inner.setStyleSheet('background:transparent;')
    ni_l = QVBoxLayout(notif_inner)
    ni_l.setContentsMargins(8, 8, 8, 8)
    ni_l.setSpacing(8)
    for _ in range(HOME_RECENT_COUNT):
        row_frame = QFrame(notif_inner)
        row_frame.setStyleSheet(f'background:{CLR_SURFACE}; border:none; border-radius:8px;')
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(8)
        icon_lbl = QLabel(row_frame)
        icon_lbl.setFixedSize(35, 35)
        icon_lbl.setScaledContents(True)
        icon_lbl.setStyleSheet('border:none;')
        text_lbl = QLabel('--', row_frame)
        text_lbl.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}'; border:none;")
        text_lbl.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(icon_lbl)
        row_layout.addWidget(text_lbl, 1)
        app.home_notif_rows.append((icon_lbl, text_lbl))
        ni_l.addWidget(row_frame)
    nv.addWidget(notif_inner)
    grid.addWidget(nc, 2, 0, 2, 1)
    app.home_notifications_container = nc

    metrics_header = QFrame()
    metrics_header.setStyleSheet(f'background:{CLR_PANEL}; padding:8px 12px; border-top-left-radius:5px; border-top-right-radius:5px;')
    header_layout = QHBoxLayout(metrics_header)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(8)
    m_title = QLabel('Resumen de Métricas', metrics_header)
    m_title.setStyleSheet(f"color:{CLR_TITLE}; font:700 20px '{FONT_FAM}';")
    header_layout.addWidget(m_title)
    header_layout.addStretch(1)
    info_btn = QPushButton(metrics_header)
    info_btn.setCursor(Qt.PointingHandCursor)
    info_btn.setFlat(True)
    try:
        pix = load_icon_pixmap('Información.svg', QSize(40, 40))
        pix = tint_pixmap(pix, QColor(CLR_TITLE))
        info_btn.setIcon(QIcon(pix))
    except Exception:
        fallback_pix = load_icon_pixmap('Información.svg', QSize(40, 40))
        info_btn.setIcon(QIcon(fallback_pix))
    info_btn.setIconSize(QSize(40, 40))
    info_btn.clicked.connect(app._open_metrics_details)
    info_btn.setStyleSheet('border:none; padding:0;')
    header_layout.addWidget(info_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)
    grid.addWidget(metrics_header, 1, 1)
    app.home_metrics_header = metrics_header

    sumf = QFrame()
    sumf.setStyleSheet(f'background:{CLR_PANEL}; border-bottom-left-radius:5px; border-bottom-right-radius:5px;')
    gs = QGridLayout(sumf)
    gs.setContentsMargins(16, 16, 16, 16)
    gs.setHorizontalSpacing(16)
    gs.setVerticalSpacing(16)
    gauge_specs = [('devices', 'Móvil.svg'), ('temp', 'Calentador Agua.svg'), ('energy', 'Energía.svg'), ('water', 'Agua.svg')]
    app.home_metric_gauges = {}
    for i, (key, icon_name) in enumerate(gauge_specs):
        r, cidx = divmod(i, 2)
        g_container = QWidget()
        vlay = QVBoxLayout(g_container)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(4)
        gauge = metric_gauge_cls(icon_name)
        gauge.setToolTip(key)
        vlay.addWidget(gauge, alignment=Qt.AlignCenter)
        vlay.addStretch(1)
        gs.addWidget(g_container, r, cidx, alignment=Qt.AlignCenter)
        app.home_metric_gauges[key] = gauge
    grid.addWidget(sumf, 2, 1, 2, 1)
    app.home_metrics_container = sumf

    l4 = QLabel('Accesos Rápidos')
    l4.setStyleSheet(f"background:{CLR_PANEL}; color:{CLR_TITLE}; font:700 20px '{FONT_FAM}'; padding:6px 12px; border-top-left-radius:5px; border-top-right-radius:5px;")
    grid.addWidget(l4, 4, 0, 1, 2)

    h_notif = l4.sizeHint().height()
    h_metrics = metrics_header.sizeHint().height()
    h_notifications = notif_header.sizeHint().height()
    header_height = max(h_notif, h_metrics, h_notifications)
    notif_header.setFixedHeight(header_height)
    metrics_header.setFixedHeight(header_height)

    cf = QFrame()
    cf.setStyleSheet(f'background:{CLR_PANEL}; border-bottom-left-radius:5px; border-bottom-right-radius:5px;')
    hh = QHBoxLayout(cf)
    hh.setContentsMargins(16, 16, 16, 16)
    hh.setSpacing(16)
    acts = [
        ('Historial De Salud', 'Historial De Salud.svg', 'Historial De Salud'),
        ('Cámaras', 'Cámaras.svg', 'Cámaras'),
        ('Notificaciones', 'Notificaciones.svg', 'Notificaciones'),
        ('Cuenta', 'Cuenta.svg', 'Cuenta'),
    ]
    hh.addStretch(1)
    app.quick_access_buttons = []
    for n, icn, page in acts:
        b = QuickAccessButton(n, icn)
        b.clicked.connect(lambda p=page: app._open_more_section(p, True))
        hh.addWidget(b)
        app.quick_access_buttons.append(b)
    hh.addStretch(1)
    grid.addWidget(cf, 5, 0, 1, 2)
    app.home_quick_access_frame = cf

    return w


# ------------------------------------------------------------------
# Animaciones
# ------------------------------------------------------------------

def create_home_animations(app) -> list[dict[str, object]]:
    """Animaciones suaves para los bloques principales de la página de inicio."""

    def slide(target_getter, order: int, *, duration: int = 280, offset: float = 28.0, step: int = 45) -> dict[str, object]:
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
        slide(lambda: getattr(app, 'home_greeting_frame', None), 0, duration=240, offset=22.0),
        slide(lambda: getattr(app, 'home_notifications_container', None), 1, duration=260, offset=26.0),
        slide(lambda: getattr(app, 'home_metrics_container', None), 2, duration=270, offset=30.0),
        slide(lambda: getattr(app, 'home_quick_access_frame', None), 3, duration=280, offset=32.0),
    ]
