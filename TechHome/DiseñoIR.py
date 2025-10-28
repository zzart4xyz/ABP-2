"""Diálogos de autenticación para TechHome."""

from __future__ import annotations

from typing import Callable, Optional

import constants as c

try:
    import database
except Exception:  # pragma: no cover - el entorno puede carecer de dependencias
    database = None  # type: ignore

from PyQt5.QtCore import (
    Qt,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QSize,
    QEasingCurve,
    QParallelAnimationGroup,
    QTimer,
    pyqtProperty,
)
from PyQt5.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPainterPath,
    QRegion,
)
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

# ---------------------------------------------------------------------------
# Tipos de callback para separar la lógica de la interfaz.
# ---------------------------------------------------------------------------

AuthCallback = Callable[[str, str], bool]
CreateUserCallback = Callable[[str, str], bool]
LogActionCallback = Callable[[str, str], None]
InitCallback = Callable[[], None]


def show_message(parent, title: str, text: str) -> None:
    """Mostrar un mensaje informativo simple."""

    QMessageBox.information(parent, title, text)


def _apply_rounded_mask(widget, radius: int) -> None:
    """Aplicar un recorte con esquinas redondeadas a ``widget``."""

    if radius <= 0:
        widget.clearMask()
        return
    rect = widget.rect()
    if rect.isNull():
        return
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    region = QRegion(path.toFillPolygon().toPolygon())
    widget.setMask(region)


