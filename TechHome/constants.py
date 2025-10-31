import os
import random
import csv
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QDate, QSize
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QGraphicsDropShadowEffect

"""
This module centralizes all constants, theme definitions, translation
dictionaries and helper functions used throughout the TechHome
application.  Splitting these elements into a dedicated module makes
them reusable across different parts of the codebase while keeping
configuration in one place.  The original values and behaviours are
preserved; importing modules should refer to attributes of this module
so that runtime changes to the theme take immediate effect.
"""

# ---------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------

THEMES = {
    "dark": {
        "CLR_BG": "#07101B",
        "CLR_PANEL": "#0D1A26",
        "CLR_SURFACE": "#15202B",
        "CLR_HOVER": "#11253B",
        "CLR_TITLE": "#1EBEFF",
        "CLR_TEXT_IDLE": "#B0CFEF",
        "CLR_ITEM_ACT": "#16324C",
        "CLR_HEADER_BG": "#0E2233",
        "CLR_HEADER_TEXT": "#1EBEFF",
        "CLR_TRACK": "#1A2B3C",
        "CLR_PLACEHOLDER": "#6A86A6",
        "SHADOW_ALPHA": 200,
    },
    "light": {
        "CLR_BG": "#F0F0F0",
        "CLR_PANEL": "#FFFFFF",
        "CLR_SURFACE": "#FFFFFF",
        "CLR_HOVER": "#F0F0F0",
        "CLR_TITLE": "#0078D7",
        "CLR_TEXT_IDLE": "#000000",
        "CLR_ITEM_ACT": "#E0E0E0",
        "CLR_HEADER_BG": "#D0D0D0",
        "CLR_HEADER_TEXT": "#0078D7",
        "CLR_TRACK": "#C0C0C0",
        "CLR_PLACEHOLDER": "#808080",
        "SHADOW_ALPHA": 80,
    },
}

# Default values for theme-dependent globals.  They are overwritten by
# calling ``set_theme_constants`` below but explicitly declaring them
# here helps static analysers and keeps import-time values defined.
CLR_BG = THEMES["dark"]["CLR_BG"]
CLR_PANEL = THEMES["dark"]["CLR_PANEL"]
CLR_SURFACE = THEMES["dark"]["CLR_SURFACE"]
CLR_HOVER = THEMES["dark"]["CLR_HOVER"]
CLR_TITLE = THEMES["dark"]["CLR_TITLE"]
CLR_TEXT_IDLE = THEMES["dark"]["CLR_TEXT_IDLE"]
CLR_ITEM_ACT = THEMES["dark"]["CLR_ITEM_ACT"]
CLR_HEADER_BG = THEMES["dark"]["CLR_HEADER_BG"]
CLR_HEADER_TEXT = THEMES["dark"]["CLR_HEADER_TEXT"]
CLR_TRACK = THEMES["dark"]["CLR_TRACK"]
CLR_PLACEHOLDER = THEMES["dark"]["CLR_PLACEHOLDER"]
SHADOW_ALPHA = THEMES["dark"]["SHADOW_ALPHA"]
CURRENT_THEME = "dark"


def _coerce_color(value: str) -> QColor:
    """Return a ``QColor`` from ``value`` safeguarding invalid inputs."""

    color = QColor(value)
    if not color.isValid():
        color = QColor("#000000")
    return color


def tone(color: str, factor: float) -> str:
    """Lighten (``factor`` > 0) or darken (``factor`` < 0) ``color``."""

    qc = _coerce_color(color)
    factor = max(-0.95, min(0.95, factor))
    if factor >= 0:
        return qc.lighter(int(100 + factor * 100)).name()
    return qc.darker(int(100 + (-factor) * 100)).name()


def with_alpha(color: str, alpha: float) -> str:
    """Return ``color`` expressed as an ``rgba`` string with ``alpha``."""

    qc = _coerce_color(color)
    alpha = max(0.0, min(1.0, alpha))
    return f"rgba({qc.red()}, {qc.green()}, {qc.blue()}, {int(alpha * 255)})"


