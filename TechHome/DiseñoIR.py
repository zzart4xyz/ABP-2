"""Diálogos de autenticación para TechHome."""

from __future__ import annotations

from typing import Callable, Optional

import constants as c

from PyQt5.QtCore import Qt, QEvent, QPoint, QPropertyAnimation, QSize
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from dialogs import BaseFormDialog

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


def show_message(parent, title: str, text: str) -> None:
    """Mostrar un mensaje informativo simple."""

    QMessageBox.information(parent, title, text)


class FloatingLabelInput(QFrame):
    """
    Input con etiqueta flotante + iconos:
      • Etiqueta flota al enfocar o tener texto.
      • Icono izquierdo opcional (por ejemplo Usuario.svg).
      • Para contraseñas: botón de candado que alterna mostrar/ocultar con una animación
        y cambia entre Cerrado.svg ↔ Habierto.svg.
    """
    def __init__(self, text: str = "", is_password: bool = False, parent=None, label_px: int = 14, left_icon_name: str | None = None, right_icon_name: str | None = None):
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
class _LoginContent(QFrame):
    """Contenido reutilizable para el diálogo de inicio de sesión."""

    def __init__(self, mapping, parent=None):
        super().__init__(parent)
        self._mapping = mapping or {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel(self._mapping.get("Iniciar Sesión", "Iniciar Sesión"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 26px '{c.FONT_FAM}';")
        layout.addWidget(title)

        subtitle = QLabel(self._mapping.get(
            "Introduce tus credenciales para continuar.",
            "Enter your credentials to continue.",
        ))
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:500 13px '{c.FONT_FAM}';")
        layout.addWidget(subtitle)

        self.user_input = FloatingLabelInput(
            self._mapping.get("Usuario", "Usuario"),
            label_px=16,
            right_icon_name="Usuario.svg",
        )
        self.user_input.setFixedHeight(64)
        layout.addWidget(self.user_input)

        self.password_input = FloatingLabelInput(
            self._mapping.get("Contraseña", "Contraseña"),
            is_password=True,
            label_px=16,
        )
        self.password_input.setFixedHeight(64)
        layout.addWidget(self.password_input)

        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        self.feedback.setAlignment(Qt.AlignCenter)
        self.feedback.hide()
        layout.addWidget(self.feedback)

        layout.addStretch(1)

        self.register_button = QPushButton(self._mapping.get(
            "¿No Tienes Una Cuenta? Regístrate",
            "¿No Tienes Una Cuenta? Regístrate",
        ))
        self.register_button.setCursor(Qt.PointingHandCursor)
        self.register_button.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; color:{c.CLR_TITLE}; font:600 14px '{c.FONT_FAM}'; }}\n"
            f"QPushButton:hover {{ color:{c.CLR_TEXT_IDLE}; }}"
        )
        layout.addWidget(self.register_button, alignment=Qt.AlignCenter)

    def show_feedback(self, text: str, *, error: bool = True) -> None:
        if not text:
            self.feedback.hide()
            self.feedback.setText("")
            return
        colour = "#ff6b6b" if error else c.CLR_TITLE
        self.feedback.setStyleSheet(f"color:{colour}; font:600 13px '{c.FONT_FAM}';")
        self.feedback.setText(text)
        self.feedback.show()

    def clear_password(self) -> None:
        self.password_input.setText("")

    def focus_username(self) -> None:
        self.user_input.line_edit.setFocus()

    def focus_password(self) -> None:
        self.password_input.line_edit.setFocus()


