from PyQt5.QtCore import (
    Qt, QPoint, QTimer, QPropertyAnimation, QParallelAnimationGroup,
    QSequentialAnimationGroup, QSize, QEvent, QEasingCurve, pyqtProperty,
    QRectF, QRect
)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QFont, QPainter, QPen, QLinearGradient, QPainterPath, QConicalGradient, QTransform, QRegion
from PyQt5.QtWidgets import (
    QDialog, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QCheckBox, QDateTimeEdit, QSpinBox, QProgressBar,
    QAbstractSpinBox, QMessageBox, QToolButton, QGraphicsDropShadowEffect
)

import constants as c
import os
from PyQt5.QtWidgets import QWidget

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

def _crop_pixmap_to_content(pixmap: QPixmap) -> QPixmap:
    """Return a copy of the pixmap cropped to the smallest rectangle
    containing all non‑transparent pixels.

    If the pixmap has no opaque pixels, the original pixmap is returned.
    """
    if pixmap.isNull():
        return pixmap
    img = pixmap.toImage()
    w, h = img.width(), img.height()
    left, right = w, -1
    top, bottom = h, -1
    # Find bounds of opaque pixels
    for yy in range(h):
        for xx in range(w):
            if img.pixelColor(xx, yy).alpha() > 0:
                if xx < left:
                    left = xx
                if xx > right:
                    right = xx
                if yy < top:
                    top = yy
                if yy > bottom:
                    bottom = yy
    # If no opaque pixels found, return the original pixmap
    if right < left or bottom < top:
        return pixmap
    rect = QRect(left, top, right - left + 1, bottom - top + 1)
    return pixmap.copy(rect)


def _find_pixmap_centroid(pixmap: QPixmap) -> tuple[float, float]:
    """Compute the alpha‑weighted centroid of non‑transparent pixels in a pixmap.

    Returns a tuple (cx, cy) giving the centre of mass in pixel coordinates.  If
    the pixmap is completely transparent, the geometric centre is returned.
    """
    if pixmap.isNull():
        return pixmap.width() / 2.0, pixmap.height() / 2.0
    img = pixmap.toImage()
    width, height = img.width(), img.height()
    sum_x = 0.0
    sum_y = 0.0
    total_alpha = 0.0
    for yy in range(height):
        for xx in range(width):
            a = img.pixelColor(xx, yy).alpha()
            if a > 0:
                total_alpha += a
                sum_x += xx * a
                sum_y += yy * a
    if total_alpha == 0:
        return width / 2.0, height / 2.0
    return sum_x / total_alpha, sum_y / total_alpha


# -----------------------------------------------------------------------------
# Custom splash screen progress indicator
#
# The CircularProgress widget draws a ring representing a percentage value and
# displays an icon at its center.  It supports arbitrary diameters and
# stroke widths.  The ring colour is a fixed gradient from light blue to
# deep blue, similar to the design provided by the user.  Clients can
# update the progress via the ``setValue`` method, which triggers a repaint.