def card_style(radius=None) -> str:
    """Gradient background used for the main content shell."""

    if radius is None:
        radius = globals().get("FRAME_RAD", 5)
    top = tone(CLR_BG, 0.18)
    mid = tone(CLR_BG, 0.04)
    bottom = tone(CLR_BG, -0.18)
    border = with_alpha("#FFFFFF", 0.08)
    return (
        "background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
        f" stop:0 {top}, stop:0.55 {mid}, stop:1 {bottom});"
        f"border-radius:{radius}px;"
        f"border:1px solid {border};"
    )


def side_panel_style(radius=None) -> str:
    """Gradient styling for the navigation side panel."""

    if radius is None:
        radius = globals().get("FRAME_RAD", 5)
    top = tone(CLR_PANEL, 0.22)
    mid = tone(CLR_PANEL, 0.08)
    bottom = tone(CLR_PANEL, -0.12)
    border = with_alpha("#FFFFFF", 0.05)
    return (
        "background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
        f" stop:0 {top}, stop:0.45 {mid}, stop:1 {bottom});"
        f"border-radius:{radius}px;"
        f"border:1px solid {border};"
    )


def content_panel_style(radius=None) -> str:
    """Styling for stacked pages container."""

    if radius is None:
        radius = globals().get("FRAME_RAD", 5)
    top = tone(CLR_SURFACE, 0.14)
    mid = tone(CLR_SURFACE, 0.02)
    bottom = tone(CLR_SURFACE, -0.08)
    border = with_alpha("#FFFFFF", 0.06)
    return (
        "background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
        f" stop:0 {top}, stop:0.55 {mid}, stop:1 {bottom});"
        f"border-radius:{radius}px;"
        f"border:1px solid {border};"
    )


def nav_button_style() -> str:
    """Shared stylesheet for navigation buttons."""

    hover_bg = with_alpha(CLR_TITLE, 0.18)
    checked_border = with_alpha(CLR_TITLE, 0.28)
    gradient_a = with_alpha(CLR_TITLE, 0.28)
    gradient_b = with_alpha(CLR_TITLE, 0.08)
    return (
        "QPushButton {"
        f" color:{CLR_TEXT_IDLE};"
        " background:transparent;"
        " border:none;"
        " padding:10px 18px;"
        " border-radius:10px;"
        f" font:700 18px '{FONT_FAM}';"
        " text-align:left;"
        "}"
        "QPushButton:hover {"
        f" background:{hover_bg};"
        f" color:{CLR_TITLE};"
        "}"
        "QPushButton:checked {"
        f" background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {gradient_a}, stop:1 {gradient_b});"
        f" color:{CLR_TITLE};"
        f" border:1px solid {checked_border};"
        "}"
    )


def build_global_stylesheet() -> str:
    """Compose the shared application stylesheet."""

    radius = globals().get("FRAME_RAD", 5)
    handle = with_alpha(CLR_TITLE, 0.7)
    handle_hover = with_alpha(CLR_TITLE, 0.9)
    track = with_alpha(CLR_TRACK, 0.35)
    panel_glow = tone(CLR_PANEL, 0.25)
    border = with_alpha(CLR_TITLE, 0.55)
    field_bg = tone(CLR_SURFACE, 0.05)
    field_border = with_alpha(CLR_TITLE, 0.25)
    return f"""
        QMainWindow {{
            background: transparent;
        }}
        QWidget#card {{
            background: transparent;
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 12px;
            margin: 8px 4px 8px 4px;
        }}
        QScrollBar::groove:vertical {{
            background: {track};
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background: {handle};
            border-radius: 6px;
            min-height: 36px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {handle_hover};
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 12px;
            margin: 4px 8px 4px 8px;
        }}
        QScrollBar::groove:horizontal {{
            background: {track};
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background: {handle};
            border-radius: 6px;
            min-width: 36px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {handle_hover};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
            height: 0px;
        }}
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
        QToolTip {{
            background: {panel_glow};
            color: {CLR_TEXT_IDLE};
            border: 1px solid {border};
            padding: 6px 10px;
            border-radius: 6px;
            font: 600 11px '{FONT_FAM}';
        }}
        QComboBox,
        QSpinBox,
        QDoubleSpinBox,
        QDateEdit,
        QTimeEdit,
        QDateTimeEdit {{
            background: {field_bg};
            border: 1px solid {field_border};
            border-radius: {radius}px;
            color: {CLR_TEXT_IDLE};
            padding: 6px 10px;
            font: 500 14px '{FONT_FAM}';
        }}
        QComboBox::drop-down {{
            width: 22px;
            border: none;
            background: transparent;
        }}
        QComboBox QAbstractItemView {{
            background: {tone(CLR_SURFACE, 0.1)};
            border-radius: {radius}px;
            border: 1px solid {field_border};
            selection-background-color: {with_alpha(CLR_TITLE, 0.35)};
            selection-color: {CLR_TEXT_IDLE};
        }}
        QFrame[variant="surface"] {{
            background: {tone(CLR_SURFACE, 0.08)};
            border-radius: {radius}px;
            border: 1px solid {with_alpha('#FFFFFF', 0.04)};
        }}
    """