class FloatingLabelInput(QFrame):
    """Campo de texto con etiqueta flotante e iconos opcionales."""

    def __init__(
        self,
        text: str = "",
        is_password: bool = False,
        parent=None,
        label_px: int = 14,
        left_icon_name: str | None = None,
        right_icon_name: str | None = None,
    ):
        super().__init__(parent)
        self._active_colour = c.CLR_TITLE
        self._inactive_colour = c.CLR_PLACEHOLDER
        self._text_colour = c.CLR_TEXT_IDLE
        self._focused = False
        self._label_px = label_px
        self._is_password = is_password

        self.line_edit = QLineEdit(self)
        self.line_edit.setEchoMode(QLineEdit.Password if is_password else QLineEdit.Normal)
        self.line_edit.setFrame(False)
        self.line_edit.setStyleSheet(
            f"QLineEdit {{ border: none; background: transparent; color:{self._text_colour}; font:600 14px '{c.FONT_FAM}'; }}"
        )
        self.line_edit.setPlaceholderText("")

        self.label = QLabel(text, self)
        self.label.setStyleSheet(f"color:{self._inactive_colour}; font:600 {self._label_px}px '{c.FONT_FAM}';")
        self.label.show()

        self.left_icon = None
        self._left_icon_w = 0
        if left_icon_name:
            self.left_icon = QLabel(self)
            self.left_icon.setStyleSheet("background:transparent; border:none;")
            pm = c.pixmap(left_icon_name)
            if not pm.isNull():
                self.left_icon.setPixmap(pm.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.left_icon.setFixedSize(38, 38)
            self._left_icon_w = 42

        self.right_icon = None
        self._has_right_icon = False
        self._end_icon_w = 36
        self._end_margin = 6
        self._gap_between_end_icons = 6
        if right_icon_name:
            self.right_icon = QLabel(self)
            self.right_icon.setStyleSheet("background:transparent; border:none;")
            rpm = c.pixmap(right_icon_name)
            if not rpm.isNull():
                self.right_icon.setPixmap(
                    rpm.scaled(self._end_icon_w, self._end_icon_w, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            self.right_icon.setFixedSize(self._end_icon_w, self._end_icon_w)
            self._has_right_icon = True

        self.lock_btn = None
        self._right_pad = 0
        if is_password:
            self.lock_btn = QToolButton(self)
            self.lock_btn.setCursor(Qt.PointingHandCursor)
            self.lock_btn.setStyleSheet("QToolButton { background:transparent; border:none; }")
            self._icon_locked = QIcon(c.pixmap("Cerrado.svg"))
            self._icon_unlocked = QIcon(c.pixmap("Habierto.svg"))
            self.lock_btn.setIcon(self._icon_locked)
            self.lock_btn.setIconSize(QSize(self._end_icon_w, self._end_icon_w))
            self.lock_btn.clicked.connect(self._toggle_password_visibility)
            self._eye_anim = None
        end_count = int(bool(getattr(self, "lock_btn", None))) + int(bool(getattr(self, "right_icon", None)))
        self._right_pad = (
            end_count * self._end_icon_w
            + max(0, end_count - 1) * self._gap_between_end_icons
            + self._end_margin
            + 4
        )

        self._anim = None
        self._up_pos = QPoint(0, 0)
        self._down_pos = QPoint(0, 0)

        self.setFocusPolicy(Qt.StrongFocus)
        self.installEventFilter(self)
        self.line_edit.installEventFilter(self)
        self.label.setCursor(Qt.IBeamCursor)
        self.label.installEventFilter(self)

        self.line_edit.textChanged.connect(self._update_label_state)
        self.line_edit.setTextMargins(self._left_icon_w, 0, self._right_pad, 0)

    def sizeHint(self):
        return QSize(240, 56)

    def eventFilter(self, source, event):
        if source is self.line_edit:
            if event.type() == QEvent.FocusIn:
                self._focused = True
                self._update_label_state()
            elif event.type() == QEvent.FocusOut:
                self._focused = False
                self._update_label_state()
        if source is self or source is self.label:
            if event.type() == QEvent.MouseButtonPress:
                self.line_edit.setFocus()
                self.line_edit.setCursorPosition(len(self.line_edit.text()))
                self._focused = True
                self._update_label_state()
                return True
        return super().eventFilter(source, event)

    def _toggle_password_visibility(self):
        if self.line_edit.echoMode() == QLineEdit.Password:
            self.line_edit.setEchoMode(QLineEdit.Normal)
            if self.lock_btn:
                self.lock_btn.setIcon(self._icon_unlocked)
        else:
            self.line_edit.setEchoMode(QLineEdit.Password)
            if self.lock_btn:
                self.lock_btn.setIcon(self._icon_locked)
        if self.lock_btn:
            self.lock_btn.setIconSize(QSize(self._end_icon_w, self._end_icon_w))
            anim = QPropertyAnimation(self.lock_btn, b"iconSize", self)
            anim.setDuration(180)
            anim.setStartValue(QSize(self._end_icon_w, self._end_icon_w))
            anim.setKeyValueAt(0.5, QSize(self._end_icon_w + 6, self._end_icon_w + 6))
            anim.setEndValue(QSize(self._end_icon_w, self._end_icon_w))
            anim.start()
            self._eye_anim = anim

    def _update_label_state(self):
        has_text = bool(self.line_edit.text())
        target_up = self._focused or has_text
        dest = self._up_pos if target_up else self._down_pos
        new_colour = self._active_colour if target_up else self._inactive_colour
        if self._anim:
            self._anim.stop()
            self._anim = None
        if self.label.pos() != dest:
            self._anim = QPropertyAnimation(self.label, b"pos", self)
            self._anim.setDuration(220)
            self._anim.setStartValue(self.label.pos())
            self._anim.setEndValue(dest)
            self._anim.start()
        else:
            self.label.move(dest)
        self.label.setStyleSheet(f"color:{new_colour}; font:600 {self._label_px}px '{c.FONT_FAM}';")
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        label_h = self.label.sizeHint().height()
        line_h = max(28, getattr(self, "_end_icon_w", 26) + 4)
        line_y = max(0, h - line_h - 2)
        self.line_edit.setGeometry(0, line_y, w, line_h)
        up_y = 2
        down_y = line_y + max(0, (line_h - label_h) // 2)
        if down_y <= up_y:
            down_y = up_y + 12
        self._up_pos = QPoint(0, up_y)
        self._down_pos = QPoint(0, down_y)
        self.label.resize(w, label_h)
        if self.left_icon:
            ix = 2
            iy = line_y + (line_h - self.left_icon.height()) // 2
            self.left_icon.move(ix, iy)
            self.left_icon.show()
        anchor_right = w - getattr(self, "_end_margin", 6)
        iy = line_y + (line_h - getattr(self, "_end_icon_w", 26)) // 2
        right_x = anchor_right

        def _place_end_widget(widget):
            nonlocal right_x
            if not widget:
                return
            size = getattr(self, "_end_icon_w", 26)
            widget.resize(size, size)
            right_x -= size
            widget.move(right_x, iy)
            widget.show()
            right_x -= getattr(self, "_gap_between_end_icons", 6)

        if getattr(self, "_is_password", False):
            _place_end_widget(getattr(self, "lock_btn", None))
        if getattr(self, "_has_right_icon", False):
            _place_end_widget(getattr(self, "right_icon", None))
        self.line_edit.setTextMargins(self._left_icon_w, 0, getattr(self, "_right_pad", 0), 0)
        initial = self._up_pos if (self._focused or bool(self.line_edit.text())) else self._down_pos
        self.label.move(initial)
        self._update_label_state()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        has_text = bool(self.line_edit.text())
        colour = self._active_colour if (self._focused or has_text) else self._inactive_colour
        pen = QPen(QColor(colour))
        pen.setWidth(2)
        painter.setPen(pen)
        y = self.height() - 1
        painter.drawLine(0, y, self.width(), y)
        painter.end()

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str):
        self.line_edit.setText(text)

    def setEchoMode(self, mode):
        self.line_edit.setEchoMode(mode)


class TriangularBackground(QFrame):
    """Panel que dibuja un gradiente diagonal para el diseño dividido."""

    def __init__(self, orientation: str = "left", t_ratio: float = 0.7, b_ratio: float = 0.3, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.t_ratio = t_ratio
        self.b_ratio = b_ratio
        self.setStyleSheet("background:transparent;")

    def getTRatio(self) -> float:
        return self.t_ratio

    def setTRatio(self, value: float) -> None:
        self.t_ratio = value
        self.update()

    def getBRatio(self) -> float:
        return self.b_ratio

    def setBRatio(self, value: float) -> None:
        self.b_ratio = value
        self.update()

    tRatio = pyqtProperty(float, fget=getTRatio, fset=setTRatio)
    bRatio = pyqtProperty(float, fget=getBRatio, fset=setBRatio)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        path = QPainterPath()
        if self.orientation == "left":
            x_top = self.t_ratio * w
            x_bottom = self.b_ratio * w
            path.moveTo(0, 0)
            path.lineTo(x_top, 0)
            path.lineTo(x_bottom, h)
            path.lineTo(0, h)
            path.closeSubpath()
        else:
            x_top = w * (1 - self.t_ratio)
            x_bottom = w * (1 - self.b_ratio)
            path.moveTo(x_top, 0)
            path.lineTo(w, 0)
            path.lineTo(w, h)
            path.lineTo(x_bottom, h)
            path.closeSubpath()
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(c.CLR_TITLE))
        grad.setColorAt(1.0, QColor(c.CLR_ITEM_ACT))
        painter.fillPath(path, grad)
        pen = QPen(QColor(c.CLR_TITLE))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(int(path.elementAt(1).x), int(path.elementAt(1).y), int(path.elementAt(2).x), int(path.elementAt(2).y))
        painter.end()


class LoginDialog(QDialog):
    """Diálogo combinado de inicio de sesión y registro con diseño dividido."""

    def __init__(
        self,
        parent=None,
        *,
        init_callback: Optional[InitCallback] = None,
        authenticate_callback: Optional[AuthCallback] = None,
        create_user_callback: Optional[CreateUserCallback] = None,
        log_action_callback: Optional[LogActionCallback] = None,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(700, 420)

        self.lang = getattr(parent, "lang", "es") if parent else "es"
        self.mapping = c.TRANSLATIONS_EN if self.lang == "en" else {}

        self._init_callback = self._resolve_init(init_callback)
        self._authenticate = self._resolve_auth(authenticate_callback)
        self._create_user = self._resolve_create(create_user_callback)
        self._log_action = self._resolve_logger(log_action_callback)

        try:
            self._init_callback()
        except Exception:
            pass

        self.current_user: str | None = None
        self.current_page = "login"

        self.root = QFrame(self)
        self.root.setObjectName("login_root")
        self.root.setGeometry(0, 0, self.width(), self.height())
        self.root.setStyleSheet(
            f"QFrame#login_root {{ background:{c.CLR_PANEL}; border:none; border-radius:{c.FRAME_RAD}px; }}"
        )

        w = self.width()
        h = self.height()
        self.login_page = QFrame(self.root)
        self.login_page.setGeometry(0, 0, w, h)
        self.register_page = QFrame(self.root)
        self.register_page.setGeometry(w, 0, w, h)

        self._init_login_page()
        self._init_register_page()

        self._login_opacity = QGraphicsOpacityEffect(self.login_page)
        self._login_opacity.setOpacity(1.0)
        self.login_page.setGraphicsEffect(self._login_opacity)
        self._register_opacity = QGraphicsOpacityEffect(self.register_page)
        self._register_opacity.setOpacity(0.0)
        self.register_page.setGraphicsEffect(self._register_opacity)

        self.border_overlay = QFrame(self.root)
        self.border_overlay.setGeometry(0, 0, self.width(), self.height())
        self.border_overlay.setStyleSheet(
            f"background: transparent; border:3px solid {c.CLR_TITLE}; border-radius:{c.FRAME_RAD}px;"
        )
        self.border_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.border_overlay.raise_()

        QTimer.singleShot(0, lambda: _apply_rounded_mask(self, c.FRAME_RAD))

    # ------------------------------------------------------------------
    # Resolución de callbacks
    # ------------------------------------------------------------------
    def _resolve_init(self, callback: Optional[InitCallback]) -> InitCallback:
        if callback:
            return callback
        if database and hasattr(database, "init_db"):
            return getattr(database, "init_db")
        return lambda: None

    def _resolve_auth(self, callback: Optional[AuthCallback]) -> AuthCallback:
        if callback:
            return callback
        if database and hasattr(database, "authenticate"):
            return getattr(database, "authenticate")
        return lambda _u, _p: False

    def _resolve_create(self, callback: Optional[CreateUserCallback]) -> CreateUserCallback:
        if callback:
            return callback
        if database and hasattr(database, "create_user"):
            return getattr(database, "create_user")
        return lambda _u, _p: False

    def _resolve_logger(self, callback: Optional[LogActionCallback]) -> Optional[LogActionCallback]:
        if callback:
            return callback
        if database and hasattr(database, "log_action"):
            return getattr(database, "log_action")
        return None

    def _t(self, text: str, fallback: str | None = None) -> str:
        if self.mapping:
            return self.mapping.get(text, fallback or text)
        return text

    # ------------------------------------------------------------------
    # Construcción de páginas
    # ------------------------------------------------------------------
    def _init_login_page(self) -> None:
        page = self.login_page
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        form = QFrame(page)
        form.setStyleSheet(f"background:{c.CLR_PANEL};")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(40, 40, 40, 40)
        form_layout.setSpacing(30)

        title_lbl = QLabel(self._t("Iniciar Sesión", "Log In"))
        title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 38px '{c.FONT_FAM}';")
        title_lbl.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title_lbl)

        self.login_user = FloatingLabelInput(
            self._t("Usuario", "Username"),
            label_px=20,
            right_icon_name="Usuario.svg",
        )
        self.login_user.setFixedHeight(70)
        self.login_user.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.login_user)

        self.login_pass = FloatingLabelInput(
            self._t("Contraseña", "Password"),
            is_password=True,
            label_px=20,
        )
        self.login_pass.setFixedHeight(70)
        self.login_pass.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.login_pass)

        self.btn_login = QPushButton(self._t("Entrar", "Login"))
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet(
            f"QPushButton {{\n"
            f"    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c.CLR_TITLE}, stop:1 {c.CLR_ITEM_ACT});\n"
            f"    color: {c.CLR_BG};\n"
            f"    border: none;\n"
            f"    border-radius: {c.FRAME_RAD}px;\n"
            f"    font:600 20px '{c.FONT_FAM}';\n"
            f"    padding: 12px 28px;\n"
            f"}}\n"
            f"QPushButton:hover {{\n"
            f"    background: qlineargradient(x1:1, y1:0, x2:0, y2:0, stop:0 {c.CLR_TITLE}, stop:1 {c.CLR_ITEM_ACT});\n"
            f"}}"
        )
        self.btn_login.clicked.connect(self._on_login_action)
        self.login_user.line_edit.returnPressed.connect(self._on_login_action)
        self.login_pass.line_edit.returnPressed.connect(self._on_login_action)
        form_layout.addWidget(self.btn_login)

        form_layout.addStretch(1)

        self.link_to_register = QPushButton(self._t("¿No tienes una cuenta? Regístrate", "Need an account? Sign up"))
        self.link_to_register.setCursor(Qt.PointingHandCursor)
        self.link_to_register.setStyleSheet(
            f"background:transparent; border:none; color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}'; text-decoration: underline;"
        )
        self.link_to_register.clicked.connect(self._animate_to_register)
        form_layout.addWidget(self.link_to_register, alignment=Qt.AlignCenter)

        self.login_bg = TriangularBackground("right", t_ratio=0.90, b_ratio=0.20)
        msg_layout = QVBoxLayout(self.login_bg)
        msg_layout.setContentsMargins(40, 40, 40, 40)
        msg_layout.setSpacing(10)
        msg_layout.addStretch(3)

        layout.addWidget(form, stretch=1)
        layout.addWidget(self.login_bg, stretch=2)

    def _init_register_page(self) -> None:
        page = self.register_page
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.signup_bg = TriangularBackground("left", t_ratio=0.90, b_ratio=0.20)
        msg_layout = QVBoxLayout(self.signup_bg)
        msg_layout.setContentsMargins(40, 40, 40, 40)
        msg_layout.setSpacing(10)
        msg_layout.addStretch(3)

        form = QFrame(page)
        form.setStyleSheet(f"background:{c.CLR_PANEL};")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(40, 40, 40, 40)
        form_layout.setSpacing(30)

        title_lbl = QLabel(self._t("Registrarse", "Register"))
        title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 38px '{c.FONT_FAM}';")
        title_lbl.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title_lbl)

        self.register_user = FloatingLabelInput(
            self._t("Usuario", "Username"),
            label_px=20,
            right_icon_name="Usuario.svg",
        )
        self.register_user.setFixedHeight(70)
        self.register_user.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.register_user)

        self.register_pass = FloatingLabelInput(
            self._t("Contraseña", "Password"),
            is_password=True,
            label_px=20,
        )
        self.register_pass.setFixedHeight(70)
        self.register_pass.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.register_pass)

        self.btn_register = QPushButton(self._t("Registrar", "Register"))
        self.btn_register.setCursor(Qt.PointingHandCursor)
        self.btn_register.setStyleSheet(
            f"QPushButton {{\n"
            f"    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c.CLR_TITLE}, stop:1 {c.CLR_ITEM_ACT});\n"
            f"    color: {c.CLR_BG};\n"
            f"    border: none;\n"
            f"    border-radius: {c.FRAME_RAD}px;\n"
            f"    font:600 20px '{c.FONT_FAM}';\n"
            f"    padding: 12px 28px;\n"
            f"}}\n"
            f"QPushButton:hover {{\n"
            f"    background: qlineargradient(x1:1, y1:0, x2:0, y2:0, stop:0 {c.CLR_TITLE}, stop:1 {c.CLR_ITEM_ACT});\n"
            f"}}"
        )
        self.btn_register.clicked.connect(self._on_register_action)
        self.register_user.line_edit.returnPressed.connect(self._on_register_action)
        self.register_pass.line_edit.returnPressed.connect(self._on_register_action)
        form_layout.addWidget(self.btn_register)

        form_layout.addStretch(1)

        self.link_to_login = QPushButton(self._t("¿Ya tienes una cuenta? Inicia sesión", "Already have an account? Log in"))
        self.link_to_login.setCursor(Qt.PointingHandCursor)
        self.link_to_login.setStyleSheet(
            f"background:transparent; border:none; color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}'; text-decoration: underline;"
        )
        self.link_to_login.clicked.connect(self._animate_to_login)
        form_layout.addWidget(self.link_to_login, alignment=Qt.AlignCenter)

        layout.addWidget(self.signup_bg, stretch=2)
        layout.addWidget(form, stretch=1)

        for field in (self.register_user, self.register_pass):
            field._focused = False
            field._update_label_state()

    # ------------------------------------------------------------------
    # Animaciones
    # ------------------------------------------------------------------
    def _animate_to_register(self) -> None:
        if self.current_page == "register":
            return
        self.current_page = "register"
        width = self.width()

        self.register_page.move(width, 0)
        self._register_opacity.setOpacity(0.0)

        duration = 600

        login_pos_anim = QPropertyAnimation(self.login_page, b"pos")
        login_pos_anim.setDuration(duration)
        login_pos_anim.setStartValue(self.login_page.pos())
        login_pos_anim.setEndValue(QPoint(-width, 0))
        login_pos_anim.setEasingCurve(QEasingCurve.InOutCubic)

        login_opacity_anim = QPropertyAnimation(self._login_opacity, b"opacity")
        login_opacity_anim.setDuration(duration)
        login_opacity_anim.setStartValue(1.0)
        login_opacity_anim.setEndValue(0.0)
        login_opacity_anim.setEasingCurve(QEasingCurve.InOutCubic)

        reg_pos_anim = QPropertyAnimation(self.register_page, b"pos")
        reg_pos_anim.setDuration(duration)
        reg_pos_anim.setStartValue(self.register_page.pos())
        reg_pos_anim.setEndValue(QPoint(0, 0))
        reg_pos_anim.setEasingCurve(QEasingCurve.InOutCubic)

        reg_opacity_anim = QPropertyAnimation(self._register_opacity, b"opacity")
        reg_opacity_anim.setDuration(duration)
        reg_opacity_anim.setStartValue(0.0)
        reg_opacity_anim.setEndValue(1.0)
        reg_opacity_anim.setEasingCurve(QEasingCurve.InOutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(login_pos_anim)
        group.addAnimation(login_opacity_anim)
        group.addAnimation(reg_pos_anim)
        group.addAnimation(reg_opacity_anim)

        def finished():
            self._reset_register_labels()
            group.finished.disconnect(finished)

        group.finished.connect(finished)
        group.start()

    def _animate_to_login(self) -> None:
        if self.current_page == "login":
            return
        self.current_page = "login"
        width = self.width()

        self.login_page.move(-width, 0)
        self._login_opacity.setOpacity(0.0)

        duration = 600

        reg_pos_anim = QPropertyAnimation(self.register_page, b"pos")
        reg_pos_anim.setDuration(duration)
        reg_pos_anim.setStartValue(self.register_page.pos())
        reg_pos_anim.setEndValue(QPoint(width, 0))
        reg_pos_anim.setEasingCurve(QEasingCurve.InOutCubic)

        reg_opacity_anim = QPropertyAnimation(self._register_opacity, b"opacity")
        reg_opacity_anim.setDuration(duration)
        reg_opacity_anim.setStartValue(1.0)
        reg_opacity_anim.setEndValue(0.0)
        reg_opacity_anim.setEasingCurve(QEasingCurve.InOutCubic)

        login_pos_anim = QPropertyAnimation(self.login_page, b"pos")
        login_pos_anim.setDuration(duration)
        login_pos_anim.setStartValue(self.login_page.pos())
        login_pos_anim.setEndValue(QPoint(0, 0))
        login_pos_anim.setEasingCurve(QEasingCurve.InOutCubic)

        login_opacity_anim = QPropertyAnimation(self._login_opacity, b"opacity")
        login_opacity_anim.setDuration(duration)
        login_opacity_anim.setStartValue(0.0)
        login_opacity_anim.setEndValue(1.0)
        login_opacity_anim.setEasingCurve(QEasingCurve.InOutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(reg_pos_anim)
        group.addAnimation(reg_opacity_anim)
        group.addAnimation(login_pos_anim)
        group.addAnimation(login_opacity_anim)

        def finished():
            self.login_page.move(0, 0)
            self._login_opacity.setOpacity(1.0)
            group.finished.disconnect(finished)

        group.finished.connect(finished)
        group.start()

    def _reset_register_labels(self) -> None:
        for field in (self.register_user, self.register_pass):
            field._focused = False
            field._update_label_state()

    # ------------------------------------------------------------------
    # Acciones de autenticación
    # ------------------------------------------------------------------
    def _on_login_action(self) -> None:
        username = self.login_user.text().strip()
        password = self.login_pass.text()
        if not username or not password:
            show_message(
                self,
                self._t("Error", "Error"),
                self._t(
                    "Debes introducir un usuario y una contraseña.",
                    "You must enter a username and a password.",
                ),
            )
            return
        try:
            authenticated = self._authenticate(username, password)
        except Exception:
            authenticated = False
        if authenticated:
            self.current_user = username
            self.accept()
            return
        show_message(
            self,
            self._t("Error", "Error"),
            self._t(
                "Usuario o contraseña incorrectos.",
                "Incorrect username or password.",
            ),
        )

    def _on_register_action(self) -> None:
        username = self.register_user.text().strip()
        password = self.register_pass.text()
        if not username or not password:
            show_message(
                self,
                self._t("Error", "Error"),
                self._t(
                    "Debes introducir un nombre de usuario y una contraseña.",
                    "You must enter a username and a password.",
                ),
            )
            return
        try:
            created = self._create_user(username, password)
        except Exception:
            created = False
        if not created:
            show_message(
                self,
                self._t("Error", "Error"),
                self._t(
                    "El nombre de usuario ya existe.",
                    "The username already exists.",
                ),
            )
            return

        if self._log_action is not None:
            try:
                self._log_action(username, "Registro de usuario")
            except Exception:
                pass

        show_message(
            self,
            self._t("Éxito", "Success"),
            self._t(
                "Cuenta creada correctamente. Ahora puedes iniciar sesión.",
                "Account created successfully. You can now log in.",
            ),
        )
        QTimer.singleShot(0, self._animate_to_login)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        _apply_rounded_mask(self, c.FRAME_RAD)
