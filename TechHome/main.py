import sys
import random
import csv
import os
from datetime import datetime, timedelta
from PyQt5.QtCore import Qt, QPoint, QTimer, QDate, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QConicalGradient, QPixmap, QIcon, QPainterPath, QLinearGradient
try:
    from PyQt5.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QStackedWidget, QLineEdit, QComboBox, QScrollBar, QTableWidget, QTableWidgetItem, QTabWidget, QListWidget, QListWidgetItem, QDialog, QTextEdit, QDateTimeEdit, QSpinBox, QCalendarWidget, QCheckBox, QStyledItemDelegate, QStyle, QToolButton, QTableView, QHeaderView, QAbstractSpinBox, QSizePolicy, QProgressBar, QGraphicsOpacityEffect
from constants import *

def load_icon_pixmap(name: str, size: QSize) -> QPixmap:
    try:
        p = os.path.join(ICON_DIR, name)
        if os.path.isfile(p):
            ico = QIcon(p)
            pix = ico.pixmap(size)
            if not pix.isNull():
                return pix
    except Exception:
        pass
    base_dir = None
    try:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules', '@fortawesome', 'fontawesome-free', 'svgs', 'solid')
        p2 = os.path.join(base_dir, name)
        if os.path.isfile(p2):
            ico = QIcon(p2)
            pix = ico.pixmap(size)
            if not pix.isNull():
                return pix
    except Exception:
        pass
    fallback_candidates = []
    if base_dir is not None:
        fallback_candidates.append(os.path.join(base_dir, 'circle-info.svg'))
        fallback_candidates.append(os.path.join(base_dir, 'info.svg'))
    try:
        fallback_candidates.append(os.path.join(ICON_DIR, 'info.svg'))
    except Exception:
        pass
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

