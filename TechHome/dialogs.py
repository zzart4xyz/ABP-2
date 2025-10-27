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