def set_theme_constants(theme: str):
    """
    Update the module-level colour constants to values from the given theme.

    The ``theme`` argument should be one of the keys in ``THEMES``.
    Updating these globals will cause all widgets that reference them via
    this module (i.e. ``constants.CLR_BG``) to reflect the new colour
    scheme immediately.  If an unknown theme is supplied, the dark
    theme will be used as a fallback.
    """
    palette = THEMES.get(theme, THEMES["dark"])
    globals().update(palette)
    globals()["CURRENT_THEME"] = theme
    globals()["GLOBAL_STYLESHEET"] = build_global_stylesheet()

# Initialise with dark theme defaults
set_theme_constants("dark")

# ---------------------------------------------------------------------
# Application constants
# ---------------------------------------------------------------------

# Layout constants
PANEL_W              = 260
FRAME_RAD            = 5
FONT_FAM             = "Segoe UI, Inter, sans-serif"
MIN_GAUGE            = 680
GAUGE_CONTENT_FACTOR = 0.50
SHIFT_FACTOR         = 0.10

# Paths relative to this file
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
#
# The application expects an ``Icons N`` folder containing the various
# device icons.  In the original code this directory lived alongside
# the source files.  To support external icon locations (for example
# on a user's Windows machine) the ``ICON_DIR`` constant is now set to
# an absolute path pointing at the directory provided by the user.  If
# that path does not exist on the current platform, the code falls
# back to the local ``Icons N`` directory relative to ``constants.py``.
_user_icon_path = r"C:/Users/zzart4.xyz/Desktop/TechHome/Icons N"
_default_icon_dir = os.path.join(ROOT_DIR, "Icons N")

# Search order: prefer the user-provided directory when it contains the
# renamed (Spanish) icons, otherwise fall back to the packaged assets.
_icon_search_paths: list[str] = []
if os.path.isdir(_user_icon_path):
    _icon_search_paths.append(_user_icon_path)
_icon_search_paths.append(_default_icon_dir)

def _has_localized_icons(path: str) -> bool:
    """Return ``True`` if the directory contains the renamed SVG assets."""

    required = ("Inicio.svg", "Dispositivos.svg", "Luz.svg")
    return all(os.path.isfile(os.path.join(path, name)) for name in required)


ICON_DIR = next((path for path in _icon_search_paths if _has_localized_icons(path)), _default_icon_dir)
ICON_SEARCH_PATHS = tuple(dict.fromkeys(_icon_search_paths))


def resolve_icon_path(name: str) -> str | None:
    """Return the absolute path to an icon, searching known directories."""

    for base in ICON_SEARCH_PATHS:
        candidate = os.path.join(base, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def load_icon_pixmap(name: str, size: QSize) -> QPixmap:
    """Load ``name`` as a pixmap of ``size`` searching known icon folders."""

    try:
        icon_path = resolve_icon_path(name)
        if icon_path:
            ico = QIcon(icon_path)
            pix = ico.pixmap(size)
            if not pix.isNull():
                return pix
    except Exception:
        pass
    base_dir = None
    try:
        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "node_modules",
            "@fortawesome",
            "fontawesome-free",
            "svgs",
            "solid",
        )
        candidate = os.path.join(base_dir, name)
        if os.path.isfile(candidate):
            ico = QIcon(candidate)
            pix = ico.pixmap(size)
            if not pix.isNull():
                return pix
    except Exception:
        pass
    fallback_candidates = []
    if base_dir is not None:
        fallback_candidates.append(os.path.join(base_dir, "circle-info.svg"))
        fallback_candidates.append(os.path.join(base_dir, "info.svg"))
    info_path = resolve_icon_path("Información.svg")
    if info_path:
        fallback_candidates.append(info_path)
    for fb in fallback_candidates:
        if fb and os.path.isfile(fb):
            try:
                ico = QIcon(fb)
                pix = ico.pixmap(size)
                if not pix.isNull():
                    return pix
            except Exception:
                continue
    return QPixmap(size)


