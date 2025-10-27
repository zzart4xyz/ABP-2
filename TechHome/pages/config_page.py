"""Construcción de la página de configuración."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from constants import CLR_PANEL, CLR_TEXT_IDLE, CLR_TITLE, CLR_SURFACE, CLR_ITEM_ACT, FONT_FAM


def build_config_page(app):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 20, 0, 0)
    v.setSpacing(20)
    lbl_title = QLabel('Configuración')
    lbl_title.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:700 24px '{FONT_FAM}';")
    v.addWidget(lbl_title)

    def make_combo_frame(label_text, options, callback):
        frame = QFrame()
        frame.setFixedHeight(60)
        frame.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}';")
        combo = QComboBox()
        combo.addItems(options)
        combo.setStyleSheet(f"\n            QComboBox {{ background:{CLR_SURFACE}; color:{CLR_TEXT_IDLE};\n           font:600 16px '{FONT_FAM}'; border:2px solid {CLR_TITLE};\n                          border-radius:5px; padding:4px 8px; }}\n            QComboBox::drop-down {{ border:none; }}\n            QComboBox QAbstractItemView {{ background:{CLR_PANEL};\n                          border:2px solid {CLR_TITLE};\n                          selection-background-color:{CLR_ITEM_ACT};\n                          color:{CLR_TEXT_IDLE}; outline:none;padding:4px; }}\n        ")
        combo.currentIndexChanged.connect(callback)
        layout.addWidget(lbl)
        layout.addWidget(combo)
        layout.addStretch(1)
        return frame, combo

    theme_frame, app.combo_theme = make_combo_frame('Tema:', ['Oscuro', 'Claro'], lambda ix: app._set_theme('dark' if ix == 0 else 'light'))
    v.addWidget(theme_frame)

    lang_frame, app.combo_lang = make_combo_frame('Idioma:', ['Español', 'Inglés'], lambda ix: app._change_language('es' if ix == 0 else 'en'))
    v.addWidget(lang_frame)

    time_frame, app.combo_time = make_combo_frame('Tiempo:', ['24 hr', '12 hr'], lambda ix: app._set_time_format(ix == 0))
    v.addWidget(time_frame)

    notifF = QFrame()
    notifF.setFixedHeight(60)
    notifF.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
    nh = QHBoxLayout(notifF)
    nh.setContentsMargins(16, 0, 16, 0)
    nh.setSpacing(16)
    app.chk_notif = QPushButton('Notificaciones Emergentes')
    app.chk_notif.setCheckable(True)
    app.chk_notif.setChecked(True)
    app.chk_notif.setStyleSheet(f"\n            QPushButton {{ color:{CLR_TEXT_IDLE}; font:600 16px '{FONT_FAM}'; border:none; background:transparent; }}\n            QPushButton:checked {{ color:{CLR_TITLE}; }}\n        ")
    app.chk_notif.toggled.connect(app._toggle_notifications)
    nh.addWidget(app.chk_notif)
    nh.addStretch(1)
    v.addWidget(notifF)

    aboutF = QFrame()
    aboutF.setFixedHeight(100)
    aboutF.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
    ah = QVBoxLayout(aboutF)
    ah.setContentsMargins(16, 16, 16, 16)
    lbl_app = QLabel('TechHome v1.0')
    lbl_app.setStyleSheet(f"color:{CLR_TITLE}; font:700 18px '{FONT_FAM}';")
    lbl_desc = QLabel('Creado por el equipo VitalTech')
    lbl_desc.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
    ah.addWidget(lbl_app)
    ah.addWidget(lbl_desc)
    v.addWidget(aboutF)
    v.addStretch(1)

    return w
