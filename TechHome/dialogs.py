from datetime import datetime, date, time

from PyQt5.QtCore import (
    Qt, QPoint, QTimer, QPropertyAnimation, QParallelAnimationGroup,
    QSequentialAnimationGroup, QSize, QEvent, QEasingCurve, pyqtProperty,
    QRectF, QRect, pyqtSignal
)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QFont, QPainter, QPen, QLinearGradient, QPainterPath, QConicalGradient, QTransform, QRegion
from PyQt5.QtWidgets import (
    QDialog, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QCheckBox, QDateTimeEdit, QSpinBox, QProgressBar,
    QAbstractSpinBox, QMessageBox, QToolButton, QGraphicsDropShadowEffect,
    QComboBox, QSizePolicy
)

import constants as c
import os
from PyQt5.QtWidgets import QWidget
from models import AlarmState, TimerState, WEEKDAY_ORDER
from widgets import CircularCountdown, _format_seconds
from ui_helpers import (
    apply_rounded_mask as _apply_rounded_mask,
    crop_pixmap_to_content as _crop_pixmap_to_content,
    find_pixmap_centroid as _find_pixmap_centroid,
)

# -----------------------------------------------------------------------------
# Helper functions to process icon pixmaps
#
# Many of the icons used in the application are sourced from FontAwesome and
# include transparent padding in the SVG or raster files.  If left intact,
# this padding causes the icon to appear off‑centre within circular gauges.
# To ensure icons are visually centred, we crop away all transparent
# margins and compute the alpha‑weighted centroid of the remaining content.
# These helpers are defined at module scope so they can be reused by
# different widgets (e.g. CircularProgress and MetricGauge) without
# redefining them locally within constructors.

# -----------------------------------------------------------------------------
# Custom splash screen progress indicator
#
# The CircularProgress widget draws a ring representing a percentage value and
# displays an icon at its center.  It supports arbitrary diameters and
# stroke widths.  The ring colour is a fixed gradient from light blue to
# deep blue, similar to the design provided by the user.  Clients can
# update the progress via the ``setValue`` method, which triggers a repaint.

# Import the local database helper for user authentication.  This module
# provides functions to initialise the database and create/authenticate
# users.  See ``database.py`` for details.
import database




"""
Dialog components used across the TechHome application.  These classes
encapsulate common form behaviour and present login and splash
interfaces.  They draw on the centralised constants module to pick up
colours, fonts and translation strings, ensuring consistency and ease
of maintenance.
"""


def _with_alpha(color: str, alpha: float) -> str:
    qcol = QColor(color)
    qcol.setAlphaF(max(0.0, min(1.0, alpha)))
    return qcol.name(QColor.HexArgb)


def _combo_arrow_style() -> str:
    """Return stylesheet rules that swap the combo box arrow icons."""

    parts: list[str] = []
    down_path = c.resolve_icon_path("chevron-down.svg")
    if down_path:
        down_url = down_path.replace("\\", "/")
        parts.append(
            f"QComboBox::down-arrow {{ image: url(\"{down_url}\"); width:16px; height:16px; }}"
        )
    up_path = c.resolve_icon_path("chevron-up.svg")
    if up_path:
        up_url = up_path.replace("\\", "/")
        parts.append(
            f"QComboBox::down-arrow:on {{ image: url(\"{up_url}\"); }}"
        )
    return "".join(parts)