class _RegisterContent(QFrame):
    """Contenido del diálogo de registro con estilo consistente."""

    def __init__(self, mapping, parent=None):
        super().__init__(parent)
        self._mapping = mapping or {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel(self._mapping.get("Registrarse", "Registrarse"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 26px '{c.FONT_FAM}';")
        layout.addWidget(title)

        helper = QLabel(self._mapping.get(
            "Crea tu cuenta para comenzar a personalizar TechHome.",
            "Create your account to start personalising TechHome.",
        ))
        helper.setWordWrap(True)
        helper.setAlignment(Qt.AlignCenter)
        helper.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:500 13px '{c.FONT_FAM}';")
        layout.addWidget(helper)

        self.user_input = FloatingLabelInput(
            self._mapping.get("Usuario", "Usuario"),
            label_px=16,
            right_icon_name="Usuario.svg",
        )
        self.user_input.setFixedHeight(64)
        layout.addWidget(self.user_input)

        self.password_input = FloatingLabelInput(
            self._mapping.get("Contraseña", "Contraseña"),
            is_password=True,
            label_px=16,
        )
        self.password_input.setFixedHeight(64)
        layout.addWidget(self.password_input)

        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        self.feedback.setAlignment(Qt.AlignCenter)
        self.feedback.hide()
        layout.addWidget(self.feedback)

        layout.addStretch(1)

    def show_feedback(self, text: str, *, error: bool = True) -> None:
        if not text:
            self.feedback.hide()
            self.feedback.setText("")
            return
        colour = "#ff6b6b" if error else c.CLR_TITLE
        self.feedback.setStyleSheet(f"color:{colour}; font:600 13px '{c.FONT_FAM}';")
        self.feedback.setText(text)
        self.feedback.show()

    def clear(self) -> None:
        self.user_input.setText("")
        self.password_input.setText("")


class LoginDialog(BaseFormDialog):
    """Diálogo de inicio de sesión con el mismo marco que otras ventanas."""

    def __init__(
        self,
        parent=None,
        *,
        init_callback: Optional[InitCallback] = None,
        authenticate_callback: Optional[AuthCallback] = None,
        create_user_callback: Optional[CreateUserCallback] = None,
        log_action_callback: Optional[LogActionCallback] = None,
    ):
        self.lang = getattr(parent, 'lang', 'es') if parent else 'es'
        self.mapping = c.TRANSLATIONS_EN if self.lang == 'en' else {}
        self._init_callback: InitCallback = init_callback or (lambda: None)
        self._authenticate: AuthCallback = authenticate_callback or (lambda _u, _p: False)
        self._create_user: CreateUserCallback = create_user_callback or (lambda _u, _p: False)
        self._log_action: Optional[LogActionCallback] = log_action_callback
        try:
            self._init_callback()
        except Exception:
            pass

        self.current_user: str | None = None
        self._content = _LoginContent(self.mapping, parent=parent)

        super().__init__(
            self._t("Iniciar Sesión", "Log In"),
            self._content,
            self._t("Entrar", "Login"),
            cancel_text=self._t("Cancelar", "Cancel"),
            size=(460, 420),
            parent=parent,
        )

        try:
            self.btn_ok.clicked.disconnect()
        except Exception:
            pass
        self.btn_ok.clicked.connect(self._on_login_action)
        self.btn_ok.setDefault(True)

        self._content.register_button.clicked.connect(self._open_register_dialog)
        self._content.user_input.line_edit.returnPressed.connect(self._on_login_action)
        self._content.password_input.line_edit.returnPressed.connect(self._on_login_action)
        self._content.focus_username()

    def _t(self, text: str, fallback: str | None = None) -> str:
        if self.mapping:
            return self.mapping.get(text, fallback or text)
        return text

    def _on_login_action(self) -> None:
        username = self._content.user_input.text().strip()
        password = self._content.password_input.text()
        if not username or not password:
            self._content.show_feedback(
                self._t(
                    "Debes introducir un usuario y una contraseña.",
                    "You must enter a username and a password.",
                ),
                error=True,
            )
            return
        try:
            authenticated = self._authenticate(username, password)
        except Exception:
            authenticated = False
        if authenticated:
            self.current_user = username
            self._content.show_feedback("")
            self.accept()
            return
        self._content.show_feedback(
            self._t(
                "Usuario o contraseña incorrectos.",
                "Incorrect username or password.",
            ),
            error=True,
        )

    def _open_register_dialog(self) -> None:
        dialog = RegisterDialog(
            mapping=self.mapping,
            parent=self,
            create_user_callback=self._create_user,
            log_action_callback=self._log_action,
        )
        if dialog.exec_() == dialog.Accepted and dialog.registered_user:
            username = dialog.registered_user
            self._content.user_input.setText(username)
            self._content.clear_password()
            self._content.show_feedback(
                self._t(
                    "Cuenta creada correctamente. Ahora puedes iniciar sesión.",
                    "Account created successfully. You can now log in.",
                ),
                error=False,
            )
            self._content.focus_password()


class RegisterDialog(BaseFormDialog):
    """Ventana de registro que reutiliza el marco común de diálogos."""

    def __init__(
        self,
        *,
        mapping,
        parent=None,
        create_user_callback: Optional[CreateUserCallback] = None,
        log_action_callback: Optional[LogActionCallback] = None,
    ):
        self.mapping = mapping or {}
        self._create_user: CreateUserCallback = create_user_callback or (lambda _u, _p: False)
        self._log_action: Optional[LogActionCallback] = log_action_callback
        self._content = _RegisterContent(self.mapping, parent=parent)
        super().__init__(
            self._t("Registrarse", "Register"),
            self._content,
            self._t("Registrar", "Register"),
            cancel_text=self._t("Cancelar", "Cancel"),
            size=(460, 420),
            parent=parent,
        )

        try:
            self.btn_ok.clicked.disconnect()
        except Exception:
            pass
        self.btn_ok.clicked.connect(self._on_register_action)
        self.btn_ok.setDefault(True)

        self._content.user_input.line_edit.returnPressed.connect(self._on_register_action)
        self._content.password_input.line_edit.returnPressed.connect(self._on_register_action)

        self.registered_user: str | None = None

    def _t(self, text: str, fallback: str | None = None) -> str:
        if self.mapping:
            return self.mapping.get(text, fallback or text)
        return text

    def _on_register_action(self) -> None:
        username = self._content.user_input.text().strip()
        password = self._content.password_input.text()
        if not username or not password:
            self._content.show_feedback(
                self._t(
                    "Debes introducir un nombre de usuario y una contraseña.",
                    "You must enter a username and a password.",
                ),
                error=True,
            )
            return
        try:
            created = self._create_user(username, password)
        except Exception:
            created = False
        if not created:
            self._content.show_feedback(
                self._t(
                    "El nombre de usuario ya existe.",
                    "The username already exists.",
                ),
                error=True,
            )
            return

        self.registered_user = username
        if self._log_action is not None:
            try:
                self._log_action(username, "Registro de usuario")
            except Exception:
                pass

        self._content.show_feedback("")
        show_message(
            self,
            self._t("Éxito", "Success"),
            self._t(
                "Cuenta creada correctamente. Ahora puedes iniciar sesión.",
                "Account created successfully. You can now log in.",
            ),
        )
        self.accept()
