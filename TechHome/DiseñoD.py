"""Construcción de la página de dispositivos."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QSize, QEasingCurve
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from constants import (
    CLR_HOVER,
    CLR_ITEM_ACT,
    CLR_PANEL,
    CLR_SURFACE,
    CLR_TEXT_IDLE,
    CLR_TITLE,
    FONT_FAM,
    icon,
)
from widgets import CustomScrollBar, DeviceRow, GroupCard


def build_devices_page(app):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 20, 0, 0)
    v.setSpacing(20)

    hh = QHBoxLayout()
    lbl = QLabel('Dispositivos')
    lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:700 24px '{FONT_FAM}'; border:none;")
    plus = QPushButton()
    plus.setIcon(icon('Más.svg'))
    plus.setIconSize(QSize(24, 24))
    plus.setFixedSize(32, 32)
    plus.setFlat(True)
    plus.setStyleSheet('border:none; background:transparent;')
    plus.clicked.connect(app._add_device)
    hh.addWidget(lbl)
    hh.addStretch(1)
    hh.addWidget(plus)
    v.addLayout(hh)

    g_lbl = QLabel('Grupos')
    g_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}'; border:none;")
    v.addWidget(g_lbl)

    grp_w = QWidget()
    grp_w.setStyleSheet('background:transparent;')
    gl = QHBoxLayout(grp_w)
    gl.setContentsMargins(0, 0, 0, 0)
    gl.setSpacing(16)
    app.grp_layout = gl
    app.group_cards = []
    app.devices_group_container = grp_w
    groups = [
        ('Todo', 'Todo.svg'),
        ('Dormitorio', 'Dormitorio.svg'),
        ('Baño', 'Baño.svg'),
        ('Sala', 'Sala.svg'),
        ('Comedor', 'Comedor.svg'),
        ('Cocina', 'Cocina.svg'),
    ]
    for title, icon_name in groups:
        card = GroupCard(title, icon_name, rename_callback=app._rename_group, select_callback=None)
        gl.addWidget(card)
        app.group_cards.append(card)
    app.add_group_card = GroupCard('Grupo Nuevo', 'Más.svg', add_callback=app._add_group)
    gl.addWidget(app.add_group_card)

    grp_scroll = QScrollArea()
    grp_scroll.setWidget(grp_w)
    grp_scroll.setWidgetResizable(True)
    grp_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    grp_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    grp_scroll.setFrameShape(QFrame.NoFrame)
    grp_scroll.setHorizontalScrollBar(CustomScrollBar(Qt.Horizontal))
    grp_scroll.setStyleSheet('background:transparent;')
    grp_scroll.viewport().setStyleSheet('background:transparent;')
    v.addWidget(grp_scroll)

    app.group_indicator = QLabel('Grupo Actual: Todo')
    app.group_indicator.setStyleSheet(f"background:{CLR_HOVER}; color:{CLR_TITLE}; font:700 16px '{FONT_FAM}'; padding:4px 8px; border-radius:5px;")
    v.addWidget(app.group_indicator)

    fh = QHBoxLayout()
    search = QLineEdit()
    search.setFixedHeight(40)
    search.setPlaceholderText('Buscar')
    search.setCursor(Qt.PointingHandCursor)
    search.setStyleSheet(f"\n            QLineEdit {{ background:{CLR_SURFACE}; border:2px solid #1A2B3C;\n        border-radius:5px; padding:0 40px 0 12px;\n                         color:{CLR_TEXT_IDLE}; font:700 16px '{FONT_FAM}'; }}\n            QLineEdit:focus {{ border-color:{CLR_TITLE}; }}\n        ")
    search.addAction(icon('Buscar.svg'), QLineEdit.LeadingPosition)
    cb1 = QComboBox()
    cb1.addItems(['Tech', 'Interruptores', 'Otro'])
    cb2 = QComboBox()
    cb2.addItems(['De La A A La Z', 'De La Z A La A'])
    app.device_category_cb = cb1
    app.device_sort_cb = cb2
    app.devices_search_field = search
    app.devices_category_combo = cb1
    app.devices_sort_combo = cb2
    for cb in (cb1, cb2):
        cb.setFixedHeight(40)
        cb.setStyleSheet(f"\n                QComboBox {{ background:{CLR_SURFACE};color:{CLR_TEXT_IDLE};\n             font:700 16px '{FONT_FAM}';border:2px solid {CLR_TITLE};\n                              border-radius:5px;padding:0 12px; }}\n                QComboBox::drop-down {{ border:none; }}\n                QComboBox QAbstractItemView {{ background:{CLR_PANEL};\n                              border:2px solid {CLR_TITLE};\n                              selection-background-color:{CLR_ITEM_ACT};\n                              color:{CLR_TEXT_IDLE};outline:none;padding:4px; }}\n                QComboBox QAbstractItemView::item {{ height:30px;padding-left:10px; }}\n                QComboBox QAbstractItemView::item:hover {{ background:{CLR_ITEM_ACT}; }}\n            ")
    cb1.currentIndexChanged.connect(app._on_device_category_changed)
    cb2.currentIndexChanged.connect(app._on_device_sort_changed)
    fh.addWidget(search, 1)
    fh.addWidget(cb1)
    fh.addWidget(cb2)
    v.addLayout(fh)

    dev_w = QWidget()
    dev_w.setStyleSheet('background:transparent;')
    dl = QVBoxLayout(dev_w)
    dl.setContentsMargins(0, 0, 0, 0)
    dl.setSpacing(12)
    app.device_filter_container = dl
    app.device_list_widget = dev_w
    app.devices_buttons = []
    app.device_rows = []
    devices = [
        ('Luz Dormitorio', 'Dormitorio'), ('Lámpara Noche', 'Dormitorio'),
        ('Ventilador Dormitorio', 'Dormitorio'), ('Aire Acondicionado Dormitorio', 'Dormitorio'),
        ('Cortinas Dormitorio', 'Dormitorio'), ('Enchufe Cama', 'Dormitorio'),
        ('Luz Baño', 'Baño'), ('Extractor', 'Baño'), ('Calentador Agua', 'Baño'),
        ('Espejo Iluminado', 'Baño'), ('Ducha Automática', 'Baño'), ('Enchufe Afeitadora', 'Baño'),
        ('Luces Sala', 'Sala'), ('Televisor', 'Sala'), ('Consola Juegos', 'Sala'),
        ('Equipo Sonido', 'Sala'), ('Ventilador Sala', 'Sala'), ('Enchufe Ventana', 'Sala'),
        ('Luz Comedor', 'Comedor'), ('Calefactor Comedor', 'Comedor'), ('Enchufe Comedor', 'Comedor'),
        ('Luz Barra', 'Comedor'), ('Persianas Comedor', 'Comedor'), ('Ventilador Techo', 'Comedor'),
        ('Refrigerador', 'Cocina'), ('Horno', 'Cocina'), ('Microondas', 'Cocina'),
        ('Lavavajillas', 'Cocina'), ('Licuadora', 'Cocina'), ('Cafetera', 'Cocina')
    ]
    for name, grp in devices:
        try:
            original = name
            if hasattr(app, '_renamed_devices'):
                original = app._renamed_devices.get(name, name)
        except Exception:
            original = name
        icon_override = 'Dispositivos.svg'
        for key, fname in app._device_icon_map.items():
            if key in original:
                icon_override = fname
                break
        row = DeviceRow(name, grp, toggle_callback=app._device_toggled, rename_callback=app._rename_device, icon_override=icon_override)
        dl.addWidget(row)
        app.device_rows.append(row)
        app.devices_buttons.append(row.btn)

    dev_scroll = QScrollArea()
    dev_scroll.setWidget(dev_w)
    dev_scroll.setWidgetResizable(True)
    dev_scroll.setFrameShape(QFrame.NoFrame)
    dev_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
    dev_scroll.setStyleSheet('background:transparent;')
    dev_scroll.viewport().setStyleSheet('background:transparent;')
    v.addWidget(dev_scroll, 1)

    app.active_group = 'Todo'

    def filter_dev():
        t = search.text().lower()
        rows = []
        for row in app.device_rows:
            match = t in row.base_name.lower()
            grp_ok = app.active_group == 'Todo' or row.group == app.active_group
            if match and grp_ok:
                rows.append(row)
            dl.removeWidget(row)
        asc = cb2.currentText() == 'De La A A La Z'
        rows.sort(key=lambda r: r.base_name.lower(), reverse=not asc)
        for row in app.device_rows:
            row.setVisible(False)
        for row in rows:
            row.setVisible(True)
            dl.addWidget(row)

    search.textChanged.connect(lambda _: filter_dev())
    app._filter_devices = filter_dev

    def sort_dev(_):
        asc = cb2.currentText() == 'De La A A La Z'
        app.device_rows.sort(key=lambda r: r.base_name.lower(), reverse=not asc)
        filter_dev()

    cb2.currentIndexChanged.connect(sort_dev)
    sort_dev(0)

    def select_group(card):
        app.active_group = card.base_name
        display = card.label.text()
        app.group_indicator.setText(f'Grupo Actual: {display}')
        for ccard in app.group_cards:
            ccard.set_selected(ccard is card)
        filter_dev()

    app._group_select_func = select_group
    for card in app.group_cards:
        card.select_callback = app._group_select_func
    select_group(app.group_cards[0])

    return w


# ------------------------------------------------------------------
# Animaciones
# ------------------------------------------------------------------

def create_devices_animations(app) -> list[dict[str, object]]:
    """Animaciones suaves para la cabecera y el listado de dispositivos."""

    def slide(target_getter, order: int, *, duration: int = 240, offset: float = 22.0, step: int = 28) -> dict[str, object]:
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
        slide(lambda: getattr(app, 'devices_group_container', None), 0, duration=205, offset=16.0),
        slide(lambda: getattr(app, 'group_indicator', None), 1, duration=215, offset=19.0),
        slide(lambda: getattr(app, 'device_list_widget', None), 2, duration=235, offset=24.0),
    ]