def _style_spinbox(spin: QSpinBox, large: bool = False) -> None:
    font_sz = 28 if large else 16
    height = 64 if large else 48
    min_width = 92 if large else 0
    # Large timer/alarm fields should keep their vibrant accent colour while
    # smaller utility spin boxes retain the high-contrast idle text tone.
    text_color = c.CLR_TITLE if large else c.CLR_TEXT_IDLE
    font = QFont(c.FONT_FAM)
    font.setPixelSize(font_sz)
    font.setWeight(QFont.DemiBold)
    up_path = c.resolve_icon_path("chevron-up.svg")
    down_path = c.resolve_icon_path("chevron-down.svg")
    arrow_rules: list[str] = []
    if up_path:
        up_url = up_path.replace("\\", "/")
        arrow_rules.append(f"QSpinBox::up-arrow {{ image: url(\"{up_url}\"); width:18px; height:18px; }}")
        arrow_rules.append(f"QSpinBox::up-arrow:disabled {{ image: url(\"{up_url}\"); }}")
    else:
        arrow_rules.append("QSpinBox::up-arrow { width:0; height:0; }")
    if down_path:
        down_url = down_path.replace("\\", "/")
        arrow_rules.append(f"QSpinBox::down-arrow {{ image: url(\"{down_url}\"); width:18px; height:18px; }}")
        arrow_rules.append(f"QSpinBox::down-arrow:disabled {{ image: url(\"{down_url}\"); }}")
    else:
        arrow_rules.append("QSpinBox::down-arrow { width:0; height:0; }")
    style = (
        f"QSpinBox {{ background:{c.CLR_SURFACE}; color:{text_color}; border:2px solid {c.CLR_ITEM_ACT}; border-radius:12px; padding-right:38px; }}"
        f"QSpinBox::up-button {{ subcontrol-origin:border; subcontrol-position:right top; width:36px; border:none; background:transparent; }}"
        f"QSpinBox::down-button {{ subcontrol-origin:border; subcontrol-position:right bottom; width:36px; border:none; background:transparent; }}"
        f"QSpinBox::up-button:hover {{ background:{c.CLR_ITEM_ACT}; }}"
        f"QSpinBox::down-button:hover {{ background:{c.CLR_ITEM_ACT}; }}"
        + "".join(arrow_rules)
    )
    spin.setFont(font)
    spin.setStyleSheet(style)
    spin.setFixedHeight(height)
    if min_width:
        spin.setMinimumWidth(min_width)
    spin.setAlignment(Qt.AlignCenter)
    line_edit = spin.lineEdit()
    line_edit.setFont(font)
    line_edit.setAlignment(Qt.AlignCenter)
    line_edit.setTextMargins(0, 0, 0, 0)
    line_edit.setContentsMargins(0, 0, 0, 0)
    line_edit.setStyleSheet(
        f"QLineEdit {{ background: transparent; border: none;"
        f" color: {text_color};"
        f" selection-background-color:{c.CLR_ITEM_ACT};"
        f" selection-color:{c.CLR_TITLE if large else c.CLR_BG}; }}"
    )


class BaseFormDialog(QDialog):
    """Base dialog with header and standard buttons."""

    def __init__(self, title: str, content, ok_text: str,
                 cancel_text: str = "Cancelar", size=(350, 200), parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(*size)

        main = QFrame(self)
        main.setObjectName("main")
        main.setStyleSheet(
            f"""
            QFrame#main {{
                background:{c.CLR_PANEL};
                border:2px solid {c.CLR_TITLE};
                border-radius:5px;
            }}
            """
        )
        main.setGeometry(0, 0, self.width(), self.height())
        _apply_rounded_mask(self, 5)

        # set up dragging support
        self._drag_offset = QPoint()

        v = QVBoxLayout(main)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title_lbl = QLabel(title, main)
        title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}';")
        title_lbl.setAlignment(Qt.AlignCenter)
        header.addWidget(title_lbl)
        header.addStretch(1)

        close_btn = QPushButton("", main)
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background:transparent;
                border:2px solid {c.CLR_TITLE};
                border-radius:5px;
            }}
            QPushButton:hover {{
                background:{c.CLR_TITLE};
            }}
            """
        )
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)

        v.addLayout(header)
        v.addWidget(content, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.btn_cancel = QPushButton(cancel_text, main)
        self.btn_ok     = QPushButton(ok_text, main)
        for btn in (self.btn_cancel, self.btn_ok):
            btn.setFixedSize(100, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background:transparent;
                    border:2px solid {c.CLR_TITLE};
                    border-radius:5px;
                    font:600 14px '{c.FONT_FAM}';
                    color:{c.CLR_TEXT_IDLE};
                }}
                QPushButton:hover {{
                    background:{c.CLR_TITLE};
                    color:#07101B;
                }}
                """
            )
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        v.addLayout(btn_layout)

    def get_value(self, getter):
        """Run the dialog and return the resulting value."""
        if self.exec_() == QDialog.Accepted:
            return getter(), True
        return "", False

    # drag without moving the main window
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_offset)
            e.accept()


