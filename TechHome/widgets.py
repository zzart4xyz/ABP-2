from PyQt5.QtCore import Qt, QRectF, QPoint, QSize, QDate, QTimer, QPointF, pyqtSignal, QPropertyAnimation
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPixmap,
    QRadialGradient, QConicalGradient, QTextCharFormat, QTransform,
    QIcon
)
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QGraphicsOpacityEffect, QStackedWidget, QLineEdit, QComboBox, QScrollBar, QListWidget,
    QListWidgetItem, QTabWidget, QListView, QStyledItemDelegate, QStyle, QToolButton, QTableView,
    QHeaderView, QSizePolicy, QCalendarWidget, QTableWidget, QSpinBox
)

import constants as c

"""
Custom widgets used throughout the TechHome interface.  These include
scrollbars, delegates, cards and draggable notes as well as helper
functions to style tables.  Each component relies on the central
constants module to access colours and utility functions so that theme
changes propagate consistently.
"""


class NotesManager:
    def __init__(self, container, cell_size, spacing, rows, columns):
        self.container = container
        self.cell_w, self.cell_h = cell_size
        self.spacing = spacing
        self.rows = rows
        self.columns = columns
        self.occupancy = {}

    def total_grid_width(self):
        return self.columns * self.cell_w + (self.columns - 1) * self.spacing

    def total_grid_height(self):
        return self.rows * self.cell_h + (self.rows - 1) * self.spacing

    def margin_x(self):
        return max(0, (self.container.width() - self.total_grid_width()) // 2)

    def margin_y(self):
        return max(0, (self.container.height() - self.total_grid_height()) // 2)

    def get_max_rows(self):
        return self.rows

    def cell_to_pos(self, cell):
        row, col = cell
        x = self.margin_x() + col * (self.cell_w + self.spacing)
        y = self.margin_y() + row * (self.cell_h + self.spacing)
        return QPoint(x, y)

    def pos_to_cell(self, pos):
        x_rel = pos.x() - self.margin_x()
        y_rel = pos.y() - self.margin_y()
        col = round(x_rel / (self.cell_w + self.spacing))
        row = round(y_rel / (self.cell_h + self.spacing))
        col = max(0, min(col, self.columns - 1))
        row = max(0, min(row, self.rows - 1))
        return (row, col)

    def is_free(self, cell):
        return cell not in self.occupancy

    def occupy(self, cell, note):
        self.occupancy[cell] = note

    def release(self, cell):
        if cell in self.occupancy:
            del self.occupancy[cell]


class DraggableNote(QFrame):
    def __init__(self, text: str, manager: NotesManager, timestamp: str):
        super().__init__(manager.container)
        self.manager = manager
        self.text = text
        self.timestamp = timestamp
        self.setFixedSize(manager.cell_w, manager.cell_h)
        self.text_label = QLabel(text, self)
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.ts_label = QLabel(timestamp, self)
        self.ts_label.setAlignment(Qt.AlignCenter)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)
        v.addWidget(self.text_label, stretch=3)
        v.addWidget(self.ts_label, stretch=1)
        self._drag_start = QPoint()
        self._orig_pos = QPoint()
        self._cell = None
        self.apply_theme()

    def apply_theme(self):
        """Update colours based on the active theme."""
        self.setStyleSheet(
            f"""
            QFrame {{
                background:{c.CLR_PANEL};
                border: 2px solid {c.CLR_TITLE};
                border-radius:5px;
            }}
            """
        )
        self.text_label.setStyleSheet(
            f"color:{c.CLR_TEXT_IDLE}; font:600 16px '{c.FONT_FAM}';"
        )
        self.ts_label.setStyleSheet(
            f"color:{c.CLR_TEXT_IDLE}; font:500 12px '{c.FONT_FAM}';"
        )
        c.make_shadow(self, 12, 4, 100)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            e.accept()
            self._drag_start = e.globalPos()
            self._orig_pos = self.pos()
            if self._cell is not None:
                self.manager.release(self._cell)
                self._cell = None
            self.raise_()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            e.accept()
            delta = e.globalPos() - self._drag_start
            new_pos = self._orig_pos + delta
            rect = self.manager.container.rect()
            x = max(0, min(new_pos.x(), rect.width() - self.width()))
            y = max(0, min(new_pos.y(), rect.height() - self.height()))
            self.move(x, y)
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            e.accept()
            cell = self.manager.pos_to_cell(self.pos())
            if self.manager.is_free(cell):
                new_p = self.manager.cell_to_pos(cell)
                self.move(new_p)
                self.manager.occupy(cell, self)
                self._cell = cell
            else:
                self.move(self._orig_pos)
        else:
            super().mouseReleaseEvent(e)


class CustomScrollBar(QScrollBar):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")
        if orientation == Qt.Vertical:
            self.setFixedWidth(10)
        else:
            self.setFixedHeight(12)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(26, 43, 60))
        painter.drawRoundedRect(r, 6, 6)
        handle = QRectF(r)
        if self.maximum() > 0:
            total = self.maximum() + self.pageStep()
            if self.orientation() == Qt.Vertical:
                h = r.height()
                hh = max(20, self.pageStep() * h // total)
                y = self.sliderPosition() * (h - hh) // max(1, self.maximum())
                handle = QRectF(0, y, r.width(), hh)
            else:
                w = r.width()
                ww = max(20, self.pageStep() * w // total)
                x = self.sliderPosition() * (w - ww) // max(1, self.maximum())
                handle = QRectF(x, 0, ww, r.height())
        painter.setBrush(QColor(30, 140, 200))
        painter.drawRoundedRect(handle, 6, 6)
        painter.end()


class NoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, index)


def style_table(tbl):
    """Apply uniform style and no-focus behaviour to tables."""
    tbl.setAlternatingRowColors(False)
    tbl.setShowGrid(True)
    tbl.setFrameShape(QFrame.NoFrame)
    tbl.setFocusPolicy(Qt.NoFocus)
    tbl.setItemDelegate(NoFocusDelegate(tbl))
    tbl.setStyleSheet(
        f"QTableWidget {{ background:{c.CLR_PANEL}; color:{c.CLR_TEXT_IDLE}; gridline-color:{c.CLR_TITLE}; font:500 14px '{c.FONT_FAM}'; }}"
        f" QTableWidget::item {{ padding:10px; background:transparent; }}"
        f" QTableWidget::item:selected {{ background:{c.CLR_ITEM_ACT}; color:{c.CLR_TITLE}; }}"
        f" QTableWidget::item:focus {{ outline:none; }}"
    )
    sb = CustomScrollBar(Qt.Vertical)
    sb.setStyleSheet("margin:2px; background:transparent;")
    tbl.setVerticalScrollBar(sb)
    tbl.setViewportMargins(0, 0, 4, 0)


class CurrentMonthCalendar(QCalendarWidget):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.event_dates = set()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(600, 360)
        self.currentPageChanged.connect(self._adjust_rows)
        QTimer.singleShot(0, self._setup_navbar)
        QTimer.singleShot(0, self._adjust_rows)

    def _setup_navbar(self):
        nav = self.findChild(QWidget, "qt_calendar_navigationbar")
        if not nav or not nav.layout():
            return
        layout = nav.layout()
        # Keep Qt's internal widgets alive to prevent crashes
        self._default_prev = nav.findChild(QToolButton, "qt_calendar_prevmonth")
        self._default_next = nav.findChild(QToolButton, "qt_calendar_nextmonth")
        self._default_month = nav.findChild(QToolButton, "qt_calendar_monthbutton")
        self._default_year = nav.findChild(QSpinBox, "qt_calendar_yearedit")
        for w in (self._default_prev, self._default_next, self._default_month, self._default_year):
            if w:
                w.hide()
        while layout.count():
            layout.takeAt(0)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)
        self._prev = QToolButton()
        left_pix = c.pixmap("Arrow.svg")
        self._prev.setIcon(QIcon(left_pix))
        self._prev.setIconSize(QSize(16, 16))
        self._prev.setFixedSize(24, 24)
        self._prev.setCursor(Qt.PointingHandCursor)
        self._prev.clicked.connect(self.showPreviousMonth)
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(
            f"color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}'; padding:0 4px;"
        )
        self._next = QToolButton()
        right_pix = c.pixmap("Arrow.svg").transformed(QTransform().scale(-1, 1))
        self._next.setIcon(QIcon(right_pix))
        self._next.setIconSize(QSize(16, 16))
        self._next.setFixedSize(24, 24)
        self._next.setCursor(Qt.PointingHandCursor)
        self._next.clicked.connect(self.showNextMonth)
        layout.addWidget(self._prev)
        layout.addWidget(self._label, 1)
        layout.addWidget(self._next)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(c.CLR_HEADER_TEXT))
        fmt.setFont(QFont(c.FONT_FAM, 10, QFont.Bold))
        for d in range(1, 8):
            self.setWeekdayTextFormat(Qt.DayOfWeek(d), fmt)
        self.currentPageChanged.connect(self._update_header)
        self._update_header()

    def _update_header(self):
        date = QDate(self.yearShown(), self.monthShown(), 1)
        self._label.setText(date.toString("MMMM yyyy"))
        self._format_dates()

    def _format_dates(self):
        dim = QTextCharFormat()
        col = QColor(c.CLR_TEXT_IDLE)
        col.setAlphaF(0.5)
        dim.setForeground(col)
        norm = QTextCharFormat()
        norm.setForeground(QColor(c.CLR_TEXT_IDLE))
        month = self.monthShown(); year = self.yearShown()
        first = QDate(year, month, 1)
        offset = (first.dayOfWeek() - int(self.firstDayOfWeek()) + 7) % 7
        start = first.addDays(-offset)
        for i in range(42):
            d = start.addDays(i)
            self.setDateTextFormat(d, norm if d.month() == month else dim)

    def update_events(self, dates):
        converted = set()
        for d in dates:
            if isinstance(d, QDate):
                converted.add(d)
            else:
                converted.add(QDate(d.year, d.month, d.day))
        self.event_dates = converted
        self.updateCells()

    def _adjust_rows(self):
        view = self.findChild(QTableView, "qt_calendar_calendarview")
        if not view:
            return
        hdr = view.horizontalHeader()
        hdr.setStyleSheet(
            f"QHeaderView::section {{background:{c.CLR_HEADER_BG};"
            f" color:{c.CLR_TITLE}; border:none;}}"
        )
        hdr.setFixedHeight(c.CAL_HEADER_HEIGHT)
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setDefaultSectionSize(c.CAL_CELL_SIZE)
        vhdr = view.verticalHeader()
        vhdr.setSectionResizeMode(QHeaderView.Stretch)
        vhdr.setDefaultSectionSize(c.CAL_CELL_SIZE)
        first = QDate(self.yearShown(), self.monthShown(), 1)
        offset = (first.dayOfWeek() - int(self.firstDayOfWeek()) + 7) % 7
        weeks = (offset + first.daysInMonth() + 6) // 7
        for r in range(6):
            view.setRowHidden(r, r >= weeks)
        base_height = c.CAL_HEADER_HEIGHT + c.CAL_CELL_SIZE * weeks
        view.setMinimumHeight(base_height)
        view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        if date == QDate.currentDate():
            pen = QPen(QColor(c.CLR_TITLE))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect.adjusted(3, 3, -3, -3))
        if date in self.event_dates:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(c.CLR_TITLE))
            painter.drawEllipse(
                QRectF(rect.center().x() - 2, rect.bottom() - 6, 4, 4)
            )


