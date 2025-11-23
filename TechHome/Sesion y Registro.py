"""Diálogos de autenticación para TechHome."""

from __future__ import annotations

from typing import Callable, Optional

import constants as c

from PyQt5.QtCore import (
    Qt,
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QAbstractAnimation,
    QPoint,
    QPropertyAnimation,
    QSize,
    pyqtProperty,
)
from PyQt5.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
)

from mixins import FramelessWindowMixin
from widgets import FloatingLabelInput, TriangularBackground
from ui_helpers import apply_rounded_mask as _apply_rounded_mask
from dialogs import show_message as _dialog_message

# ---------------------------------------------------------------------------
# Tipos de callback para separar la lógica de la interfaz.
#
# El diseño debe vivir en este módulo, mientras que la lógica de acceso a
# datos (por ejemplo, validaciones o escritura en base de datos) debe ser
# suministrada desde el exterior.  Para ello se emplean ``Callable`` con
# firmas bien definidas que pueden inyectarse desde ``main.py``.
# ---------------------------------------------------------------------------

AuthCallback = Callable[[str, str], bool]
CreateUserCallback = Callable[[str, str], bool]
LogActionCallback = Callable[[str, str], None]
InitCallback = Callable[[], None]

__all__ = [
    "FloatingLabelInput",
    "TriangularBackground",
    "LoginDialog",
    "AuthCallback",
    "CreateUserCallback",
    "LogActionCallback",
    "InitCallback",
]


def show_message(parent, title: str, text: str) -> None:
    """Mostrar un mensaje informativo con el estilo de TechHome."""

    _dialog_message(parent, title, text)