class MessageDialog(BaseFormDialog):
    """Simple message dialog with a single OK button.

    This class derives from :class:`BaseFormDialog` to reuse the custom
    frameless window styling.  It displays a short message and an OK button
    styled according to the application's palette.  The cancel button is
    hidden to avoid confusion since there's only one possible action.
    """

    def __init__(self, title: str, message: str, parent=None):
        """Construct a message dialog with centered text and reduced height.

        The message dialog uses a fixed height slightly smaller than
        the default provided by :class:`BaseFormDialog` to avoid
        occupying unnecessary vertical space.  The message text is
        centered within its area to enhance readability.
        """
        # Create a label to hold the message text.  It is set to wrap
        # long lines and uses the standard input font and colour.  The
        # alignment ensures the text is centred horizontally and
        # vertically within its container.
        label = QLabel(message)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            f"color:{c.CLR_TEXT_IDLE}; font:500 14px '{c.FONT_FAM}';"
        )
        # Set a slightly reduced height for the dialog.  Width stays the
        # same as the standard dialog to maintain consistency.
        size = (350, 150)
        # Initialise the base dialog with only an OK button; pass an empty
        # cancel_text so that the cancel button can be hidden below.
        super().__init__(title, label, ok_text="Aceptar", cancel_text="", parent=parent, size=size)
        # Hide the cancel button since this dialog only needs one action.
        self.btn_cancel.hide()
        # Center the dialog relative to its parent if a parent is provided.
        if parent is not None:
            # Compute the centre of the parent and align this dialog to it.
            parent_geom = parent.frameGeometry()
            dlg_geom = self.frameGeometry()
            x = parent_geom.center().x() - dlg_geom.width() // 2
            y = parent_geom.center().y() - dlg_geom.height() // 2
            # Move the dialog so that it appears centrally over the parent.
            self.move(x, y)


