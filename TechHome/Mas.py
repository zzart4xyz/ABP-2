
"""Construcción de la página 'Más'."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt, QSize, QEasingCurve
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from constants import (
    CLR_BG,
    CLR_HOVER,
    CLR_HEADER_BG,
    CLR_HEADER_TEXT,
    CLR_ITEM_ACT,
    CLR_PLACEHOLDER,
    CLR_PANEL,
    CLR_SURFACE,
    CLR_TEXT_IDLE,
    CLR_TITLE,
    FONT_FAM,
    button_style,
    icon,
    input_style,
    make_shadow,
    load_icon_pixmap,
    tint_pixmap,
    pill_button_style,
)
from widgets import (
    AlarmCard,
    CardButton,
    CustomScrollBar,
    DraggableNote,
    NoFocusDelegate,
    NotesManager,
    TimerCard,
    TimerFullscreenView,
    CurrentMonthCalendar,
    style_table,
)

def build_more_page(app):
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    app.more_stack = QStackedWidget()
    gp = QWidget()
    g = QGridLayout(gp)
    g.setContentsMargins(16, 16, 16, 16)
    g.setHorizontalSpacing(24)
    g.setVerticalSpacing(24)
    items = ['Listas Y Notas', 'Recordatorios', 'Alarmas Y Timers', 'Calendario', 'Notificaciones', 'Cámaras', 'Historial De Salud', 'Información']
    page_map = {text: i + 1 for i, text in enumerate(items)}
    app.more_pages = page_map
    app.more_grid_widget = gp
    icon_map = {
        'Listas Y Notas': 'Listas Y Notas.svg',
        'Recordatorios': 'Recordatorios.svg',
        'Alarmas Y Timers': 'Alarmas Y Timers.svg',
        'Calendario': 'Calendario.svg',
        'Notificaciones': 'Notificaciones.svg',
        'Cámaras': 'Cámaras.svg',
        'Historial De Salud': 'Historial De Salud.svg',
        'Información': 'Información.svg',
    }
    app.more_card_buttons = []
    for idx, text in enumerate(items):
        icon_name = icon_map.get(text, None)
        ccard = CardButton(text, icon_name)
        if text == 'Notificaciones':
            ccard.clicked.connect(lambda ix=page_map[text], s=app: (setattr(s, 'from_home_more', False), s._populate_notif_table(), s._switch_page(s.more_stack, ix)))
        elif text == 'Historial De Salud':
            ccard.clicked.connect(lambda ix=page_map[text], s=app: (setattr(s, 'from_home_more', False), s._populate_health_table(), s._switch_page(s.more_stack, ix)))
        else:
            ccard.clicked.connect(lambda ix=page_map[text], s=app: (setattr(s, 'from_home_more', False), s._switch_page(s.more_stack, ix)))
        r, cidx = divmod(idx, 2)
        g.addWidget(ccard, r, cidx)
        app.more_card_buttons.append(ccard)
    g.setRowStretch(4, 1)
    app.more_stack.addWidget(gp)
    ln = QWidget()
    ln_layout = QVBoxLayout(ln)
    ln_layout.setContentsMargins(16, 16, 16, 16)
    ln_layout.setSpacing(8)
    back = QPushButton()
    back.setIcon(icon('Flecha.svg'))
    back.setIconSize(QSize(24, 24))
    back.setFixedSize(40, 40)
    back.setStyleSheet('background:transparent; border:none;')
    back.clicked.connect(app._back_from_more)
    ln_layout.addWidget(back, alignment=Qt.AlignLeft)
    title_ln = QLabel('Listas Y Notas')
    title_ln.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
    ln_layout.addWidget(title_ln)
    tab = QTabWidget()
    tab.setStyleSheet(f"\n            QTabBar::tab {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n                padding:8px 16px;\n                border:2px solid {CLR_TITLE};\n                border-bottom:none;\n                border-top-left-radius:5px;\n                border-top-right-radius:5px;\n                font:600 16px '{FONT_FAM}';\n            }}\n            QTabBar::tab:selected {{\n                background:{CLR_ITEM_ACT};\n                color:{CLR_TITLE};\n            }}\n            QTabBar::tab:!selected {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n            }}\n            QTabWidget::pane {{ border:none; }}\n        ")
    tab.setTabPosition(QTabWidget.North)
    tab.tabBar().setDocumentMode(True)
    tab.tabBar().setStyleSheet('QTabBar::tab { min-width: 120px; margin:4px; padding:8px 20px; }')
    lists_tab = QWidget()
    lists_l = QHBoxLayout(lists_tab)
    lists_l.setContentsMargins(0, 0, 0, 0)
    lists_l.setSpacing(16)
    left_frame = QFrame()
    left_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
    lf_layout = QVBoxLayout(left_frame)
    lf_layout.setContentsMargins(8, 8, 8, 8)
    lf_layout.setSpacing(8)
    app.create_list_btn = QPushButton('Crear Lista')
    app.create_list_btn.setFixedHeight(36)
    app.create_list_btn.setStyleSheet(f"background:{CLR_TITLE}; color:#07101B; font:600 14px '{FONT_FAM}'; border:none; border-radius:5px;")
    app.create_list_btn.clicked.connect(app._on_add_list)
    lf_layout.addWidget(app.create_list_btn)
    app.lists_widget = QListWidget()
    app.lists_widget.setItemDelegate(NoFocusDelegate(app.lists_widget))
    app.lists_widget.setStyleSheet(f"\n            QListWidget {{ background:transparent; border:none; color:{CLR_TEXT_IDLE}; font:500 16px '{FONT_FAM}'; }}\n            QListWidget::item {{ outline:none; }}\n            QListWidget::item:selected {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; border-radius:5px; }}\n        ")
    lf_layout.addWidget(app.lists_widget)
    lists_l.addWidget(left_frame, 1)
    detail_frame = QFrame()
    detail_frame.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
    df_layout = QVBoxLayout(detail_frame)
    df_layout.setContentsMargins(8, 8, 8, 8)
    df_layout.setSpacing(8)
    app.list_title = QLabel('')
    app.list_title.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 20px '{FONT_FAM}';")
    df_layout.addWidget(app.list_title, alignment=Qt.AlignLeft)
    app.add_item_btn = QPushButton('Añadir Elemento')
    app.add_item_btn.setFixedHeight(36)
    app.add_item_btn.setStyleSheet(f"background:{CLR_TITLE}; color:#07101B; font:600 14px '{FONT_FAM}'; border:none; border-radius:5px;")
    df_layout.addWidget(app.add_item_btn, alignment=Qt.AlignLeft)
    app.list_items_widget = QListWidget()
    app.list_items_widget.setItemDelegate(NoFocusDelegate(app.list_items_widget))
    app.list_items_widget.setStyleSheet(f"\n            QListWidget {{ background:transparent; border:none; color:{CLR_TEXT_IDLE}; font:500 16px '{FONT_FAM}'; }}\n            QListWidget::item {{ outline:none; }}\n            QListWidget::item:selected {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; border-radius:5px; }}\n        ")
    items_scroll = QScrollArea()
    items_scroll.setWidgetResizable(True)
    items_scroll.setWidget(app.list_items_widget)
    items_scroll.setFrameShape(QFrame.NoFrame)
    items_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
    df_layout.addWidget(items_scroll, 1)
    lists_l.addWidget(detail_frame, 2)
    tab.addTab(lists_tab, 'Listas')
    app.lists_widget.currentTextChanged.connect(app._on_list_selected)
    app.add_item_btn.clicked.connect(app._on_add_list_item)
    notes_tab = QWidget()
    notes_l = QVBoxLayout(notes_tab)
    notes_l.setContentsMargins(0, 0, 0, 0)
    notes_l.setSpacing(8)
    add_note = QPushButton('Agregar nota')
    add_note.setIcon(icon('Más.svg'))
    add_note.setIconSize(QSize(24, 24))
    add_note.setFixedHeight(40)
    add_note.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}'; background:transparent; border:none;")
    notes_l.addWidget(add_note, alignment=Qt.AlignLeft)
    frame_notes = QFrame()
    frame_notes.setStyleSheet(f'QFrame {{ border: 2px solid {CLR_TITLE}; border-radius:5px; background:{CLR_SURFACE}; }}')
    vcn = QVBoxLayout(frame_notes)
    vcn.setContentsMargins(4, 4, 4, 4)
    notes_scroll = QScrollArea()
    notes_scroll.setWidgetResizable(True)
    notes_container = QWidget()
    notes_container.setStyleSheet(f'background:{CLR_SURFACE};')
    notes_scroll.setWidget(notes_container)
    notes_scroll.setFrameShape(QFrame.NoFrame)
    notes_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
    notes_scroll.setStyleSheet(f'background:{CLR_SURFACE}; border:none;')
    notes_scroll.viewport().setStyleSheet(f'background:{CLR_SURFACE};')
    vcn.addWidget(notes_scroll)
    app.notes_grid = QGridLayout(notes_container)
    app.notes_grid.setSpacing(16)
    spacing = app.notes_grid.spacing()
    app.notes_manager = NotesManager(notes_container, cell_size=(200, 150), spacing=spacing, rows=3, columns=3)
    app.notes_items = []
    notes_l.addWidget(frame_notes)
    add_note.clicked.connect(app._add_note)
    tab.addTab(notes_tab, 'Notas')
    ln_layout.addWidget(tab)
    app.more_stack.addWidget(ln)
    rec_page = QFrame()
    rec_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
    rp_layout = QVBoxLayout(rec_page)
    rp_layout.setContentsMargins(24, 24, 24, 24)
    rp_layout.setSpacing(22)
    back_rec = QPushButton()
    back_rec.setIcon(icon('Flecha.svg'))
    back_rec.setIconSize(QSize(24, 24))
    back_rec.setFixedSize(36, 36)
    back_rec.setStyleSheet('background:transparent; border:none;')
    back_rec.clicked.connect(app._back_from_more)
    rp_layout.addWidget(back_rec, alignment=Qt.AlignLeft)
    cards_frame = QFrame()
    cards_frame.setObjectName('remBoard')
    cards_frame.setStyleSheet(
        f"QFrame#remBoard {{ background:{CLR_PANEL}; border-radius:18px; border:2px solid {CLR_HEADER_BG}; }}"
    )
    board_layout = QVBoxLayout(cards_frame)
    board_layout.setContentsMargins(26, 24, 26, 26)
    board_layout.setSpacing(22)
    header_row = QHBoxLayout()
    header_row.setSpacing(12)
    section_title = QLabel('Recordatorios')
    section_title.setStyleSheet(f"color:{CLR_TITLE}; font:600 20px '{FONT_FAM}';")
    header_row.addWidget(section_title)
    header_row.addStretch(1)
    app.record_count_badge = QLabel('0 activos')
    app.record_count_badge.setStyleSheet(
        f"color:{CLR_TITLE}; background:{CLR_SURFACE}; border-radius:14px; padding:4px 12px; font:600 13px '{FONT_FAM}';"
    )
    header_row.addWidget(app.record_count_badge)

    def make_toolbar_btn(accent: bool = False) -> QToolButton:
        btn = QToolButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(46, 38)
        btn.setStyleSheet(pill_button_style(accent))
        return btn

    def apply_toolbar_icon(button: QToolButton, icon_name: str) -> bool:
        pix = load_icon_pixmap(icon_name, QSize(20, 20))
        if pix.isNull():
            return False
        ico = QIcon()
        for mode in (QIcon.Normal, QIcon.Disabled, QIcon.Active, QIcon.Selected):
            ico.addPixmap(pix, mode, QIcon.Off)
        button.setIcon(ico)
        button.setIconSize(pix.size())
        return True

    app.edit_reminder_btn = make_toolbar_btn()
    if not apply_toolbar_icon(app.edit_reminder_btn, 'pen-to-square.svg'):
        app.edit_reminder_btn.setText('✏')
    header_row.addWidget(app.edit_reminder_btn)

    app.delete_reminder_btn = make_toolbar_btn()
    if not apply_toolbar_icon(app.delete_reminder_btn, 'trash-can.svg'):
        app.delete_reminder_btn.setText('🗑')
    header_row.addWidget(app.delete_reminder_btn)

    app.add_reminder_btn = make_toolbar_btn(True)
    add_icon = icon('plus.svg')
    if not add_icon.isNull():
        app.add_reminder_btn.setIcon(add_icon)
        app.add_reminder_btn.setIconSize(QSize(20, 20))
    else:
        app.add_reminder_btn.setText('+')
    header_row.addWidget(app.add_reminder_btn)
    board_layout.addLayout(header_row)
    table_shell = QFrame()
    table_shell.setObjectName('remTableShell')
    table_shell.setStyleSheet(
        f"QFrame#remTableShell {{ background:{CLR_SURFACE}; border-radius:20px; border:2px solid {CLR_HEADER_BG}; }}"
    )
    make_shadow(table_shell, 28, 6)
    shell_layout = QVBoxLayout(table_shell)
    shell_layout.setContentsMargins(14, 14, 14, 14)
    shell_layout.setSpacing(0)
    app.reminder_table = QTableWidget(0, 3)
    app.reminder_table.setObjectName('reminderTable')
    app.reminder_table.setHorizontalHeaderLabels(['Recordatorio', 'Fecha', 'Hora'])
    header = app.reminder_table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QHeaderView.Stretch)
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    header.setHighlightSections(False)
    header.setStyleSheet(
        f"QHeaderView::section {{ background:{CLR_HEADER_BG}; color:{CLR_HEADER_TEXT}; border:none; padding:12px 14px; font:600 14px '{FONT_FAM}'; }}"
        " QHeaderView::section:first { border-top-left-radius:14px; }"
        " QHeaderView::section:last { border-top-right-radius:14px; }"
    )
    app.reminder_table.verticalHeader().setVisible(False)
    app.reminder_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    app.reminder_table.setSelectionMode(QAbstractItemView.SingleSelection)
    app.reminder_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    app.reminder_table.setAlternatingRowColors(False)
    style_table(app.reminder_table)
    app.reminder_table.setStyleSheet(
        f"QTableWidget#reminderTable {{ background:{CLR_PANEL}; border-radius:16px; border:2px solid {CLR_HEADER_BG};"
        f" gridline-color:{CLR_HEADER_BG}; color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}'; }}"
        f" QTableWidget#reminderTable::item {{ padding:14px 10px; background:transparent; }}"
        f" QTableWidget#reminderTable::item:selected {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; }}"
        " QTableWidget#reminderTable::item:focus { outline:none; }"
    )
    shell_layout.addWidget(app.reminder_table)
    board_layout.addWidget(table_shell, 1)
    rp_layout.addWidget(cards_frame, 1)
    app.more_stack.addWidget(rec_page)
    alarm_page = QFrame()
    alarm_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
    ap_layout = QVBoxLayout(alarm_page)
    ap_layout.setContentsMargins(16, 16, 16, 16)
    ap_layout.setSpacing(12)
    back_alarm = QPushButton()
    back_alarm.setIcon(icon('Flecha.svg'))
    back_alarm.setIconSize(QSize(24, 24))
    back_alarm.setFixedSize(36, 36)
    back_alarm.setStyleSheet('background:transparent; border:none;')
    back_alarm.clicked.connect(app._back_from_more)
    ap_layout.addWidget(back_alarm, alignment=Qt.AlignLeft)
    title_alarm = QLabel('Alarmas Y Timers')
    title_alarm.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
    ap_layout.addWidget(title_alarm)
    tab_at = QTabWidget()
    tab_at.setStyleSheet(f"\n            QTabBar::tab {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n                padding:8px 16px;\n                border:2px solid {CLR_TITLE};\n                border-bottom:none;\n                border-top-left-radius:5px;\n                border-top-right-radius:5px;\n                font:600 16px '{FONT_FAM}';\n            }}\n            QTabBar::tab:selected {{\n                background:{CLR_ITEM_ACT};\n                color:{CLR_TITLE};\n            }}\n            QTabBar::tab:!selected {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n            }}\n            QTabWidget::pane {{ border:none; }}\n        ")
    tab_at.setTabPosition(QTabWidget.North)
    tab_at.tabBar().setDocumentMode(True)
    tab_at.tabBar().setStyleSheet('QTabBar::tab { min-width: 120px; margin:4px; padding:8px 20px; }')
    alarm_tab = QWidget()
    at_l = QVBoxLayout(alarm_tab)
    at_l.setContentsMargins(0, 0, 0, 0)
    at_l.setSpacing(8)
    alarm_toolbar = QFrame()
    alarm_toolbar.setObjectName("alarmToolbar")
    alarm_toolbar.setStyleSheet(f"QFrame#alarmToolbar {{ background:{CLR_PANEL}; border-radius:16px; padding:6px; }}")
    alarm_tb = QHBoxLayout(alarm_toolbar)
    alarm_tb.setContentsMargins(6, 6, 6, 6)
    alarm_tb.setSpacing(6)
    app.edit_alarm_mode_btn = QToolButton()
    app.edit_alarm_mode_btn.setCursor(Qt.PointingHandCursor)
    app.edit_alarm_mode_btn.setFixedSize(46, 38)
    app.edit_alarm_mode_btn.setStyleSheet(pill_button_style())
    edit_alarm_icon = icon('pen-to-square.svg')
    if not edit_alarm_icon.isNull():
        app.edit_alarm_mode_btn.setIcon(edit_alarm_icon)
        app.edit_alarm_mode_btn.setIconSize(QSize(20, 20))
    else:
        app.edit_alarm_mode_btn.setText('✏')
    alarm_tb.addWidget(app.edit_alarm_mode_btn)
    app.add_alarm_btn = QToolButton()
    app.add_alarm_btn.setCursor(Qt.PointingHandCursor)
    app.add_alarm_btn.setFixedSize(46, 38)
    app.add_alarm_btn.setStyleSheet(pill_button_style(True))
    add_alarm_icon = icon('plus.svg')
    if not add_alarm_icon.isNull():
        app.add_alarm_btn.setIcon(add_alarm_icon)
        app.add_alarm_btn.setIconSize(QSize(20, 20))
    else:
        app.add_alarm_btn.setText('+')
    alarm_tb.addWidget(app.add_alarm_btn)
    alarm_controls = QHBoxLayout()
    alarm_controls.setContentsMargins(0, 0, 0, 0)
    alarm_controls.addStretch(1)
    alarm_controls.addWidget(alarm_toolbar)
    at_l.addLayout(alarm_controls)

    alarm_scroll = QScrollArea()
    alarm_scroll.setWidgetResizable(True)
    alarm_scroll.setFrameShape(QFrame.NoFrame)
    alarm_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
    alarm_container = QWidget()
    alarm_container.setStyleSheet('background:transparent;')
    alarm_scroll.setWidget(alarm_container)
    app.alarm_cards_layout = QVBoxLayout(alarm_container)
    app.alarm_cards_layout.setContentsMargins(0, 0, 0, 0)
    app.alarm_cards_layout.setSpacing(16)
    app.alarm_empty_label = QLabel('No hay alarmas configuradas')
    app.alarm_empty_label.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
    app.alarm_empty_label.setAlignment(Qt.AlignCenter)
    app.alarm_cards_layout.addWidget(app.alarm_empty_label)
    app.alarm_cards_layout.addStretch(1)
    at_l.addWidget(alarm_scroll, 1)
    tab_at.addTab(alarm_tab, 'Alarmas')
    timer_tab = QWidget()
    ti_l = QVBoxLayout(timer_tab)
    ti_l.setContentsMargins(0, 0, 0, 0)
    ti_l.setSpacing(12)
    timer_toolbar = QFrame()
    timer_toolbar.setObjectName("timerToolbar")
    timer_toolbar.setStyleSheet(f"QFrame#timerToolbar {{ background:{CLR_PANEL}; border-radius:16px; padding:6px; }}")
    timer_tb = QHBoxLayout(timer_toolbar)
    timer_tb.setContentsMargins(6, 6, 6, 6)
    timer_tb.setSpacing(6)
    app.edit_timer_mode_btn = QToolButton()
    app.edit_timer_mode_btn.setCursor(Qt.PointingHandCursor)
    app.edit_timer_mode_btn.setFixedSize(46, 38)
    app.edit_timer_mode_btn.setStyleSheet(pill_button_style())
    edit_timer_pix = load_icon_pixmap('pen-to-square.svg', QSize(20, 20))
    if edit_timer_pix.isNull():
        edit_timer_pix = load_icon_pixmap('edit.svg', QSize(20, 20))
    if not edit_timer_pix.isNull():
        tinted_edit = tint_pixmap(edit_timer_pix, QColor(CLR_TITLE))
        app.edit_timer_mode_btn.setIcon(QIcon(tinted_edit))
        app.edit_timer_mode_btn.setIconSize(QSize(20, 20))
    else:
        app.edit_timer_mode_btn.setText('✏')
    timer_tb.addWidget(app.edit_timer_mode_btn)
    app.add_timer_btn = QToolButton()
    app.add_timer_btn.setCursor(Qt.PointingHandCursor)
    app.add_timer_btn.setFixedSize(46, 38)
    app.add_timer_btn.setStyleSheet(pill_button_style(True))
    add_timer_pix = load_icon_pixmap('plus.svg', QSize(20, 20))
    if add_timer_pix.isNull():
        add_timer_pix = load_icon_pixmap('circle-plus.svg', QSize(20, 20))
    if not add_timer_pix.isNull():
        tinted_add = tint_pixmap(add_timer_pix, QColor(CLR_TITLE))
        app.add_timer_btn.setIcon(QIcon(tinted_add))
        app.add_timer_btn.setIconSize(QSize(20, 20))
    else:
        app.add_timer_btn.setText('+')
    timer_tb.addWidget(app.add_timer_btn)
    timer_controls = QHBoxLayout()
    timer_controls.setContentsMargins(0, 0, 0, 0)
    timer_controls.addStretch(1)
    timer_controls.addWidget(timer_toolbar)
    app.timer_toolbar_frame = timer_toolbar
    ti_l.addLayout(timer_controls)

    timer_scroll = QScrollArea()
    timer_scroll.setWidgetResizable(True)
    timer_scroll.setFrameShape(QFrame.NoFrame)
    timer_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
    timer_container = QWidget()
    timer_container.setStyleSheet('background:transparent;')
    timer_scroll.setWidget(timer_container)
    timer_container_layout = QVBoxLayout(timer_container)
    timer_container_layout.setContentsMargins(0, 0, 0, 0)
    timer_container_layout.setSpacing(16)
    app.timer_empty_label = QLabel('No hay timers activos')
    app.timer_empty_label.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
    app.timer_empty_label.setAlignment(Qt.AlignCenter)
    timer_container_layout.addWidget(app.timer_empty_label)
    timer_cards_frame = QWidget()
    timer_cards_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    app.timer_cards_layout = QGridLayout(timer_cards_frame)
    app.timer_cards_layout.setContentsMargins(0, 0, 0, 0)
    app.timer_cards_layout.setHorizontalSpacing(16)
    app.timer_cards_layout.setVerticalSpacing(16)
    app.timer_cards_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
    app.timer_cards_layout.setColumnStretch(0, 1)
    app.timer_cards_layout.setColumnStretch(1, 1)
    app.timer_cards_widget = timer_cards_frame
    timer_container_layout.addWidget(timer_cards_frame, 0, Qt.AlignTop)
    timer_container_layout.addStretch(1)

    app.timer_list_widget = timer_scroll
    ti_l.addWidget(timer_scroll, 1)
    app.timer_fullscreen_view = TimerFullscreenView()
    tab_at.addTab(timer_tab, 'Timers')
    ap_layout.addWidget(tab_at, 1)
    app.more_stack.addWidget(alarm_page)
    calendar_page = QFrame()
    calendar_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
    cp_layout = QVBoxLayout(calendar_page)
    cp_layout.setContentsMargins(16, 16, 16, 16)
    cp_layout.setSpacing(8)
    back_cal = QPushButton()
    back_cal.setIcon(icon('Flecha.svg'))
    back_cal.setIconSize(QSize(24, 24))
    back_cal.setFixedSize(36, 36)
    back_cal.setStyleSheet('background:transparent; border:none;')
    back_cal.clicked.connect(app._back_from_more)
    cp_layout.addWidget(back_cal, alignment=Qt.AlignLeft)
    title_cal = QLabel('Calendario')
    title_cal.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
    cp_layout.addWidget(title_cal)
    cal = CurrentMonthCalendar()
    cal.setGridVisible(True)
    cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
    cal_style = f"""
        QCalendarWidget {{
            background:{CLR_PANEL};
            color:{CLR_TEXT_IDLE};
            border:1px solid {CLR_HEADER_BG};
            border-radius:10px;
            padding:12px;
        }}
        QCalendarWidget QWidget {{
            background:{CLR_PANEL};
            color:{CLR_TEXT_IDLE};
        }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background: transparent;
            border: none;
            margin-bottom:10px;
        }}
        QCalendarWidget QToolButton {{
            color:{CLR_TEXT_IDLE};
            background:{CLR_SURFACE};
            border:1px solid {CLR_HEADER_BG};
            border-radius:8px;
            padding:6px 10px;
            font:700 14px '{FONT_FAM}';
        }}
        QCalendarWidget QToolButton::menu-indicator {{ image:none; }}
        QCalendarWidget QToolButton#qt_calendar_prevmonth,
        QCalendarWidget QToolButton#qt_calendar_nextmonth {{
            min-width:28px;
            background:{CLR_SURFACE};
        }}
        QCalendarWidget QToolButton:hover {{
            background:{CLR_HOVER};
            color:{CLR_TITLE};
            border-color:{CLR_TITLE};
        }}
        QCalendarWidget QToolButton:pressed {{
            background:{CLR_TITLE};
            color:{CLR_BG};
            border-color:{CLR_TITLE};
        }}
        QCalendarWidget QWidget#qt_calendar_calendarview {{
            background:{CLR_BG};
            alternate-background-color:{CLR_BG};
            border:1px solid {CLR_HEADER_BG};
            border-radius:8px;
            margin:0px;
        }}
        QCalendarWidget QTableView {{
            selection-background-color: transparent;
            outline: none;
        }}
        QCalendarWidget QAbstractItemView {{
            background:{CLR_BG};
            color:{CLR_TEXT_IDLE};
            selection-background-color: transparent;
            selection-color:{CLR_TITLE};
            gridline-color:{CLR_HEADER_BG};
            font:600 15px '{FONT_FAM}';
        }}
        QCalendarWidget QHeaderView::section {{
            background:{CLR_HEADER_BG};
            color:{CLR_HEADER_TEXT};
            border:none;
            font:700 13px '{FONT_FAM}';
            padding:6px 4px;
        }}
        QCalendarWidget::item {{
            background:{CLR_BG};
            color:{CLR_TEXT_IDLE};
            padding:8px;
            font:600 15px '{FONT_FAM}';
            border-radius:12px;
            margin:2px;
        }}
        QCalendarWidget::item:enabled:hover {{
            background:{CLR_HOVER};
            color:{CLR_TITLE};
        }}
        QCalendarWidget::item:selected:enabled {{
            background:{CLR_TITLE};
            color:{CLR_BG};
            border:1px solid {CLR_TITLE};
        }}
        QCalendarWidget::item:enabled:selected:hover {{
            background:{CLR_TITLE};
            color:{CLR_BG};
        }}
        QCalendarWidget::item:disabled {{
            color:{CLR_PLACEHOLDER};
        }}
        QCalendarWidget QWidget#qt_calendar_monthbutton,
        QCalendarWidget QWidget#qt_calendar_yearbutton {{
            min-width:84px;
            background: transparent;
            border: none;
        }}
        QCalendarWidget QWidget:focus {{ outline: none; }}
    """
    cal.setStyleSheet(cal_style)
    cal.selectionChanged.connect(app._on_calendar_date_selected)
    cal_frame = QFrame()
    cal_frame.setStyleSheet(f'background:{CLR_PANEL}; border:1px solid {CLR_HEADER_BG}; border-radius:10px;')
    cf_layout = QVBoxLayout(cal_frame)
    cf_layout.setContentsMargins(4, 4, 4, 4)
    cf_layout.addWidget(cal)
    cal_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    cp_layout.addWidget(cal_frame, 1)
    app.calendar_widget = cal
    app._refresh_calendar_events()
    app.more_stack.addWidget(calendar_page)
    notif_page = QFrame()
    notif_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
    np_layout = QVBoxLayout(notif_page)
    np_layout.setContentsMargins(16, 16, 16, 16)
    np_layout.setSpacing(12)
    back_not = QPushButton()
    back_not.setIcon(icon('Flecha.svg'))
    back_not.setIconSize(QSize(24, 24))
    back_not.setFixedSize(36, 36)
    back_not.setStyleSheet('background:transparent; border:none;')
    back_not.clicked.connect(app._back_from_more)
    np_layout.addWidget(back_not, alignment=Qt.AlignLeft)
    title_not = QLabel('Notificaciones')
    title_not.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
    np_layout.addWidget(title_not)
    notif_frame = QFrame()
    notif_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-bottom-left-radius:5px; border-bottom-right-radius:5px;')
    nf_layout = QVBoxLayout(notif_frame)
    nf_layout.setContentsMargins(8, 8, 8, 8)
    nf_layout.setSpacing(8)
    app.notif_table = QTableWidget()
    app.notif_table.setColumnCount(2)
    app.notif_table.setHorizontalHeaderLabels(['Hora', 'Mensaje'])
    hdr2 = app.notif_table.horizontalHeader()
    hdr2.setStyleSheet(f"\n            QHeaderView::section {{\n                background:{CLR_HEADER_BG};\n                color:{CLR_HEADER_TEXT};\n                padding:8px;\n                font:600 14px '{FONT_FAM}';\n                border:none;\n            }}\n        ")
    hdr2.setDefaultAlignment(Qt.AlignCenter)
    app.notif_table.verticalHeader().setVisible(False)
    app.notif_table.setEditTriggers(QTableWidget.NoEditTriggers)
    style_table(app.notif_table)
    app.notif_table.setColumnWidth(0, 120)
    app.notif_table.setColumnWidth(1, 420)
    make_shadow(notif_frame, 15, 6, 150)
    nf_layout.addWidget(app.notif_table)
    np_layout.addWidget(notif_frame, 1)
    app.more_stack.addWidget(notif_page)
    cam_page = QFrame()
    cam_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
    cp = QVBoxLayout(cam_page)
    cp.setContentsMargins(16, 16, 16, 16)
    cp.setSpacing(8)
    back_cam = QPushButton()
    back_cam.setIcon(icon('Flecha.svg'))
    back_cam.setIconSize(QSize(24, 24))
    back_cam.setFixedSize(36, 36)
    back_cam.setStyleSheet('background:transparent; border:none;')
    back_cam.clicked.connect(app._back_from_more)
    cp.addWidget(back_cam, alignment=Qt.AlignLeft)
    title_cam = QLabel('Cámaras')
    title_cam.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
    cp.addWidget(title_cam)
    cam_frame = QFrame()
    cam_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
    cf_layout = QVBoxLayout(cam_frame)
    cf_layout.setContentsMargins(8, 8, 8, 8)
    cf_layout.setSpacing(8)
    grid = QGridLayout()
    grid.setSpacing(16)
    for i in range(2):
        for j in range(2):
            frame = QFrame()
            frame.setFixedSize(300, 200)
            frame.setStyleSheet(f'\n                    QFrame {{ background:{CLR_HOVER}; border:2px solid {CLR_TITLE}; border-radius:5px; }}\n                ')
            lbl = QLabel('Vista cámara', frame)
            lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 16px '{FONT_FAM}';")
            lbl.setAlignment(Qt.AlignCenter)
            vbox = QVBoxLayout(frame)
            vbox.addStretch(1)
            vbox.addWidget(lbl)
            vbox.addStretch(1)
            grid.addWidget(frame, i, j)
    cf_layout.addLayout(grid, 1)
    make_shadow(cam_frame, 15, 6, 150)
    cp.addWidget(cam_frame, 1)
    app.more_stack.addWidget(cam_page)
    health_page = QFrame()
    health_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
    hp = QVBoxLayout(health_page)
    hp.setContentsMargins(16, 16, 16, 16)
    hp.setSpacing(12)
    back_h = QPushButton()
    back_h.setIcon(icon('Flecha.svg'))
    back_h.setIconSize(QSize(24, 24))
    back_h.setFixedSize(36, 36)
    back_h.setStyleSheet('background:transparent; border:none;')
    back_h.clicked.connect(app._back_from_more)
    hp.addWidget(back_h, alignment=Qt.AlignLeft)
    title_h = QLabel('Historial De Salud')
    title_h.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
    hp.addWidget(title_h)
    frame_h = QFrame()
    frame_h.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
    fh_layout = QVBoxLayout(frame_h)
    fh_layout.setContentsMargins(8, 8, 8, 8)
    fh_layout.setSpacing(8)
    app.table_health = QTableWidget()
    app.table_health.setColumnCount(6)
    app.table_health.setHorizontalHeaderLabels(['Fecha', 'PA', 'BPM', 'SpO₂', 'Temp', 'FR'])
    hdrh = app.table_health.horizontalHeader()
    hdrh.setStyleSheet(f"QHeaderView::section {{ background:{CLR_HEADER_BG}; color:{CLR_HEADER_TEXT}; padding:8px; font:600 14px '{FONT_FAM}'; border:none; }}")
    hdrh.setDefaultAlignment(Qt.AlignCenter)
    app.table_health.verticalHeader().setVisible(False)
    app.table_health.setEditTriggers(QTableWidget.NoEditTriggers)
    style_table(app.table_health)
    sb = CustomScrollBar(Qt.Vertical)
    sb.setStyleSheet('margin:2px; background:transparent;')
    app.table_health.setVerticalScrollBar(sb)
    app.table_health.setViewportMargins(0, 0, 4, 0)
    app.table_health.setColumnWidth(0, 160)
    fh_layout.addWidget(app.table_health)
    hp.addWidget(frame_h, 1)
    app.more_stack.addWidget(health_page)
    account_page = QFrame()
    account_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
    ap = QVBoxLayout(account_page)
    ap.setContentsMargins(16, 16, 16, 16)
    ap.setSpacing(12)
    back_a = QPushButton()
    back_a.setIcon(icon('Flecha.svg'))
    back_a.setIconSize(QSize(24, 24))
    back_a.setFixedSize(36, 36)
    back_a.setStyleSheet('background:transparent; border:none;')
    back_a.clicked.connect(app._back_from_more)
    ap.addWidget(back_a, alignment=Qt.AlignLeft)
    title_a = QLabel('Información')
    title_a.setStyleSheet(f"color:{CLR_TITLE}; font:700 24px '{FONT_FAM}';")
    ap.addWidget(title_a)
    grid = QGridLayout()
    grid.setContentsMargins(0, 8, 0, 0)
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(16)
    summary_items = [
        ('Dispositivos', 'acc_dev_label', 'Dispositivos.svg'),
        ('Listas', 'acc_list_label', 'Listas.svg'),
        ('Notas', 'acc_note_label', 'Notas.svg'),
        ('Recordatorios', 'acc_rem_label', 'Recordatorios.svg'),
        ('Alarmas', 'acc_alarm_label', 'Alarmas.svg'),
        ('Timers', 'acc_timer_label', 'Timers.svg'),
        ('Historial Salud', 'acc_health_label', 'Historial De Salud.svg'),
        ('Acciones', 'acc_action_label', 'Acciones.svg'),
        ('Tema', 'acc_theme_label', 'Tema.svg'),
        ('Idioma', 'acc_lang_label', 'Idioma.svg'),
        ('Hora', 'acc_time_label', 'Hora.svg'),
        ('Notificaciones', 'acc_notif_label', 'Notificaciones.svg'),
    ]
    cols = 3
    loc_icon_map = {
        'Dispositivos': 'Dispositivos.svg',
        'Listas': 'Listas.svg',
        'Notas': 'Notas.svg',
        'Recordatorios': 'Recordatorios.svg',
        'Alarmas': 'Alarmas.svg',
        'Timers': 'Timers.svg',
        'Historial Salud': 'Historial De Salud.svg',
        'Acciones': 'Acciones.svg',
        'Tema': 'Tema.svg',
        'Idioma': 'Idioma.svg',
        'Hora': 'Hora.svg',
        'Notificaciones': 'Notificaciones.svg',
    }
    for idx, (title, attr_name, icon_name) in enumerate(summary_items):
        card = QFrame()
        card.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        card.setFixedHeight(90)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hl = QHBoxLayout(card)
        hl.setContentsMargins(8, 4, 8, 4)
        hl.setSpacing(8)
        lbl_icon = QLabel()
        pix = load_icon_pixmap(icon_name, QSize(24, 24))
        pix_tinted = tint_pixmap(pix, QColor(CLR_TITLE))
        lbl_icon.setPixmap(pix_tinted)
        hl.addWidget(lbl_icon)
        txt_layout = QVBoxLayout()
        txt_layout.setContentsMargins(0, 0, 0, 0)
        txt_layout.setSpacing(0)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color:{CLR_TITLE}; font:600 14px '{FONT_FAM}';")
        lbl_value = QLabel('--')
        lbl_value.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:700 15px '{FONT_FAM}';")
        lbl_value.setWordWrap(True)
        txt_layout.addWidget(lbl_title)
        txt_layout.addWidget(lbl_value)
        loc_lbl = QLabel()
        loc_lbl.setFixedSize(18, 18)
        loc_lbl.setScaledContents(True)
        icon_filename = loc_icon_map.get(title)
        if icon_filename:
            loc_pm = load_icon_pixmap(icon_filename, QSize(18, 18))
            if not loc_pm.isNull():
                loc_lbl.setPixmap(tint_pixmap(loc_pm, QColor(CLR_TITLE)))
        loc_lbl.setContentsMargins(0, 4, 0, 0)
        txt_layout.addWidget(loc_lbl)
        hl.addLayout(txt_layout)
        setattr(app, attr_name, lbl_value)
        loc_attr_name = attr_name.replace('_label', '_loc_label')
        setattr(app, loc_attr_name, loc_lbl)
        row = idx // cols
        col = idx % cols
        grid.addWidget(card, row, col)
    ap.addLayout(grid)
    ap.addSpacing(12)
    ap.addStretch(1)
    app.account_page = account_page
    app.more_stack.addWidget(account_page)
    layout.addWidget(app.more_stack)
    return w


# ------------------------------------------------------------------
# Animaciones
# ------------------------------------------------------------------

def create_more_animations(app) -> list[dict[str, object]]:
    """Animaciones suaves para el panel principal de la sección Más."""

    base_duration = 220

    def slide(target_getter, order: int, *, duration: int = base_duration, offset: float = 24.0, step: int = 32) -> dict[str, object]:
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
        slide(lambda: getattr(app, 'more_stack', None), 0, offset=18.0),
        slide(lambda: getattr(app, 'more_grid_widget', None), 1, offset=24.0),
    ]