def tint_pixmap(pixmap: QPixmap, color: QColor) -> QPixmap:
    """Return a tinted copy of ``pixmap`` using ``color`` as the overlay."""

    if pixmap.isNull():
        return pixmap
    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.transparent)
    painter = QPainter(tinted)
    painter.setCompositionMode(QPainter.CompositionMode_Source)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), color)
    painter.end()
    return tinted

# Path to the logo used in the splash screen.  By default this points to
# ``Logos/Logo.png`` relative to the project root.  Users may provide a
# custom logo (e.g., "Isotipo TechHome.svg") via their TechHome folder.  To
# accommodate this, we check for a user‑specified logo in the known
# locations.  If found, that file will be used; otherwise we fall back to
# the packaged default.

# First, allow the user to specify a custom logo file in their local
# TechHome folder on Windows.  If that file exists on the current system,
# it will be used.
_user_logo_path = r"C:/Users/zzart4.xyz/Desktop/TechHome/Logos/Isotipo TechHome.svg"
_default_logo = os.path.join(ROOT_DIR, "Logos", "Logo.png")
_packaged_iso_logo = os.path.join(ROOT_DIR, "Isotipo TechHome.svg")

if os.path.isfile(_user_logo_path):
    LOGO_PATH = _user_logo_path
elif os.path.isfile(_packaged_iso_logo):
    # If the custom logo has been packaged alongside constants.py, use it
    LOGO_PATH = _packaged_iso_logo
else:
    # Fallback to the default packaged logo
    LOGO_PATH = _default_logo
HEALTH_CSV_PATH     = os.path.join(ROOT_DIR, "health.csv")

GRAD_STOPS           = [
    (0.00, "#3ac1ff"), (0.25, "#1a8dff"),
    (0.50, "#006cff"), (0.75, "#1a8dff"),
    (1.00, "#3ac1ff"),
]

MAX_NOTIFICATIONS    = 100
HOME_RECENT_COUNT    = 5
CAL_CELL_SIZE        = 36
CAL_HEADER_HEIGHT    = 32
CAL_BTN_WIDTH        = 100

# ---------------------------------------------------------------------
# Translation dictionaries
# ---------------------------------------------------------------------