class TimerEditorDialog(BaseFormDialog):
    """Dialog used to create or edit timers."""

    def __init__(self, timer: TimerState | None = None, parent=None):
        self._source = timer
        form = QFrame()
        layout = QVBoxLayout(form)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        self.delete_btn = QToolButton()
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setToolTip("Eliminar timer")
        self.delete_btn.setStyleSheet(
            f"QToolButton {{ color:{c.CLR_TEXT_IDLE}; background:transparent; border:none; font:600 14px '{c.FONT_FAM}'; }}"
            f"QToolButton:hover {{ color:{c.CLR_TITLE}; }}"
        )
        delete_icon = c.icon("trash-can.svg")
        if not delete_icon.isNull():
            self.delete_btn.setIcon(delete_icon)
            self.delete_btn.setIconSize(QSize(18, 18))
        else:
            self.delete_btn.setText("🗑")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setVisible(timer is not None)
        toolbar.addWidget(self.delete_btn)
        layout.addLayout(toolbar)

        time_row = QHBoxLayout()
        time_row.setSpacing(10)
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 23)
        _style_spinbox(self.hours_spin, large=True)
        time_row.addWidget(self.hours_spin)

        colon1 = QLabel(":")
        colon1.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 28px '{c.FONT_FAM}';")
        time_row.addWidget(colon1)

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        _style_spinbox(self.minutes_spin, large=True)
        time_row.addWidget(self.minutes_spin)

        colon2 = QLabel(":")
        colon2.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 28px '{c.FONT_FAM}';")
        time_row.addWidget(colon2)

        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        _style_spinbox(self.seconds_spin, large=True)
        time_row.addWidget(self.seconds_spin)
        layout.addLayout(time_row)

        label_row = QHBoxLayout()
        label_row.setSpacing(8)
        label_icon = QLabel()
        pen_pix = c.pixmap("pen-to-square.svg")
        if not pen_pix.isNull():
            label_icon.setPixmap(c.tint_pixmap(pen_pix.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation), QColor(c.CLR_TITLE)))
        else:
            label_icon.setText("✎")
            label_icon.setStyleSheet(f"color:{c.CLR_TITLE}; font:600 16px '{c.FONT_FAM}';")
        label_row.addWidget(label_icon)

        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Etiqueta del timer")
        self.label_edit.setStyleSheet(c.input_style())
        label_row.addWidget(self.label_edit)
        layout.addLayout(label_row)

        self.loop_check = QCheckBox("Repetir automáticamente")
        self.loop_check.setStyleSheet(
            f"QCheckBox {{ color:{c.CLR_TEXT_IDLE}; font:500 14px '{c.FONT_FAM}'; spacing:8px; }}"
            f"QCheckBox::indicator {{ width:22px; height:22px; border-radius:11px; border:2px solid {c.CLR_ITEM_ACT}; background:{c.CLR_SURFACE}; }}"
            f"QCheckBox::indicator:checked {{ background:{c.CLR_TITLE}; border-color:{c.CLR_TITLE}; }}"
        )
        layout.addWidget(self.loop_check)

        title = "Editar timer" if timer else "Nuevo timer"
        super().__init__(title, form, "Guardar", parent=parent, size=(360, 320))
        self._deleted = False

        if timer:
            duration = int(getattr(timer, "duration", 0))
            hours, rem = divmod(duration, 3600)
            minutes, seconds = divmod(rem, 60)
            self.hours_spin.setValue(hours)
            self.minutes_spin.setValue(minutes)
            self.seconds_spin.setValue(seconds)
            self.label_edit.setText(timer.label)
            self.loop_check.setChecked(bool(timer.loop))
        else:
            self.minutes_spin.setValue(1)

    def _on_delete(self) -> None:
        self._deleted = True
        self.accept()

    @property
    def was_deleted(self) -> bool:
        return self._deleted

    def result_state(self) -> TimerState:
        duration = self.hours_spin.value() * 3600 + self.minutes_spin.value() * 60 + self.seconds_spin.value()
        label = self.label_edit.text().strip() or "Timer"
        base_remaining = duration
        running = False
        last_started = None
        timer_id = None
        if self._source is not None:
            timer_id = self._source.timer_id
            running = self._source.running and duration > 0 and self._source.remaining > 0
            base_remaining = min(self._source.remaining, duration)
            if running:
                last_started = self._source.last_started
        return TimerState(
            label=label,
            duration=duration,
            remaining=base_remaining,
            running=running,
            loop=self.loop_check.isChecked(),
            timer_id=timer_id,
            last_started=last_started,
        )


