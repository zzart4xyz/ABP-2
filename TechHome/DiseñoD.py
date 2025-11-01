"""Diseño renovado para la página de dispositivos."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QEasingCurve, QSize
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
    CLR_TEXT_IDLE,
    CLR_TITLE,
    FONT_FAM,
    icon,
    with_alpha,
)
from ui_helpers import create_card, create_header, create_row, init_page
from widgets import CustomScrollBar, DeviceRow, GroupCard

GROUP_SPECS = [
    ("Todo", "Todo.svg"),
    ("Dormitorio", "Dormitorio.svg"),
    ("Baño", "Baño.svg"),
    ("Sala", "Sala.svg"),
    ("Comedor", "Comedor.svg"),
    ("Cocina", "Cocina.svg"),
]

DEVICE_SPECS = [
    ("Luz Dormitorio", "Dormitorio"),
    ("Lámpara Noche", "Dormitorio"),
    ("Ventilador Dormitorio", "Dormitorio"),
    ("Aire Acondicionado Dormitorio", "Dormitorio"),
    ("Cortinas Dormitorio", "Dormitorio"),
    ("Enchufe Cama", "Dormitorio"),
    ("Luz Baño", "Baño"),
    ("Extractor", "Baño"),
    ("Calentador Agua", "Baño"),
    ("Espejo Iluminado", "Baño"),
    ("Ducha Automática", "Baño"),
    ("Enchufe Afeitadora", "Baño"),
    ("Luces Sala", "Sala"),
    ("Televisor", "Sala"),
    ("Consola Juegos", "Sala"),
    ("Equipo Sonido", "Sala"),
    ("Ventilador Sala", "Sala"),
    ("Enchufe Ventana", "Sala"),
    ("Luz Comedor", "Comedor"),
    ("Calefactor Comedor", "Comedor"),
    ("Enchufe Comedor", "Comedor"),
    ("Luz Barra", "Comedor"),
    ("Persianas Comedor", "Comedor"),
    ("Ventilador Techo", "Comedor"),
    ("Refrigerador", "Cocina"),
    ("Horno", "Cocina"),
    ("Microondas", "Cocina"),
    ("Lavavajillas", "Cocina"),
    ("Licuadora", "Cocina"),
    ("Cafetera", "Cocina"),
]


def build_devices_page(app):
    page, root = init_page("devices_page")

    header_card, header_layout = create_card(role="hero", orientation="h", margins=(18, 14, 18, 14))
    title_lbl = QLabel("Dispositivos")
    title_lbl.setStyleSheet(f"color:{CLR_TITLE}; font:700 26px '{FONT_FAM}';")
    header_layout.addWidget(title_lbl)
    header_layout.addStretch(1)
    add_btn = QPushButton()
    add_btn.setProperty("class", "icon")
    add_btn.setIcon(icon("Más.svg"))
    add_btn.setIconSize(QSize(26, 26))
    add_btn.setCursor(Qt.PointingHandCursor)
    add_btn.clicked.connect(app._add_device)
    header_layout.addWidget(add_btn)
    root.addWidget(header_card)
    app.devices_title_label = title_lbl
    app.devices_add_button = add_btn
    app.devices_header_card = header_card

    groups_card, groups_layout = create_card()
    groups_header, groups_label, _ = create_header("Grupos")
    groups_layout.addWidget(groups_header)
    app.devices_groups_label = groups_label
    app.devices_groups_header = groups_header
    groups_container = QWidget()
    groups_container.setStyleSheet("background:transparent;")
    groups_row = QHBoxLayout(groups_container)
    groups_row.setContentsMargins(0, 0, 0, 0)
    groups_row.setSpacing(16)
    app.grp_layout = groups_row
    app.group_cards = []
    for name, icon_name in GROUP_SPECS:
        card = GroupCard(name, icon_name, rename_callback=app._rename_group, select_callback=None)
        groups_row.addWidget(card)
        app.group_cards.append(card)
    app.add_group_card = GroupCard("Grupo Nuevo", "Más.svg", add_callback=app._add_group)
    groups_row.addWidget(app.add_group_card)
    scroll = QScrollArea()
    scroll.setWidget(groups_container)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBar(CustomScrollBar(Qt.Horizontal))
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setStyleSheet("background:transparent;")
    groups_layout.addWidget(scroll)
    app.devices_groups_scroll = scroll
    indicator = QLabel("Grupo actual: Todo")
    indicator.setStyleSheet(
        f"background:{CLR_HOVER}; color:{CLR_TITLE}; font:600 16px '{FONT_FAM}'; padding:6px 12px; border-radius:12px;"
    )
    indicator.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    groups_layout.addWidget(indicator)
    root.addWidget(groups_card)
    app.devices_groups_card = groups_card
    app.devices_groups_scroll = scroll
    app.devices_groups_scrollbar = scroll.horizontalScrollBar()
    app.group_indicator = indicator

    filter_frame, filter_layout = create_row(margins=(20, 12, 20, 12))
    search = QLineEdit()
    search.setPlaceholderText("Buscar")
    search.setFixedHeight(42)
    focus_bg = with_alpha(CLR_TITLE, 0.22)
    base_bg = with_alpha(CLR_TITLE, 0.12)
    search.setStyleSheet(
        f"""
        QLineEdit {{
            background:{base_bg};
            border:none;
            border-radius:16px;
            padding:0 18px;
            color:{CLR_TEXT_IDLE};
            font:600 16px '{FONT_FAM}';
        }}
        QLineEdit:focus {{
            background:{focus_bg};
        }}
        """
    )
    search.addAction(icon("Buscar.svg"), QLineEdit.LeadingPosition)
    filter_layout.addWidget(search, 1)
    cb_category = QComboBox()
    cb_category.addItems(["Tech", "Interruptores", "Otro"])
    cb_sort = QComboBox()
    cb_sort.addItems(["De La A A La Z", "De La Z A La A"])
    combo_style = f"""
        QComboBox {{
            background:{base_bg};
            color:{CLR_TEXT_IDLE};
            font:600 15px '{FONT_FAM}';
            border:none;
            border-radius:16px;
            padding:0 18px;
            min-width:140px;
            min-height:40px;
        }}
        QComboBox:on {{
            background:{focus_bg};
        }}
        QComboBox::drop-down {{ border:none; width:22px; }}
        QComboBox QAbstractItemView {{
            background:{with_alpha(CLR_TITLE, 0.16)};
            border:none;
            selection-background-color:{with_alpha(CLR_TITLE, 0.28)};
            color:{CLR_TEXT_IDLE};
        }}
    """
    for combo in (cb_category, cb_sort):
        combo.setFixedHeight(42)
        combo.setCursor(Qt.PointingHandCursor)
        combo.setStyleSheet(combo_style)
        filter_layout.addWidget(combo)
    root.addWidget(filter_frame)
    app.devices_filter_bar = filter_frame
    app.devices_search_field = search
    app.device_category_cb = cb_category
    app.device_sort_cb = cb_sort
    app.devices_category_combo = cb_category
    app.devices_sort_combo = cb_sort
    cb_category.currentIndexChanged.connect(app._on_device_category_changed)
    cb_sort.currentIndexChanged.connect(app._on_device_sort_changed)

    list_card, list_layout = create_card()
    list_layout.setSpacing(12)
    container = QWidget()
    container.setStyleSheet("background:transparent;")
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(12)
    list_scroll = QScrollArea()
    list_scroll.setWidget(container)
    list_scroll.setWidgetResizable(True)
    list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    list_scroll.setFrameShape(QFrame.NoFrame)
    v_scroll = CustomScrollBar(Qt.Vertical)
    list_scroll.setVerticalScrollBar(v_scroll)
    list_scroll.setStyleSheet("background:transparent;")
    list_layout.addWidget(list_scroll)
    root.addWidget(list_card, 1)

    app.devices_list_card = list_card
    app.device_scroll_area = list_scroll
    app.devices_vertical_scrollbar = v_scroll
    app.device_list_widget = container
    app.device_filter_container = container_layout
    app.devices_buttons = []
    app.device_rows = []

    for base_name, group in DEVICE_SPECS:
        original = base_name
        if hasattr(app, "_renamed_devices"):
            original = app._renamed_devices.get(base_name, base_name)
        icon_override = "Dispositivos.svg"
        for key, fname in getattr(app, "_device_icon_map", {}).items():
            if key in original:
                icon_override = fname
                break
        row = DeviceRow(base_name, group, toggle_callback=app._device_toggled, rename_callback=app._rename_device, icon_override=icon_override)
        container_layout.addWidget(row)
        app.device_rows.append(row)
        app.devices_buttons.append(row.btn)

    app.active_group = "Todo"

    def filter_devices():
        text = search.text().lower()
        visible_rows = []
        for row in app.device_rows:
            match = text in row.base_name.lower()
            group_ok = app.active_group == "Todo" or row.group == app.active_group
            if match and group_ok:
                visible_rows.append(row)
            container_layout.removeWidget(row)
        asc = cb_sort.currentText() == "De La A A La Z"
        visible_rows.sort(key=lambda r: r.base_name.lower(), reverse=not asc)
        for row in app.device_rows:
            row.setVisible(False)
        for row in visible_rows:
            row.setVisible(True)
            container_layout.addWidget(row)

    search.textChanged.connect(lambda _: filter_devices())
    app._filter_devices = filter_devices

    def sort_devices(_):
        asc = cb_sort.currentText() == "De La A A La Z"
        app.device_rows.sort(key=lambda r: r.base_name.lower(), reverse=not asc)
        filter_devices()

    cb_sort.currentIndexChanged.connect(sort_devices)
    sort_devices(0)

    def select_group(card):
        app.active_group = card.base_name
        indicator.setText(f"Grupo actual: {card.label.text()}")
        for candidate in app.group_cards:
            candidate.set_selected(candidate is card)
        filter_devices()

    app._group_select_func = select_group
    for card in app.group_cards:
        card.select_callback = app._group_select_func
    select_group(app.group_cards[0])

    return page


def create_devices_animations(app) -> list[dict[str, object]]:
    base_duration = 320

    def slide(target_getter, order: int, *, offset: float = 24.0, step: int = 40) -> dict[str, object]:
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
        slide(lambda: getattr(app, "devices_header_card", None), 0, offset=22.0),
        slide(lambda: getattr(app, "devices_groups_header", None), 1, offset=20.0),
        slide(lambda: getattr(app, "devices_groups_scroll", None), 2, offset=24.0),
        slide(lambda: getattr(app, "group_indicator", None), 3, offset=18.0),
        slide(lambda: getattr(app, "devices_filter_bar", None), 4, offset=24.0),
        slide(lambda: getattr(app, "devices_list_card", None), 5, offset=32.0),
        slide(lambda: getattr(app, "devices_groups_scrollbar", None), 6, offset=14.0),
        slide(lambda: getattr(app, "devices_vertical_scrollbar", None), 7, offset=14.0),
    ]

    for idx, card in enumerate(getattr(app, "group_cards", [])):
        specs.append(slide(lambda card=card: card, 8 + idx, offset=18.0))

    base = 8 + len(getattr(app, "group_cards", []))
    for idx, row in enumerate(getattr(app, "device_rows", [])):
        specs.append(slide(lambda row=row: row, base + idx, offset=20.0))

    return specs