TRANSLATIONS_EN = {
    "Inicio": "Home",
    "Dispositivos": "Devices",
    "Más": "More",
    "Salud": "Health",
    "Configuración": "Settings",
    "¡Hola, Usuario!": "Hello, User!",
    "Notificaciones": "Notifications",
    "Resumen De Métricas": "Metrics Summary",
    "Accesos Rápidos": "Quick Access",
    "Dispositivos\nActivos": "Active\nDevices",
    "Temp.\nInterior": "Indoor\nTemp",
    "Uso De\nEnergía": "Energy\nUsage",
    "Uso De\nAgua": "Water\nUsage",
    "Historial De Salud": "Health History",
    "Cámaras": "Cameras",
    "Otros": "Others",
    "Grupos": "Groups",
    "Grupo Actual:": "Current Group:",
    "Grupo Nuevo": "New Group",
    "Buscar": "Search",
    "De La A A La Z": "A to Z",
    "De La Z A La A": "Z to A",
    "Crear Lista": "Create List",
    "Nueva Lista": "New List",
    "Crear": "Create",
    "Añadir Elemento": "Add Item",
    "Listas Y Notas": "Lists And Notes",
    "Listas": "Lists",
    "Notas": "Notes",
    "Alarmas Y Timers": "Alarms And Timers",
    "Calendario": "Calendar",
    "Recordatorios": "Reminders",
    "Notificaciones Emergentes": "Popup Notifications",
    "Tema:": "Theme:",
    "Idioma:": "Language:",
    "Tiempo:": "Time:",
    "Oscuro": "Dark",
    "Claro": "Light",
    "Español": "Spanish",
    "Inglés": "English",
    "24 hr": "24 hr",
    "12 hr": "12 hr",
    "Eliminar Seleccionado": "Delete Selected",
    "Alarmas": "Alarms",
    "Timers": "Timers",
    "Etiqueta": "Label",
    "Etiqueta De Alarma": "Alarm Label",
    "Etiqueta Del Timer": "Timer Label",
    "Fecha Y Hora": "Date and Time",
    "Mensaje": "Message",
    "Iniciar Sesión": "Log In",
    "Usuario": "Username",
    "Contraseña": "Password",
    "Confirmar Contraseña": "Confirm Password",
    "Recuérdame": "Remember Me",
    "Olvidé mi contraseña": "Forgot Password",
    "¿No Tienes Una Cuenta? Regístrate": "Don't Have An Account? Register",
    "Registrar": "Register",
    "Registrarse": "Register",
    "¿Ya Tienes Una Cuenta? Inicia Sesión": "Already Have An Account? Log In",
    "Entrar": "Login",
    "Nuevo Elemento": "New Element",
    "Añadir": "Add",
    " Añadir": " Add",
    "Contenido De La Nota": "Note Content",
    "Contenido de la nota": "Note Content",
    "Guardar": "Save",
    "Nombre De La Lista": "List Name",
    "Nombre Del Elemento": "Item Name",
    "Agregar Nota": "Add Note",
    "Agregar nota": "Add Note",
    "Texto Del Recordatorio": "Reminder Text",
    "Vista Cámara": "Camera View",
    "Vista cámara": "Camera View",
    "Hora": "Time",
    "Fecha": "Date",
    "Restante": "Remaining",
    "Siguiente": "Next",
    "Iniciar": "Start",
    "Puerta Principal Abierta": "Front Door Open",
    "Luces Sala Encendidas": "Living Room Lights On",
    "Alerta De Temperatura": "Temperature Alert",
    "Sensor De Movimiento Detectado": "Motion Sensor Detected",
    "Ventana Cocina Abierta": "Kitchen Window Open",
    "Cancelar": "Cancel",
    "Todo": "All",
    "Dormitorio": "Bedroom",
    "Baño": "Bathroom",
    "Sala": "Living Room",
    "Comedor": "Dining Room",
    "Cocina": "Kitchen",
    "Luz Dormitorio": "Bedroom Light",
    "Lámpara Noche": "Night Lamp",
    "Ventilador Dormitorio": "Bedroom Fan",
    "Aire Acondicionado Dormitorio": "Bedroom Air Conditioner",
    "Cortinas Dormitorio": "Bedroom Curtains",
    "Enchufe Cama": "Bed Outlet",
    "Luz Baño": "Bathroom Light",
    "Extractor": "Extractor",
    "Calentador Agua": "Water Heater",
    "Espejo Iluminado": "Lighted Mirror",
    "Ducha Automática": "Automatic Shower",
    "Enchufe Afeitadora": "Shaver Outlet",
    "Luces Sala": "Living Room Lights",
    "Televisor": "Television",
    "Consola Juegos": "Game Console",
    "Equipo Sonido": "Sound System",
    "Ventilador Sala": "Living Room Fan",
    "Enchufe Ventana": "Window Outlet",
    "Luz Comedor": "Dining Light",
    "Calefactor Comedor": "Dining Heater",
    "Enchufe Comedor": "Dining Outlet",
    "Luz Barra": "Bar Light",
    "Persianas Comedor": "Dining Blinds",
    "Ventilador Techo": "Ceiling Fan",
    "Refrigerador": "Refrigerator",
    "Horno": "Oven",
    "Microondas": "Microwave",
    "Lavavajillas": "Dishwasher",
    "Licuadora": "Blender",
    "Cafetera": "Coffee Maker",
    "Compra": "Shopping",
    "Tareas": "Tasks",
    "Nuevo Dispositivo": "New Device",
    "Apagado": "Off",
    "Encendido": "On",
    "Recordatorio Añadido": "Reminder Added",
    "Recordatorio Eliminado": "Reminder Deleted",
    "Alarma Añadida": "Alarm Added",
    "Alarma Eliminada": "Alarm Deleted",
    "Timer Añadido": "Timer Added",
    "Timer Eliminado": "Timer Deleted",
    "Diagnóstico Registrado": "Health Check Saved",
    # Account section label
    # Section labels for the information/about page.  "Información"
    # corresponds to the page formerly known as "Cuenta" and is
    # translated as "Information".  Retain the original "Cuenta" to
    # translate any remaining occurrences of "Cuenta" in other parts
    # of the application.
    "Cuenta": "Account",
    "Información": "Information",
    "Sesión": "Session",
    # Update version strings for release 1.0
    "Versión 1.0": "Version 1.0",
    "TechHome v1.0": "TechHome v1.0",

    # Attribution of the development team
    "Creado por el equipo VitalTech": "Created by the VitalTech team",
}

