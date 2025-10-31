"""Diálogos de autenticación para TechHome."""

from __future__ import annotations

from typing import Callable, Optional

import constants as c

from PyQt5.QtCore import (
    Qt,
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
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


class FloatingLabelInput(QFrame):
    """
    Input con etiqueta flotante + iconos:
      • Etiqueta flota al enfocar o tener texto.
      • Icono izquierdo opcional (por ejemplo Usuario.svg).
      • Para contraseñas: botón de candado que alterna mostrar/ocultar con una animación
        y cambia entre Cerrado.svg ↔ Habierto.svg.
    """

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
        # Colores / estado
        self._active_colour = c.CLR_TITLE
        self._inactive_colour = c.CLR_PLACEHOLDER
        self._text_colour = c.CLR_TEXT_IDLE
        self._focused = False
        self._label_px = label_px
        self._is_password = is_password

        # QLineEdit base
        self.line_edit = QLineEdit(self)
        self.line_edit.setEchoMode(QLineEdit.Password if is_password else QLineEdit.Normal)
        self.line_edit.setFrame(False)
        self.line_edit.setStyleSheet(
            f"QLineEdit {{ border: none; background: transparent; color:{self._text_colour}; font:600 14px '{c.FONT_FAM}'; }}"
        )
        self.line_edit.setPlaceholderText("")

        # Etiqueta flotante
        self.label = QLabel(text, self)
        self.label.setStyleSheet(f"color:{self._inactive_colour}; font:600 {self._label_px}px '{c.FONT_FAM}';")
        self.label.show()

        # Icono izquierdo opcional
        self.left_icon = None
        self._left_icon_w = 0
        if left_icon_name:
            self.left_icon = QLabel(self)
            self.left_icon.setStyleSheet("background:transparent; border:none;")
            pm = c.pixmap(left_icon_name)
            if not pm.isNull():
                # Escalar el icono izquierdo a 36px para adaptarlo al nuevo tamaño de iconos finales
                self.left_icon.setPixmap(pm.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # Aumentar el tamaño del contenedor del icono izquierdo para ajustarse al icono más grande
            self.left_icon.setFixedSize(38, 38)  # área clicable un poco mayor
            # Reservar más espacio a la izquierda para el icono y un margen adicional
            self._left_icon_w = 42  # margen visual + separación del texto

        # Icono derecho opcional (Usuario a la derecha)
        self.right_icon = None
        self._has_right_icon = False
        # Aumentar el tamaño de los iconos finales (por ejemplo, candado e icono derecho) a 36 px
        self._end_icon_w = 36
        self._end_margin = 6
        self._gap_between_end_icons = 6
        if right_icon_name:
            self.right_icon = QLabel(self)
            self.right_icon.setStyleSheet("background:transparent; border:none;")
            rpm = c.pixmap(right_icon_name)
            if not rpm.isNull():
                self.right_icon.setPixmap(rpm.scaled(self._end_icon_w, self._end_icon_w, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.right_icon.setFixedSize(self._end_icon_w, self._end_icon_w)
            self._has_right_icon = True
        # Botón de candado (solo para contraseñas)
        self.lock_btn = None
        self._right_pad = 0
        if is_password:
            self.lock_btn = QToolButton(self)
            self.lock_btn.setCursor(Qt.PointingHandCursor)
            self.lock_btn.setStyleSheet("QToolButton { background:transparent; border:none; }")
            self._icon_locked = QIcon(c.pixmap("Cerrado.svg"))
            self._icon_unlocked = QIcon(c.pixmap("Habierto.svg"))
            self.lock_btn.setIcon(self._icon_locked)
            # Ajustar el tamaño del icono del candado al nuevo ancho de iconos finales
            self.lock_btn.setIconSize(QSize(self._end_icon_w, self._end_icon_w))
            self.lock_btn.clicked.connect(self._toggle_password_visibility)
            # animación del botón (rebote de apertura)
            self._eye_anim = None
        # Padding derecho del texto según iconos al final
        end_count = int(bool(getattr(self, 'lock_btn', None))) + int(bool(getattr(self, 'right_icon', None)))
        self._right_pad = (end_count * self._end_icon_w + max(0, end_count - 1) * self._gap_between_end_icons + self._end_margin + 4)

        # Animación etiqueta
        self._anim = None
        self._up_pos = QPoint(0, 0)
        self._down_pos = QPoint(0, 0)

        # Eventos para foco/click
        self.setFocusPolicy(Qt.StrongFocus)
        self.installEventFilter(self)
        self.line_edit.installEventFilter(self)
        self.label.setCursor(Qt.IBeamCursor)
        self.label.installEventFilter(self)

        # Actualizar etiqueta cuando cambia el texto
        self.line_edit.textChanged.connect(self._update_label_state)

        # Márgenes del texto para no chocar con iconos
        self.line_edit.setTextMargins(self._left_icon_w, 0, self._right_pad, 0)

    def sizeHint(self):
        return QSize(240, 56)

    # ---------- Interacción ----------
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
        """
        Toggle the password visibility and animate the lock icon without
        shrinking it.  The animation now begins and ends at the
        default icon size (26×26), briefly enlarging the icon mid‑way
        for visual feedback.  This prevents the unlocked icon from
        appearing smaller after the toggle.
        """
        # Alternar modo de eco y actualizar el icono correspondiente
        if self.line_edit.echoMode() == QLineEdit.Password:
            self.line_edit.setEchoMode(QLineEdit.Normal)
            self.lock_btn.setIcon(self._icon_unlocked)
        else:
            self.line_edit.setEchoMode(QLineEdit.Password)
            self.lock_btn.setIcon(self._icon_locked)
        # Restablecer el tamaño del icono antes de animar para evitar
        # que quede reducido tras la animación.
        self.lock_btn.setIconSize(QSize(self._end_icon_w, self._end_icon_w))
        # Animación de rebote: no se reduce, sólo se agranda y vuelve
        anim = QPropertyAnimation(self.lock_btn, b"iconSize", self)
        anim.setDuration(180)
        # Inicia y finaliza en el tamaño por defecto
        anim.setStartValue(QSize(self._end_icon_w, self._end_icon_w))
        # A mitad de animación se agranda para dar sensación de clic
        anim.setKeyValueAt(0.5, QSize(self._end_icon_w + 6, self._end_icon_w + 6))
        # Termina en el tamaño por defecto
        anim.setEndValue(QSize(self._end_icon_w, self._end_icon_w))
        anim.start()
        # Mantener referencia para evitar garbage collection prematuro
        self._eye_anim = anim

    # ---------- Etiqueta flotante ----------
    def _update_label_state(self):
        has_text = bool(self.line_edit.text())
        target_up = self._focused or has_text
        dest = self._up_pos if target_up else self._down_pos
        new_colour = self._active_colour if target_up else self._inactive_colour
        if self._anim:
            self._anim.stop(); self._anim = None
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

    # ---------- Layout ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width(); h = self.height()
        label_h = self.label.sizeHint().height()
        # Ajustar la altura de línea para que los iconos más grandes no se corten. Si el ancho del icono final supera 28px,
        # se añade un margen adicional de 4px para que quepa cómodamente.
        line_h = max(28, getattr(self, '_end_icon_w', 26) + 4)
        line_y = max(0, h - line_h - 2)
        self.line_edit.setGeometry(0, line_y, w, line_h)
        # Posiciones etiqueta
        up_y = 2
        down_y = line_y + max(0, (line_h - label_h) // 2)
        if down_y <= up_y:
            down_y = up_y + 12
        self._up_pos = QPoint(0, up_y)
        self._down_pos = QPoint(0, down_y)
        self.label.resize(w, label_h)
        # Icono izquierdo
        if self.left_icon:
            ix = 2
            iy = line_y + (line_h - self.left_icon.height()) // 2
            self.left_icon.move(ix, iy)
            self.left_icon.show()
        # Botones/íconos del extremo derecho: candado al borde, luego icono derecho
        anchor_right = w - getattr(self, '_end_margin', 6)
        iy = line_y + (line_h - getattr(self, '_end_icon_w', 26)) // 2
        right_x = anchor_right
        def _place_end_widget(wdg):
            nonlocal right_x
            if not wdg:
                return
            size = getattr(self, '_end_icon_w', 26)
            wdg.resize(size, size)
            right_x -= size
            wdg.move(right_x, iy)
            wdg.show()
            right_x -= getattr(self, '_gap_between_end_icons', 6)
        _place_end_widget(getattr(self, 'lock_btn', None) if getattr(self, '_is_password', False) else None)
        _place_end_widget(getattr(self, 'right_icon', None) if getattr(self, '_has_right_icon', False) else None)
        # actualizar márgenes de texto
        self.line_edit.setTextMargins(self._left_icon_w, 0, getattr(self, '_right_pad', 0), 0)
        # colocar etiqueta conforme al estado actual
        initial = self._up_pos if (self._focused or bool(self.line_edit.text())) else self._down_pos
        self.label.move(initial)
        self._update_label_state()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        has_text = bool(self.line_edit.text())
        colour = self._active_colour if (self._focused or has_text) else self._inactive_colour
        pen = QPen(QColor(colour)); pen.setWidth(2)
        p.setPen(pen)
        y = self.height() - 1
        p.drawLine(0, y, self.width(), y)
        p.end()

    # ---------- Proxies ----------
    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str):
        self.line_edit.setText(text)

    def setEchoMode(self, mode):
        self.line_edit.setEchoMode(mode)


class TriangularBackground(QFrame):
    """
    A custom QFrame that draws a polygonal background with a diagonal edge
    separating a coloured gradient from the dark panel.  The orientation
    determines whether the gradient appears on the left or right side.  The
    shape is controlled by two ratios which specify the width of the
    gradient at the top and bottom.  A border is drawn along the edges of
    the gradient region to match the application's accent colour.

    Parameters
    ----------
    orientation : str
        Either ``'left'`` or ``'right'``.  When ``'left'``, the gradient
        region occupies the left side of the frame; when ``'right'``, it
        occupies the right side.
    t_ratio : float
        The relative width of the gradient region at the top of the frame.
        Must be between 0 and 1.  Defaults to 0.7.
    b_ratio : float
        The relative width of the gradient region at the bottom of the frame.
        Must be between 0 and 1.  Defaults to 0.3.
    """

    def __init__(self, orientation: str = 'left', t_ratio: float = 0.7, b_ratio: float = 0.3, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.t_ratio = t_ratio
        self.b_ratio = b_ratio
        self.setStyleSheet("background:transparent;")

    # Expose t_ratio and b_ratio as animatable properties.  Defining
    # getters and setters along with ``pyqtProperty`` allows
    # ``QPropertyAnimation`` to smoothly transition these values.  Each setter
    # triggers a repaint so the diagonal updates in real time.
    def getTRatio(self) -> float:
        return self.t_ratio

    def setTRatio(self, value: float):
        self.t_ratio = value
        self.update()

    def getBRatio(self) -> float:
        return self.b_ratio

    def setBRatio(self, value: float):
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
        # Fill the gradient region
        path = QPainterPath()
        if self.orientation == 'left':
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
        # Draw only the diagonal line to avoid conflicting with the global border
        pen = QPen(QColor(c.CLR_TITLE))
        pen.setWidth(2)
        painter.setPen(pen)
        if self.orientation == 'left':
            painter.drawLine(int(x_top), 0, int(x_bottom), h)
        else:
            painter.drawLine(int(x_top), 0, int(x_bottom), h)
        painter.end()


class LoginDialog(QDialog):
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
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

        duration = 600  # milliseconds

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

        duration = 600  # milliseconds

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