class TimerDisplayDialog(QDialog):
    """Floating dialog that mirrors the timer card in a dedicated window."""

    playRequested = pyqtSignal()
    pauseRequested = pyqtSignal()
    resetRequested = pyqtSignal()
    closed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self._state = None
        self._expanded = False
        self._default_size = QSize(320, 360)
        self._expanded_size = QSize(420, 460)
        self.resize(self._default_size)

        self.panel = QFrame(self)
        self.panel.setObjectName("timerDisplayPanel")
        self.panel.setStyleSheet(
            f"QFrame#timerDisplayPanel {{ background:{c.CLR_PANEL}; border-radius:20px; border:1px solid {_with_alpha('#FFFFFF', 0.08)}; }}"
        )
        c.make_shadow(self.panel, 30, 12, 160)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.title_lbl = QLabel("Timer")
        self.title_lbl.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:600 18px '{c.FONT_FAM}';")
        header.addWidget(self.title_lbl)
        header.addStretch(1)

        self.expand_btn = QToolButton()
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setToolTip("Ampliar")
        self.expand_btn.setStyleSheet(
            f"QToolButton {{ background:transparent; border:none; border-radius:16px; padding:6px; color:{c.CLR_TEXT_IDLE}; }}"
            f"QToolButton:hover {{ background:{c.CLR_ITEM_ACT}; color:{c.CLR_TITLE}; }}"
        )
        expand_icon = c.icon("square-arrow-up-right.svg")
        if not expand_icon.isNull():
            self.expand_btn.setIcon(expand_icon)
            self.expand_btn.setIconSize(QSize(20, 20))
        else:
            self.expand_btn.setText("⤢")
        self.expand_btn.clicked.connect(self._toggle_expand)
        header.addWidget(self.expand_btn)

        self.close_btn = QToolButton()
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setToolTip("Cerrar")
        self.close_btn.setText("✕")
        self.close_btn.setStyleSheet(
            f"QToolButton {{ background:transparent; border:none; border-radius:16px; padding:6px; color:{c.CLR_TEXT_IDLE}; font:700 16px '{c.FONT_FAM}'; }}"
            f"QToolButton:hover {{ background:{c.CLR_ITEM_ACT}; color:{c.CLR_TITLE}; }}"
        )
        self.close_btn.clicked.connect(self.close)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        self.dial = CircularCountdown(220, 14)
        layout.addWidget(self.dial, alignment=Qt.AlignCenter)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(18)
        controls.addStretch(1)

        play_disabled_bg = _with_alpha(c.CLR_SURFACE, 0.35)
        play_disabled_fg = _with_alpha(c.CLR_TEXT_IDLE, 0.5)
        self.play_btn = QToolButton()
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setFixedSize(68, 68)
        self.play_btn.setStyleSheet(
            f"QToolButton {{ background:{c.CLR_TITLE}; border:none; border-radius:34px; padding:16px; color:#07101B; }}"
            f"QToolButton:hover:!disabled {{ background:{c.CLR_ITEM_ACT}; color:{c.CLR_TITLE}; }}"
            f"QToolButton:disabled {{ background:{play_disabled_bg}; color:{play_disabled_fg}; }}"
        )
        self._play_icon = c.icon("play.svg")
        self._pause_icon = c.icon("pause.svg")
        self._set_play_icon(False)
        self.play_btn.clicked.connect(self._on_play_clicked)
        controls.addWidget(self.play_btn)

        reset_disabled_bg = _with_alpha(c.CLR_SURFACE, 0.4)
        reset_disabled_fg = _with_alpha(c.CLR_TEXT_IDLE, 0.45)
        self.reset_btn = QToolButton()
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setFixedSize(56, 56)
        self.reset_btn.setStyleSheet(
            f"QToolButton {{ background:{_with_alpha(c.CLR_SURFACE, 0.85)}; border:none; border-radius:28px; padding:14px; color:{c.CLR_TEXT_IDLE}; }}"
            f"QToolButton:hover:!disabled {{ background:{c.CLR_ITEM_ACT}; color:{c.CLR_TITLE}; }}"
            f"QToolButton:disabled {{ background:{reset_disabled_bg}; color:{reset_disabled_fg}; }}"
        )
        reset_icon = c.icon("rotate-left.svg")
        if not reset_icon.isNull():
            self.reset_btn.setIcon(reset_icon)
            self.reset_btn.setIconSize(QSize(24, 24))
        self.reset_btn.clicked.connect(lambda: self.resetRequested.emit())
        self.reset_btn.setEnabled(False)
        controls.addWidget(self.reset_btn)
        controls.addStretch(1)
        layout.addLayout(controls)

        self._set_panel_geometry()

    def _set_panel_geometry(self) -> None:
        self.panel.setGeometry(self.rect())
        _apply_rounded_mask(self, 20)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._set_panel_geometry()

    def _on_play_clicked(self) -> None:
        if self._state is None:
            self.playRequested.emit()
            return
        running = bool(getattr(self._state, "running", False))
        remaining = int(getattr(self._state, "remaining", 0))
        if running and remaining > 0:
            self.pauseRequested.emit()
        else:
            self.playRequested.emit()

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        target = self._expanded_size if self._expanded else self._default_size
        self.resize(target)
        icon = c.icon("square-arrow-down-left.svg") if self._expanded else c.icon("square-arrow-up-right.svg")
        if not icon.isNull():
            self.expand_btn.setIcon(icon)
            self.expand_btn.setIconSize(QSize(20, 20))
            self.expand_btn.setText("")
        else:
            self.expand_btn.setText("⤡" if self._expanded else "⤢")
        self.expand_btn.setToolTip("Restaurar" if self._expanded else "Ampliar")

    def set_state(self, state: TimerState, progress: float, subtitle: str, running: bool) -> None:
        self._state = state
        label = getattr(state, "label", "Timer") or "Timer"
        self.title_lbl.setText(label)
        remaining = int(getattr(state, "remaining", 0))
        duration = max(0, int(getattr(state, "duration", 0)))
        self.dial.update_state(progress, _format_seconds(remaining), subtitle)
        is_running = running and remaining > 0
        can_reset = duration > 0 and remaining != duration
        self.play_btn.setEnabled(duration > 0)
        self._set_play_icon(is_running)
        self.reset_btn.setEnabled(can_reset)

    def _set_play_icon(self, running: bool) -> None:
        icon = self._pause_icon if running else self._play_icon
        if icon.isNull():
            self.play_btn.setText("⏸" if running else "▶")
            self.play_btn.setIcon(QIcon())
        else:
            self.play_btn.setText("")
            self.play_btn.setIcon(icon)
            self.play_btn.setIconSize(QSize(30, 30))

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.closed.emit(self)
class AlarmEditorDialog(BaseFormDialog):
    """Dialog used to create or edit alarms."""

    def __init__(self, alarm: AlarmState | None = None, parent=None):
        self._source = alarm
        form = QFrame()
        layout = QVBoxLayout(form)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(1, 12)
        _style_spinbox(self.hour_spin, large=True)
        time_row.addWidget(self.hour_spin)

        colon = QLabel(":")
        colon.setStyleSheet(f"color:{c.CLR_TITLE}; font:600 20px '{c.FONT_FAM}';")
        time_row.addWidget(colon)

        self.minute_spin = QSpinBox()
        self.minute_spin.setRange(0, 59)
        _style_spinbox(self.minute_spin, large=True)
        time_row.addWidget(self.minute_spin)

        self.ampm_combo = QComboBox()
        self.ampm_combo.addItems(["a. m.", "p. m."])
        combo_style = (
            f"QComboBox {{ background:{c.CLR_SURFACE}; color:{c.CLR_TEXT_IDLE}; padding:6px 12px; font:600 14px '{c.FONT_FAM}'; border:2px solid {c.CLR_TITLE}; border-radius:5px; }}"
            f"QComboBox QAbstractItemView {{ background:{c.CLR_PANEL}; color:{c.CLR_TEXT_IDLE}; selection-background-color:{c.CLR_ITEM_ACT}; }}"
        )
        self.ampm_combo.setStyleSheet(combo_style + _combo_arrow_style())
        time_row.addWidget(self.ampm_combo)
        layout.addLayout(time_row)

        label_row = QHBoxLayout()
        label_row.setSpacing(8)
        alarm_label_icon = QLabel()
        pen_pix = c.pixmap("pen-to-square.svg")
        if not pen_pix.isNull():
            alarm_label_icon.setPixmap(c.tint_pixmap(pen_pix.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation), QColor(c.CLR_TITLE)))
        else:
            alarm_label_icon.setText("✎")
            alarm_label_icon.setStyleSheet(f"color:{c.CLR_TITLE}; font:600 16px '{c.FONT_FAM}';")
        label_row.addWidget(alarm_label_icon)

        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Nombre de la alarma")
        self.label_edit.setStyleSheet(c.input_style())
        label_row.addWidget(self.label_edit)
        layout.addLayout(label_row)

        repeat_lbl = QLabel("Repetir alarma")
        repeat_lbl.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:600 14px '{c.FONT_FAM}';")
        layout.addWidget(repeat_lbl)

        self.day_buttons: list[QToolButton] = []
        day_row = QHBoxLayout()
        day_row.setSpacing(6)
        for symbol in WEEKDAY_ORDER:
            btn = QToolButton()
            btn.setText(symbol)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QToolButton {{ background:{c.CLR_SURFACE}; color:{c.CLR_TEXT_IDLE}; border-radius:12px; padding:6px 12px; font:600 12px '{c.FONT_FAM}'; border:none; }}"
                f"QToolButton:checked {{ background:{c.CLR_ITEM_ACT}; color:{c.CLR_TITLE}; }}"
            )
            self.day_buttons.append(btn)
            day_row.addWidget(btn)
        day_row.addStretch(1)
        layout.addLayout(day_row)

        sound_row = QHBoxLayout()
        sound_row.setSpacing(6)
        sound_icon = QLabel()
        sound_icon.setStyleSheet("border:none;")
        note_pix = c.pixmap("music-note.svg")
        if not note_pix.isNull():
            tinted = c.tint_pixmap(note_pix.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation), QColor(c.CLR_TITLE))
            sound_icon.setPixmap(tinted)
        else:
            sound_icon.setText("♪")
            sound_icon.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 16px '{c.FONT_FAM}'; border:none;")
        sound_row.addWidget(sound_icon)
        sound_lbl = QLabel("Sonido")
        sound_lbl.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:600 14px '{c.FONT_FAM}';")
        sound_row.addWidget(sound_lbl)
        sound_row.addStretch(1)
        layout.addLayout(sound_row)

        self.sound_combo = QComboBox()
        self.sound_combo.addItems(["Predeterminado", "Campanillas", "Digital", "Suave"])
        self.sound_combo.setStyleSheet(combo_style + _combo_arrow_style())
        layout.addWidget(self.sound_combo)

        snooze_row = QHBoxLayout()
        snooze_row.setSpacing(8)
        snooze_lbl = QLabel("Repetir cada")
        snooze_lbl.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:600 14px '{c.FONT_FAM}';")
        snooze_row.addWidget(snooze_lbl)
        self.snooze_spin = QSpinBox()
        self.snooze_spin.setRange(1, 30)
        self.snooze_spin.setValue(5)
        self.snooze_spin.setSuffix(" min")
        _style_spinbox(self.snooze_spin)
        snooze_row.addWidget(self.snooze_spin)
        layout.addLayout(snooze_row)

        title = "Editar alarma" if alarm else "Nueva alarma"
        super().__init__(title, form, "Guardar", parent=parent, size=(380, 480))
        self._deleted = False

        if alarm:
            trigger = alarm.trigger
            hour = trigger.hour
            ampm = 1 if hour >= 12 else 0
            display_hour = hour % 12 or 12
            self.hour_spin.setValue(display_hour)
            self.minute_spin.setValue(trigger.minute)
            self.ampm_combo.setCurrentIndex(ampm)
            self.label_edit.setText(alarm.label)
            for idx, btn in enumerate(self.day_buttons):
                btn.setChecked(idx in alarm.repeat_days)
            if alarm.sound:
                idx = self.sound_combo.findText(alarm.sound)
                if idx >= 0:
                    self.sound_combo.setCurrentIndex(idx)
            self.snooze_spin.setValue(int(alarm.snooze_minutes))
        else:
            self.hour_spin.setValue(7)
            self.minute_spin.setValue(0)
            self.ampm_combo.setCurrentIndex(0)

    def _on_delete(self) -> None:
        self._deleted = True
        self.accept()

    @property
    def was_deleted(self) -> bool:
        return self._deleted

    def _selected_days(self) -> set[int]:
        return {idx for idx, btn in enumerate(self.day_buttons) if btn.isChecked()}

    def result_state(self) -> AlarmState:
        hour = self.hour_spin.value() % 12
        if self.ampm_combo.currentIndex() == 1:
            hour = (hour % 12) + 12
        elif hour == 12:
            hour = 0
        minute = self.minute_spin.value()
        base_date = self._source.trigger.date() if self._source else date.today()
        trigger_dt = datetime.combine(base_date, time(hour=hour, minute=minute))
        label = self.label_edit.text().strip() or "Alarma"
        return AlarmState(
            label=label,
            trigger=trigger_dt,
            enabled=self._source.enabled if self._source else True,
            repeat_days=self._selected_days(),
            sound=self.sound_combo.currentText(),
            snooze_minutes=self.snooze_spin.value(),
            alarm_id=self._source.alarm_id if self._source else None,
        )


