"""Construcción y animaciones de la sección de cuenta."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QEasingCurve
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from constants import (
    CLR_BG,
    CLR_HOVER,
    CLR_PANEL,
    CLR_SURFACE,
    CLR_TEXT_IDLE,
    CLR_TITLE,
    FONT_FAM,
)


# ---------------------------------------------------------------------------
# Diseño de la página de cuenta
# ---------------------------------------------------------------------------


def build_account_page(app) -> QWidget:
    """Crear la página de información de cuenta para ``app``."""

    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 20, 0, 0)
    layout.setSpacing(20)

    header_row = QHBoxLayout()
    title = QLabel('Cuenta')
    title.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:700 26px '{FONT_FAM}'; border:none;")
    manage_btn = QPushButton('Gestionar perfil')
    manage_btn.setCursor(Qt.PointingHandCursor)
    manage_btn.setStyleSheet(
        f"QPushButton {{ background:{CLR_TITLE}; color:{CLR_BG}; border-radius:6px;"
        f" padding:8px 16px; font:600 14px '{FONT_FAM}'; border:none; }}"
        f"QPushButton:hover {{ background:{CLR_HOVER}; color:{CLR_TITLE}; }}"
    )
    header_row.addWidget(title)
    header_row.addStretch(1)
    header_row.addWidget(manage_btn)
    layout.addLayout(header_row)

    summary_frame = QFrame()
    summary_frame.setStyleSheet(
        f"background:{CLR_PANEL}; border-radius:10px; border:1px solid rgba(255,255,255,0.04);"
    )
    summary_layout = QVBoxLayout(summary_frame)
    summary_layout.setContentsMargins(24, 20, 24, 20)
    summary_layout.setSpacing(12)
    summary_title = QLabel('Resumen de la cuenta')
    summary_title.setStyleSheet(f"color:{CLR_TITLE}; font:600 18px '{FONT_FAM}';")
    summary_layout.addWidget(summary_title)

    info_grid = QGridLayout()
    info_grid.setHorizontalSpacing(24)
    info_grid.setVerticalSpacing(12)

    username_lbl = QLabel('Usuario')
    username_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 14px '{FONT_FAM}';")
    username_val = QLabel(getattr(app, 'username', None) or 'Usuario TechHome')
    username_val.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}';")
    app.account_username_label = username_val

    email_lbl = QLabel('Correo')
    email_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 14px '{FONT_FAM}';")
    email_val = QLabel(getattr(app, 'user_email', 'usuario@techhome.app'))
    email_val.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}';")
    app.account_email_label = email_val

    status_lbl = QLabel('Estado')
    status_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 14px '{FONT_FAM}';")
    status_val = QLabel('Activo')
    status_val.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}';")
    app.account_status_label = status_val

    membership_lbl = QLabel('Plan')
    membership_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 14px '{FONT_FAM}';")
    membership_val = QLabel(getattr(app, 'account_plan', 'TechHome Familiar'))
    membership_val.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}';")
    app.account_plan_label = membership_val

    info_grid.addWidget(username_lbl, 0, 0)
    info_grid.addWidget(username_val, 0, 1)
    info_grid.addWidget(email_lbl, 1, 0)
    info_grid.addWidget(email_val, 1, 1)
    info_grid.addWidget(status_lbl, 0, 2)
    info_grid.addWidget(status_val, 0, 3)
    info_grid.addWidget(membership_lbl, 1, 2)
    info_grid.addWidget(membership_val, 1, 3)

    summary_layout.addLayout(info_grid)
    layout.addWidget(summary_frame)

    security_frame = QFrame()
    security_frame.setStyleSheet(f"background:{CLR_PANEL}; border-radius:10px;")
    security_layout = QVBoxLayout(security_frame)
    security_layout.setContentsMargins(24, 20, 24, 20)
    security_layout.setSpacing(12)
    security_title = QLabel('Seguridad')
    security_title.setStyleSheet(f"color:{CLR_TITLE}; font:600 18px '{FONT_FAM}';")
    security_layout.addWidget(security_title)
    password_lbl = QLabel('Último cambio de contraseña: hace 32 días')
    password_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
    security_layout.addWidget(password_lbl)
    devices_lbl = QLabel('Dispositivos conectados: 4')
    devices_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
    security_layout.addWidget(devices_lbl)
    app.account_devices_label = devices_lbl

    security_actions = QHBoxLayout()
    security_actions.setSpacing(12)
    change_pass = QPushButton('Cambiar contraseña')
    change_pass.setCursor(Qt.PointingHandCursor)
    change_pass.setStyleSheet(
        f"QPushButton {{ background:{CLR_SURFACE}; color:{CLR_TITLE}; border-radius:6px;"
        f" padding:8px 16px; font:600 14px '{FONT_FAM}'; border:none; }}"
        f"QPushButton:hover {{ background:{CLR_HOVER}; color:{CLR_TITLE}; }}"
    )
    sessions_btn = QPushButton('Cerrar sesiones abiertas')
    sessions_btn.setCursor(Qt.PointingHandCursor)
    sessions_btn.setStyleSheet(
        f"QPushButton {{ background:{CLR_SURFACE}; color:{CLR_TITLE}; border-radius:6px;"
        f" padding:8px 16px; font:600 14px '{FONT_FAM}'; border:none; }}"
        f"QPushButton:hover {{ background:{CLR_HOVER}; color:{CLR_TITLE}; }}"
    )
    security_actions.addWidget(change_pass)
    security_actions.addWidget(sessions_btn)
    security_actions.addStretch(1)
    security_layout.addLayout(security_actions)
    layout.addWidget(security_frame)

    activity_frame = QFrame()
    activity_frame.setStyleSheet(f"background:{CLR_PANEL}; border-radius:10px;")
    activity_layout = QVBoxLayout(activity_frame)
    activity_layout.setContentsMargins(24, 20, 24, 20)
    activity_layout.setSpacing(12)
    activity_title = QLabel('Actividad reciente')
    activity_title.setStyleSheet(f"color:{CLR_TITLE}; font:600 18px '{FONT_FAM}';")
    activity_layout.addWidget(activity_title)
    activity_events = [
        'Inicio de sesión desde Windows • hace 2 h',
        'Cambio de escena "Buenas noches" • ayer',
        'Actualización de dispositivos • hace 3 días',
    ]
    for event in activity_events:
        item_lbl = QLabel(event)
        item_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
        activity_layout.addWidget(item_lbl)
    layout.addWidget(activity_frame)

    plan_frame = QFrame()
    plan_frame.setStyleSheet(f"background:{CLR_PANEL}; border-radius:10px;")
    plan_layout = QVBoxLayout(plan_frame)
    plan_layout.setContentsMargins(24, 20, 24, 20)
    plan_layout.setSpacing(12)
    plan_title = QLabel('Plan y facturación')
    plan_title.setStyleSheet(f"color:{CLR_TITLE}; font:600 18px '{FONT_FAM}';")
    plan_layout.addWidget(plan_title)
    plan_desc = QLabel('Tu suscripción incluye automatizaciones ilimitadas y acceso multiusuario.')
    plan_desc.setWordWrap(True)
    plan_desc.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
    plan_layout.addWidget(plan_desc)
    invoice_btn = QPushButton('Ver historial de pagos')
    invoice_btn.setCursor(Qt.PointingHandCursor)
    invoice_btn.setStyleSheet(
        f"QPushButton {{ background:{CLR_SURFACE}; color:{CLR_TITLE}; border-radius:6px;"
        f" padding:8px 16px; font:600 14px '{FONT_FAM}'; border:none; }}"
        f"QPushButton:hover {{ background:{CLR_HOVER}; color:{CLR_TITLE}; }}"
    )
    plan_layout.addWidget(invoice_btn)
    layout.addWidget(plan_frame)

    layout.addStretch(1)

    # Exponer referencias para animaciones y lógica externa
    app.account_title_label = title
    app.account_manage_button = manage_btn
    app.account_summary_frame = summary_frame
    app.account_security_frame = security_frame
    app.account_activity_frame = activity_frame
    app.account_plan_frame = plan_frame
    app.account_invoice_button = invoice_btn
    app.account_security_buttons = (change_pass, sessions_btn)

    return w


# ---------------------------------------------------------------------------
# Animaciones de la página de cuenta
# ---------------------------------------------------------------------------


def create_account_animations(app) -> list[dict[str, object]]:
    """Animaciones suaves para los bloques principales de la cuenta."""

    base_duration = 360

    def slide(target_getter, order: int, *, offset: float = 30.0, step: int = 45) -> dict[str, object]:
        return {
            'type': 'slide_fade',
            'target': target_getter,
            'delay': max(0, order) * step,
            'duration': base_duration,
            'offset': offset,
            'direction': 'down',
            'easing': QEasingCurve.OutCubic,
        }

    return [
        slide(lambda: getattr(app, 'account_title_label', None), 0, offset=26.0, step=35),
        slide(lambda: getattr(app, 'account_manage_button', None), 1, offset=26.0, step=35),
        slide(lambda: getattr(app, 'account_summary_frame', None), 2),
        slide(lambda: getattr(app, 'account_security_frame', None), 3),
        slide(lambda: getattr(app, 'account_activity_frame', None), 4),
        slide(lambda: getattr(app, 'account_plan_frame', None), 5),
        slide(lambda: getattr(app, 'account_invoice_button', None), 6, offset=32.0),
    ]


__all__ = ['build_account_page', 'create_account_animations']