# Reverse mapping to convert back to Spanish
TRANSLATIONS_ES = {v: k for k, v in TRANSLATIONS_EN.items()}

# ---------------------------------------------------------------------
# Style helper functions
# ---------------------------------------------------------------------

def input_style(cls: str = "QLineEdit", bg: str = None, pad: int = 6) -> str:
    """
    Return a standard stylesheet for text inputs.

    :param cls: The Qt class name (e.g. ``QLineEdit`` or ``QTextEdit``).
    :param bg:  Background colour for the input; defaults to ``CLR_SURFACE``.
    :param pad: Padding in pixels inside the input.
    :returns: A stylesheet string with appropriate colours.
    """
    if bg is None:
        bg = CLR_SURFACE
    return (
        f"""
        {cls} {{
            background:{bg};
            color:{CLR_TEXT_IDLE};
            /* Note: qproperty-placeholderTextColor is not supported on
               all Qt styles (e.g., Windows).  We specify the
               placeholder colour via the ::placeholder pseudo-state
               instead to avoid warnings. */
            font:500 14px '{FONT_FAM}';
            padding:{pad}px;
            border:1px solid {CLR_TRACK};
            border-radius:5px;
        }}
        {cls}:focus {{
            border:2px solid {CLR_TITLE};
        }}
        {cls}::placeholder {{
            color:{CLR_PLACEHOLDER};
        }}
    """
    )

def icon(name: str) -> QIcon:
    """
    Load an icon from the ``Icons N`` directory.  The argument should be
    the filename of the icon (for example ``'Inicio.svg'``).
    """
    path = resolve_icon_path(name)
    return QIcon(path) if path else QIcon()

def pixmap(name: str) -> QPixmap:
    """Convenience wrapper for loading a QPixmap from the icon directory."""
    path = resolve_icon_path(name)
    return QPixmap(path) if path else QPixmap()

def button_style(color: str = None, padding: str = "0px") -> str:
    """
    Build a stylesheet for ``QPushButton`` objects.

    :param color: Foreground (text) colour; defaults to ``CLR_TEXT_IDLE``.
    :param padding: CSS padding specification (e.g. ``'4px 8px'``).
    """
    if color is None:
        color = CLR_TEXT_IDLE
    return f"""
        QPushButton {{
            background:transparent;
            border:2px solid {CLR_TITLE};
            border-radius:5px;
            font:600 14px '{FONT_FAM}';
            color:{color};
            padding:{padding};
        }}
        QPushButton:hover {{
            background:{CLR_TITLE};
            color:#07101B;
        }}
    """

def make_shadow(widget, radius: int = 15, offset: int = 4, alpha: int = None):
    """
    Apply a drop shadow effect to a widget.  The opacity is adjusted
    according to the current theme.

    :param widget: The widget to which the shadow should be applied.
    :param radius: Blur radius for the shadow.
    :param offset: Vertical offset of the shadow.
    :param alpha: Optional override for the shadow alpha channel; if
                  omitted the value from ``SHADOW_ALPHA`` is used and
                  halved in light mode.
    """
    if alpha is None:
        alpha = SHADOW_ALPHA
    # Light themes use a softer shadow
    if CURRENT_THEME == "light":
        alpha = max(20, alpha // 2)
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(radius)
    effect.setOffset(0, offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
    return effect