def show_message(parent, title: str, message: str):
    """Display a custom message dialog.

    This helper constructs a :class:`MessageDialog` and blocks until the
    user acknowledges the message.  It should be used instead of
    :func:`QMessageBox.warning` or :func:`QMessageBox.information` to
    ensure a consistent look and feel across the application.

    :param parent: The parent widget for modality and centering.
    :param title: The title text to display in the header.
    :param message: The body text of the message.
    """
    dlg = MessageDialog(title, message, parent=parent)
    dlg.exec_()


class NewNoteDialog(BaseFormDialog):
    def __init__(self, parent=None):
        text_edit = QTextEdit()
        text_edit.setStyleSheet(c.input_style("QTextEdit", pad=8))
        lang = getattr(parent, 'lang', 'es') if parent else 'es'
        mapping = c.TRANSLATIONS_EN if lang == 'en' else {}
        title = mapping.get("Contenido De La Nota", "Contenido De La Nota")
        ok = mapping.get("Guardar", "Guardar")
        cancel = mapping.get("Cancelar", "Cancelar")
        super().__init__(title, text_edit, ok, cancel_text=cancel,
                         parent=parent, size=(450, 350))
        self.text_edit = text_edit

    def getText(self):
        return self.get_value(lambda: self.text_edit.toPlainText())