class CardButton(QFrame):
    clicked = pyqtSignal()
    def __init__(self, text: str, icon_name: str | None = None):
        """
        Construct a card button for the "More" page.  The card displays
        a coloured gradient background, optional icon and a label.  An
        icon may be provided via ``icon_name``; if None, the card will
        only display the text.  The ``icon_name`` should refer to a
        filename within the ``Icons N`` directory (e.g. ``'bell.svg'``).

        :param text: The label to display on the card.
        :param icon_name: Optional SVG filename for the icon.  When
                          provided, an icon will be shown to the left
                          of the label.
        """
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(300, 140)
        # Use a gradient background consistent with other cards.
        self.setStyleSheet(
            f"""
                QFrame {{
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                              stop:0 {c.CLR_HEADER_BG}, stop:1 {c.CLR_HOVER});
                    border:2px solid {c.CLR_TITLE};
                    border-radius:5px;
                }}
                QFrame:hover {{ background:{c.CLR_HOVER}; }}
            """
        )
        # Layout with space for an optional icon and the text.  The
        # contents margins are chosen to align with other widgets.
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(16)
        # Add icon if provided
        if icon_name:
            icon_lbl = QLabel()
            # Load the pixmap from the constants module.  Icons are
            # scaled up for better visibility on these large cards.
            try:
                pix = c.pixmap(icon_name)
            except Exception:
                pix = None
            if not pix or pix.isNull():
                # Fallback: if the file can't be loaded, leave blank
                icon_lbl.setPixmap(QPixmap())
            else:
                icon_lbl.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_lbl.setAlignment(Qt.AlignVCenter)
            icon_lbl.setStyleSheet("border:none;")
            lay.addWidget(icon_lbl, 0)
        # Add the text label.  The stretch factor of 1 ensures that
        # longer labels occupy the remaining space.
        txt_lbl = QLabel(text)
        # Center the text horizontally and vertically within its available space.  This
        # ensures the label appears centered in the card while the icon remains
        # anchored on the left.
        txt_lbl.setAlignment(Qt.AlignCenter)
        txt_lbl.setStyleSheet(
            f"color:{c.CLR_TEXT_IDLE}; font:700 20px '{c.FONT_FAM}'; border:none; background:transparent;"
        )
        lay.addWidget(txt_lbl, 1)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class QuickAccessButton(QFrame):
    clicked = pyqtSignal()
    def __init__(self, text: str, icon_name: str):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(180, 40)
        self.setStyleSheet(
            f"background:{c.CLR_SURFACE};border:2px solid {c.CLR_TITLE};"
            f"border-radius:5px;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(c.pixmap(icon_name).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_lbl.setStyleSheet("border:none;")
        text_lbl = QLabel(text)
        text_lbl.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:600 14px '{c.FONT_FAM}'; border:none;")
        lay.addWidget(icon_lbl)
        lay.addWidget(text_lbl)
        # The quick access button originally faded in/out when the mouse
        # entered or left.  To keep the buttons always visible at full
        # opacity, we omit the opacity effect and animation.
        self._effect = None
        self._hover_anim = None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)

    def enterEvent(self, e):
        """
        Override to suppress the hover fade animation.  The default
        implementation is still called so standard event handling occurs.
        """
        super().enterEvent(e)

    def leaveEvent(self, e):
        """
        Override to suppress the hover fade animation.  The default
        implementation is still called so standard event handling occurs.
        """
        super().leaveEvent(e)