class CircularProgress(QWidget):
    """Circular progress indicator with a central icon."""

    def __init__(self, icon_path: str, diameter: int = 200, stroke_width: int = 10, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0
        self._max_value = 100
        self.diameter = diameter
        self.stroke_width = stroke_width
        # Load the icon.  Support SVG files via QSvgRenderer and raster
        # formats via QPixmap.  Scale the icon to occupy a larger
        # proportion of the diameter for a bolder appearance.  The ratio
        # here (0.6) determines the relative size of the icon within
        # the ring.
        size = int(diameter * 0.6)
        pix = QPixmap()
        try:
            if icon_path and icon_path.lower().endswith('.svg'):
                try:
                    from PyQt5.QtSvg import QSvgRenderer
                except Exception:
                    QSvgRenderer = None
                if QSvgRenderer is not None and os.path.isfile(icon_path):
                    renderer = QSvgRenderer(icon_path)
                    if renderer.isValid():
                        pm = QPixmap(size, size)
                        pm.fill(Qt.transparent)
                        painter = QPainter(pm)
                        renderer.render(painter)
                        painter.end()
                        pix = pm
            if pix.isNull() and icon_path and os.path.isfile(icon_path):
                pix = QPixmap(icon_path)
        except Exception:
            pass
        # Crop padding from the source pixmap before scaling
        if not pix.isNull():
            cropped = _crop_pixmap_to_content(pix)
            self.icon_pixmap = cropped.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            self.icon_pixmap = QPixmap()
        # Set the preferred size of this widget
        self.setMinimumSize(diameter, diameter)
        self.setMaximumSize(diameter, diameter)

    def setValue(self, value: int) -> None:
        """Update the progress value (0–max_value)."""
        self._value = max(0, min(self._max_value, value))
        self.update()

    def value(self) -> int:
        return self._value

    def maxValue(self) -> int:
        return self._max_value

    def setMaxValue(self, max_value: int) -> None:
        self._max_value = max(1, max_value)
        self.update()

    def paintEvent(self, event) -> None:
        # Draw the progress ring and the icon using QPainter.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Compute bounding rect for the arc.  Leave space for the stroke.
        margin = self.stroke_width / 2.0
        rect = QRectF(margin, margin, self.diameter - self.stroke_width, self.diameter - self.stroke_width)
        # Background ring (dark).  Use the panel colour with reduced opacity
        # for subtlety.
        bg_pen = QPen(QColor(c.CLR_SURFACE))
        bg_pen.setWidth(self.stroke_width)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)
        # Progress ring.  Use a gradient brush along the arc.  To get a
        # circular gradient effect, we use QConicalGradient centred on the
        # widget.  The start angle is -90 degrees (top) and stops define
        # colours from cyan to blue.
        progress_angle = (self._value / self._max_value) * 360.0
        gradient = QConicalGradient(self.diameter / 2.0, self.diameter / 2.0, -90)
        # Define gradient stops: bright cyan to mid blue to dark blue
        gradient.setColorAt(0.0, QColor(0, 191, 255))  # #00BFFF
        gradient.setColorAt(0.5, QColor(0, 128, 255))  # #0080FF
        gradient.setColorAt(1.0, QColor(0, 70, 205))   # #0046CD
        progress_pen = QPen()
        progress_pen.setWidth(self.stroke_width)
        progress_pen.setBrush(gradient)
        progress_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(progress_pen)
        # Draw the arc representing progress.  QPainter.drawArc expects
        # integer values for the start angle and span length (in 1/16ths of a
        # degree).  Cast the computed span to int to avoid TypeError.
        start_angle = -90 * 16
        span_angle = -int(progress_angle * 16)
        painter.drawArc(rect, start_angle, span_angle)
        # Draw the centre icon
        if not self.icon_pixmap.isNull():
            # Compute centroid of the icon to ensure visual centring
            cx, cy = _find_pixmap_centroid(self.icon_pixmap)
            offset_x = (self.icon_pixmap.width() / 2.0) - cx
            offset_y = (self.icon_pixmap.height() / 2.0) - cy
            ix = (self.diameter - self.icon_pixmap.width()) / 2.0 + offset_x
            iy = (self.diameter - self.icon_pixmap.height()) / 2.0 + offset_y
            painter.drawPixmap(int(ix), int(iy), self.icon_pixmap)
        painter.end()

# Import the local database helper for user authentication.  This module
# provides functions to initialise the database and create/authenticate
# users.  See ``database.py`` for details.
import database


def _apply_rounded_mask(widget, radius: int):
    """Clip a top-level widget to a rounded rectangle to avoid semi-transparent edges."""
    try:
        r = int(max(0, radius))
    except Exception:
        # Fallback if radius is not numeric (e.g. from constants), let Qt coerce later
        r = 10
    path = QPainterPath()
    # Use the widget's full rect; QRectF accepts QRect
    path.addRoundedRect(QRectF(widget.rect()), r, r)
    # Convert the path into a region and apply as window mask
    region = QRegion(path.toFillPolygon().toPolygon())
    widget.setMask(region)


"""
Dialog components used across the TechHome application.  These classes
encapsulate common form behaviour and present login and splash
interfaces.  They draw on the centralised constants module to pick up
colours, fonts and translation strings, ensuring consistency and ease
of maintenance.
"""


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


class SplashScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Resize the dialog to accommodate header, ring, descriptive text,
        # progress bar and action buttons, similar to the provided
        # reference design.
        self.resize(420, 600)
        # Create the outer card with rounded corners and a glowing edge.
        frame = QFrame(self)
        frame.setObjectName("splash")
        frame.setStyleSheet(
            f"QFrame#splash {{ background:{c.CLR_PANEL}; border:2px solid {c.CLR_TITLE}; border-radius:20px; }}"
        )
        frame.setGeometry(0, 0, self.width(), self.height())
        _apply_rounded_mask(self, c.FRAME_RAD)
        _apply_rounded_mask(self, 20)
        # Layout for the card contents
        v = QVBoxLayout(frame)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)
        # Header: title and close button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        self.title_lbl = QLabel("TechHome", self)
        self.title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 30px '{c.FONT_FAM}';")
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch(1)
        self.close_btn = QPushButton("", self)
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(
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
        self.close_btn.clicked.connect(self.reject)
        header_layout.addWidget(self.close_btn)
        v.addLayout(header_layout)
        # Circular progress ring
        icon_path = c.LOGO_PATH
        self.ring = CircularProgress(icon_path, diameter=220, stroke_width=14)
        self.ring.setFixedSize(240, 240)
        v.addStretch(1)
        v.addWidget(self.ring, alignment=Qt.AlignHCenter)
        v.addSpacing(8)
        # Status labels
        self.status_lbl = QLabel("Cargando…", self)
        self.status_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 26px '{c.FONT_FAM}';")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        v.addWidget(self.status_lbl)
        self.sub_status_lbl = QLabel("Preparando panel", self)
        self.sub_status_lbl.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:500 18px '{c.FONT_FAM}';")
        self.sub_status_lbl.setAlignment(Qt.AlignCenter)
        v.addWidget(self.sub_status_lbl)
        v.addSpacing(12)
        # Progress bar and percentage label
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(14)
        # Style the progress bar so the chunk grows smoothly from left
        # to right.  Avoid specifying a gradient that spans the full
        # width, as that can make the bar appear static until the end.
        # Instead use a single colour (the primary accent) for the
        # chunk so its width reflects the progress percentage.
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border:none;
                border-radius:7px;
                background:{c.CLR_SURFACE};
            }}
            QProgressBar::chunk {{
                border-radius:7px;
                background:{c.CLR_TITLE};
            }}
            """
        )
        # Give the progress bar a stretch factor so it occupies the
        # remaining horizontal space, allowing the chunk to grow
        progress_layout.addWidget(self.progress_bar, 1)
        self.percent_lbl = QLabel("0%", self)
        self.percent_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}';")
        progress_layout.addWidget(self.percent_lbl)
        v.addLayout(progress_layout)
        # Bottom buttons
        v.addStretch(1)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        self.pause_btn = QPushButton("Pausar", self)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setFixedSize(140, 40)
        self.pause_btn.setStyleSheet(
            f"""
            QPushButton {{
                background:transparent;
                color:{c.CLR_TITLE};
                border:2px solid {c.CLR_TITLE};
                border-radius:10px;
                font:600 18px '{c.FONT_FAM}';
            }}
            QPushButton:hover {{
                background:{c.CLR_HOVER};
            }}
            """
        )
        self.pause_btn.clicked.connect(self._toggle_pause)
        btn_layout.addWidget(self.pause_btn)
        self.continue_btn = QPushButton("Continuar", self)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setFixedSize(140, 40)
        self.continue_btn.setStyleSheet(
            f"""
            QPushButton {{
                background:qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00BFFF, stop:1 #0066FF);
                color:{c.CLR_BG};
                border:none;
                border-radius:10px;
                font:600 18px '{c.FONT_FAM}';
            }}
            QPushButton:disabled {{
                background:{c.CLR_SURFACE};
                color:{c.CLR_PLACEHOLDER};
            }}
            QPushButton:hover:!disabled {{
                background:qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00BFFF, stop:1 #0070FF);
            }}
            """
        )
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.continue_btn)
        v.addLayout(btn_layout)
        # Initialise progress variables and tasks.  ``self._tasks`` holds
        # tuples of (percentage_threshold, description) so that the
        # secondary status text updates as progress crosses these values.
        self._progress_value = 0
        self._dot_step = 0
        # Define loading phases.  Adjust thresholds and messages as
        # required for real application steps.
        self._tasks = [
            (0,    "Preparando panel"),
            (25,   "Cargando dispositivos"),
            (50,   "Iniciando servicios"),
            (75,   "Estableciendo conexión"),
            (100,  "Completado")
        ]
        # Pause flag indicates whether the timer is running
        self._paused = False
        # Timer to update progress and animate labels
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        # Start the timer with a shorter interval for smoother animation
        self._timer.start(30)

    def _advance(self):
        # Skip updates if paused
        if getattr(self, '_paused', False):
            return
        # Increment progress
        self._progress_value += 1
        if self._progress_value > 100:
            self._progress_value = 100
        # Update the ring and progress bar
        self.ring.setValue(self._progress_value)
        # Update the progress bar directly.  This ensures the fill
        # gradually increases with each tick instead of jumping at the end.
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(self._progress_value)
        if hasattr(self, 'percent_lbl'):
            self.percent_lbl.setText(f"{self._progress_value}%")
        # Animate the "Cargando" text by cycling dots
        if hasattr(self, 'status_lbl'):
            self._dot_step += 1
            dots = self._dot_step % 4
            self.status_lbl.setText("Cargando" + "." * dots)
        # Update the secondary status based on current progress
        if hasattr(self, 'sub_status_lbl') and hasattr(self, '_tasks'):
            desc = self._tasks[0][1]
            for thr, txt in self._tasks:
                if self._progress_value >= thr:
                    desc = txt
            self.sub_status_lbl.setText(desc)
        # When complete, stop the timer and enable the continue button
        if self._progress_value >= 100:
            # Ensure all indicators show 100% before stopping
            self._progress_value = 100
            self.ring.setValue(100)
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setValue(100)
            if hasattr(self, 'percent_lbl'):
                self.percent_lbl.setText("100%")
            if hasattr(self, 'status_lbl'):
                # Freeze the loading text at the completed state
                self.status_lbl.setText("Cargando...")
            # Update the secondary text to the final phase
            if hasattr(self, 'sub_status_lbl') and hasattr(self, '_tasks'):
                self.sub_status_lbl.setText(self._tasks[-1][1])
            self._timer.stop()
            if hasattr(self, 'continue_btn'):
                self.continue_btn.setEnabled(True)

    def _toggle_pause(self):
        """Toggle the loading progress between paused and running.

        When paused, stop the timer and change the button text to
        "Reanudar".  When resumed, restart the timer and revert the
        text to "Pausar".  This allows the user to pause the loading
        animation instead of cancelling it outright.
        """
        # If the progress is complete, do not allow pausing
        if self._progress_value >= 100:
            return
        if not self._paused:
            # Pause progress
            self._paused = True
            self._timer.stop()
            if hasattr(self, 'pause_btn'):
                self.pause_btn.setText("Reanudar")
        else:
            # Resume progress
            self._paused = False
            # Resume the timer with the same smooth interval used in __init__
            self._timer.start(30)
            if hasattr(self, 'pause_btn'):
                self.pause_btn.setText("Pausar")


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(400, 380)
        frame = QFrame(self)
        frame.setObjectName("login")
        frame.setStyleSheet(
            f"QFrame#login {{ background:{c.CLR_PANEL}; border:2px solid {c.CLR_TITLE}; border-radius:{c.FRAME_RAD}px; }}"
        )
        frame.setGeometry(0, 0, self.width(), self.height())
        _apply_rounded_mask(self, 20)
        v = QVBoxLayout(frame)
        v.setContentsMargins(24, 24, 24, 24)
        self.title_lbl = QLabel("Iniciar Sesión")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        # Enlarge title font size for better visibility
        self.title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 26px '{c.FONT_FAM}';")
        v.addWidget(self.title_lbl)
        v.addSpacing(12)
        self.mode = "login"
        # Use floating label inputs for the user and password fields.  These
        # custom widgets animate their labels when focused or when text
        # is present, providing a more modern look and feel.  The
        # ``is_password`` flag enables password echo mode on the
        # underlying QLineEdit.
        # Use larger label size for the inputs to make the content appear bigger
        self.user = FloatingLabelInput("Usuario", label_px=18)
        self.passw = FloatingLabelInput("Contraseña", is_password=True, label_px=18)
        # Removed the confirm password field (self.passw2) to simplify registration.
        # The login form previously included a "Recuérdame" checkbox and an
        # "Olvidé mi contraseña" button.  These elements have been removed to
        # simplify the interface.
        self.btn_action = QPushButton("Entrar")
        self.btn_action.setCursor(Qt.PointingHandCursor)
        self.btn_action.setStyleSheet(
            f"background:{c.CLR_TITLE}; color:#07101B; font:600 18px '{c.FONT_FAM}'; border:none; border-radius:{c.FRAME_RAD}px; padding:10px 20px;"
        )
        # Initialising the local user database.  This ensures the
        # users table exists before we attempt to authenticate or
        # register a user.  See ``database.py`` for implementation.
        database.init_db()
        # Replace the default button action with a custom handler
        # that performs login or registration based on the current mode.
        self.btn_action.clicked.connect(self._on_action)
        self.toggle = QPushButton("¿No tienes una cuenta? Regístrate")
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.setStyleSheet(
            f"background:transparent; color:{c.CLR_TITLE}; border:none; font:600 16px '{c.FONT_FAM}';"
        )
        self.toggle.clicked.connect(self._switch_mode)
        v.addWidget(self.user)
        v.addWidget(self.passw)
        # Do not add a confirmation field; only user and password inputs are used.
        # Add a spacer to push the action button and toggle towards the bottom.
        v.addStretch(1)
        v.addWidget(self.btn_action)
        v.addWidget(self.toggle)

        # End of __init__ method

    def _switch_mode(self):
        """
        Toggle between login and registration modes.  In registration mode the confirmation
        password field is shown and button labels/texts are updated to reflect account creation.
        In login mode the confirmation field is hidden and labels/texts return to their original state.
        """
        if self.mode == "login":
            # Enter registration mode: show the confirm password field and update labels
            self.mode = "register"
            # Confirmation field removed; nothing to show.
            # Update UI text
            self.btn_action.setText("Registrar")
            self.title_lbl.setText("Registrarse")
            self.toggle.setText("¿Ya tienes una cuenta? Inicia sesión")
            # Defer resetting the floating labels until the widgets have been laid out
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(50, self._reset_form_labels)
        else:
            # Return to login mode: hide the confirm password field and update labels
            self.mode = "login"
            # Confirmation field removed; nothing to hide.
            # Update UI text
            self.btn_action.setText("Entrar")
            self.title_lbl.setText("Iniciar Sesión")
            self.toggle.setText("¿No tienes una cuenta? Regístrate")
            # Defer resetting the floating labels as above
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(50, self._reset_form_labels)

    def _on_action(self):
        """
        Handle the primary button action for the login dialog.  In
        ``login`` mode, this attempts to authenticate the user
        against the local SQLite database.  On success the dialog
        accepts; on failure it shows an error message.
        In ``register`` mode, this attempts to create a new user.
        It validates that the password and confirmation match and
        reports errors if the username already exists or the
        passwords mismatch.  Upon successful registration it
        switches back to login mode and informs the user.
        """
        username = self.user.text().strip()
        password = self.passw.text()
        if not username or not password:
            # Display an error message when either field is empty.
            show_message(self, "Error", "Debes introducir un usuario y una contraseña.")
            return
        if self.mode == "login":
            if database.authenticate(username, password):
                # Successful login
                self.accept()
            else:
                # Warn the user that the credentials are invalid.
                show_message(self, "Error", "Usuario o contraseña incorrectos.")
        else:  # register mode
            # Attempt to create a new user with just username and password (no confirmation).
            if not database.create_user(username, password):
                # Warn that the chosen username is already taken.
                show_message(self, "Error", "El nombre de usuario ya existe.")
                return
            # Inform the user that account creation was successful.
            show_message(self, "Éxito", "Cuenta creada correctamente. Ahora puedes iniciar sesión.")
            # Switch back to login mode automatically
            self._switch_mode()

    def _reset_form_labels(self):
        """Reset the floating labels for the login/registration fields.

        This helper iterates over the user, password and confirmation
        inputs in the simple login dialog and forces their floating
        labels to start in the down position by clearing the focused
        state and updating the label.  It is invoked via a
        single‑shot timer from ``_switch_mode`` to ensure the widget
        geometries have been computed before resetting.
        """
        for fld in (self.user, self.passw):
            if fld is not None:
                fld._focused = False
                fld._update_label_state()

###############################################################################
# Modern login and registration dialog
###############################################################################

# -----------------------------------------------------------------------------
# Custom input and background widgets for the login/registration pages
# -----------------------------------------------------------------------------


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

# The following class redeclaration replaces the previously defined
# ``LoginDialog`` with a split‑screen design inspired by the reference
# images supplied by the user.  In Python, later definitions of a
# class with the same name override earlier ones at import time, so
# this version will be used by the application.

class LoginDialog(QDialog):
    """Login and registration dialog with a modern split‑screen design.

    This implementation replaces the old login/register layout with a two‑panel
    interface.  The dark form panel contains the input fields and buttons,
    while a gradient message panel occupies the opposite side.  Switching
    between login and registration views triggers a sliding animation for a
    fluid transition.  Colours are drawn from the application's theme
    constants to maintain visual consistency.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Apply frameless, translucent styling like the rest of the application.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # A larger canvas accommodates the split design.
        self.resize(700, 420)

        # Determine language settings from the parent if available; default to Spanish.
        self.lang = getattr(parent, 'lang', 'es') if parent else 'es'
        self.mapping = c.TRANSLATIONS_EN if self.lang == 'en' else {}

        # Initialise the local user database.
        database.init_db()

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
        from PyQt5.QtWidgets import QGraphicsOpacityEffect
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
        title_text = "Iniciar Sesión"
        title_lbl = QLabel(title_text)
        # Enlarge title font further for better visibility
        title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 38px '{c.FONT_FAM}';")
        title_lbl.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title_lbl)

        # Username input using floating label style.
        # Etiqueta y placeholder del campo de usuario en español
        user_ph = "Usuario"
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
        pass_ph = "Contraseña"
        self.login_pass = FloatingLabelInput(pass_ph, is_password=True, label_px=20)
        self.login_pass.setFixedHeight(70)
        self.login_pass.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.login_pass)

        # Login button.
        # Texto del botón de entrada en español
        self.btn_login = QPushButton("Entrar")
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
        self.link_to_register = QPushButton("¿No tienes una cuenta? Regístrate")
        self.link_to_register.setCursor(Qt.PointingHandCursor)
        # Increase the font size for the sign-up link
        self.link_to_register.setStyleSheet(
            f"background:transparent; border:none; color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}'; text-decoration: underline;"
        )
        self.link_to_register.clicked.connect(self._animate_to_register)
        form_layout.addWidget(self.link_to_register, alignment=Qt.AlignCenter)

        # Right: gradient message container with triangular shape.
        # Use equal ratios so that the diagonal reaches the midpoint of the container.
        # Centre the diagonal so it crosses the middle of the widget but remains slanted.
        # Setting t_ratio and b_ratio such that their sum equals 1 ensures the line's midpoint
        # sits at the centre of the panel.  For the login page the gradient is on the right,
        # so t_ratio > b_ratio to slope downwards to the right.
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
        # Give the form 1/3 and the gradient 2/3 width so that the diagonal can
        # be centred relative to the combined panels.
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
        # Centre the diagonal in the register view, mirroring the login view.  For
        # orientation 'left' the gradient is on the left so b_ratio > t_ratio to
        # slope downwards to the left.  The sum of t_ratio and b_ratio is 1 to
        # centre the diagonal line.
        # With the gradient panel occupying two thirds of the space we set
        # the ratios so that their sum is 1.5, centring the diagonal line.
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
        # Increase spacing further to enlarge the form vertically
        form_layout.setSpacing(30)

        # Usar texto fijo en español para el título del formulario de registro
        title_text = "Registrarse"
        title_lbl = QLabel(title_text)
        # Enlarge title font further for better visibility
        title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 38px '{c.FONT_FAM}';")
        title_lbl.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title_lbl)

        # Username input for registration.
        # Etiqueta y placeholder del campo de usuario en español
        user_ph = "Usuario"
        self.register_user = FloatingLabelInput(user_ph, label_px=20, right_icon_name="Usuario.svg")
        self.register_user.setFixedHeight(70)
        self.register_user.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.register_user)

        # Password input.  The user requested the email field be replaced by a
        # password field, so the second input captures the password.  Use the
        # same translation as the login password field and enable password mode.
        # Etiqueta y placeholder del campo de contraseña en español
        pass_ph = "Contraseña"
        self.register_pass = FloatingLabelInput(pass_ph, is_password=True, label_px=20)
        self.register_pass.setFixedHeight(70)
        self.register_pass.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{c.CLR_TEXT_IDLE}; font:600 20px '{c.FONT_FAM}'; }}"
        )
        form_layout.addWidget(self.register_pass)

        # Removed the confirm password input. Registration only requires username and password.

        # Register button.
        # Texto del botón de registro en español
        self.btn_register = QPushButton("Registrar")
        self.btn_register.setCursor(Qt.PointingHandCursor)
        # Apply a larger font size and padding to the register button
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
        # Texto del enlace para volver al inicio de sesión en español
        self.link_to_login = QPushButton("¿Ya tienes una cuenta? Inicia sesión")
        self.link_to_login.setCursor(Qt.PointingHandCursor)
        self.link_to_login.setStyleSheet(
            f"background:transparent; border:none; color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}'; text-decoration: underline;"
        )
        self.link_to_login.clicked.connect(self._animate_to_login)
        form_layout.addWidget(self.link_to_login, alignment=Qt.AlignCenter)

        # Assemble the register page layout: message on the left, form on the right.
        # Use a 2/3 : 1/3 ratio so the diagonal can be centred relative to both panels.
        layout.addWidget(self.signup_bg, stretch=2)
        layout.addWidget(form, stretch=1)

        # After constructing the registration page, ensure that the floating
        # labels on the username and password fields start in their down
        # position when the page first appears. Without this explicit
        # reset the labels may remain in the up position (as if focused)
        # because the resize events can fire before the widget is fully
        # laid out. By clearing the focused state and invoking
        # ``_update_label_state`` we guarantee the labels animate upward
        # only when the user focuses a field or enters text.
        for _fld in (self.register_user, self.register_pass):
            # Ensure the field is marked as not focused
            _fld._focused = False
            # Force an initial update of the label state
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
        # Use a gradient background that brightens on hover.
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
        """Reset the floating labels for registration fields.

        This helper iterates over the username, password and confirm
        password inputs on the register page and forces their floating
        labels to start in the down position by clearing the focused
        state and updating the label.  It is scheduled via a
        single‑shot timer from ``_animate_to_register`` to ensure
        the page has finished animating and the widget geometries
        have been computed before resetting.
        """
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
            show_message(self, "Error", "Debes introducir un usuario y una contraseña.")
            return
        if database.authenticate(username, password):
            # Record the authenticated username for the calling code
            # before closing the dialog.  This allows the main
            # application to personalise the UI and log user actions.
            self.current_user = username
            # Successful login ends the dialog with accept().
            self.accept()
        else:
            show_message(self, "Error", "Usuario o contraseña incorrectos.")

    def _on_register_action(self):
        """Attempt to register a new user with the provided information."""
        username = self.register_user.text().strip()
        password = self.register_pass.text()
        # Ensure required fields are populated
        if not username or not password:
            show_message(self, "Error", self.mapping.get(
                "Debes introducir un nombre de usuario y una contraseña.",
                "You must enter a username and a password."
            ))
            return
        # Attempt to create the user in the database
        if not database.create_user(username, password):
            show_message(self, "Error", self.mapping.get(
                "El nombre de usuario ya existe.",
                "The username already exists."
            ))
            return
        # Successful registration; inform the user and slide back to login.  Also
        # record the registration in the actions table so it appears in the
        # account history.  This call uses the plain username rather than a
        # hashed value to keep the log readable.  It is safe from SQL
        # injection because the underlying function uses parameter binding.
        database.log_action(username, "Registro de usuario")
        show_message(
            self,
            self.mapping.get("Éxito", "Success"),
            self.mapping.get(
                "Cuenta creada correctamente. Ahora puedes iniciar sesión.",
                "Account created successfully. You can now log in."
            ),
        )
        self._animate_to_login()