class NewListDialog(BaseFormDialog):
    def __init__(self, parent=None):
        line = QLineEdit()
        lang = getattr(parent, 'lang', 'es') if parent else 'es'
        mapping = c.TRANSLATIONS_EN if lang == 'en' else {}
        ph = mapping.get("Nombre De La Lista", "Nombre De La Lista")
        line.setPlaceholderText(ph)
        line.setStyleSheet(c.input_style(pad=8))
        title = mapping.get("Nueva Lista", "Nueva Lista")
        ok = mapping.get("Crear", "Crear")
        cancel = mapping.get("Cancelar", "Cancelar")
        super().__init__(title, line, ok, cancel_text=cancel, parent=parent)
        self.input = line

    def getText(self):
        return self.get_value(lambda: self.input.text())


class NewElementDialog(BaseFormDialog):
    def __init__(self, parent=None):
        line = QLineEdit()
        lang = getattr(parent, 'lang', 'es') if parent else 'es'
        mapping = c.TRANSLATIONS_EN if lang == 'en' else {}
        ph = mapping.get("Nombre Del Elemento", "Nombre Del Elemento")
        line.setPlaceholderText(ph)
        line.setStyleSheet(c.input_style(pad=8))
        title = mapping.get("Nuevo Elemento", "Nuevo Elemento")
        ok = mapping.get("Añadir", "Añadir")
        cancel = mapping.get("Cancelar", "Cancelar")
        super().__init__(title, line, ok, cancel_text=cancel, parent=parent)
        self.input = line

    def getText(self):
        return self.get_value(lambda: self.input.text())