class GroupCard(QFrame):
    def __init__(self, name: str, icon: str = "Home.svg", add_callback=None,
                 rename_callback=None, select_callback=None):
        super().__init__()
        self.base_name = name
        self.add_callback = add_callback
        self.rename_callback = rename_callback
        self.select_callback = select_callback
        self.selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(200, 120)
        radius = 5
        self._radius = radius
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)
        self.label = QLabel(name)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:600 18px '{c.FONT_FAM}'; border:none;")
        lay.addWidget(self.label)
        self.edit = QLineEdit(name)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setVisible(False)
        self.edit.setStyleSheet(
            f"color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}';"
            f"background:{c.CLR_HOVER}; border:2px solid {c.CLR_TITLE};"
            "border-radius:5px; padding:2px;"
        )
        self.edit.returnPressed.connect(self._finish_edit)
        self.edit.editingFinished.connect(self._finish_edit)
        lay.addWidget(self.edit)
        lay.addStretch(1)
        ic = QLabel()
        ic.setPixmap(c.pixmap(icon).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("border:none;")
        lay.addWidget(ic)
        # apply initial style
        self._update_style()
        c.make_shadow(self, 30, 6, 180 if add_callback else 200)

    def _update_style(self):
        border = "#00BFFF" if self.selected else "transparent"
        bg = f"{c.CLR_HOVER}" if self.selected else \
            f"qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c.CLR_HEADER_BG}, stop:1 {c.CLR_HOVER})"
        color = c.CLR_TITLE if self.selected else c.CLR_TEXT_IDLE
        self.setStyleSheet(
            f"""
            QFrame {{
                background:{bg};
                border:2px solid {border};
                border-radius:{self._radius}px;
            }}
            """
        )
        if hasattr(self, "label"):
            self.label.setStyleSheet(f"color:{color}; font:600 18px '{c.FONT_FAM}'; border:none;")

    def set_selected(self, state: bool):
        self.selected = state
        self._update_style()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.add_callback:
                self.add_callback()
            elif self.select_callback:
                self.select_callback(self)
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton and not self.add_callback:
            self._start_edit()
        super().mouseDoubleClickEvent(e)

    def _start_edit(self):
        self.edit.setText(self.label.text())
        self.label.hide()
        self.edit.show()
        self.edit.setFocus()
        self.edit.selectAll()

    def _finish_edit(self):
        new = self.edit.text().strip()
        valid = self.rename_callback(self, new) if self.rename_callback else bool(new)
        if valid:
            self.base_name = new
            self.label.setText(new)
        self.edit.hide()
        self.label.show()


class DeviceRow(QFrame):
    def __init__(self, name: str, group: str,
                 toggle_callback=None, rename_callback=None,
                 icon_override: str | None = None):
        """
        A row representing a controllable device.  Displays an icon, the device
        name (with inline editing support), and a toggle button.  If
        ``icon_override`` is provided it will be used instead of computing
        the icon from the name.  This allows persistent icon selection even
        when devices are renamed.
        """
        super().__init__()
        self.group = group
        self.base_name = name
        self.rename_callback = rename_callback
        self.setFixedHeight(60)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QFrame {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                          stop:0 {c.CLR_HEADER_BG}, stop:1 {c.CLR_HOVER});
                border:2px solid transparent;
                border-radius:5px;
            }}
            """
        )
        # Apply a drop shadow to the row for better contrast against the background.
        c.make_shadow(self, 30, 6, 200)
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 8, 12, 8)
        ic = QLabel()
        # Mapping of keywords to icon filenames.  If no keyword matches, the
        # generic Devices.svg icon will be used.  This mapping mirrors the
        # one used by AnimatedBackground for notifications.
        _icon_map = {
            "Luz": "lightbulb.svg",
            "Luces": "lightbulb.svg",
            "Lámpara": "lamp-desk.svg",
            "Ventilador": "fan.svg",
            "Aire Acondicionado": "air-conditioner.svg",
            "Cortinas": "blinds.svg",
            "Persianas": "blinds.svg",
            "Enchufe": "plug.svg",
            "Extractor": "wind.svg",
            "Calentador Agua": "temperature-high.svg",
            "Espejo": "circle-half-stroke.svg",
            "Ducha": "shower.svg",
            "Televisor": "tv.svg",
            "Consola Juegos": "gamepad.svg",
            "Equipo Sonido": "boombox.svg",
            "Calefactor": "fire.svg",
            "Refrigerador": "refrigerator.svg",
            "Horno": "oven.svg",
            "Microondas": "microwave.svg",
            "Lavavajillas": "washing-machine.svg",
            "Licuadora": "blender.svg",
            "Cafetera": "mug-saucer.svg",
        }
        # Determine which icon to use.  Use the override if provided,
        # otherwise search for a matching keyword in the device name.
        icon_name = icon_override if icon_override else "Devices.svg"
        if not icon_override:
            for key, fname in _icon_map.items():
                if key in name:
                    icon_name = fname
                    break
        # Load and enlarge the pixmap; using a 32×32 size for improved
        # visibility.  Qt.KeepAspectRatio ensures the SVG scales correctly.
        pix = c.pixmap(icon_name).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ic.setPixmap(pix)
        # Fix the QLabel size so the pixmap stays vertically centred within the
        # row (which is 60px high).  Without this the icon may appear aligned
        # to the top.
        ic.setFixedSize(32, 32)
        ic.setAlignment(Qt.AlignVCenter)
        ic.setStyleSheet("border:none;")
        h.addWidget(ic)
        h.addSpacing(8)
        # Device name label (display mode)
        self.label = QLabel(name)
        self.label.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:600 18px '{c.FONT_FAM}'; border:none;")
        # Device name editor (edit mode)
        self.edit = QLineEdit(name)
        self.edit.setAlignment(Qt.AlignLeft)
        self.edit.setStyleSheet(
            f"color:{c.CLR_TITLE}; font:600 18px '{c.FONT_FAM}';"
            f"background:{c.CLR_HOVER}; border:2px solid {c.CLR_TITLE};"
            "border-radius:5px; padding:2px;"
        )
        self.edit.returnPressed.connect(self._finish_edit)
        self.edit.editingFinished.connect(self._finish_edit)
        name_container = QStackedWidget()
        name_container.addWidget(self.label)
        name_container.addWidget(self.edit)
        name_container.setCurrentWidget(self.label)
        self.name_container = name_container
        h.addWidget(name_container)
        h.addStretch(1)
        # Toggle button (on/off)
        self.btn = QPushButton("Apagado")
        self.btn.setCheckable(True)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setFixedWidth(120)
        self.btn.setStyleSheet(
            f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                              stop:0 {c.CLR_HEADER_BG}, stop:1 {c.CLR_SURFACE});
                              border:2px solid {c.CLR_TRACK};border-radius:5px;
                              color:{c.CLR_TEXT_IDLE};font:600 14px '{c.FONT_FAM}';
                              padding:6px 16px; }}
            QPushButton:checked {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                              stop:0 #00BFFF, stop:1 #0066FF); border-color:#00BFFF; color:white; }}
        """
        )
        # Update the button text based on the current toggle state and language
        self.btn.toggled.connect(lambda checked: self.update_button_text())
        if toggle_callback:
            self.btn.toggled.connect(lambda chk, self=self: toggle_callback(self, chk))
        h.addWidget(self.btn)
        # Initial label for the button
        self.update_button_text()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._start_edit()
        super().mouseDoubleClickEvent(e)

    @property
    def name(self):
        return self.label.text()

    def _start_edit(self):
        self.edit.setText(self.label.text())
        self.name_container.setCurrentWidget(self.edit)
        self.edit.setFocus()
        self.edit.selectAll()

    def _finish_edit(self):
        new = self.edit.text().strip()
        valid = self.rename_callback(self, new) if self.rename_callback else bool(new)
        if valid:
            self.base_name = new
            self.label.setText(new)
        self.name_container.setCurrentWidget(self.label)

    def update_button_text(self):
        # traverse up to find parent with 'lang' attribute
        parent = self.parent()
        while parent and not hasattr(parent, 'lang'):
            parent = parent.parent()
        lang = getattr(parent, 'lang', 'es')
        on = 'Encendido' if lang == 'es' else 'On'
        off = 'Apagado' if lang == 'es' else 'Off'
        self.btn.setText(on if self.btn.isChecked() else off)