class MetricGauge(QWidget):

    def __init__(self, icon_name: str, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        base_pix = load_icon_pixmap(icon_name, QSize(64, 64))
        self._icon_tinted = tint_pixmap(base_pix, QColor(CLR_TITLE))
        self._value = 1.0
        self._animation = None
        self.setMinimumSize(120, 120)
        try:
            from PyQt5.QtWidgets import QSizePolicy
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        self.setAttribute(Qt.WA_TranslucentBackground)

    @pyqtProperty(float)
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        self._value = max(0.0, min(1.0, v))
        self.update()

    def setValue(self, v: float, animate: bool=False) -> None:
        v = max(0.0, min(1.0, v))
        if animate:
            if self._animation is not None:
                self._animation.stop()
            anim = QPropertyAnimation(self, b'value')
            anim.setDuration(800)
            anim.setStartValue(self._value)
            anim.setEndValue(v)
            anim.setEasingCurve(QEasingCurve.InOutCubic)
            self._animation = anim
            anim.start()
        else:
            self.value = v

    def paintEvent(self, e) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        off_x = (self.width() - side) / 2.0
        off_y = (self.height() - side) / 2.0
        outer_margin = side * 0.03
        outer_thickness = side * 0.09
        inner_thickness = side * 0.09
        ring_gap = side * 0.025
        outer_rect = QRectF(off_x + outer_margin + outer_thickness / 2.0, off_y + outer_margin + outer_thickness / 2.0, side - 2 * (outer_margin + outer_thickness / 2.0), side - 2 * (outer_margin + outer_thickness / 2.0))
        center = outer_rect.center()
        start_angle = -120.0
        base_grad = QConicalGradient(center, -90.0)
        base_grad.setColorAt(0.0, QColor(0, 90, 180))
        base_grad.setColorAt(0.25, QColor(0, 50, 120))
        base_grad.setColorAt(0.5, QColor(0, 30, 70))
        base_grad.setColorAt(0.75, QColor(0, 50, 120))
        base_grad.setColorAt(1.0, QColor(0, 90, 180))
        base_pen = QPen(QBrush(base_grad), outer_thickness)
        base_pen.setCapStyle(Qt.FlatCap)
        painter.setPen(base_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(outer_rect, 0, -360 * 16)
        delta = outer_thickness / 2.0 + ring_gap + inner_thickness / 2.0
        inner_rect = outer_rect.adjusted(delta, delta, -delta, -delta)
        active_pen = QPen(QColor(0, 200, 255), inner_thickness)
        active_pen.setCapStyle(Qt.FlatCap)
        gap_deg = 50.0
        span_deg = (360.0 - gap_deg) * self.value
        start_angle_qt = int(90.0 * 16)
        span_angle_qt = int(-span_deg * 16)
        painter.setPen(active_pen)
        painter.drawArc(inner_rect, start_angle_qt, span_angle_qt)
        inner_inner_rect = inner_rect.adjusted(inner_thickness / 2.0, inner_thickness / 2.0, -inner_thickness / 2.0, -inner_thickness / 2.0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(CLR_PANEL))
        painter.drawEllipse(inner_inner_rect)
        icon_size = side * 0.45
        pm = self._icon_tinted.scaled(int(icon_size), int(icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ix = off_x + (side - pm.width()) / 2.0
        iy = off_y + (side - pm.height()) / 2.0
        painter.drawPixmap(int(ix), int(iy), pm)
        painter.end()

class GraphWidget(QWidget):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._values: list[float] = []
        self._prev_values: list[float] = []
        self._color: QColor = QColor(0, 200, 255)
        self._anim_progress: float = 1.0
        self._anim: QPropertyAnimation | None = None
        self.setMinimumHeight(50)
        try:
            from PyQt5.QtWidgets import QSizePolicy
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        except Exception:
            pass

    @pyqtProperty(float)
    def animProgress(self) -> float:
        return self._anim_progress

    @animProgress.setter
    def animProgress(self, v: float) -> None:
        self._anim_progress = v
        self.update()

    def setValues(self, values: list[float], color: QColor, *, animate: bool=False) -> None:
        if animate and self._values:
            self._prev_values = list(self._values)
        else:
            self._prev_values = []
        self._values = list(values)
        self._color = color
        if self._anim:
            self._anim.stop()
            self._anim = None
        if animate and self._prev_values:
            self._anim_progress = 0.0
            self._anim = QPropertyAnimation(self, b'animProgress')
            self._anim.setDuration(600)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            try:
                self._anim.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass
            self._anim.start()
        else:
            self._anim_progress = 1.0
            self.update()

    def paintEvent(self, e) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self._values or len(self._values) < 2:
            painter.end()
            return
        w = self.width()
        h = self.height()
        if self._prev_values and self._anim_progress < 1.0:
            values_to_draw: list[float] = []
            for idx in range(len(self._values)):
                new_val = self._values[idx]
                if idx < len(self._prev_values):
                    prev_val = self._prev_values[idx]
                elif self._prev_values:
                    prev_val = self._prev_values[-1]
                else:
                    prev_val = new_val
                val = prev_val + (new_val - prev_val) * self._anim_progress
                values_to_draw.append(val)
        else:
            values_to_draw = self._values
        min_val = min(values_to_draw)
        max_val = max(values_to_draw)
        value_range = max_val - min_val
        if value_range <= 0:
            value_range = 1.0
        line_path = QPainterPath()
        area_path = QPainterPath()
        points: list[tuple[float, float]] = []
        for idx, val in enumerate(values_to_draw):
            x = w * idx / (len(values_to_draw) - 1)
            y = h - h * (val - min_val) / value_range
            points.append((x, y))
        first_x, first_y = points[0]
        area_path.moveTo(first_x, h)
        line_path.moveTo(first_x, first_y)
        area_path.lineTo(first_x, first_y)
        for x, y in points[1:]:
            line_path.lineTo(x, y)
            area_path.lineTo(x, y)
        last_x, last_y = points[-1]
        area_path.lineTo(last_x, h)
        area_path.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        base_color = QColor(self._color)
        top_color = QColor(base_color)
        top_color.setAlphaF(0.6)
        bottom_color = QColor(base_color)
        bottom_color.setAlphaF(0.0)
        grad.setColorAt(0.0, top_color)
        grad.setColorAt(1.0, bottom_color)
        painter.fillPath(area_path, QBrush(grad))
        shadow_pen = QPen(QColor(base_color))
        shadow_pen.setWidthF(4.0)
        shadow_color = QColor(base_color)
        shadow_color.setAlphaF(0.3)
        shadow_pen.setColor(shadow_color)
        shadow_pen.setCapStyle(Qt.RoundCap)
        shadow_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(shadow_pen)
        painter.save()
        painter.translate(0, 2)
        painter.drawPath(line_path)
        painter.restore()
        pen = QPen(base_color, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(line_path)
        painter.end()

class MetricsDetailsDialog(QDialog):

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._main = parent
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        from PyQt5.QtCore import QPoint
        self._drag_offset: QPoint = QPoint()
        outer = QFrame(self)
        outer.setStyleSheet(f'background:{CLR_PANEL}; border:none; border-radius:8px;')
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(16)
        header_container = QWidget(outer)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_label = QLabel('Resumen de Métricas', header_container)
        header_label.setStyleSheet(f"color:{CLR_TITLE}; font:700 28px '{FONT_FAM}';")
        header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        close_btn = QPushButton('', header_container)
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f'\n            QPushButton {{\n                background:transparent;\n                border:2px solid {CLR_TITLE};\n                border-radius:5px;\n            }}\n            QPushButton:hover {{\n                background:{CLR_TITLE};\n            }}\n            ')
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(header_label)
        header_layout.addStretch(1)
        header_layout.addWidget(close_btn)
        outer_layout.addWidget(header_container)
        header_container.mousePressEvent = self._start_drag
        header_container.mouseMoveEvent = self._drag_move
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        self.card_widgets: dict[str, dict[str, QWidget]] = {}
        gauge_specs = [('devices', 'mobile.svg'), ('temp', 'temperature-high.svg'), ('energy', 'bolt.svg'), ('water', 'droplet.svg')]
        for key, icon_name in gauge_specs:
            card = QFrame(outer)
            card.setStyleSheet(f'background:{CLR_SURFACE}; border:none; border-radius:8px;')
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(8)
            gauge = MetricGauge(icon_name)
            gauge.setMinimumSize(160, 160)
            try:
                from PyQt5.QtWidgets import QSizePolicy
                gauge.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            except Exception:
                pass
            card_layout.addWidget(gauge, alignment=Qt.AlignHCenter)
            class_label = QLabel('', card)
            class_label.setAlignment(Qt.AlignCenter)
            class_label.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}';")
            card_layout.addWidget(class_label)
            value_label = QLabel('', card)
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
            card_layout.addWidget(value_label)
            trend_container = QWidget(card)
            trend_layout = QHBoxLayout(trend_container)
            trend_layout.setContentsMargins(0, 0, 0, 0)
            trend_layout.setSpacing(4)
            arrow_label = QLabel(trend_container)
            percent_label = QLabel(trend_container)
            percent_label.setStyleSheet(f"font:500 14px '{FONT_FAM}';")
            trend_layout.addWidget(arrow_label)
            trend_layout.addWidget(percent_label)
            trend_layout.addStretch(1)
            trend_container.setVisible(False)
            card_layout.addWidget(trend_container)
            graph = GraphWidget(card)
            graph.setMinimumHeight(40)
            card_layout.addWidget(graph)
            self.card_widgets[key] = {'gauge': gauge, 'class': class_label, 'value': value_label, 'arrow': arrow_label, 'percent': percent_label, 'graph': graph}
            cards_layout.addWidget(card)
        outer_layout.addLayout(cards_layout)
        border_frame = QFrame(self)
        border_frame.setStyleSheet(f'background:transparent; border:2px solid {CLR_TITLE}; border-radius:10px;')
        border_layout = QVBoxLayout(border_frame)
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.addWidget(outer)
        dlg_layout = QVBoxLayout(self)
        dlg_layout.setContentsMargins(0, 0, 0, 0)
        dlg_layout.addWidget(border_frame)
        self.setLayout(dlg_layout)
        self._trend_up_color = QColor(0, 200, 120)
        self._trend_down_color = QColor(220, 80, 80)
        self._arrow_up_pix = tint_pixmap(load_icon_pixmap('arrow-up.svg', QSize(16, 16)), self._trend_up_color)
        self._arrow_down_pix = tint_pixmap(load_icon_pixmap('arrow-down.svg', QSize(16, 16)), self._trend_down_color)

    def update_metrics(self) -> None:
        metrics = getattr(self._main, 'home_metrics', {})
        history = getattr(self._main, 'metric_history', {})
        total_devices = len(getattr(self._main, 'devices_buttons', []))
        active_devices = metrics.get('devices', 0)
        for key, widgets in self.card_widgets.items():
            curr = metrics.get(key, 0)
            if key == 'devices':
                progress = active_devices / total_devices if total_devices > 0 else 0.0
            elif key == 'temp':
                progress = curr / 40.0 if curr >= 0 else 0.0
            elif key == 'energy':
                progress = curr / 5.0
            elif key == 'water':
                progress = curr / 200.0
            progress = max(0.0, min(1.0, progress))
            widgets['gauge'].setValue(progress, animate=True)
            metric_names = {'devices': 'Dispositivos', 'temp': 'Temperatura', 'energy': 'Energía', 'water': 'Agua'}
            widgets['class'].setText(metric_names.get(key, key))
            if key == 'devices':
                val_text = f'{active_devices} de {total_devices}' if total_devices > 0 else f'{active_devices}'
            elif key == 'temp':
                val_text = f'{curr:.1f}°C'
            elif key == 'energy':
                val_text = f'{curr:.2f} kW'
            elif key == 'water':
                val_text = f'{curr} L'
            widgets['value'].setText(val_text)
            widgets['arrow'].setVisible(False)
            widgets['percent'].setText('')
            widgets['percent'].setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
            graph_color = QColor(CLR_TITLE)
            prev_vals = history.get(key, [])
            graph_values = prev_vals[-12:] if prev_vals else []
            widgets['graph'].setValues(graph_values, graph_color, animate=True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._start_drag(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            self._drag_move(event)
        else:
            super().mouseMoveEvent(event)

    def _start_drag(self, event) -> None:
        from PyQt5.QtCore import QPoint
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _drag_move(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
            event.accept()

class NotificationsDetailsDialog(QDialog):

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._main = parent
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        from PyQt5.QtCore import QPoint
        self._drag_offset: QPoint = QPoint()
        self.current_filter: str = 'Todas'
        self.search_text: str = ''
        outer = QFrame(self)
        outer.setStyleSheet(f'background:{CLR_PANEL}; border:none; border-radius:8px;')
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(16)
        header_container = QWidget(outer)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_label = QLabel('Notificaciones', header_container)
        header_label.setStyleSheet(f"color:{CLR_TITLE}; font:700 28px '{FONT_FAM}';")
        header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        close_btn = QPushButton('', header_container)
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f'\n            QPushButton {{\n                background:transparent;\n                border:2px solid {CLR_TITLE};\n                border-radius:5px;\n            }}\n            QPushButton:hover {{\n                background:{CLR_TITLE};\n            }}\n            ')
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(header_label)
        header_layout.addStretch(1)
        header_layout.addWidget(close_btn)
        outer_layout.addWidget(header_container)
        header_container.mousePressEvent = self._start_drag
        header_container.mouseMoveEvent = self._drag_move
        # Build the category filter buttons container.  Previously
        # the notifications dialog allowed the user to filter by
        # "Todas", "Alertas" and "Recordatorios".  The user has
        # requested to remove this UI so that all notifications are
        # always shown.  We still construct the widget to avoid
        # breaking any internal references but hide it immediately.
        filter_container = QWidget(outer)
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(24)
        categories = ['Todas', 'Alertas', 'Recordatorios']
        self.filter_buttons: dict[str, QPushButton] = {}
        for cat in categories:
            btn = QPushButton(cat, filter_container)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"\n                QPushButton {{\n                    background:transparent;\n                    color:{CLR_TEXT_IDLE};\n                    font:600 16px '{FONT_FAM}';\n                    border:none;\n                    padding-bottom:4px;\n                }}\n                QPushButton:checked {{\n                    color:{CLR_TITLE};\n                    border-bottom:2px solid {CLR_TITLE};\n                }}\n                ")
            btn.clicked.connect(lambda checked, c=cat: self._set_filter(c))
            filter_layout.addWidget(btn)
            self.filter_buttons[cat] = btn
        # default to "Todas" but hide the entire filter UI
        self.filter_buttons['Todas'].setChecked(True)
        outer_layout.addWidget(filter_container)
        # Always show all notifications by hiding the filter buttons
        # container.  Without a visible filter, the current_filter
        # remains "Todas" so update_notifications will display
        # everything.
        filter_container.hide()
        search_container = QWidget(outer)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)
        self.search_edit = QLineEdit(search_container)
        self.search_edit.setPlaceholderText('Buscar')
        # Reduce the height slightly while keeping the internal font size unchanged.
        self.search_edit.setFixedHeight(36)
        # Add extra left padding to accommodate the leading icon (space before text).
        self.search_edit.setStyleSheet(f"background:{CLR_SURFACE}; color:{CLR_TITLE}; font:500 16px '{FONT_FAM}'; padding:6px 12px 6px 36px; border:1px solid {CLR_TRACK}; border-radius:8px;")
        self.search_edit.textChanged.connect(self._on_search_changed)
        # Prepare an icon for the leading position inside the search bar.
        search_pix: QPixmap | None = None
        try:
            # Try the explicit Search.svg first as requested
            for icon_name in ('Search.svg', 'magnifying-glass.svg', 'search.svg', 'magnifying-glass-circle.svg', 'circle-info.svg'):
                tmp = load_icon_pixmap(icon_name, QSize(20, 20))
                if tmp is not None and (not tmp.isNull()):
                    search_pix = tint_pixmap(tmp, QColor(CLR_TITLE))
                    break
        except Exception:
            search_pix = None
        if search_pix is None or search_pix.isNull():
            # Draw a simple magnifying glass fallback if no icon is found
            fallback = QPixmap(20, 20)
            fallback.fill(Qt.transparent)
            try:
                painter = QPainter(fallback)
                painter.setRenderHint(QPainter.Antialiasing)
                pen = QPen(QColor(CLR_TITLE))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawEllipse(4, 4, 10, 10)
                painter.drawLine(13, 13, 18, 18)
                painter.end()
                search_pix = fallback
            except Exception:
                search_pix = fallback
        if search_pix is not None and (not search_pix.isNull()):
            search_icon = QIcon(search_pix)
            # Place the icon inside the QLineEdit on the left side (leading).
            self.search_edit.addAction(search_icon, QLineEdit.LeadingPosition)
        # Only the QLineEdit itself is added to the layout; the action handles the icon.
        search_layout.addWidget(self.search_edit)
        outer_layout.addWidget(search_container)
        self.scroll = QScrollArea(outer)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        try:
            sb = CustomScrollBar(Qt.Vertical)
            sb.setStyleSheet('margin:2px; background:transparent;')
            self.scroll.setVerticalScrollBar(sb)
        except Exception:
            pass
        self.scroll.setStyleSheet('background:transparent;')
        self.scroll.viewport().setStyleSheet('background:transparent;')
        try:
            self.scroll.setViewportMargins(0, 0, 4, 0)
        except Exception:
            pass
        scroll_container = QWidget()
        self.scroll.setWidget(scroll_container)
        self.notif_grid = QGridLayout(scroll_container)
        self.notif_grid.setContentsMargins(0, 0, 0, 0)
        self.notif_grid.setHorizontalSpacing(16)
        self.notif_grid.setVerticalSpacing(16)
        outer_layout.addWidget(self.scroll)
        border_frame = QFrame(self)
        border_frame.setStyleSheet(f'background:transparent; border:2px solid {CLR_TITLE}; border-radius:10px;')
        border_layout = QVBoxLayout(border_frame)
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.addWidget(outer)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        self.update_notifications()
        try:
            size_candidate = None
            mdlg = getattr(parent, 'metrics_dialog', None)
            if mdlg is not None:
                sz = mdlg.sizeHint()
                if sz is None or sz.isEmpty():
                    sz = mdlg.size()
                if not sz.isEmpty():
                    size_candidate = sz
            if size_candidate is None:
                tmp = MetricsDetailsDialog(parent)
                try:
                    tmp.update_metrics()
                except Exception:
                    pass
                sz = tmp.sizeHint()
                if sz is None or sz.isEmpty():
                    sz = tmp.size()
                size_candidate = sz
                tmp.deleteLater()
            if size_candidate is not None and (not size_candidate.isEmpty()):
                min_w = size_candidate.width()
                min_h = size_candidate.height()
                self.setMinimumSize(min_w, min_h)
                self.resize(min_w, min_h)
        except Exception:
            self.setMinimumSize(900, 500)

    def _set_filter(self, category: str) -> None:
        for cat, btn in self.filter_buttons.items():
            btn.setChecked(cat == category)
        self.current_filter = category
        self.update_notifications()

    def _on_search_changed(self, text: str) -> None:
        self.search_text = text
        self.update_notifications()

    def update_notifications(self) -> None:
        while self.notif_grid.count():
            item = self.notif_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        notifications: list[tuple[str, str]] = getattr(self._main, 'notifications', [])
        notifications = notifications[::-1]
        filtered: list[tuple[str, str]] = []
        for ts, text in notifications:
            cat = self._categorise_notification(text)
            if self.current_filter == 'Todas' or cat == self.current_filter:
                translated = self._main._translate_notif(text)
                if self.search_text:
                    if self.search_text.lower() not in translated.lower():
                        continue
                filtered.append((ts, text))
        for idx, (ts, text) in enumerate(filtered):
            row = idx // 2
            col = idx % 2
            card = self._create_notification_card(ts, text)
            self.notif_grid.addWidget(card, row, col)

    def _categorise_notification(self, text: str) -> str:
        t = text
        if t.startswith('Recordatorio') or t.startswith('Reminder'):
            return 'Recordatorios'
        if 'Alarma' in t or 'Alarm' in t:
            return 'Alertas'
        if 'Timer' in t:
            return 'Alertas'
        return 'Alertas'

    def _create_notification_card(self, ts: str, text: str) -> QWidget:
        card = QFrame()
        # Use a fixed height for all notification cards so they appear uniform.
        # A slightly taller container accommodates larger icons and two lines of text.
        # Fix the card size so that all notification cards are 80px high and 380px wide.
        card.setFixedSize(380, 80)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setStyleSheet(f'background:{CLR_SURFACE}; border:none; border-radius:8px;')
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(12)

        # Build a larger icon container.  Increase the diameter to 48px and
        # draw the notification icon slightly larger for better visibility.
        icon_container = QLabel(card)
        # Scale down the icon container to 48px to better fit within the 200px card width.
        icon_container.setFixedSize(48, 48)
        icon_name = self._main._get_notification_icon_name(text)
        try:
            ipix = load_icon_pixmap(icon_name, QSize(28, 28))
        except Exception:
            ipix = load_icon_pixmap(icon_name, QSize(28, 28))
        bg_pix = QPixmap(48, 48)
        bg_pix.fill(Qt.transparent)
        painter = QPainter(bg_pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(CLR_HOVER))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 48, 48)
        if ipix and (not ipix.isNull()):
            x = (48 - ipix.width()) // 2
            y = (48 - ipix.height()) // 2
            painter.drawPixmap(x, y, ipix)
        painter.end()
        icon_container.setPixmap(bg_pix)
        card_layout.addWidget(icon_container)

        # Create a text container with centred labels for the notification message
        # and its relative time.  Align text centrally for a balanced look.
        text_container = QWidget(card)
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        msg_lbl = QLabel(self._main._translate_notif(text), text_container)
        msg_lbl.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}';")
        msg_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        msg_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        time_lbl = QLabel(self._relative_time_str(ts), text_container)
        time_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
        time_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        text_layout.addWidget(msg_lbl)
        text_layout.addWidget(time_lbl)
        card_layout.addWidget(text_container, 1)

        # Keep the redirect button on the right.  Its size remains the same so
        # that the overall card width does not change unpredictably.
        redirect_btn = QPushButton(card)
        redirect_pix = QPixmap()
        try:
            # Load the down-chevron icon at a slightly larger size so it renders crisply when scaled.
            redirect_pix = load_icon_pixmap('square-chevron-down.svg', QSize(28, 28))
        except Exception:
            pass
        if redirect_pix and (not redirect_pix.isNull()):
            redirect_btn.setIcon(QIcon(redirect_pix))
            # Enlarge the arrow icon itself for better visibility.
            redirect_btn.setIconSize(QSize(24, 24))
        redirect_btn.setStyleSheet('background:transparent; border:none; padding:0px; margin:0px;')
        # Increase the button size to accommodate the larger icon while remaining compact.
        redirect_btn.setFixedSize(32, 32)
        redirect_btn.clicked.connect(lambda _, t=text: self._navigate_to_notification_source(t))
        card_layout.addWidget(redirect_btn)
        return card

    def _navigate_to_notification_source(self, text: str) -> None:
        try:
            t = text.strip()
            for suffix in (' Encendido', ' Apagado', ' On', ' Off'):
                if t.endswith(suffix):
                    try:
                        self._main._switch_page(self._main.stack, 1)
                    except Exception:
                        pass
                    self.close()
                    return
            if t.startswith('Recordatorio') or t.startswith('Reminder'):
                try:
                    self._main._switch_page(self._main.stack, 2)
                    page_idx = self._main.more_pages.get('Recordatorios', None)
                    if page_idx is not None:
                        self._main._switch_page(self._main.more_stack, page_idx)
                except Exception:
                    pass
                self.close()
                return
            if 'Alarma' in t or 'Alarm' in t or 'Timer' in t:
                try:
                    self._main._switch_page(self._main.stack, 2)
                    page_idx = self._main.more_pages.get('Alarmas Y Timers', None)
                    if page_idx is not None:
                        self._main._switch_page(self._main.more_stack, page_idx)
                except Exception:
                    pass
                self.close()
                return
            if 'Cámara' in t or 'Camara' in t or 'Camera' in t:
                try:
                    self._main._switch_page(self._main.stack, 2)
                    page_idx = self._main.more_pages.get('Cámaras', None)
                    if page_idx is not None:
                        self._main._switch_page(self._main.more_stack, page_idx)
                except Exception:
                    pass
                self.close()
                return
            self.close()
        except Exception:
            try:
                self.close()
            except Exception:
                pass

    def _relative_time_str(self, ts: str) -> str:
        """
        Return a human-friendly Spanish description of how long ago the given
        time (HH:MM) occurred.  The output capitalises the first word and
        uses singular/plural forms (minuto/minutos, hora/horas, día/días).
        """
        try:
            now = datetime.now()
            # Parse hour and minute from the timestamp string "HH:MM"
            h, m = map(int, ts.split(':'))
            event_dt = datetime(now.year, now.month, now.day, h, m)
            # If the event time is in the future relative to now, assume it was from the previous day.
            if event_dt > now:
                event_dt -= timedelta(days=1)
            delta = now - event_dt
            total_min = int(delta.total_seconds() // 60)
            if total_min < 1:
                return 'Hace 0 minutos'
            if total_min < 60:
                # Minutes ago
                return f"Hace {total_min} minuto{'s' if total_min != 1 else ''}"
            hours = total_min // 60
            if hours < 24:
                # Hours ago
                return f"Hace {hours} hora{'s' if hours != 1 else ''}"
            days = hours // 24
            # Days ago
            return f"Hace {days} día{'s' if days != 1 else ''}"
        except Exception:
            return ''

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._start_drag(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            self._drag_move(event)
        else:
            super().mouseMoveEvent(event)

    def _start_drag(self, event) -> None:
        from PyQt5.QtCore import QPoint
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _drag_move(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
            event.accept()
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from constants import HEALTH_CSV_PATH, CLR_HEADER_BG, CLR_HOVER, CLR_TITLE, CLR_TEXT_IDLE, FONT_FAM, make_shadow, CLR_BG, FRAME_RAD, set_theme_constants, TRANSLATIONS_EN, TRANSLATIONS_ES, MAX_NOTIFICATIONS, HOME_RECENT_COUNT, PANEL_W, CLR_PANEL, CLR_ITEM_ACT, CLR_SURFACE, CLR_TRACK, CLR_HEADER_TEXT, CURRENT_THEME, button_style, icon, input_style, pixmap
from dialogs import NewNoteDialog, NewListDialog, NewElementDialog, SplashScreen, LoginDialog
import database
from widgets import NotesManager, DraggableNote, CustomScrollBar, NoFocusDelegate, style_table, CurrentMonthCalendar, CardButton, QuickAccessButton, GroupCard, DeviceRow
from health import BPMGauge, MetricsPanel

class AnimatedBackground(QWidget):

    def __init__(self, parent=None, *, username: str | None=None, login_time: datetime | None=None):
        super().__init__(parent)
        self.username = username
        self.login_time = login_time
        self.lists = {'Compra': [], 'Tareas': []}
        self.recordatorios = []
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._check_reminders)
        self.reminder_timer.start(60000)
        self.alarms = []
        self.timers = []
        self.timer_update = QTimer(self)
        self.timer_update.timeout.connect(self._update_timers)
        self.timer_update.start(1000)
        self.calendar_widget = None
        self.calendar_event_table = None
        self._angle = 0
        QTimer(self, timeout=self._on_timeout).start(50)
        self.home_metrics = {'devices': 0, 'temp': 22.0, 'energy': 1.2, 'water': 50}
        self.notifications = []
        self.time_24h = True
        self.health_history = []
        try:
            with open(HEALTH_CSV_PATH, newline='', encoding='utf-8') as f:
                for row in csv.reader(f):
                    dt, pa, bpm, spo2, temp, fr = row
                    try:
                        values = (datetime.fromisoformat(dt), pa, int(bpm), int(spo2), float(temp), int(fr))
                    except ValueError:
                        continue
                    self.health_history.append(values)
        except FileNotFoundError:
            pass
        self.popup_label = QLabel('', self)
        self.popup_label.setStyleSheet(f"QLabel {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {CLR_HEADER_BG}, stop:1 {CLR_HOVER}); border:2px solid {CLR_TITLE}; border-radius:5px; padding:8px 12px; color:{CLR_TEXT_IDLE}; font:600 14px '{FONT_FAM}'; }}")
        make_shadow(self.popup_label, 15, 4, 180)
        self.popup_effect = QGraphicsOpacityEffect(self.popup_label)
        self.popup_label.setGraphicsEffect(self.popup_effect)
        self.show_anim = QPropertyAnimation(self.popup_effect, b'opacity')
        self.show_anim.setDuration(300)
        self.hide_anim = QPropertyAnimation(self.popup_effect, b'opacity')
        self.hide_anim.setDuration(300)
        self.hide_anim.finished.connect(self.popup_label.hide)
        self.popup_label.hide()
        self.notifications_enabled = True
        self._device_icon_map: dict[str, str] = {'Luz': 'lightbulb.svg', 'Luces': 'lightbulb.svg', 'Lámpara': 'lamp-desk.svg', 'Ventilador': 'fan.svg', 'Aire Acondicionado': 'air-conditioner.svg', 'Cortinas': 'blinds.svg', 'Persianas': 'blinds.svg', 'Enchufe': 'plug.svg', 'Extractor': 'wind.svg', 'Calentador Agua': 'temperature-high.svg', 'Espejo': 'circle-half-stroke.svg', 'Ducha': 'shower.svg', 'Televisor': 'tv.svg', 'Consola Juegos': 'gamepad.svg', 'Equipo Sonido': 'boombox.svg', 'Calefactor': 'fire.svg', 'Refrigerador': 'refrigerator.svg', 'Horno': 'oven.svg', 'Microondas': 'microwave.svg', 'Lavavajillas': 'washing-machine.svg', 'Licuadora': 'blender.svg', 'Cafetera': 'mug-saucer.svg'}
        self.metric_timer = QTimer(self, timeout=self._update_metrics)
        self.metric_timer.start(5000)
        self.metric_history: dict[str, list[float]] = {'devices': [], 'temp': [], 'energy': [], 'water': []}
        self.metrics_dialog: MetricsDetailsDialog | None = None
        self.notifications_dialog: NotificationsDetailsDialog | None = None
        self.loading_settings: bool = False
        self.from_home_more = False
        self.lang = 'es'
        self.theme = 'dark'
        # Track renamed devices so that notification icons remain consistent even after renaming.
        # Maps new device names to the original base names used for icon lookup.
        self._renamed_devices: dict[str, str] = {}
        # Pre-load any persisted rename mappings before building the UI.  This
        # ensures that device icons can be chosen based on the original base
        # names during initial construction.  Without this pre-load, devices
        # that were renamed in a previous session would be assigned generic
        # icons when the UI is first built.
        if getattr(self, 'username', None):
            try:
                renamed = database.get_renamed_devices(self.username)
                if isinstance(renamed, dict):
                    self._renamed_devices.update(renamed)
            except Exception:
                pass

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(0)
        card = QFrame(self)
        card.setObjectName('card')
        card.setStyleSheet(f'QFrame#card {{ background:{CLR_BG}; border-radius:{FRAME_RAD}px; }}')
        lay.addWidget(card)
        self.card = card
        self._style_popup_label()
        self.popup_label.raise_()
        self._build_ui(card)
        self._apply_language()
        if getattr(self, 'username', None):
            try:
                self._load_user_settings()
            except Exception as e:
                print(f'Error loading settings: {e}')
        if getattr(self, 'username', None):
            try:
                self._load_persistent_state()
            except Exception as e:
                print(f'Error restoring state: {e}')
            try:
                self._refresh_account_info()
            except Exception as e:
                print(f'Error updating account info: {e}')
            # After restoring state and account info, load any persisted notifications
            # from the user's database.  This ensures notifications from previous
            # sessions are displayed on the home screen and in the details dialog.
            if getattr(self, 'username', None):
                try:
                    # Retrieve all stored notifications.  These are returned as
                    # (timestamp, message) tuples ordered from oldest to newest.
                    self.notifications = database.get_notifications(self.username)
                except Exception:
                    # On failure, keep the existing in‑memory notifications list
                    pass
                # Load any persisted rename mappings to reconstruct the
                # original base names for devices.  This allows
                # _get_notification_icon_name to choose the correct icon even
                # after renaming devices across sessions.
                try:
                    renamed = database.get_renamed_devices(self.username)
                    if hasattr(self, '_renamed_devices') and isinstance(renamed, dict):
                        self._renamed_devices.update(renamed)
                except Exception:
                    pass
                # Trim the in‑memory list to the maximum allowed size
                try:
                    from constants import MAX_NOTIFICATIONS
                    if isinstance(self.notifications, list):
                        self.notifications = self.notifications[-MAX_NOTIFICATIONS:]
                except Exception:
                    # Default to 100 notifications if constants import fails
                    if isinstance(self.notifications, list):
                        self.notifications = self.notifications[-100:]
                # Refresh the home notifications panel to display loaded notifications
                try:
                    self._refresh_home_notifications()
                except Exception:
                    pass

    def _on_timeout(self):
        self._angle = (self._angle + 1) % 360
        self.update()

    def current_time(self, sec=False):
        fmt = '%H:%M:%S' if sec else '%H:%M'
        if not self.time_24h:
            fmt = '%I:%M:%S %p' if sec else '%I:%M %p'
        return datetime.now().strftime(fmt)

    def format_datetime(self, dt, sec=False):
        fmt = '%d/%m/%Y ' + ('%H:%M:%S' if sec else '%H:%M')
        if not self.time_24h:
            fmt = '%d/%m/%Y ' + ('%I:%M:%S %p' if sec else '%I:%M %p')
        return dt.strftime(fmt)

    def _set_time_format(self, is24):
        if not getattr(self, 'loading_settings', False) and getattr(self, 'username', None):
            try:
                database.save_setting(self.username, 'time_24h', '1' if is24 else '0')
            except Exception:
                pass
        self.time_24h = is24
        if hasattr(self, 'home_time_label'):
            self.home_time_label.setText(self.current_time())

    def _set_theme(self, theme):
        if self.theme == theme:
            return
        if not getattr(self, 'loading_settings', False) and getattr(self, 'username', None):
            try:
                database.save_setting(self.username, 'theme', theme)
            except Exception:
                pass
        notes_data = []
        for n in getattr(self, 'notes_items', []):
            notes_data.append((n.text, n.timestamp, n._cell))
        current_list = getattr(self, 'list_title', None)
        selected_name = current_list.text() if current_list else None
        self.theme = theme
        set_theme_constants(theme)
        layout = self.layout()
        if self.card:
            layout.removeWidget(self.card)
            self.card.deleteLater()
        card = QFrame(self)
        card.setObjectName('card')
        card.setStyleSheet(f'QFrame#card {{ background:{CLR_BG}; border-radius:{FRAME_RAD}px; }}')
        layout.addWidget(card)
        self.card = card
        self._build_ui(card)
        self._apply_language()
        self._restore_lists(selected_name)
        self._restore_notes(notes_data)
        self._style_popup_label()
        self.popup_label.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, 'popup_label'):
            try:
                x = self.width() - self.popup_label.width() - 40
                y = 20
                if x < 0:
                    x = 0
                self.popup_label.move(x, y)
            except Exception:
                pass

    def _toggle_notifications(self, enabled):
        if not getattr(self, 'loading_settings', False) and getattr(self, 'username', None):
            try:
                database.save_setting(self.username, 'notifications_enabled', '1' if enabled else '0')
            except Exception:
                pass
        self.notifications_enabled = enabled
        if not enabled:
            self.popup_label.hide()

    def _on_device_category_changed(self, index: int) -> None:
        if getattr(self, 'loading_settings', False):
            return
        user = getattr(self, 'username', None)
        if not user:
            return
        try:
            text = self.device_category_cb.itemText(index)
            database.save_setting(user, 'device_category', text)
        except Exception:
            pass

    def _on_device_sort_changed(self, index: int) -> None:
        if getattr(self, 'loading_settings', False):
            return
        user = getattr(self, 'username', None)
        if not user:
            return
        try:
            text = self.device_sort_cb.itemText(index)
            database.save_setting(user, 'device_sort_order', text)
        except Exception:
            pass

    def _switch_page(self, stack, index):
        if index == stack.currentIndex():
            return
        effect = QGraphicsOpacityEffect(stack)
        stack.setGraphicsEffect(effect)
        anim_out = QPropertyAnimation(effect, b'opacity', stack)
        anim_out.setDuration(300)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)

        def on_faded():
            stack.setCurrentIndex(index)
            anim_in = QPropertyAnimation(effect, b'opacity', stack)
            anim_in.setDuration(300)
            anim_in.setStartValue(0.0)
            anim_in.setEndValue(1.0)
            anim_in.finished.connect(lambda: stack.setGraphicsEffect(None))
            anim_in.start()
        anim_out.finished.connect(on_faded)
        anim_out.start()

    def _change_language(self, lang):
        if self.lang == lang:
            return
        if not getattr(self, 'loading_settings', False) and getattr(self, 'username', None):
            try:
                database.save_setting(self.username, 'language', lang)
            except Exception:
                pass
        self.lang = lang
        self._apply_language()

    def _translate_name(self, name, mapping):
        if name in mapping:
            return mapping[name]
        if self.lang == 'en':
            if name.startswith('Grupo Nuevo'):
                suf = name[11:].strip()
                return f"New Group{suf and ' ' + suf}"
            if name.startswith('Nuevo Dispositivo'):
                suf = name[17:].strip()
                return f"New Device{suf and ' ' + suf}"
        else:
            if name.startswith('New Group'):
                suf = name[8:].strip()
                return f"Grupo Nuevo{suf and ' ' + suf}"
            if name.startswith('New Device'):
                suf = name[10:].strip()
                return f"Nuevo Dispositivo{suf and ' ' + suf}"
        return name

    def _apply_language(self):
        mapping = TRANSLATIONS_EN if self.lang == 'en' else TRANSLATIONS_ES
        for w in self.findChildren((QLabel, QPushButton, QCheckBox, QToolButton)):
            txt = w.text()
            if txt in mapping:
                w.setText(mapping[txt])
        for w in self.findChildren(QLineEdit):
            ph = w.placeholderText()
            if ph in mapping:
                w.setPlaceholderText(mapping[ph])
        for combo in self.findChildren(QComboBox):
            for i in range(combo.count()):
                t = combo.itemText(i)
                if t in mapping:
                    combo.setItemText(i, mapping[t])
        for tab in self.findChildren(QTabWidget):
            for i in range(tab.count()):
                t = tab.tabText(i)
                if t in mapping:
                    tab.setTabText(i, mapping[t])
        for btn in getattr(self, 'buttons', []):
            base = getattr(btn, 'base_text', btn.text().strip())
            btn.setText(f'   {mapping.get(base, base)}')
        for card in getattr(self, 'group_cards', []):
            card.label.setText(self._translate_name(card.base_name, mapping))
        if hasattr(self, 'add_group_card'):
            self.add_group_card.label.setText(self._translate_name(self.add_group_card.base_name, mapping))
        for row in getattr(self, 'device_rows', []):
            row.label.setText(self._translate_name(row.base_name, mapping))
            row.update_button_text()
        if hasattr(self, 'group_indicator'):
            prefix = 'Current Group:' if self.lang == 'en' else 'Grupo Actual:'
            name = self._translate_name(self.active_group, mapping)
            self.group_indicator.setText(f'{prefix} {name}')
        tables = {'table_recordatorios': ['Fecha Y Hora', 'Mensaje'], 'table_alarms': ['Fecha Y Hora', 'Etiqueta'], 'table_timers': ['Etiqueta', 'Restante'], 'notif_table': ['Hora', 'Mensaje'], 'table_health': ['Fecha', 'PA', 'BPM', 'SpO₂', 'Temp', 'FR']}
        for attr, headers in tables.items():
            tbl = getattr(self, attr, None)
            if tbl:
                tbl.setHorizontalHeaderLabels([mapping.get(h, h) for h in headers])
        if hasattr(self, 'table_recordatorios'):
            self._populate_record_table()
        if hasattr(self, 'table_alarms'):
            self._populate_alarm_table()
        if hasattr(self, 'table_timers'):
            self._populate_timer_table()
        if hasattr(self, 'notif_table'):
            self._populate_notif_table()
        if hasattr(self, 'table_health'):
            self._populate_health_table()

    def _translate_notif(self, text):
        mapping = TRANSLATIONS_EN if self.lang == 'en' else TRANSLATIONS_ES
        if text in mapping:
            return mapping[text]
        if self.lang == 'en':
            if text.startswith('Recordatorio: '):
                return f"Reminder: {text.split(': ', 1)[1]}"
            if text.startswith('Timer ') and text.endswith(' Completado'):
                lbl = text[6:-11]
                return f'Timer {lbl} Completed'
            if text.endswith(' Encendido') or text.endswith(' Apagado'):
                name, state = text.rsplit(' ', 1)
                name = self._translate_name(name, mapping)
                state = mapping.get(state, state)
                return f'{name} {state}'
        else:
            if text.startswith('Reminder: '):
                return f"Recordatorio: {text.split(': ', 1)[1]}"
            if text.startswith('Timer ') and text.endswith(' Completed'):
                lbl = text[6:-9]
                return f'Timer {lbl} Completado'
            if text.endswith(' On') or text.endswith(' Off'):
                name, state = text.rsplit(' ', 1)
                name = self._translate_name(name, mapping)
                state = mapping.get(state, state)
                return f'{name} {state}'
        return text

    def _get_notification_icon_name(self, text: str) -> str:
        if not text:
            return 'info.svg'
        t = text.strip()
        for suffix in (' Encendido', ' Apagado', ' On', ' Off'):
            if t.endswith(suffix):
                name = t[:-len(suffix)].strip()
                # If this device has been renamed, use the original base name for icon lookup
                try:
                    original = name
                    if hasattr(self, '_renamed_devices'):
                        original = self._renamed_devices.get(name, name)
                except Exception:
                    original = name
                icon_name = 'Devices.svg'
                for key, fname in self._device_icon_map.items():
                    # Match against the original name to preserve the icon assignment
                    if key in original:
                        icon_name = fname
                        break
                return icon_name
        if t.startswith('Recordatorio') or t.startswith('Reminder'):
            return 'bell.svg'
        if 'Alarma' in t or 'Alarm' in t:
            return 'alarm-clock.svg'
        if 'Timer' in t:
            return 'hourglass-half.svg'
        return 'info.svg'

    def _style_popup_label(self):
        self.popup_label.setStyleSheet(f"QLabel {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {CLR_HEADER_BG}, stop:1 {CLR_HOVER}); border:2px solid {CLR_TITLE}; border-radius:5px; padding:8px 12px; color:{CLR_TEXT_IDLE}; font:600 14px '{FONT_FAM}'; }}")
        make_shadow(self.popup_label, 15, 4, 180)

    def _add_notification(self, text):
        # Do not add a notification if notifications are disabled
        if not self.notifications_enabled:
            return
        # Compute the current timestamp string (with seconds) used for display
        ts = self.current_time(True)
        # Persist the notification to the user's database, if a username is set.
        # This call also prunes older notifications beyond MAX_NOTIFICATIONS.
        user = getattr(self, 'username', None)
        if user:
            try:
                database.save_notification(user, ts, text)
            except Exception:
                # Ignore database errors; the notification will still be shown in memory
                pass
        # Append the notification to the in‑memory list and trim to the maximum
        # allowed number.  Keeping the list to at most MAX_NOTIFICATIONS in
        # memory prevents unbounded growth and mirrors the database pruning.
        self.notifications.append((ts, text))
        try:
            from constants import MAX_NOTIFICATIONS
            self.notifications = self.notifications[-MAX_NOTIFICATIONS:]
        except Exception:
            # Fallback: keep last 100 notifications if constant import fails
            self.notifications = self.notifications[-100:]
        # Update the home panel with the newest notifications
        try:
            self._refresh_home_notifications()
        except Exception:
            pass
        # If the notifications details page is visible, refresh its table
        try:
            if self.stack.currentIndex() == 2 and self.more_stack.currentIndex() == 5:
                self._populate_notif_table()
        except Exception:
            pass
        # Prepare and display the popup.  Translate the message text using
        # the current language settings for readability.
        display = self._translate_notif(text)
        icon_name = self._get_notification_icon_name(text)
        icon_path = os.path.join(ICON_DIR, icon_name) if os.path.isabs(ICON_DIR) else os.path.join(ICON_DIR, icon_name)
        self.popup_label.setTextFormat(Qt.RichText)
        rich_text = f"<img src='{icon_path}' width='20' height='20' style='vertical-align:middle;margin-right:6px;'/> {display}"
        self.popup_label.setText(rich_text)
        self.popup_label.adjustSize()
        try:
            parent_width = self.parent().width() if self.parent() else self.width()
        except Exception:
            parent_width = self.width()
        x = parent_width - self.popup_label.width() - 40
        if x < 0:
            x = 0
        self.popup_label.move(x, 20)
        self.hide_anim.stop()
        self.popup_label.show()
        self.show_anim.setStartValue(0.0)
        self.show_anim.setEndValue(1.0)
        self.show_anim.start()
        QTimer.singleShot(3000, lambda: (self.hide_anim.setStartValue(1.0), self.hide_anim.setEndValue(0.0), self.hide_anim.start()))
        try:
            if hasattr(self, 'notifications_dialog') and self.notifications_dialog is not None:
                if self.notifications_dialog.isVisible():
                    self.notifications_dialog.update_notifications()
        except Exception:
            pass

    def _check_reminders(self):
        now = datetime.now()
        due = [(dt, txt) for dt, txt in self.recordatorios if dt <= now]
        for dt, txt in due:
            self.recordatorios.remove((dt, txt))
            if self.notifications_enabled:
                mapping = TRANSLATIONS_EN if self.lang == 'en' else {}
                self.popup_label.setText('🔔 ' + mapping.get(txt, txt))
                self.popup_label.adjustSize()
                try:
                    parent_width = self.parent().width() if self.parent() else self.width()
                except Exception:
                    parent_width = self.width()
                x = parent_width - self.popup_label.width() - 40
                if x < 0:
                    x = 0
                self.popup_label.move(x, 20)
                self.hide_anim.stop()
                self.popup_label.show()
                self.show_anim.setStartValue(0.0)
                self.show_anim.setEndValue(1.0)
                self.show_anim.start()
                QTimer.singleShot(3000, lambda: (self.hide_anim.setStartValue(1.0), self.hide_anim.setEndValue(0.0), self.hide_anim.start()))
                self._add_notification(f'Recordatorio: {txt}')
        if self.stack.currentIndex() == 2 and self.more_stack.currentIndex() == 2:
            self._populate_record_table()
        if due:
            self._refresh_calendar_events()

    def _add_recordatorio(self):
        text = self.input_record_text.text().strip()
        dt = self.input_record_datetime.dateTime().toPyDateTime()
        if text and dt:
            self.recordatorios.append((dt, text))
            self._populate_record_table()
            self.input_record_text.clear()
            self.input_record_datetime.setDateTime(datetime.now())
            self._add_notification('Recordatorio Añadido')
            self._refresh_calendar_events()
            if hasattr(self, 'username') and self.username:
                try:
                    database.save_reminder(self.username, dt.isoformat(), text)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Recordatorio añadido: {text} @ {dt.isoformat()}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _populate_record_table(self):
        data = sorted(self.recordatorios, key=lambda x: x[0])
        tbl = self.table_recordatorios
        tbl.setRowCount(len(data))
        for i, (dt, txt) in enumerate(data):
            tbl.setItem(i, 0, QTableWidgetItem(dt.strftime('%Y-%m-%d %H:%M')))
            tbl.setItem(i, 1, QTableWidgetItem(txt))

    def _delete_selected_recordatorio(self):
        row = self.table_recordatorios.currentRow()
        if 0 <= row < len(self.recordatorios):
            data = sorted(self.recordatorios, key=lambda x: x[0])
            dt, txt = data[row]
            self.recordatorios.remove((dt, txt))
            self._populate_record_table()
            self._add_notification('Recordatorio Eliminado')
            self._refresh_calendar_events()
            if hasattr(self, 'username') and self.username:
                try:
                    database.delete_reminder(self.username, dt.isoformat(), txt)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Recordatorio eliminado: {txt}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _update_timers(self):
        now = datetime.now()
        updated = []
        for end_dt, txt in list(self.timers):
            if now >= end_dt:
                if self.notifications_enabled:
                    mapping = TRANSLATIONS_EN if self.lang == 'en' else {}
                    self.popup_label.setText('⏰ ' + mapping.get(txt, txt))
                    self.popup_label.adjustSize()
                    try:
                        parent_width = self.parent().width() if self.parent() else self.width()
                    except Exception:
                        parent_width = self.width()
                    x = parent_width - self.popup_label.width() - 40
                    if x < 0:
                        x = 0
                    self.popup_label.move(x, 20)
                    self.hide_anim.stop()
                    self.popup_label.show()
                    self.show_anim.setStartValue(0.0)
                    self.show_anim.setEndValue(1.0)
                    self.show_anim.start()
                    QTimer.singleShot(3000, lambda: (self.hide_anim.setStartValue(1.0), self.hide_anim.setEndValue(0.0), self.hide_anim.start()))
                    self._add_notification(f'Timer {txt} Completado')
            else:
                updated.append((end_dt, txt))
        self.timers = updated
        if self.stack.currentIndex() == 2 and self.more_stack.currentIndex() == 3:
            self._populate_timer_table()

    def _add_alarm(self):
        text = self.input_alarm_text.text().strip()
        dt = self.input_alarm_datetime.dateTime().toPyDateTime()
        if text and dt:
            self.alarms.append((dt, text))
            self._populate_alarm_table()
            self.input_alarm_text.clear()
            self.input_alarm_datetime.setDateTime(datetime.now())
            self._add_notification('Alarma Añadida')
            self._refresh_calendar_events()
            if hasattr(self, 'username') and self.username:
                try:
                    database.save_alarm(self.username, dt.isoformat(), text)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Alarma añadida: {text} @ {dt.isoformat()}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _populate_alarm_table(self):
        data = sorted(self.alarms, key=lambda x: x[0])
        tbl = self.table_alarms
        tbl.setRowCount(len(data))
        for i, (dt, txt) in enumerate(data):
            tbl.setItem(i, 0, QTableWidgetItem(dt.strftime('%Y-%m-%d %H:%M')))
            tbl.setItem(i, 1, QTableWidgetItem(txt))

    def _delete_selected_alarm(self):
        row = self.table_alarms.currentRow()
        if 0 <= row < len(self.alarms):
            data = sorted(self.alarms, key=lambda x: x[0])
            dt, txt = data[row]
            self.alarms.remove((dt, txt))
            self._populate_alarm_table()
            self._add_notification('Alarma Eliminada')
            self._refresh_calendar_events()
            if hasattr(self, 'username') and self.username:
                try:
                    database.delete_alarm(self.username, dt.isoformat(), txt)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Alarma eliminada: {txt}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _add_timer(self):
        seconds = self.input_timer_seconds.value()
        txt = self.input_timer_text.text().strip() or 'Timer'
        if seconds > 0:
            end = datetime.now() + timedelta(seconds=seconds)
            self.timers.append((end, txt))
            self._populate_timer_table()
            self.input_timer_seconds.setValue(0)
            self.input_timer_text.clear()
            self._add_notification('Timer Añadido')
            if hasattr(self, 'username') and self.username:
                try:
                    database.save_timer(self.username, end.isoformat(), txt)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Timer añadido: {txt} ({seconds} s)')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _populate_timer_table(self):
        data = list(self.timers)
        tbl = self.table_timers
        tbl.setRowCount(len(data))
        for i, (end_dt, txt) in enumerate(data):
            remain = max(0, int((end_dt - datetime.now()).total_seconds()))
            tbl.setItem(i, 0, QTableWidgetItem(f'{txt}'))
            tbl.setItem(i, 1, QTableWidgetItem(f'{remain} s'))

    def _delete_selected_timer(self):
        row = self.table_timers.currentRow()
        if 0 <= row < len(self.timers):
            timer_desc = self.timers[row][1] if row < len(self.timers) else 'Timer'
            end_dt, txt = self.timers[row]
            del self.timers[row]
            self._populate_timer_table()
            self._add_notification('Timer Eliminado')
            if hasattr(self, 'username') and self.username:
                try:
                    database.delete_timer(self.username, end_dt.isoformat(), txt)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Timer eliminado: {txt}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _populate_notif_table(self):
        data = self.notifications
        tbl = self.notif_table
        tbl.setRowCount(len(data))
        for i, (ts, txt) in enumerate(data):
            tbl.setItem(i, 0, QTableWidgetItem(ts))
            icon_name = self._get_notification_icon_name(txt)
            icon_path = os.path.join(ICON_DIR, icon_name) if os.path.isabs(ICON_DIR) else os.path.join(ICON_DIR, icon_name)
            item = QTableWidgetItem(self._translate_notif(txt))
            if os.path.exists(icon_path):
                item.setIcon(QIcon(icon_path))
            tbl.setItem(i, 1, item)

    def _populate_health_table(self):
        data = self.health_history
        tbl = self.table_health
        tbl.setRowCount(len(data))
        for i, (dt, pa, bpm, spo2, temp, fr) in enumerate(data):
            values = [dt.strftime('%Y-%m-%d %H:%M'), pa, bpm, spo2, temp, fr]
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(i, j, item)
            tbl.setRowHeight(i, 32)

    def _refresh_home_notifications(self):
        # Slice the last ``HOME_RECENT_COUNT`` notifications and reverse
        # the order so the most recent notification appears at the top.
        # When the notifications list is ordered from oldest to newest,
        # reversing the slice results in a descending chronological
        # display (newest first).
        recent = self.notifications[-HOME_RECENT_COUNT:][::-1]
        for i, row in enumerate(self.home_notif_rows):
            icon_lbl, text_lbl = row
            if i < len(recent):
                ts, txt = recent[i]
                # Derive the icon based on the notification text (after renaming and
                # translation).  ``_get_notification_icon_name`` accounts for
                # renamed devices by looking up the original base name.
                icon_name = self._get_notification_icon_name(txt)
                # Resolve the path to the icon within the Icons directory.  If
                # ``ICON_DIR`` is relative, join it with the filename.
                icon_path = os.path.join(ICON_DIR, icon_name) if os.path.isabs(ICON_DIR) else os.path.join(ICON_DIR, icon_name)
                pix = QPixmap(icon_path)
                if not pix.isNull():
                    pix = pix.scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon_lbl.setPixmap(pix)
                else:
                    icon_lbl.clear()
                # Show the translated notification text.  Use a single-line display
                # since the home screen has limited space.
                text_lbl.setText(self._translate_notif(txt))
            else:
                # If there are fewer notifications than display rows, fill with
                # placeholder dashes.
                icon_lbl.clear()
                text_lbl.setText('--')

    def _update_metrics(self):
        self.home_metrics['devices'] = sum((btn.isChecked() for btn in self.devices_buttons))
        self.home_metrics['temp'] = round(random.uniform(20.0, 25.0), 1)
        self.home_metrics['energy'] = round(random.uniform(0.5, 2.5), 2)
        self.home_metrics['water'] = random.randint(30, 200)
        if hasattr(self, 'home_metric_gauges'):
            total_devices = len(getattr(self, 'devices_buttons', []))
            active_devices = self.home_metrics.get('devices', 0)
            for key, gauge in self.home_metric_gauges.items():
                val = self.home_metrics.get(key, 0)
                hist = self.metric_history.setdefault(key, [])
                hist.append(val)
                if len(hist) > 48:
                    hist.pop(0)
                progress = 0.0
                if key == 'devices':
                    progress = active_devices / total_devices if total_devices > 0 else 0.0
                elif key == 'temp':
                    progress = val / 40.0 if val >= 0 else 0.0
                elif key == 'energy':
                    progress = val / 5.0
                elif key == 'water':
                    progress = val / 200.0
                progress = max(0.0, min(1.0, progress))
                gauge.setValue(progress, animate=True)
        if getattr(self, 'metrics_dialog', None) is not None and self.metrics_dialog.isVisible():
            try:
                self.metrics_dialog.update_metrics()
            except Exception:
                pass

    def _device_toggled(self, row, checked):
        self._update_metrics()
        state = 'Encendido' if checked else 'Apagado'
        self._add_notification(f'{row.base_name} {state}')
        if hasattr(self, 'username') and self.username:
            try:
                database.log_action(self.username, f"Dispositivo '{row.base_name}' {state}")
            except Exception:
                pass
        if hasattr(self, 'username') and self.username:
            try:
                database.save_device_state(self.username, row.base_name, row.group, checked)
            except Exception:
                pass
        try:
            self._refresh_account_info()
        except Exception:
            pass

    def _open_more_section(self, name, from_home=False):
        if hasattr(self, 'more_pages') and name in self.more_pages:
            if name == 'Notificaciones':
                self._populate_notif_table()
            elif name == 'Historial De Salud':
                self._populate_health_table()
            self.from_home_more = from_home
            self._switch_page(self.stack, 2)
            self._switch_page(self.more_stack, self.more_pages[name])
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Sección abierta: {name}')
                except Exception:
                    pass

    def _back_from_more(self):
        if getattr(self, 'from_home_more', False):
            self._switch_page(self.stack, 0)
            self.from_home_more = False
        self._switch_page(self.more_stack, 0)

    def _record_health_history(self, pa, bpm, spo2, temp, fr):
        now = datetime.now()
        self.health_history.append((now, pa, bpm, spo2, temp, fr))
        with open(HEALTH_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([now.isoformat(), pa, bpm, spo2, temp, fr])
        if self.stack.currentIndex() == 2 and self.more_stack.currentIndex() == 7:
            self._populate_health_table()
        self._add_notification('Diagnóstico Registrado')
        if hasattr(self, 'username') and self.username:
            try:
                database.log_action(self.username, 'Historial de salud registrado')
            except Exception:
                pass

    def _open_metrics_details(self) -> None:
        if self.metrics_dialog is None:
            # Create the metrics dialog if it doesn't exist yet.
            self.metrics_dialog = MetricsDetailsDialog(self)
        # Refresh the metrics displayed within the dialog.  Wrap in a
        # try/except to avoid crashes if an update fails.
        try:
            self.metrics_dialog.update_metrics()
        except Exception:
            pass
        # Position the dialog in the same location used for other external
        # windows (e.g., the notifications details dialog).  Center it
        # relative to the main window so it appears consistently.  Use
        # the sizeHint to determine an appropriate size if needed.
        try:
            parent = self.window()
            dlg = self.metrics_dialog
            if parent is not None and dlg is not None:
                # Ensure the dialog has a reasonable size before centering
                sz = dlg.sizeHint()
                if sz is None or sz.isEmpty():
                    sz = dlg.size()
                if sz is not None and (not sz.isEmpty()):
                    try:
                        dlg.resize(sz)
                    except Exception:
                        pass
                # Compute coordinates to center the dialog over the parent
                x = parent.x() + (parent.width() - dlg.width()) // 2
                y = parent.y() + (parent.height() - dlg.height()) // 2
                dlg.move(x, y)
        except Exception:
            pass
        # Finally show the dialog
        self.metrics_dialog.show()

    def _open_notifications_details(self) -> None:
        if not hasattr(self, 'notifications_dialog') or self.notifications_dialog is None:
            self.notifications_dialog = NotificationsDetailsDialog(self)
        try:
            self.notifications_dialog.update_notifications()
        except Exception:
            pass
        target_size = None
        try:
            mdlg = getattr(self, 'metrics_dialog', None)
            if mdlg is not None:
                sz = mdlg.sizeHint()
                if sz is None or sz.isEmpty():
                    sz = mdlg.size()
                if sz is not None and (not sz.isEmpty()):
                    target_size = sz
            if target_size is None:
                tmp = MetricsDetailsDialog(self)
                try:
                    tmp.update_metrics()
                except Exception:
                    pass
                sz = tmp.sizeHint()
                if sz is None or sz.isEmpty():
                    sz = tmp.size()
                target_size = sz
                tmp.deleteLater()
        except Exception:
            target_size = None
        if target_size is not None and (not target_size.isEmpty()):
            try:
                self.notifications_dialog.resize(target_size)
            except Exception:
                pass
        try:
            parent = self.window()
            if parent is not None:
                x = parent.x() + (parent.width() - self.notifications_dialog.width()) // 2
                y = parent.y() + (parent.height() - self.notifications_dialog.height()) // 2
                self.notifications_dialog.move(x, y)
        except Exception:
            pass
        self.notifications_dialog.show()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QConicalGradient(QPointF(self.width() / 2, self.height() / 2), self._angle)
        if CURRENT_THEME == 'light':
            colors = [(0, QColor(255, 255, 255)), (0.25, QColor(224, 224, 224)), (0.5, QColor(255, 255, 255)), (0.75, QColor(224, 224, 224)), (1.0, QColor(255, 255, 255))]
        else:
            colors = [(0, QColor(7, 16, 27)), (0.25, QColor(20, 30, 60)), (0.5, QColor(7, 16, 27)), (0.75, QColor(20, 30, 60)), (1.0, QColor(7, 16, 27))]
        for pos, ccol in colors:
            grad.setColorAt(pos, ccol)
        p.fillRect(self.rect(), grad)

    def _build_ui(self, container):
        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        panel = QFrame()
        panel.setFixedWidth(PANEL_W)
        panel.setStyleSheet(f'background:{CLR_PANEL}; border-radius:{FRAME_RAD}px;')
        vp = QVBoxLayout(panel)
        vp.setContentsMargins(20, 16, 20, 16)
        vp.setSpacing(16)
        lbl_title = QLabel('TechHome')
        lbl_title.setStyleSheet(f"color:{CLR_TITLE}; font:700 32px '{FONT_FAM}';")
        vp.addWidget(lbl_title, alignment=Qt.AlignHCenter | Qt.AlignTop)
        menu_w = QWidget()
        menu_l = QVBoxLayout(menu_w)
        menu_l.setContentsMargins(0, 0, 0, 0)
        menu_l.setSpacing(16)
        self.buttons = []
        menu_items = [('Inicio', 'Home.svg'), ('Dispositivos', 'Devices.svg'), ('Más', 'More.svg'), ('Salud', 'Health.svg'), ('Configuración', 'Config.svg')]
        for i, (label, icn) in enumerate(menu_items):
            btn = QPushButton()
            btn.base_text = label
            btn.setText(f'   {label}')
            btn.setIcon(icon(icn))
            btn.setIconSize(QSize(24, 24))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(38)
            btn.setStyleSheet(f"\n                QPushButton {{ color:{CLR_TEXT_IDLE}; background:transparent;\n                  border:none; padding:8px 16px; border-radius:5px;\n                  font:700 18px '{FONT_FAM}'; text-align:left; }}\n                QPushButton:checked {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; }}\n            ")
            btn.clicked.connect(lambda _, ix=i: self._switch_page(self.stack, ix))
            menu_l.addWidget(btn)
            self.buttons.append(btn)
        menu_l.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidget(menu_w)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        vp.addWidget(scroll, 1)
        ver_lbl = QLabel('Versión 1.0')
        ver_lbl.setStyleSheet(f"color:{CLR_TITLE}; font:700 18px '{FONT_FAM}';")
        vp.addWidget(ver_lbl, alignment=Qt.AlignHCenter | Qt.AlignBottom)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._make_home_page())
        self.stack.addWidget(self._make_devices_page())
        self.stack.addWidget(self._make_more_page())
        self.stack.addWidget(self._make_health_page())
        self.stack.addWidget(self._make_config_page())
        self.buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)
        right = QWidget()
        vr = QVBoxLayout(right)
        vr.setContentsMargins(30, 0, 30, 20)
        vr.setSpacing(10)
        vr.addWidget(self.stack)
        vr.addStretch(1)
        root.addWidget(panel, 1)
        root.addWidget(right, 4)

    def _make_home_page(self):
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 20, 0, 0)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        greet = QFrame()
        greet.setFixedHeight(80)
        greet.setStyleSheet(f'background:{CLR_PANEL}; border-bottom-left-radius:5px; border-bottom-right-radius:5px;')
        hl = QHBoxLayout(greet)
        hl.setContentsMargins(16, 0, 16, 0)
        user_display = self.username if self.username else 'Usuario'
        lg = QLabel(f'¡Hola, {user_display}!')
        lg.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}';")
        hl.addWidget(lg)
        hl.addStretch(1)
        tim = QLabel(self.current_time())
        tim.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}';")
        tim.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(tim)
        self.home_time_label = tim
        QTimer(tim, timeout=lambda: tim.setText(self.current_time())).start(1000)
        grid.addWidget(greet, 0, 0, 1, 2)
        notif_header = QFrame()
        notif_header.setStyleSheet(f'background:{CLR_PANEL}; padding:8px 12px; border-top-left-radius:5px; border-top-right-radius:5px;')
        notif_layout = QHBoxLayout(notif_header)
        notif_layout.setContentsMargins(0, 0, 0, 0)
        notif_layout.setSpacing(8)
        notif_title = QLabel('Notificaciones', notif_header)
        notif_title.setStyleSheet(f"color:{CLR_TITLE}; font:700 20px '{FONT_FAM}';")
        try:
            from PyQt5.QtWidgets import QSizePolicy
            notif_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        except Exception:
            pass
        notif_layout.addWidget(notif_title)
        notif_layout.addStretch(1)
        notif_info_btn = QPushButton(notif_header)
        notif_info_btn.setCursor(Qt.PointingHandCursor)
        notif_info_btn.setFlat(True)
        try:
            pix = load_icon_pixmap('circle-info.svg', QSize(40, 40))
            pix = tint_pixmap(pix, QColor(CLR_TITLE))
            notif_info_btn.setIcon(QIcon(pix))
        except Exception:
            fallback_pix = load_icon_pixmap('circle-info.svg', QSize(40, 40))
            notif_info_btn.setIcon(QIcon(fallback_pix))
        notif_info_btn.setIconSize(QSize(40, 40))
        notif_info_btn.setStyleSheet('border:none; padding:0;')
        notif_info_btn.clicked.connect(self._open_notifications_details)
        notif_layout.addWidget(notif_info_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(notif_header, 1, 0)
        nc = QFrame()
        nc.setStyleSheet(f'background:{CLR_BG}; border:none; border-radius:5px;')
        nc.setMinimumSize(300, 300)
        nv = QVBoxLayout(nc)
        nv.setContentsMargins(0, 0, 0, 0)
        nv.setSpacing(0)
        self.home_notif_rows: list[tuple[QLabel, QLabel]] = []
        notif_inner = QFrame()
        notif_inner.setStyleSheet('background:transparent;')
        ni_l = QVBoxLayout(notif_inner)
        ni_l.setContentsMargins(8, 8, 8, 8)
        ni_l.setSpacing(8)
        for _ in range(HOME_RECENT_COUNT):
            row_frame = QFrame(notif_inner)
            row_frame.setStyleSheet(f'background:{CLR_SURFACE}; border:none; border-radius:8px;')
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)
            icon_lbl = QLabel(row_frame)
            icon_lbl.setFixedSize(35, 35)
            icon_lbl.setScaledContents(True)
            icon_lbl.setStyleSheet('border:none;')
            text_lbl = QLabel('--', row_frame)
            text_lbl.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}'; border:none;")
            text_lbl.setAlignment(Qt.AlignCenter)
            row_layout.addWidget(icon_lbl)
            row_layout.addWidget(text_lbl, 1)
            self.home_notif_rows.append((icon_lbl, text_lbl))
            ni_l.addWidget(row_frame)
        nv.addWidget(notif_inner)
        grid.addWidget(nc, 2, 0, 2, 1)
        metrics_header = QFrame()
        metrics_header.setStyleSheet(f'background:{CLR_PANEL}; padding:8px 12px; border-top-left-radius:5px; border-top-right-radius:5px;')
        header_layout = QHBoxLayout(metrics_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        m_title = QLabel('Resumen de Métricas', metrics_header)
        m_title.setStyleSheet(f"color:{CLR_TITLE}; font:700 20px '{FONT_FAM}';")
        try:
            from PyQt5.QtWidgets import QSizePolicy
            m_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        except Exception:
            pass
        header_layout.addWidget(m_title)
        header_layout.addStretch(1)
        info_btn = QPushButton(metrics_header)
        info_btn.setCursor(Qt.PointingHandCursor)
        info_btn.setFlat(True)
        try:
            pix = load_icon_pixmap('circle-info.svg', QSize(40, 40))
            pix = tint_pixmap(pix, QColor(CLR_TITLE))
            info_btn.setIcon(QIcon(pix))
        except Exception:
            fallback_pix = load_icon_pixmap('circle-info.svg', QSize(40, 40))
            info_btn.setIcon(QIcon(fallback_pix))
        info_btn.setIconSize(QSize(40, 40))
        info_btn.clicked.connect(self._open_metrics_details)
        info_btn.setStyleSheet('border:none; padding:0;')
        header_layout.addWidget(info_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(metrics_header, 1, 1)
        sumf = QFrame()
        sumf.setStyleSheet(f'background:{CLR_PANEL}; border-bottom-left-radius:5px; border-bottom-right-radius:5px;')
        gs = QGridLayout(sumf)
        gs.setContentsMargins(16, 16, 16, 16)
        gs.setHorizontalSpacing(16)
        gs.setVerticalSpacing(16)
        gauge_specs = [('devices', 'mobile.svg'), ('temp', 'temperature-high.svg'), ('energy', 'bolt.svg'), ('water', 'droplet.svg')]
        self.home_metric_gauges = {}
        for i, (key, icon_name) in enumerate(gauge_specs):
            r, cidx = divmod(i, 2)
            g_container = QWidget()
            vlay = QVBoxLayout(g_container)
            vlay.setContentsMargins(0, 0, 0, 0)
            vlay.setSpacing(4)
            gauge = MetricGauge(icon_name)
            gauge.setToolTip(key)
            vlay.addWidget(gauge, alignment=Qt.AlignCenter)
            vlay.addStretch(1)
            gs.addWidget(g_container, r, cidx, alignment=Qt.AlignCenter)
            self.home_metric_gauges[key] = gauge
        grid.addWidget(sumf, 2, 1, 2, 1)
        l4 = QLabel('Accesos Rápidos')
        l4.setStyleSheet(f"background:{CLR_PANEL}; color:{CLR_TITLE}; font:700 20px '{FONT_FAM}'; padding:6px 12px; border-top-left-radius:5px; border-top-right-radius:5px;")
        grid.addWidget(l4, 4, 0, 1, 2)
        h_notif = l4.sizeHint().height()
        h_metrics = metrics_header.sizeHint().height()
        h_notifications = notif_header.sizeHint().height()
        header_height = max(h_notif, h_metrics, h_notifications)
        notif_header.setFixedHeight(header_height)
        metrics_header.setFixedHeight(header_height)
        cf = QFrame()
        cf.setStyleSheet(f'background:{CLR_PANEL}; border-bottom-left-radius:5px; border-bottom-right-radius:5px;')
        hh = QHBoxLayout(cf)
        hh.setContentsMargins(16, 16, 16, 16)
        hh.setSpacing(16)
        acts = [('Historial De Salud', 'files-medical.svg', 'Historial De Salud'), ('Cámaras', 'camera-cctv.svg', 'Cámaras'), ('Notificaciones', 'bell-on.svg', 'Notificaciones'), ('Cuenta', 'user.svg', 'Cuenta')]
        hh.addStretch(1)
        for n, icn, page in acts:
            b = QuickAccessButton(n, icn)
            b.clicked.connect(lambda p=page: self._open_more_section(p, True))
            hh.addWidget(b)
        hh.addStretch(1)
        grid.addWidget(cf, 5, 0, 1, 2)
        return w

    def _make_devices_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 20, 0, 0)
        v.setSpacing(20)
        hh = QHBoxLayout()
        lbl = QLabel('Dispositivos')
        lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:700 24px '{FONT_FAM}'; border:none;")
        plus = QPushButton()
        plus.setIcon(icon('More.svg'))
        plus.setIconSize(QSize(24, 24))
        plus.setFixedSize(32, 32)
        plus.setFlat(True)
        plus.setStyleSheet('border:none; background:transparent;')
        plus.clicked.connect(self._add_device)
        hh.addWidget(lbl)
        hh.addStretch(1)
        hh.addWidget(plus)
        v.addLayout(hh)
        g_lbl = QLabel('Grupos')
        g_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}'; border:none;")
        v.addWidget(g_lbl)
        grp_w = QWidget()
        grp_w.setStyleSheet('background:transparent;')
        gl = QHBoxLayout(grp_w)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(16)
        self.grp_layout = gl
        self.group_cards = []
        groups = [('Todo', 'Devices.svg'), ('Dormitorio', 'bed-front.svg'), ('Baño', 'toilet.svg'), ('Sala', 'tv.svg'), ('Comedor', 'utensils.svg'), ('Cocina', 'hat-chef.svg')]
        for title, icon_name in groups:
            card = GroupCard(title, icon_name, rename_callback=self._rename_group, select_callback=None)
            gl.addWidget(card)
            self.group_cards.append(card)
        self.add_group_card = GroupCard('Grupo Nuevo', 'More.svg', add_callback=self._add_group)
        gl.addWidget(self.add_group_card)
        grp_scroll = QScrollArea()
        grp_scroll.setWidget(grp_w)
        grp_scroll.setWidgetResizable(True)
        grp_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        grp_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        grp_scroll.setFrameShape(QFrame.NoFrame)
        grp_scroll.setHorizontalScrollBar(CustomScrollBar(Qt.Horizontal))
        grp_scroll.setStyleSheet('background:transparent;')
        grp_scroll.viewport().setStyleSheet('background:transparent;')
        v.addWidget(grp_scroll)
        self.group_indicator = QLabel('Grupo Actual: Todo')
        self.group_indicator.setStyleSheet(f"background:{CLR_HOVER}; color:{CLR_TITLE}; font:700 16px '{FONT_FAM}'; padding:4px 8px; border-radius:5px;")
        v.addWidget(self.group_indicator)
        fh = QHBoxLayout()
        search = QLineEdit()
        search.setFixedHeight(40)
        search.setPlaceholderText('Buscar')
        search.setCursor(Qt.PointingHandCursor)
        search.setStyleSheet(f"\n            QLineEdit {{ background:{CLR_SURFACE}; border:2px solid #1A2B3C;\n                         border-radius:5px; padding:0 40px 0 12px;\n                         color:{CLR_TEXT_IDLE}; font:700 16px '{FONT_FAM}'; }}\n            QLineEdit:focus {{ border-color:{CLR_TITLE}; }}\n        ")
        search.addAction(icon('Search.svg'), QLineEdit.LeadingPosition)
        cb1 = QComboBox()
        cb1.addItems(['Tech', 'Interruptores', 'Otro'])
        cb2 = QComboBox()
        cb2.addItems(['De La A A La Z', 'De La Z A La A'])
        self.device_category_cb = cb1
        self.device_sort_cb = cb2
        for cb in (cb1, cb2):
            cb.setFixedHeight(40)
            cb.setStyleSheet(f"\n                QComboBox {{ background:{CLR_SURFACE};color:{CLR_TEXT_IDLE};\n                              font:700 16px '{FONT_FAM}';border:2px solid {CLR_TITLE};\n                              border-radius:5px;padding:0 12px; }}\n                QComboBox::drop-down {{ border:none; }}\n                QComboBox QAbstractItemView {{ background:{CLR_PANEL};\n                              border:2px solid {CLR_TITLE};\n                              selection-background-color:{CLR_ITEM_ACT};\n                              color:{CLR_TEXT_IDLE};outline:none;padding:4px; }}\n                QComboBox QAbstractItemView::item {{ height:30px;padding-left:10px; }}\n                QComboBox QAbstractItemView::item:hover {{ background:{CLR_ITEM_ACT}; }}\n            ")
        cb1.currentIndexChanged.connect(self._on_device_category_changed)
        cb2.currentIndexChanged.connect(self._on_device_sort_changed)
        fh.addWidget(search, 1)
        fh.addWidget(cb1)
        fh.addWidget(cb2)
        v.addLayout(fh)
        dev_w = QWidget()
        dev_w.setStyleSheet('background:transparent;')
        dl = QVBoxLayout(dev_w)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(12)
        self.device_filter_container = dl
        self.devices_buttons = []
        self.device_rows = []
        devices = [('Luz Dormitorio', 'Dormitorio'), ('Lámpara Noche', 'Dormitorio'), ('Ventilador Dormitorio', 'Dormitorio'), ('Aire Acondicionado Dormitorio', 'Dormitorio'), ('Cortinas Dormitorio', 'Dormitorio'), ('Enchufe Cama', 'Dormitorio'), ('Luz Baño', 'Baño'), ('Extractor', 'Baño'), ('Calentador Agua', 'Baño'), ('Espejo Iluminado', 'Baño'), ('Ducha Automática', 'Baño'), ('Enchufe Afeitadora', 'Baño'), ('Luces Sala', 'Sala'), ('Televisor', 'Sala'), ('Consola Juegos', 'Sala'), ('Equipo Sonido', 'Sala'), ('Ventilador Sala', 'Sala'), ('Enchufe Ventana', 'Sala'), ('Luz Comedor', 'Comedor'), ('Calefactor Comedor', 'Comedor'), ('Enchufe Comedor', 'Comedor'), ('Luz Barra', 'Comedor'), ('Persianas Comedor', 'Comedor'), ('Ventilador Techo', 'Comedor'), ('Refrigerador', 'Cocina'), ('Horno', 'Cocina'), ('Microondas', 'Cocina'), ('Lavavajillas', 'Cocina'), ('Licuadora', 'Cocina'), ('Cafetera', 'Cocina')]
        for name, grp in devices:
            # Determine the correct icon based on the original device name.  If the
            # device has been renamed, use the original name from the rename map
            # so the icon remains consistent across renames and restarts.
            try:
                original = name
                if hasattr(self, '_renamed_devices'):
                    original = self._renamed_devices.get(name, name)
            except Exception:
                original = name
            icon_override = 'Devices.svg'
            for key, fname in self._device_icon_map.items():
                if key in original:
                    icon_override = fname
                    break
            row = DeviceRow(name, grp, toggle_callback=self._device_toggled,
                            rename_callback=self._rename_device,
                            icon_override=icon_override)
            dl.addWidget(row)
            self.device_rows.append(row)
            self.devices_buttons.append(row.btn)
        dev_scroll = QScrollArea()
        dev_scroll.setWidget(dev_w)
        dev_scroll.setWidgetResizable(True)
        dev_scroll.setFrameShape(QFrame.NoFrame)
        dev_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
        dev_scroll.setStyleSheet('background:transparent;')
        dev_scroll.viewport().setStyleSheet('background:transparent;')
        v.addWidget(dev_scroll, 1)
        self.active_group = 'Todo'

        def filter_dev():
            t = search.text().lower()
            rows = []
            for row in self.device_rows:
                match = t in row.base_name.lower()
                grp_ok = self.active_group == 'Todo' or row.group == self.active_group
                if match and grp_ok:
                    rows.append(row)
                dl.removeWidget(row)
            asc = cb2.currentText() == 'De La A A La Z'
            rows.sort(key=lambda r: r.base_name.lower(), reverse=not asc)
            for row in self.device_rows:
                row.setVisible(False)
            for row in rows:
                row.setVisible(True)
                dl.addWidget(row)
        search.textChanged.connect(lambda _: filter_dev())
        self._filter_devices = filter_dev

        def sort_dev(_):
            asc = cb2.currentText() == 'De La A A La Z'
            self.device_rows.sort(key=lambda r: r.base_name.lower(), reverse=not asc)
            filter_dev()
        cb2.currentIndexChanged.connect(sort_dev)
        sort_dev(0)

        def select_group(card):
            self.active_group = card.base_name
            display = card.label.text()
            self.group_indicator.setText(f'Grupo Actual: {display}')
            for ccard in self.group_cards:
                ccard.set_selected(ccard is card)
            filter_dev()
        self._group_select_func = select_group
        for card in self.group_cards:
            card.select_callback = self._group_select_func
        select_group(self.group_cards[0])
        return w

    def _make_more_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.more_stack = QStackedWidget()
        gp = QWidget()
        g = QGridLayout(gp)
        g.setContentsMargins(16, 16, 16, 16)
        g.setHorizontalSpacing(24)
        g.setVerticalSpacing(24)
        items = ['Listas Y Notas', 'Recordatorios', 'Alarmas Y Timers', 'Calendario', 'Notificaciones', 'Cámaras', 'Historial De Salud', 'Información']
        page_map = {text: i + 1 for i, text in enumerate(items)}
        self.more_pages = page_map
        icon_map = {'Listas Y Notas': 'clipboard-list.svg', 'Recordatorios': 'bell.svg', 'Alarmas Y Timers': 'alarm-clock.svg', 'Calendario': 'calendar-days.svg', 'Notificaciones': 'bell-on.svg', 'Cámaras': 'camera-cctv.svg', 'Historial De Salud': 'files-medical.svg', 'Información': 'info.svg'}
        for idx, text in enumerate(items):
            icon_name = icon_map.get(text, None)
            ccard = CardButton(text, icon_name)
            if text == 'Notificaciones':
                ccard.clicked.connect(lambda ix=page_map[text], s=self: (setattr(s, 'from_home_more', False), s._populate_notif_table(), s._switch_page(s.more_stack, ix)))
            elif text == 'Historial De Salud':
                ccard.clicked.connect(lambda ix=page_map[text], s=self: (setattr(s, 'from_home_more', False), s._populate_health_table(), s._switch_page(s.more_stack, ix)))
            else:
                ccard.clicked.connect(lambda ix=page_map[text], s=self: (setattr(s, 'from_home_more', False), s._switch_page(s.more_stack, ix)))
            r, cidx = divmod(idx, 2)
            g.addWidget(ccard, r, cidx)
        g.setRowStretch(4, 1)
        self.more_stack.addWidget(gp)
        ln = QWidget()
        ln_layout = QVBoxLayout(ln)
        ln_layout.setContentsMargins(16, 16, 16, 16)
        ln_layout.setSpacing(8)
        back = QPushButton()
        back.setIcon(icon('Arrow.svg'))
        back.setIconSize(QSize(24, 24))
        back.setFixedSize(40, 40)
        back.setStyleSheet('background:transparent; border:none;')
        back.clicked.connect(self._back_from_more)
        ln_layout.addWidget(back, alignment=Qt.AlignLeft)
        title_ln = QLabel('Listas Y Notas')
        title_ln.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
        ln_layout.addWidget(title_ln)
        tab = QTabWidget()
        tab.setStyleSheet(f"\n            QTabBar::tab {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n                padding:8px 16px;\n                border:2px solid {CLR_TITLE};\n                border-bottom:none;\n                border-top-left-radius:5px;\n                border-top-right-radius:5px;\n                font:600 16px '{FONT_FAM}';\n            }}\n            QTabBar::tab:selected {{\n                background:{CLR_ITEM_ACT};\n                color:{CLR_TITLE};\n            }}\n            QTabBar::tab:!selected {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n            }}\n            QTabWidget::pane {{ border:none; }}\n        ")
        tab.setTabPosition(QTabWidget.North)
        tab.tabBar().setDocumentMode(True)
        tab.tabBar().setStyleSheet('QTabBar::tab { min-width: 120px; margin:4px; padding:8px 20px; }')
        lists_tab = QWidget()
        lists_l = QHBoxLayout(lists_tab)
        lists_l.setContentsMargins(0, 0, 0, 0)
        lists_l.setSpacing(16)
        left_frame = QFrame()
        left_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        lf_layout = QVBoxLayout(left_frame)
        lf_layout.setContentsMargins(8, 8, 8, 8)
        lf_layout.setSpacing(8)
        self.create_list_btn = QPushButton('Crear Lista')
        self.create_list_btn.setFixedHeight(36)
        self.create_list_btn.setStyleSheet(f"background:{CLR_TITLE}; color:#07101B; font:600 14px '{FONT_FAM}'; border:none; border-radius:5px;")
        self.create_list_btn.clicked.connect(self._on_add_list)
        lf_layout.addWidget(self.create_list_btn)
        self.lists_widget = QListWidget()
        self.lists_widget.setItemDelegate(NoFocusDelegate(self.lists_widget))
        self.lists_widget.setStyleSheet(f"\n            QListWidget {{ background:transparent; border:none; color:{CLR_TEXT_IDLE}; font:500 16px '{FONT_FAM}'; }}\n            QListWidget::item {{ outline:none; }}\n            QListWidget::item:selected {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; border-radius:5px; }}\n        ")
        lf_layout.addWidget(self.lists_widget)
        lists_l.addWidget(left_frame, 1)
        detail_frame = QFrame()
        detail_frame.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
        df_layout = QVBoxLayout(detail_frame)
        df_layout.setContentsMargins(8, 8, 8, 8)
        df_layout.setSpacing(8)
        self.list_title = QLabel('')
        self.list_title.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 20px '{FONT_FAM}';")
        df_layout.addWidget(self.list_title, alignment=Qt.AlignLeft)
        self.add_item_btn = QPushButton('Añadir Elemento')
        self.add_item_btn.setFixedHeight(36)
        self.add_item_btn.setStyleSheet(f"background:{CLR_TITLE}; color:#07101B; font:600 14px '{FONT_FAM}'; border:none; border-radius:5px;")
        df_layout.addWidget(self.add_item_btn, alignment=Qt.AlignLeft)
        self.list_items_widget = QListWidget()
        self.list_items_widget.setItemDelegate(NoFocusDelegate(self.list_items_widget))
        self.list_items_widget.setStyleSheet(f"\n            QListWidget {{ background:transparent; border:none; color:{CLR_TEXT_IDLE}; font:500 16px '{FONT_FAM}'; }}\n            QListWidget::item {{ outline:none; }}\n            QListWidget::item:selected {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; border-radius:5px; }}\n        ")
        items_scroll = QScrollArea()
        items_scroll.setWidgetResizable(True)
        items_scroll.setWidget(self.list_items_widget)
        items_scroll.setFrameShape(QFrame.NoFrame)
        items_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
        df_layout.addWidget(items_scroll, 1)
        lists_l.addWidget(detail_frame, 2)
        tab.addTab(lists_tab, 'Listas')
        self.lists_widget.currentTextChanged.connect(self._on_list_selected)
        self.add_item_btn.clicked.connect(self._on_add_list_item)
        notes_tab = QWidget()
        notes_l = QVBoxLayout(notes_tab)
        notes_l.setContentsMargins(0, 0, 0, 0)
        notes_l.setSpacing(8)
        add_note = QPushButton('Agregar nota')
        add_note.setIcon(icon('More.svg'))
        add_note.setIconSize(QSize(24, 24))
        add_note.setFixedHeight(40)
        add_note.setStyleSheet(f"color:{CLR_TITLE}; font:600 16px '{FONT_FAM}'; background:transparent; border:none;")
        notes_l.addWidget(add_note, alignment=Qt.AlignLeft)
        frame_notes = QFrame()
        frame_notes.setStyleSheet(f'QFrame {{ border: 2px solid {CLR_TITLE}; border-radius:5px; background:{CLR_SURFACE}; }}')
        vcn = QVBoxLayout(frame_notes)
        vcn.setContentsMargins(4, 4, 4, 4)
        notes_scroll = QScrollArea()
        notes_scroll.setWidgetResizable(True)
        notes_container = QWidget()
        notes_container.setStyleSheet(f'background:{CLR_SURFACE};')
        notes_scroll.setWidget(notes_container)
        notes_scroll.setFrameShape(QFrame.NoFrame)
        notes_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
        notes_scroll.setStyleSheet(f'background:{CLR_SURFACE}; border:none;')
        notes_scroll.viewport().setStyleSheet(f'background:{CLR_SURFACE};')
        vcn.addWidget(notes_scroll)
        self.notes_grid = QGridLayout(notes_container)
        self.notes_grid.setSpacing(16)
        spacing = self.notes_grid.spacing()
        self.notes_manager = NotesManager(notes_container, cell_size=(200, 150), spacing=spacing, rows=3, columns=3)
        self.notes_items = []
        notes_l.addWidget(frame_notes)
        add_note.clicked.connect(self._add_note)
        tab.addTab(notes_tab, 'Notas')
        ln_layout.addWidget(tab)
        self.more_stack.addWidget(ln)
        rec_page = QFrame()
        rec_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
        rp_layout = QVBoxLayout(rec_page)
        rp_layout.setContentsMargins(16, 16, 16, 16)
        rp_layout.setSpacing(12)
        back_rec = QPushButton()
        back_rec.setIcon(icon('Arrow.svg'))
        back_rec.setIconSize(QSize(24, 24))
        back_rec.setFixedSize(36, 36)
        back_rec.setStyleSheet('background:transparent; border:none;')
        back_rec.clicked.connect(self._back_from_more)
        rp_layout.addWidget(back_rec, alignment=Qt.AlignLeft)
        title_rec = QLabel('Recordatorios')
        title_rec.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
        rp_layout.addWidget(title_rec)
        input_frame = QFrame()
        input_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        ih = QHBoxLayout(input_frame)
        ih.setContentsMargins(8, 8, 8, 8)
        ih.setSpacing(8)
        self.input_record_text = QLineEdit()
        self.input_record_text.setPlaceholderText('Texto Del Recordatorio')
        self.input_record_text.setStyleSheet(input_style(bg=CLR_SURFACE))
        self.input_record_datetime = QDateTimeEdit(datetime.now())
        self.input_record_datetime.setDisplayFormat('yyyy-MM-dd HH:mm')
        self.input_record_datetime.setStyleSheet(input_style('QDateTimeEdit', CLR_SURFACE))
        self.input_record_datetime.setButtonSymbols(QAbstractSpinBox.NoButtons)
        btn_add_rec = QPushButton(' Añadir')
        btn_add_rec.setIcon(icon('More.svg'))
        btn_add_rec.setIconSize(QSize(16, 16))
        btn_add_rec.setFixedSize(120, 32)
        btn_add_rec.setCursor(Qt.PointingHandCursor)
        btn_add_rec.setStyleSheet(button_style())
        btn_add_rec.clicked.connect(self._add_recordatorio)
        ih.addWidget(self.input_record_text, 2)
        ih.addWidget(self.input_record_datetime, 1)
        ih.addWidget(btn_add_rec)
        rp_layout.addWidget(input_frame)
        table_frame = QFrame()
        table_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setSpacing(8)
        self.table_recordatorios = QTableWidget()
        self.table_recordatorios.setColumnCount(2)
        self.table_recordatorios.setHorizontalHeaderLabels(['Fecha Y Hora', 'Mensaje'])
        hdr = self.table_recordatorios.horizontalHeader()
        hdr.setStyleSheet(f"QHeaderView::section {{ background:{CLR_HEADER_BG}; color:{CLR_HEADER_TEXT}; padding:8px; font:600 14px '{FONT_FAM}'; border:none; }}")
        hdr.setDefaultAlignment(Qt.AlignCenter)
        self.table_recordatorios.verticalHeader().setVisible(False)
        self.table_recordatorios.setEditTriggers(QTableWidget.NoEditTriggers)
        style_table(self.table_recordatorios)
        self.table_recordatorios.setColumnWidth(0, 160)
        make_shadow(table_frame, 12, 4, 120)
        table_layout.addWidget(self.table_recordatorios)
        rp_layout.addWidget(table_frame, 1)
        btn_del_rec = QPushButton('Eliminar Seleccionado')
        btn_del_rec.setIcon(icon('Trash.svg'))
        btn_del_rec.setIconSize(QSize(16, 16))
        btn_del_rec.setFixedSize(180, 32)
        btn_del_rec.setCursor(Qt.PointingHandCursor)
        btn_del_rec.setStyleSheet(button_style(CLR_TITLE, '4px 8px'))
        btn_del_rec.clicked.connect(self._delete_selected_recordatorio)
        rp_layout.addWidget(btn_del_rec, alignment=Qt.AlignRight)
        self.more_stack.addWidget(rec_page)
        alarm_page = QFrame()
        alarm_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
        ap_layout = QVBoxLayout(alarm_page)
        ap_layout.setContentsMargins(16, 16, 16, 16)
        ap_layout.setSpacing(12)
        back_alarm = QPushButton()
        back_alarm.setIcon(icon('Arrow.svg'))
        back_alarm.setIconSize(QSize(24, 24))
        back_alarm.setFixedSize(36, 36)
        back_alarm.setStyleSheet('background:transparent; border:none;')
        back_alarm.clicked.connect(self._back_from_more)
        ap_layout.addWidget(back_alarm, alignment=Qt.AlignLeft)
        title_alarm = QLabel('Alarmas Y Timers')
        title_alarm.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
        ap_layout.addWidget(title_alarm)
        tab_at = QTabWidget()
        tab_at.setStyleSheet(f"\n            QTabBar::tab {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n                padding:8px 16px;\n                border:2px solid {CLR_TITLE};\n                border-bottom:none;\n                border-top-left-radius:5px;\n                border-top-right-radius:5px;\n                font:600 16px '{FONT_FAM}';\n            }}\n            QTabBar::tab:selected {{\n                background:{CLR_ITEM_ACT};\n                color:{CLR_TITLE};\n            }}\n            QTabBar::tab:!selected {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n            }}\n            QTabWidget::pane {{ border:none; }}\n        ")
        tab_at.setTabPosition(QTabWidget.North)
        tab_at.tabBar().setDocumentMode(True)
        tab_at.tabBar().setStyleSheet('QTabBar::tab { min-width: 120px; margin:4px; padding:8px 20px; }')
        alarm_tab = QWidget()
        at_l = QVBoxLayout(alarm_tab)
        at_l.setContentsMargins(0, 0, 0, 0)
        at_l.setSpacing(8)
        input_frame_alarm = QFrame()
        input_frame_alarm.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        a_layout = QHBoxLayout(input_frame_alarm)
        a_layout.setContentsMargins(8, 8, 8, 8)
        a_layout.setSpacing(8)
        self.input_alarm_text = QLineEdit()
        self.input_alarm_text.setPlaceholderText('Etiqueta De Alarma')
        self.input_alarm_text.setStyleSheet(input_style(bg=CLR_SURFACE))
        self.input_alarm_datetime = QDateTimeEdit(datetime.now())
        self.input_alarm_datetime.setDisplayFormat('yyyy-MM-dd HH:mm')
        self.input_alarm_datetime.setStyleSheet(input_style('QDateTimeEdit', CLR_SURFACE))
        self.input_alarm_datetime.setButtonSymbols(QAbstractSpinBox.NoButtons)
        btn_add_alarm = QPushButton(' Añadir')
        btn_add_alarm.setIcon(icon('More.svg'))
        btn_add_alarm.setIconSize(QSize(16, 16))
        btn_add_alarm.setFixedSize(120, 32)
        btn_add_alarm.setCursor(Qt.PointingHandCursor)
        btn_add_alarm.setStyleSheet(button_style())
        btn_add_alarm.clicked.connect(self._add_alarm)
        a_layout.addWidget(self.input_alarm_text, 2)
        a_layout.addWidget(self.input_alarm_datetime, 1)
        a_layout.addWidget(btn_add_alarm)
        at_l.addWidget(input_frame_alarm)
        tbl_alarm = QFrame()
        tbl_alarm.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        tbl_al_layout = QVBoxLayout(tbl_alarm)
        tbl_al_layout.setContentsMargins(8, 8, 8, 8)
        tbl_al_layout.setSpacing(8)
        self.table_alarms = QTableWidget()
        self.table_alarms.setColumnCount(2)
        self.table_alarms.setHorizontalHeaderLabels(['Fecha Y Hora', 'Etiqueta'])
        hdra = self.table_alarms.horizontalHeader()
        hdra.setStyleSheet(f"QHeaderView::section {{ background:{CLR_HEADER_BG}; color:{CLR_HEADER_TEXT}; padding:8px; font:600 14px '{FONT_FAM}'; border:none; }}")
        hdra.setDefaultAlignment(Qt.AlignCenter)
        self.table_alarms.verticalHeader().setVisible(False)
        self.table_alarms.setEditTriggers(QTableWidget.NoEditTriggers)
        style_table(self.table_alarms)
        self.table_alarms.setColumnWidth(0, 160)
        make_shadow(tbl_alarm, 12, 4, 120)
        tbl_al_layout.addWidget(self.table_alarms)
        at_l.addWidget(tbl_alarm, 1)
        btn_del_alarm = QPushButton('Eliminar Seleccionado')
        btn_del_alarm.setIcon(icon('Trash.svg'))
        btn_del_alarm.setIconSize(QSize(16, 16))
        btn_del_alarm.setFixedSize(180, 32)
        btn_del_alarm.setCursor(Qt.PointingHandCursor)
        btn_del_alarm.setStyleSheet(button_style(CLR_TITLE, '4px 8px'))
        btn_del_alarm.clicked.connect(self._delete_selected_alarm)
        at_l.addWidget(btn_del_alarm, alignment=Qt.AlignRight)
        tab_at.addTab(alarm_tab, 'Alarmas')
        timer_tab = QWidget()
        ti_l = QVBoxLayout(timer_tab)
        ti_l.setContentsMargins(0, 0, 0, 0)
        ti_l.setSpacing(8)
        input_frame_timer = QFrame()
        input_frame_timer.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        t_layout = QHBoxLayout(input_frame_timer)
        t_layout.setContentsMargins(8, 8, 8, 8)
        t_layout.setSpacing(8)
        self.input_timer_text = QLineEdit()
        self.input_timer_text.setPlaceholderText('Etiqueta Del Timer')
        self.input_timer_text.setStyleSheet(input_style(bg=CLR_SURFACE))
        self.input_timer_seconds = QSpinBox()
        self.input_timer_seconds.setRange(0, 86400)
        self.input_timer_seconds.setSuffix(' s')
        self.input_timer_seconds.setStyleSheet(input_style('QSpinBox', CLR_SURFACE))
        self.input_timer_seconds.setButtonSymbols(QAbstractSpinBox.NoButtons)
        btn_add_timer = QPushButton(' Añadir')
        btn_add_timer.setIcon(icon('More.svg'))
        btn_add_timer.setIconSize(QSize(16, 16))
        btn_add_timer.setFixedSize(120, 32)
        btn_add_timer.setCursor(Qt.PointingHandCursor)
        btn_add_timer.setStyleSheet(button_style())
        btn_add_timer.clicked.connect(self._add_timer)
        t_layout.addWidget(self.input_timer_text, 2)
        t_layout.addWidget(self.input_timer_seconds, 1)
        t_layout.addWidget(btn_add_timer)
        ti_l.addWidget(input_frame_timer)
        tbl_timer = QFrame()
        tbl_timer.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        tbl_ti_layout = QVBoxLayout(tbl_timer)
        tbl_ti_layout.setContentsMargins(8, 8, 8, 8)
        tbl_ti_layout.setSpacing(8)
        self.table_timers = QTableWidget()
        self.table_timers.setColumnCount(2)
        self.table_timers.setHorizontalHeaderLabels(['Etiqueta', 'Restante'])
        hdrt = self.table_timers.horizontalHeader()
        hdrt.setStyleSheet(f"QHeaderView::section {{ background:{CLR_HEADER_BG}; color:{CLR_HEADER_TEXT}; padding:8px; font:600 14px '{FONT_FAM}'; border:none; }}")
        hdrt.setDefaultAlignment(Qt.AlignCenter)
        self.table_timers.verticalHeader().setVisible(False)
        self.table_timers.setEditTriggers(QTableWidget.NoEditTriggers)
        style_table(self.table_timers)
        self.table_timers.setColumnWidth(1, 120)
        make_shadow(tbl_timer, 12, 4, 120)
        tbl_ti_layout.addWidget(self.table_timers)
        ti_l.addWidget(tbl_timer, 1)
        btn_del_timer = QPushButton('Eliminar Seleccionado')
        btn_del_timer.setIcon(icon('Trash.svg'))
        btn_del_timer.setIconSize(QSize(16, 16))
        btn_del_timer.setFixedSize(180, 32)
        btn_del_timer.setCursor(Qt.PointingHandCursor)
        btn_del_timer.setStyleSheet(button_style(CLR_TITLE, '4px 8px'))
        btn_del_timer.clicked.connect(self._delete_selected_timer)
        ti_l.addWidget(btn_del_timer, alignment=Qt.AlignRight)
        tab_at.addTab(timer_tab, 'Timers')
        ap_layout.addWidget(tab_at, 1)
        self.more_stack.addWidget(alarm_page)
        calendar_page = QFrame()
        calendar_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
        cp_layout = QVBoxLayout(calendar_page)
        cp_layout.setContentsMargins(16, 16, 16, 16)
        cp_layout.setSpacing(8)
        back_cal = QPushButton()
        back_cal.setIcon(icon('Arrow.svg'))
        back_cal.setIconSize(QSize(24, 24))
        back_cal.setFixedSize(36, 36)
        back_cal.setStyleSheet('background:transparent; border:none;')
        back_cal.clicked.connect(self._back_from_more)
        cp_layout.addWidget(back_cal, alignment=Qt.AlignLeft)
        title_cal = QLabel('Calendario')
        title_cal.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
        cp_layout.addWidget(title_cal)
        cal = CurrentMonthCalendar()
        cal.setGridVisible(True)
        cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        cal_style = f"\n            QCalendarWidget {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n                border:2px solid {CLR_TITLE};\n                border-radius:5px;\n            }}\n            QCalendarWidget QWidget {{\n                background:{CLR_PANEL};\n                color:{CLR_TEXT_IDLE};\n            }}\n            QCalendarWidget QWidget#qt_calendar_calendarview {{\n                background:{CLR_BG};\n                alternate-background-color:{CLR_BG};\n                border:none;\n                margin:0;\n            }}\n            QCalendarWidget QWidget#qt_calendar_navigationbar {{\n                background:{CLR_PANEL};\n                border:none;\n                padding:0;\n                margin-bottom:8px;\n            }}\n            QCalendarWidget QToolButton::menu-indicator {{ image:none; }}\n            QCalendarWidget QAbstractItemView {{\n                background:{CLR_BG};\n                color:{CLR_TEXT_IDLE};\n                selection-background-color:{CLR_ITEM_ACT};\n                selection-color:{CLR_TITLE};\n                gridline-color:{CLR_TITLE};\n                outline:none;\n                font:600 16px '{FONT_FAM}';\n            }}\n            QCalendarWidget QHeaderView::section {{\n                background:{CLR_HEADER_BG};\n                color:{CLR_HEADER_TEXT};\n                border:none;\n                font:600 18px '{FONT_FAM}';\n            }}\n            QCalendarWidget::item {{\n                background:{CLR_BG};\n                color:{CLR_TEXT_IDLE};\n                padding:4px;\n                font:600 16px '{FONT_FAM}';\n            }}\n            QCalendarWidget::item:selected {{\n                background:{CLR_ITEM_ACT};\n                color:{CLR_TITLE};\n            }}\n            QCalendarWidget::item:enabled:hover {{\n                background:{CLR_HEADER_BG};\n                color:{CLR_TITLE};\n            }}\n        "
        cal.setStyleSheet(cal_style)
        cal.setStyleSheet(cal.styleSheet() + 'QCalendarWidget QWidget:focus{outline:none;}')
        cal.setStyleSheet(cal.styleSheet() + f'\n            /* Cabeceras de días de la semana y números de semana */\n            QCalendarWidget QTableView QHeaderView::section {{\n                background: {CLR_HEADER_BG};\n                color:      {CLR_HEADER_TEXT};\n                border: none;\n            }}\n        ')
        cal.selectionChanged.connect(self._on_calendar_date_selected)
        cal_frame = QFrame()
        cal_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        cf_layout = QVBoxLayout(cal_frame)
        cf_layout.setContentsMargins(4, 4, 4, 4)
        cf_layout.addWidget(cal)
        cal_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cp_layout.addWidget(cal_frame, 1)
        self.calendar_widget = cal
        self._refresh_calendar_events()
        self.more_stack.addWidget(calendar_page)
        notif_page = QFrame()
        notif_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
        np_layout = QVBoxLayout(notif_page)
        np_layout.setContentsMargins(16, 16, 16, 16)
        np_layout.setSpacing(12)
        back_not = QPushButton()
        back_not.setIcon(icon('Arrow.svg'))
        back_not.setIconSize(QSize(24, 24))
        back_not.setFixedSize(36, 36)
        back_not.setStyleSheet('background:transparent; border:none;')
        back_not.clicked.connect(self._back_from_more)
        np_layout.addWidget(back_not, alignment=Qt.AlignLeft)
        title_not = QLabel('Notificaciones')
        title_not.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
        np_layout.addWidget(title_not)
        notif_frame = QFrame()
        notif_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-bottom-left-radius:5px; border-bottom-right-radius:5px;')
        nf_layout = QVBoxLayout(notif_frame)
        nf_layout.setContentsMargins(8, 8, 8, 8)
        nf_layout.setSpacing(8)
        self.notif_table = QTableWidget()
        self.notif_table.setColumnCount(2)
        self.notif_table.setHorizontalHeaderLabels(['Hora', 'Mensaje'])
        hdr2 = self.notif_table.horizontalHeader()
        hdr2.setStyleSheet(f"\n            QHeaderView::section {{\n                background:{CLR_HEADER_BG};\n                color:{CLR_HEADER_TEXT};\n                padding:8px;\n                font:600 14px '{FONT_FAM}';\n                border:none;\n            }}\n        ")
        hdr2.setDefaultAlignment(Qt.AlignCenter)
        self.notif_table.verticalHeader().setVisible(False)
        self.notif_table.setEditTriggers(QTableWidget.NoEditTriggers)
        style_table(self.notif_table)
        self.notif_table.setColumnWidth(0, 120)
        self.notif_table.setColumnWidth(1, 420)
        make_shadow(notif_frame, 15, 6, 150)
        nf_layout.addWidget(self.notif_table)
        np_layout.addWidget(notif_frame, 1)
        self.more_stack.addWidget(notif_page)
        cam_page = QFrame()
        cam_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
        cp = QVBoxLayout(cam_page)
        cp.setContentsMargins(16, 16, 16, 16)
        cp.setSpacing(8)
        back_cam = QPushButton()
        back_cam.setIcon(icon('Arrow.svg'))
        back_cam.setIconSize(QSize(24, 24))
        back_cam.setFixedSize(36, 36)
        back_cam.setStyleSheet('background:transparent; border:none;')
        back_cam.clicked.connect(self._back_from_more)
        cp.addWidget(back_cam, alignment=Qt.AlignLeft)
        title_cam = QLabel('Cámaras')
        title_cam.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
        cp.addWidget(title_cam)
        cam_frame = QFrame()
        cam_frame.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        cf_layout = QVBoxLayout(cam_frame)
        cf_layout.setContentsMargins(8, 8, 8, 8)
        cf_layout.setSpacing(8)
        grid = QGridLayout()
        grid.setSpacing(16)
        for i in range(2):
            for j in range(2):
                frame = QFrame()
                frame.setFixedSize(300, 200)
                frame.setStyleSheet(f'\n                    QFrame {{ background:{CLR_HOVER}; border:2px solid {CLR_TITLE}; border-radius:5px; }}\n                ')
                lbl = QLabel('Vista cámara', frame)
                lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 16px '{FONT_FAM}';")
                lbl.setAlignment(Qt.AlignCenter)
                vbox = QVBoxLayout(frame)
                vbox.addStretch(1)
                vbox.addWidget(lbl)
                vbox.addStretch(1)
                grid.addWidget(frame, i, j)
        cf_layout.addLayout(grid, 1)
        make_shadow(cam_frame, 15, 6, 150)
        cp.addWidget(cam_frame, 1)
        self.more_stack.addWidget(cam_page)
        health_page = QFrame()
        health_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
        hp = QVBoxLayout(health_page)
        hp.setContentsMargins(16, 16, 16, 16)
        hp.setSpacing(12)
        back_h = QPushButton()
        back_h.setIcon(icon('Arrow.svg'))
        back_h.setIconSize(QSize(24, 24))
        back_h.setFixedSize(36, 36)
        back_h.setStyleSheet('background:transparent; border:none;')
        back_h.clicked.connect(self._back_from_more)
        hp.addWidget(back_h, alignment=Qt.AlignLeft)
        title_h = QLabel('Historial De Salud')
        title_h.setStyleSheet(f"color:{CLR_TITLE}; font:700 22px '{FONT_FAM}';")
        hp.addWidget(title_h)
        frame_h = QFrame()
        frame_h.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
        fh_layout = QVBoxLayout(frame_h)
        fh_layout.setContentsMargins(8, 8, 8, 8)
        fh_layout.setSpacing(8)
        self.table_health = QTableWidget()
        self.table_health.setColumnCount(6)
        self.table_health.setHorizontalHeaderLabels(['Fecha', 'PA', 'BPM', 'SpO₂', 'Temp', 'FR'])
        hdrh = self.table_health.horizontalHeader()
        hdrh.setStyleSheet(f"QHeaderView::section {{ background:{CLR_HEADER_BG}; color:{CLR_HEADER_TEXT}; padding:8px; font:600 14px '{FONT_FAM}'; border:none; }}")
        hdrh.setDefaultAlignment(Qt.AlignCenter)
        self.table_health.verticalHeader().setVisible(False)
        self.table_health.setEditTriggers(QTableWidget.NoEditTriggers)
        style_table(self.table_health)
        sb = CustomScrollBar(Qt.Vertical)
        sb.setStyleSheet('margin:2px; background:transparent;')
        self.table_health.setVerticalScrollBar(sb)
        self.table_health.setViewportMargins(0, 0, 4, 0)
        self.table_health.setColumnWidth(0, 160)
        fh_layout.addWidget(self.table_health)
        hp.addWidget(frame_h, 1)
        self.more_stack.addWidget(health_page)
        account_page = QFrame()
        account_page.setStyleSheet(f'background:{CLR_BG}; border-radius:5px;')
        ap = QVBoxLayout(account_page)
        ap.setContentsMargins(16, 16, 16, 16)
        ap.setSpacing(12)
        back_a = QPushButton()
        back_a.setIcon(icon('Arrow.svg'))
        back_a.setIconSize(QSize(24, 24))
        back_a.setFixedSize(36, 36)
        back_a.setStyleSheet('background:transparent; border:none;')
        back_a.clicked.connect(self._back_from_more)
        ap.addWidget(back_a, alignment=Qt.AlignLeft)
        title_a = QLabel('Información')
        title_a.setStyleSheet(f"color:{CLR_TITLE}; font:700 24px '{FONT_FAM}';")
        ap.addWidget(title_a)
        grid = QGridLayout()
        grid.setContentsMargins(0, 8, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        summary_items = [('Dispositivos', 'acc_dev_label', 'cube.svg'), ('Listas', 'acc_list_label', 'clipboard-list.svg'), ('Notas', 'acc_note_label', 'note-sticky.svg'), ('Recordatorios', 'acc_rem_label', 'bell.svg'), ('Alarmas', 'acc_alarm_label', 'clock.svg'), ('Timers', 'acc_timer_label', 'stopwatch.svg'), ('Historial Salud', 'acc_health_label', 'file-medical.svg'), ('Acciones', 'acc_action_label', 'user.svg'), ('Tema', 'acc_theme_label', 'gear.svg'), ('Idioma', 'acc_lang_label', 'globe.svg'), ('Hora', 'acc_time_label', 'clock.svg'), ('Notificaciones', 'acc_notif_label', 'bell.svg')]
        cols = 3
        fa_solid_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules', '@fortawesome', 'fontawesome-free', 'svgs', 'solid')
        loc_icon_map = {'Dispositivos': 'house.svg', 'Listas': 'list.svg', 'Notas': 'note-sticky.svg', 'Recordatorios': 'calendar-days.svg', 'Alarmas': 'clock.svg', 'Timers': 'hourglass-half.svg', 'Historial Salud': 'file-medical.svg', 'Acciones': 'clock-rotate-left.svg', 'Tema': 'palette.svg', 'Idioma': 'language.svg', 'Hora': 'clock.svg', 'Notificaciones': 'bell.svg'}
        for idx, (title, attr_name, icon_name) in enumerate(summary_items):
            card = QFrame()
            card.setStyleSheet(f'background:{CLR_PANEL}; border:2px solid {CLR_TITLE}; border-radius:5px;')
            card.setFixedHeight(90)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            hl = QHBoxLayout(card)
            hl.setContentsMargins(8, 4, 8, 4)
            hl.setSpacing(8)
            lbl_icon = QLabel()
            pix = load_icon_pixmap(icon_name, QSize(24, 24))
            pix_tinted = tint_pixmap(pix, QColor(CLR_TITLE))
            lbl_icon.setPixmap(pix_tinted)
            hl.addWidget(lbl_icon)
            txt_layout = QVBoxLayout()
            txt_layout.setContentsMargins(0, 0, 0, 0)
            txt_layout.setSpacing(0)
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet(f"color:{CLR_TITLE}; font:600 14px '{FONT_FAM}';")
            lbl_value = QLabel('--')
            lbl_value.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:700 15px '{FONT_FAM}';")
            lbl_value.setWordWrap(True)
            txt_layout.addWidget(lbl_title)
            txt_layout.addWidget(lbl_value)
            loc_lbl = QLabel()
            loc_lbl.setFixedSize(18, 18)
            loc_lbl.setScaledContents(True)
            icon_filename = loc_icon_map.get(title)
            loc_path = None
            if icon_filename is not None:
                potential_path = os.path.join(fa_solid_dir, icon_filename)
                if os.path.isfile(potential_path):
                    loc_path = potential_path
            if loc_path:
                ico = QIcon(loc_path)
                pm = ico.pixmap(QSize(18, 18))
                pm_tinted = tint_pixmap(pm, QColor(CLR_TITLE))
                loc_lbl.setPixmap(pm_tinted)
            loc_lbl.setContentsMargins(0, 4, 0, 0)
            txt_layout.addWidget(loc_lbl)
            hl.addLayout(txt_layout)
            setattr(self, attr_name, lbl_value)
            loc_attr_name = attr_name.replace('_label', '_loc_label')
            setattr(self, loc_attr_name, loc_lbl)
            row = idx // cols
            col = idx % cols
            grid.addWidget(card, row, col)
        ap.addLayout(grid)
        ap.addSpacing(12)
        ap.addStretch(1)
        self.account_page = account_page
        self.more_stack.addWidget(account_page)
        layout.addWidget(self.more_stack)
        return w

    def _make_health_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(10)
        gauge = BPMGauge()
        metrics = MetricsPanel()
        gauge.calculationFinished.connect(metrics.update_values)
        gauge.calculationFinished.connect(self._record_health_history)
        l.addStretch(1)
        l.addWidget(gauge, alignment=Qt.AlignHCenter)
        l.addWidget(metrics, alignment=Qt.AlignHCenter)
        l.addStretch(1)
        return w

    def _make_config_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 20, 0, 0)
        v.setSpacing(20)
        lbl_title = QLabel('Configuración')
        lbl_title.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:700 24px '{FONT_FAM}';")
        v.addWidget(lbl_title)
        themeF = QFrame()
        themeF.setFixedHeight(60)
        themeF.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
        th = QHBoxLayout(themeF)
        th.setContentsMargins(16, 0, 16, 0)
        th.setSpacing(16)
        lbl_theme = QLabel('Tema:')
        lbl_theme.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}';")
        combo_theme = QComboBox()
        combo_theme.addItems(['Oscuro', 'Claro'])
        combo_theme.setStyleSheet(f"\n            QComboBox {{ background:{CLR_SURFACE}; color:{CLR_TEXT_IDLE};\n                          font:600 16px '{FONT_FAM}'; border:2px solid {CLR_TITLE};\n                          border-radius:5px; padding:4px 8px; }}\n            QComboBox::drop-down {{ border:none; }}\n            QComboBox QAbstractItemView {{ background:{CLR_PANEL};\n                          border:2px solid {CLR_TITLE};\n                          selection-background-color:{CLR_ITEM_ACT};\n                          color:{CLR_TEXT_IDLE}; outline:none;padding:4px; }}\n        ")
        combo_theme.currentIndexChanged.connect(lambda ix: self._set_theme('dark' if ix == 0 else 'light'))
        self.combo_theme = combo_theme
        th.addWidget(lbl_theme)
        th.addWidget(combo_theme)
        th.addStretch(1)
        v.addWidget(themeF)
        langF = QFrame()
        langF.setFixedHeight(60)
        langF.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
        lh = QHBoxLayout(langF)
        lh.setContentsMargins(16, 0, 16, 0)
        lh.setSpacing(16)
        lbl_lang = QLabel('Idioma:')
        lbl_lang.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}';")
        combo_lang = QComboBox()
        combo_lang.addItems(['Español', 'Inglés'])
        combo_lang.setStyleSheet(combo_theme.styleSheet())
        combo_lang.currentIndexChanged.connect(lambda ix: self._change_language('es' if ix == 0 else 'en'))
        self.combo_lang = combo_lang
        lh.addWidget(lbl_lang)
        lh.addWidget(combo_lang)
        lh.addStretch(1)
        v.addWidget(langF)
        timeF = QFrame()
        timeF.setFixedHeight(60)
        timeF.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
        tf = QHBoxLayout(timeF)
        tf.setContentsMargins(16, 0, 16, 0)
        tf.setSpacing(16)
        lbl_time = QLabel('Tiempo:')
        lbl_time.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}';")
        combo_time = QComboBox()
        combo_time.addItems(['24 hr', '12 hr'])
        combo_time.setStyleSheet(combo_theme.styleSheet())
        combo_time.currentIndexChanged.connect(lambda ix: self._set_time_format(ix == 0))
        self.combo_time = combo_time
        tf.addWidget(lbl_time)
        tf.addWidget(combo_time)
        tf.addStretch(1)
        v.addWidget(timeF)
        notifF = QFrame()
        notifF.setFixedHeight(60)
        notifF.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
        nh = QHBoxLayout(notifF)
        nh.setContentsMargins(16, 0, 16, 0)
        nh.setSpacing(16)
        chk_notif = QPushButton('Notificaciones Emergentes')
        chk_notif.setCheckable(True)
        chk_notif.setChecked(True)
        chk_notif.setStyleSheet(f"\n            QPushButton {{ color:{CLR_TEXT_IDLE}; font:600 16px '{FONT_FAM}'; border:none; background:transparent; }}\n            QPushButton:checked {{ color:{CLR_TITLE}; }}\n        ")
        chk_notif.toggled.connect(self._toggle_notifications)
        self.chk_notif = chk_notif
        nh.addWidget(chk_notif)
        nh.addStretch(1)
        v.addWidget(notifF)
        aboutF = QFrame()
        aboutF.setFixedHeight(100)
        aboutF.setStyleSheet(f'background:{CLR_PANEL}; border-radius:5px;')
        ah = QVBoxLayout(aboutF)
        ah.setContentsMargins(16, 16, 16, 16)
        lbl_app = QLabel('TechHome v1.0')
        lbl_app.setStyleSheet(f"color:{CLR_TITLE}; font:700 18px '{FONT_FAM}';")
        lbl_desc = QLabel('Creado por el equipo VitalTech')
        lbl_desc.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
        ah.addWidget(lbl_app)
        ah.addWidget(lbl_desc)
        v.addWidget(aboutF)
        v.addStretch(1)
        return w

    def _on_list_selected(self, name):
        self.list_title.setText(name)
        self.list_items_widget.clear()
        if hasattr(self, 'username') and self.username:
            try:
                items = database.get_list_items(self.username, name)
                self.lists[name] = items
            except Exception:
                pass
        for item in self.lists.get(name, []):
            QListWidgetItem(item, self.list_items_widget)

    def _on_add_list_item(self):
        name = self.list_title.text()
        if not name:
            return
        dlg = NewElementDialog(self)
        text, ok = dlg.getText()
        if ok and text.strip():
            item_text = text.strip()
            self.lists[name].insert(0, item_text)
            QListWidgetItem(item_text, self.list_items_widget)
            if hasattr(self, 'username') and self.username:
                try:
                    order = int(datetime.now().timestamp() * 1000)
                    database.save_list_item(self.username, name, item_text, order)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f"Elemento añadido a lista '{name}': {item_text}")
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _on_add_list(self):
        dlg = NewListDialog(self)
        text, ok = dlg.getText()
        if ok and text.strip() and (text not in self.lists):
            list_name = text.strip()
            self.lists[list_name] = []
            QListWidgetItem(list_name, self.lists_widget)
            if hasattr(self, 'username') and self.username:
                try:
                    database.save_list(self.username, list_name)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Lista creada: {list_name}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _add_note(self):
        dlg = NewNoteDialog(self)
        text, ok = dlg.getText()
        if ok and text.strip():
            ts = self.format_datetime(datetime.now())
            note = DraggableNote(text.strip(), self.notes_manager, ts)
            placed = False
            for r in range(self.notes_manager.get_max_rows()):
                for cidx in range(self.notes_manager.columns):
                    cell = (r, cidx)
                    if self.notes_manager.is_free(cell):
                        pos = self.notes_manager.cell_to_pos(cell)
                        note.move(pos)
                        self.notes_manager.occupy(cell, note)
                        note._cell = cell
                        placed = True
                        break
                if placed:
                    break
            self.notes_items.append(note)
            note.show()
            if hasattr(self, 'username') and self.username:
                try:
                    row_idx, col_idx = note._cell if hasattr(note, '_cell') else (0, 0)
                    database.save_note(self.username, text.strip(), ts, row_idx, col_idx)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Nota añadida: {text.strip()}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _restore_lists(self, current):
        if not hasattr(self, 'lists_widget'):
            return
        self.lists_widget.clear()
        for name in self.lists.keys():
            QListWidgetItem(name, self.lists_widget)
        if current and current in self.lists:
            row = list(self.lists.keys()).index(current)
            self.lists_widget.setCurrentRow(row)
        elif self.lists:
            self.lists_widget.setCurrentRow(0)

    def _restore_notes(self, notes):
        if not hasattr(self, 'notes_manager'):
            return
        self.notes_items = []
        self.notes_manager.occupancy.clear()
        for text, ts, cell in notes:
            note = DraggableNote(text, self.notes_manager, ts)
            if cell is not None:
                pos = self.notes_manager.cell_to_pos(cell)
                note.move(pos)
                note._cell = cell
                self.notes_manager.occupy(cell, note)
            self.notes_items.append(note)
            note.show()

    def _add_group(self):
        base = 'Grupo Nuevo'
        names = {c.base_name for c in self.group_cards}
        n = 1
        name = f'{base} {n}'
        while name in names:
            n += 1
            name = f'{base} {n}'
        card = GroupCard(name, rename_callback=self._rename_group, select_callback=self._group_select_func)
        idx = self.grp_layout.count() - 1
        self.grp_layout.insertWidget(idx, card)
        self.group_cards.append(card)
        self._apply_language()

    def _add_device(self):
        base = 'Nuevo Dispositivo'
        names = {r.base_name for r in self.device_rows}
        n = 1
        name = f'{base} {n}'
        while name in names:
            n += 1
            name = f'{base} {n}'
        grp = self.active_group if self.active_group != 'Todo' else 'Todo'
        # Compute an icon override for the new device based on its name.  We
        # deliberately do not use the rename mapping here because this is a
        # freshly created device.  The override ensures consistent icons on
        # subsequent application launches.
        icon_override = 'Devices.svg'
        try:
            # Use the device icon map defined in AnimatedBackground to select
            # an appropriate icon based on the name.  Fall back to the generic
            # icon when no keyword matches.
            for key, fname in self._device_icon_map.items():
                if key in name:
                    icon_override = fname
                    break
        except Exception:
            pass
        row = DeviceRow(name, grp, toggle_callback=self._device_toggled,
                        rename_callback=self._rename_device,
                        icon_override=icon_override)
        self.device_rows.append(row)
        self.devices_buttons.append(row.btn)
        self.device_filter_container.addWidget(row)
        self._apply_language()
        self._update_metrics()
        try:
            self._filter_devices()
        except Exception:
            pass
        if hasattr(self, 'username') and self.username:
            try:
                database.log_action(self.username, f'Dispositivo creado: {name}')
                database.save_device_state(self.username, name, grp, False)
            except Exception:
                pass
        try:
            self._refresh_account_info()
        except Exception:
            pass

    def _load_persistent_state(self) -> None:
        if not getattr(self, 'username', None):
            return
        user = self.username
        prev_notif = getattr(self, 'notifications_enabled', True)
        self.notifications_enabled = False
        try:
            dev_states = database.get_device_states(user)
        except Exception:
            dev_states = []
        row_map = {r.base_name: r for r in getattr(self, 'device_rows', [])}
        for device_name, group_name, state in dev_states:
            row = row_map.get(device_name)
            if row is None:
                group_names = {card.base_name for card in getattr(self, 'group_cards', [])}
                grp = group_name if group_name in group_names else 'Todo'
                # Compute an icon override based on the original device name so
                # that renamed devices retain their original icon.  Use the
                # rename mapping if available.
                try:
                    original = device_name
                    if hasattr(self, '_renamed_devices'):
                        original = self._renamed_devices.get(device_name, device_name)
                except Exception:
                    original = device_name
                icon_override = 'Devices.svg'
                try:
                    for key, fname in self._device_icon_map.items():
                        if key in original:
                            icon_override = fname
                            break
                except Exception:
                    pass
                row = DeviceRow(device_name, grp, toggle_callback=self._device_toggled,
                                rename_callback=self._rename_device,
                                icon_override=icon_override)
                self.device_rows.append(row)
                self.devices_buttons.append(row.btn)
                self.device_filter_container.addWidget(row)
                self._apply_language()
                self._update_metrics()
            row.btn.setChecked(state)
        try:
            self._update_metrics()
        except Exception:
            pass
        self.lists = {}
        try:
            user_lists = database.get_lists(user)
        except Exception:
            user_lists = []
        if hasattr(self, 'lists_widget'):
            self.lists_widget.clear()
            for lname in user_lists:
                self.lists[lname] = []
                QListWidgetItem(lname, self.lists_widget)
                try:
                    items = database.get_list_items(user, lname)
                except Exception:
                    items = []
                self.lists[lname] = items
            if user_lists:
                self.lists_widget.setCurrentRow(0)
                self._on_list_selected(user_lists[0])
        if hasattr(self, 'notes_manager'):
            try:
                for note in getattr(self, 'notes_items', []):
                    note.setParent(None)
                self.notes_items = []
                self.notes_manager.occupancy.clear()
            except Exception:
                pass
            try:
                user_notes = database.get_notes(user)
            except Exception:
                user_notes = []
            for text, ts, row_idx, col_idx in user_notes:
                note = DraggableNote(text, self.notes_manager, ts)
                cell = (row_idx, col_idx)
                if not self.notes_manager.is_free(cell):
                    placed = False
                    for r in range(self.notes_manager.get_max_rows()):
                        for cidx in range(self.notes_manager.columns):
                            new_cell = (r, cidx)
                            if self.notes_manager.is_free(new_cell):
                                cell = new_cell
                                placed = True
                                break
                        if placed:
                            break
                pos = self.notes_manager.cell_to_pos(cell)
                note.move(pos)
                note._cell = cell
                self.notes_manager.occupy(cell, note)
                self.notes_items.append(note)
                note.show()
        try:
            user_rems = database.get_reminders(user)
        except Exception:
            user_rems = []
        self.recordatorios = []
        for dt_str, txt in user_rems:
            try:
                dt_obj = datetime.fromisoformat(dt_str)
            except Exception:
                continue
            self.recordatorios.append((dt_obj, txt))
        if hasattr(self, 'table_recordatorios'):
            try:
                self._populate_record_table()
            except Exception:
                pass
        try:
            user_alarms = database.get_alarms(user)
        except Exception:
            user_alarms = []
        self.alarms = []
        for dt_str, txt in user_alarms:
            try:
                dt_obj = datetime.fromisoformat(dt_str)
            except Exception:
                continue
            self.alarms.append((dt_obj, txt))
        if hasattr(self, 'table_alarms'):
            try:
                self._populate_alarm_table()
            except Exception:
                pass
        try:
            user_timers = database.get_timers(user)
        except Exception:
            user_timers = []
        self.timers = []
        now = datetime.now()
        for end_str, txt in user_timers:
            try:
                end_dt = datetime.fromisoformat(end_str)
            except Exception:
                continue
            if end_dt > now:
                self.timers.append((end_dt, txt))
        if hasattr(self, 'table_timers'):
            try:
                self._populate_timer_table()
            except Exception:
                pass
        try:
            if hasattr(self, '_refresh_calendar_events'):
                self._refresh_calendar_events()
        except Exception:
            pass
        try:
            self._filter_devices()
        except Exception:
            pass
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, lambda: setattr(self, 'notifications_enabled', prev_notif))

    def _load_user_settings(self) -> None:
        user = getattr(self, 'username', None)
        if not user:
            return
        prev_loading = getattr(self, 'loading_settings', False)
        self.loading_settings = True
        try:
            try:
                th = database.get_setting(user, 'theme')
            except Exception:
                th = None
            if th in ('dark', 'light') and th != getattr(self, 'theme', 'dark'):
                self._set_theme(th)
            if th in ('dark', 'light') and hasattr(self, 'combo_theme'):
                try:
                    self.combo_theme.blockSignals(True)
                    self.combo_theme.setCurrentIndex(0 if th == 'dark' else 1)
                finally:
                    self.combo_theme.blockSignals(False)
            try:
                lang = database.get_setting(user, 'language')
            except Exception:
                lang = None
            if lang in ('es', 'en') and lang != getattr(self, 'lang', 'es'):
                self._change_language(lang)
            if lang in ('es', 'en') and hasattr(self, 'combo_lang'):
                try:
                    self.combo_lang.blockSignals(True)
                    self.combo_lang.setCurrentIndex(0 if lang == 'es' else 1)
                finally:
                    self.combo_lang.blockSignals(False)
            try:
                t24 = database.get_setting(user, 'time_24h')
            except Exception:
                t24 = None
            if t24 is not None:
                is24 = str(t24).lower() in ('1', 'true', 'yes')
                if is24 != getattr(self, 'time_24h', True):
                    self._set_time_format(is24)
                if hasattr(self, 'combo_time'):
                    try:
                        self.combo_time.blockSignals(True)
                        self.combo_time.setCurrentIndex(0 if is24 else 1)
                    finally:
                        self.combo_time.blockSignals(False)
            try:
                notif = database.get_setting(user, 'notifications_enabled')
            except Exception:
                notif = None
            if notif is not None:
                enabled = str(notif).lower() in ('1', 'true', 'yes')
                if hasattr(self, 'notifications_enabled'):
                    if enabled != getattr(self, 'notifications_enabled', True):
                        self._toggle_notifications(enabled)
                if hasattr(self, 'chk_notif'):
                    try:
                        self.chk_notif.blockSignals(True)
                        self.chk_notif.setChecked(enabled)
                    finally:
                        self.chk_notif.blockSignals(False)
            try:
                cat = database.get_setting(user, 'device_category')
            except Exception:
                cat = None
            if cat and hasattr(self, 'device_category_cb'):
                idx = self.device_category_cb.findText(cat)
                if idx >= 0:
                    try:
                        self.device_category_cb.blockSignals(True)
                        self.device_category_cb.setCurrentIndex(idx)
                    finally:
                        self.device_category_cb.blockSignals(False)
            try:
                so = database.get_setting(user, 'device_sort_order')
            except Exception:
                so = None
            if so and hasattr(self, 'device_sort_cb'):
                idx = self.device_sort_cb.findText(so)
                if idx >= 0:
                    try:
                        self.device_sort_cb.blockSignals(True)
                        self.device_sort_cb.setCurrentIndex(idx)
                    finally:
                        self.device_sort_cb.blockSignals(False)
        finally:
            self.loading_settings = prev_loading

    def _rename_group(self, card, name):
        names = {c.base_name for c in self.group_cards if c is not card}
        return bool(name) and name not in names

    def _rename_device(self, row, name):
        names = {r.base_name for r in self.device_rows if r is not row}
        if bool(name) and name not in names:
            # Capture the old device name before updating
            old_name = getattr(row, 'base_name', None)
            # Update any existing notifications that reference this device
            try:
                updated = []
                for ts, txt in getattr(self, 'notifications', []):
                    if isinstance(txt, str) and old_name and old_name in txt:
                        # Replace only the device name portion; preserve state suffix (Encendido/Apagado/On/Off)
                        for suffix in (' Encendido', ' Apagado', ' On', ' Off'):
                            if txt.endswith(suffix) and txt[:-len(suffix)].strip() == old_name:
                                txt = f"{name}{suffix}"
                                break
                        else:
                            txt = txt.replace(old_name, name)
                    updated.append((ts, txt))
                self.notifications = updated
                # If the notifications dialog is open, refresh its contents
                dlg = getattr(self, 'notifications_dialog', None)
                if dlg is not None:
                    try:
                        dlg.update_notifications()
                    except Exception:
                        pass
                # Update the rename mapping before refreshing the home panel so that
                # _get_notification_icon_name can resolve icons correctly.  Without
                # this, the home notifications panel may temporarily show a
                # generic icon until another notification arrives.
                try:
                    if old_name and name:
                        if not hasattr(self, '_renamed_devices'):
                            self._renamed_devices = {}
                        # Determine the original base name.  If the old name
                        # already has a mapping, use its base; otherwise use
                        # the old name itself.  This preserves the icon across
                        # multiple renames by always pointing back to the
                        # original device name used for icon lookup.
                        base_original = self._renamed_devices.get(old_name, old_name)
                        self._renamed_devices[name] = base_original
                        # Remove the old mapping to avoid chains that could
                        # complicate lookup and consume memory.
                        if old_name in self._renamed_devices:
                            try:
                                del self._renamed_devices[old_name]
                            except Exception:
                                pass
                except Exception:
                    pass
                # Refresh the home notifications panel to reflect the new names
                # and icons.  This must occur after updating _renamed_devices.
                try:
                    self._refresh_home_notifications()
                except Exception:
                    pass
                # Persist the rename to the user's data database.  Update the device_name
                # column so that on next login the renamed device is preserved, without
                # altering its stored state or group.  Also record the rename mapping
                # and update any saved notifications containing the old name.
                try:
                    from database import rename_device, update_renamed_device, update_notification_names
                    username = getattr(self, 'username', None)
                    if username and old_name and name:
                        # Update the device_states table so that the new name
                        # persists for the device state and group.
                        rename_device(username, old_name, name)
                        # Persist the rename mapping.  Use the base original
                        # name for the mapping to ensure the icon remains
                        # consistent across multiple renames.  If the old
                        # device name has a base mapping, use that; otherwise
                        # use the old name itself.
                        base_original = None
                        try:
                            # Use the same logic applied to the in-memory mapping
                            base_original = self._renamed_devices.get(name, None)
                            if base_original is None:
                                # Fallback: derive base from the previous name
                                base_original = self._renamed_devices.get(old_name, old_name)
                        except Exception:
                            pass
                        if base_original is None:
                            base_original = old_name
                        # Store the mapping of the new name back to the base
                        # original name.  This call expects (username, old, new).
                        update_renamed_device(username, base_original, name)
                        # Replace occurrences of the old name in saved notifications
                        update_notification_names(username, old_name, name)
                except Exception:
                    pass
            except Exception:
                pass
            return True
        return False

    def _on_calendar_date_selected(self):
        date = self.calendar_widget.selectedDate().toPyDate()
        self.selected_day_events = [(dt, txt) for dt, txt in self.recordatorios + self.alarms if dt.date() == date]

    def _refresh_calendar_events(self):
        if self.calendar_widget:
            dates = [dt.date() for dt, _ in self.recordatorios + self.alarms]
            self.calendar_widget.update_events(dates)

    def _refresh_account_info(self) -> None:
        if not hasattr(self, 'account_page'):
            return
        total_devices = len(getattr(self, 'device_rows', []))
        active_devices = sum((1 for r in getattr(self, 'device_rows', []) if getattr(r.btn, 'isChecked', lambda: False)()))
        self.acc_dev_label.setText(f'{total_devices} ({active_devices} activos)')
        list_count = len(getattr(self, 'lists', {}))
        item_count = 0
        try:
            for items in getattr(self, 'lists', {}).values():
                item_count += len(items)
        except Exception:
            item_count = 0
        self.acc_list_label.setText(f'{list_count} listas / {item_count} elementos')
        note_count = len(getattr(self, 'notes_items', []))
        self.acc_note_label.setText(f'{note_count} notas')
        rem_count = len(getattr(self, 'recordatorios', []))
        self.acc_rem_label.setText(f'{rem_count} recordatorios')
        alarm_count = len(getattr(self, 'alarms', []))
        self.acc_alarm_label.setText(f'{alarm_count} alarmas')
        timer_count = len(getattr(self, 'timers', []))
        self.acc_timer_label.setText(f'{timer_count} timers')
        health_count = len(getattr(self, 'health_history', []))
        self.acc_health_label.setText(f'{health_count} lecturas')
        action_count_text = '–'
        if hasattr(self, 'acc_action_label'):
            try:
                if getattr(self, 'username', None):
                    cnt = database.get_action_count(self.username)
                    action_count_text = f'{cnt}'
            except Exception:
                action_count_text = '–'
            self.acc_action_label.setText(action_count_text)
        theme_txt = 'Oscuro' if getattr(self, 'theme', 'dark') == 'dark' else 'Claro'
        lang_txt = 'Español' if getattr(self, 'lang', 'es') == 'es' else 'Inglés'
        time_txt = '24 hr' if getattr(self, 'time_24h', True) else '12 hr'
        notif_txt = 'Activadas' if getattr(self, 'notifications_enabled', True) else 'Desactivadas'
        if hasattr(self, 'acc_theme_label'):
            self.acc_theme_label.setText(theme_txt)
            if hasattr(self, 'acc_theme_loc_label'):
                fa_solid_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules', '@fortawesome', 'fontawesome-free', 'svgs', 'solid')
                theme_icon_name = 'moon.svg' if getattr(self, 'theme', 'dark') == 'dark' else 'sun.svg'
                theme_icon_path = os.path.join(fa_solid_dir, theme_icon_name)
                if os.path.isfile(theme_icon_path):
                    ico = QIcon(theme_icon_path)
                    pm = ico.pixmap(QSize(18, 18))
                    pm_tinted = tint_pixmap(pm, QColor(CLR_TITLE))
                    self.acc_theme_loc_label.setPixmap(pm_tinted)
        if hasattr(self, 'acc_lang_label'):
            self.acc_lang_label.setText(lang_txt)
            if hasattr(self, 'acc_lang_loc_label'):
                fa_solid_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules', '@fortawesome', 'fontawesome-free', 'svgs', 'solid')
                lang_icon_name = 'language.svg'
                lang_icon_path = os.path.join(fa_solid_dir, lang_icon_name)
                if os.path.isfile(lang_icon_path):
                    ico = QIcon(lang_icon_path)
                    pm = ico.pixmap(QSize(18, 18))
                    pm_tinted = tint_pixmap(pm, QColor(CLR_TITLE))
                    self.acc_lang_loc_label.setPixmap(pm_tinted)
        if hasattr(self, 'acc_time_label'):
            self.acc_time_label.setText(time_txt)
            if hasattr(self, 'acc_time_loc_label'):
                fa_solid_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules', '@fortawesome', 'fontawesome-free', 'svgs', 'solid')
                time_icon_name = 'clock.svg'
                time_icon_path = os.path.join(fa_solid_dir, time_icon_name)
                if os.path.isfile(time_icon_path):
                    ico = QIcon(time_icon_path)
                    pm = ico.pixmap(QSize(18, 18))
                    pm_tinted = tint_pixmap(pm, QColor(CLR_TITLE))
                    self.acc_time_loc_label.setPixmap(pm_tinted)
        if hasattr(self, 'acc_notif_label'):
            self.acc_notif_label.setText(notif_txt)
            if hasattr(self, 'acc_notif_loc_label'):
                fa_solid_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules', '@fortawesome', 'fontawesome-free', 'svgs', 'solid')
                notif_icon_name = 'bell.svg' if getattr(self, 'notifications_enabled', True) else 'bell-slash.svg'
                notif_icon_path = os.path.join(fa_solid_dir, notif_icon_name)
                if os.path.isfile(notif_icon_path):
                    ico = QIcon(notif_icon_path)
                    pm = ico.pixmap(QSize(18, 18))
                    pm_tinted = tint_pixmap(pm, QColor(CLR_TITLE))
                    self.acc_notif_loc_label.setPixmap(pm_tinted)

class MainWindow(QMainWindow):

    def __init__(self, username: str, login_time: datetime):
        super().__init__()
        self.username = username
        self.login_time = login_time
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(1100, 700)
        self._drag = None
        self.setCentralWidget(AnimatedBackground(self, username=username, login_time=login_time))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None
if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.exec_()
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        username = getattr(login, 'current_user', None)
        login_ts = datetime.now()
        if username:
            try:
                database.log_action(username, 'Inicio de sesión')
            except Exception:
                pass
        win = MainWindow(username, login_ts)
        win.show()
        sys.exit(app.exec_())