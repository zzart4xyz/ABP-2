"""Shared imports, helpers and dialogs for TechHome."""
from __future__ import annotations

import sys
import random
import csv
import os
from dataclasses import dataclass
from typing import Callable
from datetime import datetime, timedelta

import database
from PyQt5.QtCore import Qt, QPoint, QTimer, QDate, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QConicalGradient, QPixmap, QIcon, QPainterPath, QLinearGradient

try:
    from PyQt5.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QStackedWidget, QLineEdit, QComboBox, QScrollBar, QTableWidget, QTableWidgetItem, QTabWidget, QListWidget, QListWidgetItem, QDialog, QTextEdit, QDateTimeEdit, QSpinBox, QCalendarWidget, QCheckBox, QStyledItemDelegate, QStyle, QToolButton, QTableView, QHeaderView, QAbstractSpinBox, QSizePolicy, QProgressBar, QGraphicsOpacityEffect

from constants import *
from health import BPMGauge, MetricsPanel
from widgets import (
    CardButton,
    CustomScrollBar,
    DeviceRow,
    DraggableNote,
    NotesManager,
    QuickAccessButton,
    GroupCard,
    NoFocusDelegate,
    style_table,
    CurrentMonthCalendar,
)
from dialogs import NewElementDialog, NewListDialog, NewNoteDialog

def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))

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

@dataclass(frozen=True)
class MetricSpec:
    key: str
    icon_name: str
    label: str
    progress_fn: Callable[["MetricsDetailsDialog", float], float]
    value_fn: Callable[["MetricsDetailsDialog", float], str]
    graph_color: str = CLR_TITLE

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
        self._metric_specs = self._build_metric_specs()
        for key in self._metric_order:
            spec = self._metric_specs.get(key)
            if spec is None:
                continue
            card, widget_map = self._create_metric_card(spec, outer)
            self.card_widgets[key] = widget_map
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

    def _build_metric_specs(self) -> dict[str, MetricSpec]:
        specs = [
            MetricSpec(
                key='devices',
                icon_name='mobile.svg',
                label='Dispositivos',
                progress_fn=MetricsDetailsDialog._devices_progress,
                value_fn=MetricsDetailsDialog._format_devices_value,
            ),
            MetricSpec(
                key='temp',
                icon_name='temperature-high.svg',
                label='Temperatura',
                progress_fn=lambda dlg, value: dlg._progress_by_scale(value, 40.0),
                value_fn=lambda dlg, value: f'{value:.1f}°C',
            ),
            MetricSpec(
                key='energy',
                icon_name='bolt.svg',
                label='Energía',
                progress_fn=lambda dlg, value: dlg._progress_by_scale(value, 5.0),
                value_fn=lambda dlg, value: f'{value:.2f} kW',
            ),
            MetricSpec(
                key='water',
                icon_name='droplet.svg',
                label='Agua',
                progress_fn=lambda dlg, value: dlg._progress_by_scale(value, 200.0),
                value_fn=lambda dlg, value: f'{int(value)} L',
            ),
        ]
        self._metric_order = [spec.key for spec in specs]
        return {spec.key: spec for spec in specs}

    def _create_metric_card(self, spec: MetricSpec, parent: QWidget) -> tuple[QFrame, dict[str, QWidget]]:
        card = QFrame(parent)
        card.setStyleSheet(f'background:{CLR_SURFACE}; border:none; border-radius:8px;')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)
        gauge = MetricGauge(spec.icon_name)
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
        widget_map = {
            'gauge': gauge,
            'class': class_label,
            'value': value_label,
            'arrow': arrow_label,
            'percent': percent_label,
            'graph': graph,
        }
        return card, widget_map

    def _total_devices(self) -> int:
        return len(getattr(self._main, 'devices_buttons', []))

    def _devices_progress(self, active_devices: float) -> float:
        total = self._total_devices()
        if total <= 0:
            return 0.0
        return active_devices / total

    def _format_devices_value(self, active_devices: float) -> str:
        total = self._total_devices()
        active = int(round(active_devices))
        if total > 0:
            return f'{active} de {total}'
        return f'{active}'

    @staticmethod
    def _progress_by_scale(value: float, maximum: float) -> float:
        if maximum <= 0:
            return 0.0
        return value / maximum

    def update_metrics(self) -> None:
        metrics = getattr(self._main, 'home_metrics', {})
        history = getattr(self._main, 'metric_history', {})
        for key, widgets in self.card_widgets.items():
            spec = self._metric_specs.get(key)
            if spec is None:
                continue
            raw_value = metrics.get(key, 0)
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                value = 0.0
            progress = clamp(spec.progress_fn(self, value))
            widgets['gauge'].setValue(progress, animate=True)
            widgets['class'].setText(spec.label)
            widgets['value'].setText(spec.value_fn(self, value))
            widgets['arrow'].setVisible(False)
            widgets['percent'].setText('')
            widgets['percent'].setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:500 14px '{FONT_FAM}';")
            prev_vals = history.get(key, [])
            graph_values = prev_vals[-12:] if prev_vals else []
            widgets['graph'].setValues(graph_values, QColor(spec.graph_color), animate=True)

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