class FloatingLabelInput(QFrame):
    """Campo con etiqueta flotante con iconos en izquierda/derecha.
    - Soporta left_icon_name y right_icon_name.
    - Para contraseñas: botón candado a la derecha.
    - Alinea iconos derechos en la misma X.
    - Sin contorno nativo del QLineEdit.
    """
    def __init__(self, text: str = "", is_password: bool = False, parent=None,
                 label_px: int = 16, left_icon_name: str | None = None, right_icon_name: str | None = None):
        super().__init__(parent)
        self._active_colour = c.CLR_TITLE
        self._inactive_colour = c.CLR_PLACEHOLDER
        self._text_colour = c.CLR_TEXT_IDLE
        self._focused = False
        self._label_px = label_px
        self._is_password = is_password
        # Increase the size of end icons (e.g., lock and right icons) to 36 px
        self._end_icon_w = 36
        self._end_margin = 6
        self._gap_between_end_icons = 6

        self.line_edit = QLineEdit(self)
        self.line_edit.setEchoMode(QLineEdit.Password if is_password else QLineEdit.Normal)
        self.line_edit.setFrame(False)  # sin borde blanco
        self.line_edit.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{self._text_colour}; font:600 14px '{c.FONT_FAM}'; }}"
        )
        self.line_edit.setPlaceholderText("")

        self.label = QLabel(text, self)
        self.label.setStyleSheet(f"color:{self._inactive_colour}; font:600 {self._label_px}px '{c.FONT_FAM}';")

        # Icono izquierdo
        self.left_icon = None
        self._left_icon_w = 0
        if left_icon_name:
            self.left_icon = QLabel(self)
            self.left_icon.setStyleSheet("background:transparent; border:none;")
            pm = c.pixmap(left_icon_name)
            if not pm.isNull():
                # Increase the left icon to 36 px to match other icons
                self.left_icon.setPixmap(pm.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # Increase the fixed size of the left icon container to accommodate the larger icon
            self.left_icon.setFixedSize(38, 38)
            # Increase reserved width for the left icon accordingly
            self._left_icon_w = 42

        # Icono derecho (e.g., Usuario.svg)
        self.right_icon = None
        self._has_right_icon = False
        if right_icon_name:
            self.right_icon = QLabel(self)
            self.right_icon.setStyleSheet("background:transparent; border:none;")
            rpm = c.pixmap(right_icon_name)
            if not rpm.isNull():
                # Enlarge right icon size to match the new end icon width
                self.right_icon.setPixmap(rpm.scaled(self._end_icon_w, self._end_icon_w, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # Set the fixed size based on the new end icon width
            self.right_icon.setFixedSize(self._end_icon_w, self._end_icon_w)
            self._has_right_icon = True

        # Candado derecho para password
        self.lock_btn = None
        self._has_lock = False
        if is_password:
            self.lock_btn = QToolButton(self)
            self.lock_btn.setCursor(Qt.PointingHandCursor)
            self.lock_btn.setStyleSheet("QToolButton { background:transparent; border:none; }")
            self._icon_locked = QIcon(c.pixmap("Cerrado.svg"))
            self._icon_unlocked = QIcon(c.pixmap("Habierto.svg"))
            self.lock_btn.setIcon(self._icon_locked)
            # Increase lock icon size to match the new end icon width
            self.lock_btn.setIconSize(QSize(self._end_icon_w, self._end_icon_w))
            # Set fixed size based on the new end icon width
            self.lock_btn.setFixedSize(self._end_icon_w, self._end_icon_w)
            self.lock_btn.clicked.connect(self._toggle_password_visibility)
            self._has_lock = True
            self._eye_anim = None

        # Padding derecho del texto según iconos
        end_count = int(self._has_right_icon) + int(self._has_lock)
        self._right_pad = (end_count * self._end_icon_w
                           + max(0, end_count - 1) * self._gap_between_end_icons
                           + self._end_margin + 4)

        # Animación etiqueta
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
        return QSize(260, 60)

    def eventFilter(self, source, event):
        if source is self.line_edit:
            if event.type() == QEvent.FocusIn:
                self._focused = True; self._update_label_state()
            elif event.type() == QEvent.FocusOut:
                self._focused = False; self._update_label_state()
        if source is self or source is self.label:
            if event.type() == QEvent.MouseButtonPress:
                self.line_edit.setFocus()
                self.line_edit.setCursorPosition(len(self.line_edit.text()))
                self._focused = True; self._update_label_state(); return True
        return super().eventFilter(source, event)

    def _toggle_password_visibility(self):
        """
        Toggle the visibility of the password and ensure the lock icon
        does not shrink when switching between the locked and unlocked
        states.  The animation now starts and ends at the same
        dimensions (26×26) so that the icon remains constant in size,
        providing only a brief enlargement for visual feedback.
        """
        if self.line_edit.echoMode() == QLineEdit.Password:
            self.line_edit.setEchoMode(QLineEdit.Normal)
            self.lock_btn.setIcon(self._icon_unlocked)
        else:
            self.line_edit.setEchoMode(QLineEdit.Password)
            self.lock_btn.setIcon(self._icon_locked)
        # Always reset the icon size to the desired default before animating
        self.lock_btn.setIconSize(QSize(self._end_icon_w, self._end_icon_w))
        anim = QPropertyAnimation(self.lock_btn, b"iconSize", self)
        anim.setDuration(180)
        # Start at the final size to avoid shrinking the icon
        anim.setStartValue(QSize(self._end_icon_w, self._end_icon_w))
        # Briefly enlarge the icon mid‑animation for a bounce effect by 6 px
        anim.setKeyValueAt(0.5, QSize(self._end_icon_w + 6, self._end_icon_w + 6))
        # End at the original size
        anim.setEndValue(QSize(self._end_icon_w, self._end_icon_w))
        anim.start()
        self._eye_anim = anim

    def _update_label_state(self):
        has_text = bool(self.line_edit.text())
        target_up = self._focused or has_text
        dest = self._up_pos if target_up else self._down_pos
        new_colour = self._active_colour if target_up else self._inactive_colour
        if self._anim: self._anim.stop(); self._anim = None
        if self.label.pos() != dest:
            self._anim = QPropertyAnimation(self.label, b'pos', self)
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
        w = self.width(); h = self.height()
        label_h = self.label.sizeHint().height()
        # Adjust line height to ensure larger icons fit comfortably. If the end icon width is larger than
        # 30px, add a small margin (4px) so the icons are not clipped.
        line_h = max(30, self._end_icon_w + 4)
        line_y = max(0, h - line_h - 4)
        self.line_edit.setGeometry(0, line_y, w, line_h)
        up_y = 2
        down_y = line_y + max(0, (line_h - label_h) // 2)
        if down_y <= up_y: down_y = up_y + 12
        self._up_pos = QPoint(0, up_y); self._down_pos = QPoint(0, down_y)
        self.label.resize(w, label_h)

        if self.left_icon:
            ix = 2; iy = line_y + (line_h - self.left_icon.height()) // 2
            self.left_icon.move(ix, iy); self.left_icon.show()

        anchor_right = w - self._end_margin
        iy = line_y + (line_h - self._end_icon_w) // 2
        right_x = anchor_right
        def place_end_widget(wdg):
            nonlocal right_x
            if not wdg: return
            wdg.resize(self._end_icon_w, self._end_icon_w)
            right_x -= self._end_icon_w
            wdg.move(right_x, iy)
            wdg.show()
            right_x -= self._gap_between_end_icons
        # Candado al extremo derecho; luego icono de usuario si existe
        place_end_widget(self.lock_btn if getattr(self, '_has_lock', False) else None)
        place_end_widget(self.right_icon if getattr(self, '_has_right_icon', False) else None)

        self.line_edit.setTextMargins(self._left_icon_w, 0, self._right_pad, 0)
        initial = self._up_pos if (self._focused or bool(self.line_edit.text())) else self._down_pos
        self.label.move(initial); self._update_label_state()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        colour = self._active_colour if (self._focused or bool(self.line_edit.text())) else self._inactive_colour
        pen = QPen(QColor(colour)); pen.setWidth(2); p.setPen(pen)
        y = self.height() - 1; p.drawLine(0, y, self.width(), y); p.end()

    def text(self) -> str: return self.line_edit.text()
    def setText(self, text: str): self.line_edit.setText(text)
    def setEchoMode(self, mode): self.line_edit.setEchoMode(mode)


class TriangularBackground(QFrame):
    def __init__(self, orientation: str = 'left', t_ratio: float = 0.7, b_ratio: float = 0.3, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.t_ratio = t_ratio
        self.b_ratio = b_ratio
        self.setStyleSheet("background:transparent;")

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        w = self.width(); h = self.height()
        path = QPainterPath()
        if self.orientation == 'left':
            x_top = self.t_ratio * w; x_bottom = self.b_ratio * w
            path.moveTo(0, 0); path.lineTo(x_top, 0); path.lineTo(x_bottom, h); path.lineTo(0, h); path.closeSubpath()
        else:
            x_top = w * (1 - self.t_ratio); x_bottom = w * (1 - self.b_ratio)
            path.moveTo(x_top, 0); path.lineTo(w, 0); path.lineTo(w, h); path.lineTo(x_bottom, h); path.closeSubpath()
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(c.CLR_TITLE)); grad.setColorAt(1.0, QColor(c.CLR_ITEM_ACT))
        painter.fillPath(path, grad)
        pen = QPen(QColor(c.CLR_TITLE)); pen.setWidth(2); painter.setPen(pen)
        painter.drawLine(int(x_top), 0, int(x_bottom), h)
        painter.end()