class LoginDialog(FramelessWindowMixin, QDialog):
    """Login and registration dialog with a modern split‑screen design.

    This implementation replaces the old login/register layout with a two‑panel
    interface.  The dark form panel contains the input fields and buttons,
    while a gradient message panel occupies the opposite side.  Switching
    between login and registration views triggers a sliding animation for a
    fluid transition.  Colours are drawn from the application's theme
    constants to maintain visual consistency.
    """

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
        # Apply frameless, translucent styling like the rest of the application.
        self._init_frameless()
        # A larger canvas accommodates the split design.
        self.resize(700, 420)

        # Determine language settings from the parent if available; default to Spanish.
        self.lang = getattr(parent, 'lang', 'es') if parent else 'es'
        self.mapping = c.TRANSLATIONS_EN if self.lang == 'en' else {}

        # Callbacks que conectan la interfaz con la lógica de negocio.
        # Si no se proveen, se utilizan versiones inertes para mantener
        # el comportamiento puramente visual.
        self._init_callback: InitCallback = init_callback or (lambda: None)
        self._authenticate: AuthCallback = authenticate_callback or (lambda _u, _p: False)
        self._create_user: CreateUserCallback = create_user_callback or (lambda _u, _p: False)
        self._log_action: Optional[LogActionCallback] = log_action_callback

        # Inicializar recursos externos si el llamador lo requiere.
        try:
            self._init_callback()
        except Exception:
            # El diseño no debe fallar si la inicialización externa falla.
            pass

        # Track the username of the currently authenticated user.  This
        # attribute is set upon successful login in ``_on_login_action``.
        # It remains ``None`` until a valid login occurs.  External
        # callers can read this attribute after the dialog closes to
        # determine which account was authenticated.
        self.current_user: str | None = None

        # Track which view is active for the sliding animation.
        self.current_page = 'login'

        # Root frame holds the pages but does not draw its own border.  A separate
        # overlay will handle drawing the global border so that child panels can
        # draw their own shapes without conflicting.
        self.root = QFrame(self)
        self.root.setObjectName('login_root')
        self.root.setGeometry(0, 0, self.width(), self.height())
        self.root.setStyleSheet(
            f"QFrame#login_root {{ background:{c.CLR_PANEL}; border:none; border-radius:{c.FRAME_RAD}px; }}"
        )
        self._entry_offset = 40
        self._entry_effect = QGraphicsOpacityEffect(self.root)
        self.root.setGraphicsEffect(self._entry_effect)
        self._entry_effect.setOpacity(0.0)
        self._entry_anim: QParallelAnimationGroup | None = None
        self._entry_played = False
        self._exit_anim: QParallelAnimationGroup | None = None
        self._closing = False

        # Create two pages that will slide horizontally.
        w = self.width()
        h = self.height()
        self.login_page = QFrame(self.root)
        self.login_page.setGeometry(0, 0, w, h)
        self.register_page = QFrame(self.root)
        # Start the register page off‑screen to the right.
        self.register_page.setGeometry(w, 0, w, h)

        # Construct the content for each page.
        self._init_login_page()
        self._init_register_page()

        # Apply opacity effects to pages for cross‑fade animations.  Using
        # QGraphicsOpacityEffect allows us to animate the transparency of
        # the entire page widgets.  The login page starts fully opaque
        # while the register page begins invisible off screen.  When
        # animating between pages we will adjust these opacities in
        # tandem with the slide transitions to approximate the blurred
        # transition seen in the reference video.
        self._login_opacity = QGraphicsOpacityEffect(self.login_page)
        self._login_opacity.setOpacity(1.0)
        self.login_page.setGraphicsEffect(self._login_opacity)
        self._register_opacity = QGraphicsOpacityEffect(self.register_page)
        self._register_opacity.setOpacity(0.0)
        self.register_page.setGraphicsEffect(self._register_opacity)

        # Overlay frame to draw the global border.  This sits on top of other
        # widgets and has no background so mouse events pass through.  It uses
        # the primary accent colour and matches the border radius.
        self.border_overlay = QFrame(self.root)
        self.border_overlay.setGeometry(0, 0, self.width(), self.height())
        self.border_overlay.setStyleSheet(
            f"background: transparent; border:3px solid {c.CLR_TITLE}; border-radius:{c.FRAME_RAD}px;"
        )
        self.border_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.border_overlay.raise_()

        # Ensure the top-level window is clipped to rounded corners (no transparent edges)
        _apply_rounded_mask(self, c.FRAME_RAD)

    def showEvent(self, event):
        super().showEvent(event)
        if self._entry_played:
            return
        self._entry_played = True
        final_pos = self.root.pos()
        start_pos = final_pos + QPoint(0, self._entry_offset)
        self.root.move(start_pos)
        self._entry_effect.setOpacity(0.0)

        opacity_anim = QPropertyAnimation(self._entry_effect, b"opacity", self)
        opacity_anim.setDuration(420)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.OutCubic)

        pos_anim = QPropertyAnimation(self.root, b"pos", self)
        pos_anim.setDuration(420)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(final_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(opacity_anim)
        group.addAnimation(pos_anim)

        def _cleanup():
            self.root.move(final_pos)
            self._entry_effect.setOpacity(1.0)
            self._entry_anim = None

        group.finished.connect(_cleanup)
        self._entry_anim = group
        group.start()

    def _disable_interactions(self) -> None:
        """Disable interactive controls while exit animations run."""

        widgets = [
            getattr(self, "btn_login", None),
            getattr(self, "btn_register", None),
            getattr(self, "link_to_register", None),
            getattr(self, "link_to_login", None),
        ]
        for widget in widgets:
            if widget is None:
                continue
            try:
                widget.setEnabled(False)
            except Exception:
                pass

    def _play_exit_animation(self) -> bool:
        """Animate the dialog out of view before closing.

        Returns ``True`` if an animation was started, ``False`` if we fell back
        to the default ``QDialog.accept`` behaviour because the required
        graphics effect or frame is unavailable.
        """

        if getattr(self, "_closing", False):
            return True
        effect = getattr(self, "_entry_effect", None)
        frame = getattr(self, "root", None)
        if not isinstance(effect, QGraphicsOpacityEffect) or frame is None:
            return False

        if self._exit_anim is not None and self._exit_anim.state() == self._exit_anim.Running:
            return True

        self._closing = True
        self._disable_interactions()

        try:
            if self._entry_anim is not None:
                self._entry_anim.stop()
        except Exception:
            pass

        fade = QPropertyAnimation(effect, b"opacity", self)
        fade.setDuration(320)
        try:
            start_opacity = effect.opacity()
        except Exception:
            start_opacity = 1.0
        fade.setStartValue(start_opacity)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.InOutCubic)

        start_pos = frame.pos()
        end_pos = start_pos - QPoint(0, max(12, self._entry_offset // 2))
        slide = QPropertyAnimation(frame, b"pos", self)
        slide.setDuration(320)
        slide.setStartValue(start_pos)
        slide.setEndValue(end_pos)
        slide.setEasingCurve(QEasingCurve.InOutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)

        def _finish() -> None:
            try:
                effect.setOpacity(0.0)
            except Exception:
                pass
            self._exit_anim = None
            super(LoginDialog, self).accept()

        group.finished.connect(_finish)
        self._exit_anim = group
        group.start()
        return True

    # ------------------------------------------------------------------
    # Utilidades de traducción
    # ------------------------------------------------------------------
    def _tr(self, text: str, english: str | None = None) -> str:
        """Obtener ``text`` en el idioma activo (español por defecto)."""

        if self.mapping:
            return self.mapping.get(text, english or text)
        return text

    # ------------------------------------------------------------------
    # Page Construction
    # ------------------------------------------------------------------
    def _init_login_page(self):
        """Set up the split layout and widgets for the login view."""
        page = self.login_page
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # The login view consists of a dark form panel on the left and a
        # triangular gradient panel on the right.  Using our custom
        # TriangularBackground widget we achieve the diagonal separation
        # seen in the provided reference images.

        # Left: form container for login; remove outline around text fields.
        form = QFrame(page)
        form.setStyleSheet(f"background:{c.CLR_PANEL};")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(40, 40, 40, 40)
        # Increase spacing between elements to enlarge the form vertically.
        # Increase spacing further to enlarge the form vertically
        form_layout.setSpacing(30)

        # Title.
        # Usar texto fijo en español para el título del formulario de inicio de sesión
        title_text = self._tr("Iniciar Sesión", "Log In")
        title_lbl = QLabel(title_text)
        # Enlarge title font further for better visibility
        title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 38px '{c.FONT_FAM}';")
        title_lbl.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title_lbl)

        # Username input using floating label style.
        # Etiqueta y placeholder del campo de usuario en español
        user_ph = self._tr("Usuario", "Username")
        self.login_user = FloatingLabelInput(user_ph, label_px=20, right_icon_name="Usuario.svg")
        # Increase input field height
        self.login_user.setFixedHeight(70)
        # Increase the line edit font size within the floating input
        self.login_user.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.login_user)

        # Password input.
        # Etiqueta y placeholder del campo de contraseña en español
        pass_ph = self._tr("Contraseña", "Password")
        self.login_pass = FloatingLabelInput(pass_ph, is_password=True, label_px=20)
        self.login_pass.setFixedHeight(70)
        self.login_pass.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.login_pass)

        # Login button.
        # Texto del botón de entrada en español
        self.btn_login = QPushButton(self._tr("Entrar", "Login"))
        self.btn_login.setCursor(Qt.PointingHandCursor)
        # Apply a larger font size and padding to the login button
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
        form_layout.addWidget(self.btn_login)

        # Spacer to push the toggle link to the bottom.
        form_layout.addStretch(1)

        # Toggle to register link.
        # Texto del enlace para cambiar al registro en español
        self.link_to_register = QPushButton(
            self._tr("¿No tienes una cuenta? Regístrate", "Need an account? Sign up")
        )
        self.link_to_register.setCursor(Qt.PointingHandCursor)
        # Increase the font size for the sign-up link
        self.link_to_register.setStyleSheet(
            f"background:transparent; border:none; color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}'; text-decoration: underline;"
        )
        self.link_to_register.clicked.connect(self._animate_to_register)
        form_layout.addWidget(self.link_to_register, alignment=Qt.AlignCenter)

        # Right: gradient message container with triangular shape.
        # With a wider gradient panel we need t_ratio and b_ratio to sum to 1.5
        # so that the diagonal crosses the overall centre of the root.
        self.login_bg = TriangularBackground('right', t_ratio=0.90, b_ratio=0.20)
        msg_layout = QVBoxLayout(self.login_bg)
        msg_layout.setContentsMargins(40, 40, 40, 40)
        msg_layout.setSpacing(10)
        # Remove the welcome heading and tagline; retain spacing with stretches.
        msg_layout.addStretch(1)
        msg_layout.addStretch(1)
        msg_layout.addStretch(1)

        # Assemble the login page layout.
        layout.addWidget(form, stretch=1)
        layout.addWidget(self.login_bg, stretch=2)

    def _init_register_page(self):
        """Set up the split layout and widgets for the registration view."""
        page = self.register_page
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # The register view places the gradient welcome panel on the left and
        # the registration form on the right, mirroring the login view but
        # swapping sides.  A triangular gradient is drawn by the custom
        # TriangularBackground class.

        # Left: gradient message container.  Use equal ratios so that the diagonal
        # reaches the midpoint of the container.
        self.signup_bg = TriangularBackground('left', t_ratio=0.90, b_ratio=0.20)
        msg_layout = QVBoxLayout(self.signup_bg)
        msg_layout.setContentsMargins(40, 40, 40, 40)
        msg_layout.setSpacing(10)
        # Remove the welcome heading and tagline; retain spacing with stretches.
        msg_layout.addStretch(1)
        msg_layout.addStretch(1)
        msg_layout.addStretch(1)

        # Right: form container for register; remove outline around text fields.
        form = QFrame(page)
        form.setStyleSheet(f"background:{c.CLR_PANEL};")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(40, 40, 40, 40)
        # Increase spacing between elements to enlarge the form vertically.
        form_layout.setSpacing(30)

        # Usar texto fijo en español para el título del formulario de registro
        title_text = self._tr("Registrarse", "Register")
        title_lbl = QLabel(title_text)
        # Enlarge title font further for better visibility
        title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 38px '{c.FONT_FAM}';")
        title_lbl.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title_lbl)

        # Username input for registration.
        user_ph = self._tr("Usuario", "Username")
        self.register_user = FloatingLabelInput(user_ph, label_px=20, right_icon_name="Usuario.svg")
        self.register_user.setFixedHeight(70)
        self.register_user.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.register_user)

        # Password input.
        pass_ph = self._tr("Contraseña", "Password")
        self.register_pass = FloatingLabelInput(pass_ph, is_password=True, label_px=20)
        self.register_pass.setFixedHeight(70)
        self.register_pass.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.register_pass)

        # Register button.
        self.btn_register = QPushButton(self._tr("Registrar", "Register"))
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
        form_layout.addWidget(self.btn_register)

        # Spacer to push the login link to the bottom.
        form_layout.addStretch(1)

        # Toggle back to login link.
        self.link_to_login = QPushButton(
            self._tr("¿Ya tienes una cuenta? Inicia sesión", "Already have an account? Log in")
        )
        self.link_to_login.setCursor(Qt.PointingHandCursor)
        self.link_to_login.setStyleSheet(
            f"background:transparent; border:none; color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}'; text-decoration: underline;"
        )
        self.link_to_login.clicked.connect(self._animate_to_login)
        form_layout.addWidget(self.link_to_login, alignment=Qt.AlignCenter)

        # Assemble the register page layout: message on the left, form on the right.
        layout.addWidget(self.signup_bg, stretch=2)
        layout.addWidget(form, stretch=1)

        # Ensure floating labels start down when the page appears.
        for _fld in (self.register_user, self.register_pass):
            _fld._focused = False
            _fld._update_label_state()

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------
    def _line_edit_style(self) -> str:
        """Return a stylesheet for line edits consistent with the design."""
        return (
            f"QLineEdit {{\n"
            f"    border: none;\n"
            f"    border-bottom: 2px solid {c.CLR_TITLE};\n"
            f"    padding: 6px 8px;\n"
            f"    background: transparent;\n"
            f"    color: {c.CLR_TEXT_IDLE};\n"
            f"    font:600 14px '{c.FONT_FAM}';\n"
            f"}}\n"
            f"QLineEdit::placeholder {{ color:{c.CLR_PLACEHOLDER}; }}"
        )

    def _primary_button_style(self) -> str:
        """Return a stylesheet for primary action buttons."""
        return (
            f"QPushButton {{\n"
            f"    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c.CLR_TITLE}, stop:1 {c.CLR_ITEM_ACT});\n"
            f"    color: {c.CLR_BG};\n"
            f"    border: none;\n"
            f"    border-radius: {c.FRAME_RAD}px;\n"
            f"    font:600 16px '{c.FONT_FAM}';\n"
            f"    padding: 8px 16px;\n"
            f"}}\n"
            f"QPushButton:hover {{\n"
            f"    background: qlineargradient(x1:1, y1:0, x2:0, y2:0, stop:0 {c.CLR_TITLE}, stop:1 {c.CLR_ITEM_ACT});\n"
            f"}}"
        )

    # ------------------------------------------------------------------
    # Animations
    # ------------------------------------------------------------------
    def _animate_to_register(self):
        """Slide the register page into view and hide the login page."""
        if self.current_page == 'register':
            return
        self.current_page = 'register'
        width = self.width()

        # Ensure gradients are reset to their normal diagonal before starting.
        self.login_bg.setTRatio(0.90)
        self.login_bg.setBRatio(0.20)
        self.signup_bg.setTRatio(0.90)
        self.signup_bg.setBRatio(0.20)

        # Prepare the register page position and opacity for the animation
        self.register_page.move(width, 0)
        self._register_opacity.setOpacity(0.0)

        duration = 300  # milliseconds

        # Animate login page sliding left and fading out
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

        # Animate register page sliding in and fading in
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

        # On finish, reset floating labels for registration fields
        def on_finished():
            self._reset_register_labels()
            group.finished.disconnect(on_finished)

        group.finished.connect(on_finished)
        group.start()

    def _animate_to_login(self):
        """Slide the login page back into view and hide the register page."""
        if self.current_page == 'login':
            return
        self.current_page = 'login'
        width = self.width()

        # Ensure gradients are reset to their normal diagonal before starting.
        self.login_bg.setTRatio(0.90)
        self.login_bg.setBRatio(0.20)
        self.signup_bg.setTRatio(0.90)
        self.signup_bg.setBRatio(0.20)

        # Prepare the login page position and opacity for the animation
        self.login_page.move(-width, 0)
        self._login_opacity.setOpacity(0.0)

        duration = 300  # milliseconds

        # Animate register page sliding right and fading out
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

        # Animate login page sliding in and fading in
        login_pos_anim2 = QPropertyAnimation(self.login_page, b"pos")
        login_pos_anim2.setDuration(duration)
        login_pos_anim2.setStartValue(self.login_page.pos())
        login_pos_anim2.setEndValue(QPoint(0, 0))
        login_pos_anim2.setEasingCurve(QEasingCurve.InOutCubic)

        login_opacity_anim2 = QPropertyAnimation(self._login_opacity, b"opacity")
        login_opacity_anim2.setDuration(duration)
        login_opacity_anim2.setStartValue(0.0)
        login_opacity_anim2.setEndValue(1.0)
        login_opacity_anim2.setEasingCurve(QEasingCurve.InOutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(reg_pos_anim)
        group.addAnimation(reg_opacity_anim)
        group.addAnimation(login_pos_anim2)
        group.addAnimation(login_opacity_anim2)

        # On finish, restore positions and opacity for next transition
        def on_finished():
            # Ensure pages are at correct positions after animation
            self.register_page.move(width, 0)
            self._register_opacity.setOpacity(0.0)
            group.finished.disconnect(on_finished)

        group.finished.connect(on_finished)
        group.start()

    def _reset_register_labels(self):
        """Reset the floating labels for registration fields."""
        for fld in (self.register_user, self.register_pass):
            if fld is not None:
                fld._focused = False
                fld._update_label_state()

    # ------------------------------------------------------------------
    # Login and registration actions
    # ------------------------------------------------------------------
    def _on_login_action(self):
        """Attempt to authenticate the user using the provided credentials."""
        username = self.login_user.text().strip()
        password = self.login_pass.text()
        if not username or not password:
            show_message(
                self,
                self._tr("Error", "Error"),
                self._tr("Debes introducir un usuario y una contraseña.", "You must enter a username and a password."),
            )
            return
        try:
            authenticated = self._authenticate(username, password)
        except Exception:
            authenticated = False
        if authenticated:
            self.current_user = username
            self.accept()
        else:
            show_message(
                self,
                self._tr("Error", "Error"),
                self._tr("Usuario o contraseña incorrectos.", "Incorrect username or password."),
            )

    def _on_register_action(self):
        """Attempt to register a new user with the provided information."""
        username = self.register_user.text().strip()
        password = self.register_pass.text()
        if not username or not password:
            show_message(
                self,
                self._tr("Error", "Error"),
                self._tr(
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
                self._tr("Error", "Error"),
                self._tr("El nombre de usuario ya existe.", "The username already exists."),
            )
            return
        if self._log_action is not None:
            try:
                self._log_action(username, "Registro de usuario")
            except Exception:
                pass
        show_message(
            self,
            self._tr("Éxito", "Success"),
            self._tr(
                "Cuenta creada correctamente. Ahora puedes iniciar sesión.",
                "Account created successfully. You can now log in.",
            ),
        )
        self._animate_to_login()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        _apply_rounded_mask(self, c.FRAME_RAD)

    def accept(self) -> None:  # type: ignore[override]
        """Fade and slide the dialog away before accepting."""

        if self._play_exit_animation():
            return
        super().accept()
