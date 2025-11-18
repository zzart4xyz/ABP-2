import sys
import random
import csv
import os
from dataclasses import dataclass
from typing import Any, Callable
from datetime import datetime, timedelta
from PyQt5.QtCore import (
    Qt,
    QPoint,
    QTimer,
    QDate,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    QSize,
    QPointF,
    QRectF,
    QAbstractAnimation,
    QParallelAnimationGroup,
    QSequentialAnimationGroup,
    QPauseAnimation,
    QEvent,
)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QConicalGradient, QPixmap, QIcon, QPainterPath, QLinearGradient
try:
    from PyQt5.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QStackedWidget, QLineEdit, QComboBox, QScrollBar, QTableWidget, QTableWidgetItem, QTabWidget, QListWidget, QListWidgetItem, QDialog, QTextEdit, QDateTimeEdit, QSpinBox, QCalendarWidget, QCheckBox, QStyledItemDelegate, QStyle, QToolButton, QTableView, QHeaderView, QAbstractSpinBox, QSizePolicy, QProgressBar, QGraphicsOpacityEffect
from constants import *
from models import AlarmState, ReminderState, TimerState, WEEKDAY_ORDER


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class MetricSpec:
    key: str
    icon_name: str
    label: str
    progress_fn: Callable[["MetricsDetailsDialog", float], float]
    value_fn: Callable[["MetricsDetailsDialog", float], str]
    graph_color: str = CLR_TITLE


class TimerPopupDialog(QDialog):
    """Frameless dialog that can be dragged and positioned manually."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drag_active = False
        self._drag_offset = QPoint()
        self._drag_handles: list[QWidget] = []
        self.installEventFilter(self)

    def register_drag_handle(self, widget: QWidget) -> None:
        if widget not in self._drag_handles:
            widget.installEventFilter(self)
            self._drag_handles.append(widget)

    def eventFilter(self, obj, event):  # type: ignore[override]
        if obj is self or obj in self._drag_handles:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_active = True
                self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            elif event.type() == QEvent.MouseMove and self._drag_active and event.buttons() & Qt.LeftButton:
                self.move(event.globalPos() - self._drag_offset)
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._drag_active = False
        return super().eventFilter(obj, event)

    def position_top_right(self, margin: int = 24) -> None:
        screen = self.windowHandle().screen() if self.windowHandle() else QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        geo = self.frameGeometry()
        x = available.x() + available.width() - geo.width() - margin
        y = available.y() + margin
        min_x = available.x() + margin
        self.move(max(min_x, x), y)

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


class SlideFadeEffect(QGraphicsOpacityEffect):
    """Efecto gráfico que combina deslizamiento vertical y desvanecimiento."""

    def __init__(self, *, direction: str = 'down', offset: float = 36.0, fade_enabled: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._progress: float = 0.0
        self._offset: float = float(offset)
        self._direction: str = direction if direction in {'down', 'up'} else 'down'
        self._fade_enabled: bool = fade_enabled
        if fade_enabled:
            super().setOpacity(0.0)
        else:
            super().setOpacity(1.0)

    @pyqtProperty(float)
    def progress(self) -> float:
        return self._progress

    @progress.setter
    def progress(self, value: float) -> None:
        self._progress = clamp(value, 0.0, 1.0)
        if self._fade_enabled:
            super().setOpacity(self._progress)
        self.update()

    def draw(self, painter: QPainter) -> None:  # type: ignore[override]
        painter.save()
        direction_multiplier = -1.0 if self._direction == 'down' else 1.0
        translation = (1.0 - self._progress) * self._offset * direction_multiplier
        painter.translate(0.0, translation)
        super().draw(painter)
        painter.restore()

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
        self._arrow_up_pix = tint_pixmap(load_icon_pixmap('Flecha Arriba.svg', QSize(16, 16)), self._trend_up_color)
        self._arrow_down_pix = tint_pixmap(load_icon_pixmap('Flecha Abajo.svg', QSize(16, 16)), self._trend_down_color)

    def _build_metric_specs(self) -> dict[str, MetricSpec]:
        specs = [
            MetricSpec(
                key='devices',
                icon_name='Móvil.svg',
                label='Dispositivos',
                progress_fn=MetricsDetailsDialog._devices_progress,
                value_fn=MetricsDetailsDialog._format_devices_value,
            ),
            MetricSpec(
                key='temp',
                icon_name='Calentador Agua.svg',
                label='Temperatura',
                progress_fn=lambda dlg, value: dlg._progress_by_scale(value, 40.0),
                value_fn=lambda dlg, value: f'{value:.1f}°C',
            ),
            MetricSpec(
                key='energy',
                icon_name='Energía.svg',
                label='Energía',
                progress_fn=lambda dlg, value: dlg._progress_by_scale(value, 5.0),
                value_fn=lambda dlg, value: f'{value:.2f} kW',
            ),
            MetricSpec(
                key='water',
                icon_name='Agua.svg',
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
            # Try the explicit Buscar.svg first as requested
            for icon_name in ('Buscar.svg', 'Search.svg', 'magnifying-glass.svg', 'search.svg', 'magnifying-glass-circle.svg', 'circle-info.svg'):
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
from dialogs import (
    NewNoteDialog,
    NewListDialog,
    NewElementDialog,
    TimerEditorDialog,
    AlarmEditorDialog,
    ReminderEditorDialog,
)
from DiseñoPC import SplashScreen, create_splash_animations
from DiseñoIR import LoginDialog
from DiseñoI import build_home_page, create_home_animations
from DiseñoD import build_devices_page, create_devices_animations
from DiseñoM import build_more_page, create_more_animations
from DiseñoS import build_health_page, create_health_animations
from DiseñoC import build_config_page, create_config_animations
from DiseñoCa import build_account_page, create_account_animations
import database
from widgets import (
    NotesManager,
    DraggableNote,
    CustomScrollBar,
    NoFocusDelegate,
    style_table,
    CurrentMonthCalendar,
    CardButton,
    QuickAccessButton,
    GroupCard,
    DeviceRow,
    TimerCard,
    TimerFullscreenView,
    AlarmCard,
)
from health import BPMGauge, MetricsPanel

class AnimatedBackground(QWidget):

    def __init__(self, parent=None, *, username: str | None=None, login_time: datetime | None=None):
        super().__init__(parent)
        self.username = username
        self.login_time = login_time
        self.lists = {'Compra': [], 'Tareas': []}
        self.recordatorios: list[ReminderState] = []
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._check_reminders)
        self.reminder_timer.start(60000)
        self.alarms: list[AlarmState] = []
        self.timers: list[TimerState] = []
        self._alarm_card_widgets: dict[int, AlarmCard] = {}
        self._timer_card_widgets: dict[int, TimerCard] = {}
        self._timer_fullscreen_timer: TimerState | None = None
        self.timer_fullscreen_dialog: QDialog | None = None
        self._alarm_edit_mode = False
        self._timer_edit_mode = False
        self._last_selected_timer: TimerState | None = None
        self._last_selected_alarm: AlarmState | None = None
        self.timer_update = QTimer(self)
        self.timer_update.timeout.connect(self._update_timers)
        self.timer_update.start(1000)
        self.calendar_widget = None
        self.calendar_event_table = None
        self._angle = 0
        self._bg_timer = QTimer(self)
        self._bg_timer.timeout.connect(self._on_timeout)
        self._bg_timer.start(200)
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
        self._device_icon_map: dict[str, str] = {
            'Luz': 'Luz.svg',
            'Luces': 'Luces.svg',
            'Lámpara': 'Lámpara.svg',
            'Ventilador': 'Ventilador.svg',
            'Aire Acondicionado': 'Aire Acondicionado.svg',
            'Cortinas': 'Cortinas.svg',
            'Persianas': 'Persianas.svg',
            'Enchufe': 'Enchufe.svg',
            'Extractor': 'Extractor.svg',
            'Calentador Agua': 'Calentador Agua.svg',
            'Espejo': 'Espejo.svg',
            'Ducha': 'Ducha.svg',
            'Televisor': 'Televisor.svg',
            'Consola Juegos': 'Consola Juegos.svg',
            'Equipo Sonido': 'Equipo Sonido.svg',
            'Calefactor': 'Calefactor.svg',
            'Refrigerador': 'Refrigerador.svg',
            'Horno': 'Horno.svg',
            'Microondas': 'Microondas.svg',
            'Lavavajillas': 'Lavavajillas.svg',
            'Licuadora': 'Licuadora.svg',
            'Cafetera': 'Cafetera.svg',
        }
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

    def _force_full_opacity(self, root: QWidget) -> None:
        widgets: list[QWidget] = [root]
        widgets.extend(root.findChildren(QWidget))
        for widget in widgets:
            final_pos = widget.property('_techhome_final_pos')
            if isinstance(final_pos, QPoint):
                try:
                    widget.move(final_pos)
                except Exception:
                    pass
            effect = widget.graphicsEffect()
            if isinstance(effect, QGraphicsOpacityEffect):
                try:
                    effect.setOpacity(1.0)
                except Exception:
                    pass
                try:
                    widget.setGraphicsEffect(None)
                except Exception:
                    pass

    def _resolve_animation_widget(self, target: Any) -> QWidget | None:
        widget = None
        if callable(target):
            try:
                widget = target()
            except TypeError:
                widget = target(self)
        elif isinstance(target, str):
            widget = getattr(self, target, None)
        return widget if isinstance(widget, QWidget) else None

    def _build_animation_entry(self, spec: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(spec, dict):
            return None
        widget = self._resolve_animation_widget(spec.get('target'))
        if widget is None:
            return None
        anim_type_raw = spec.get('type', 'fade')
        anim_type = str(anim_type_raw).lower() if anim_type_raw is not None else 'fade'

        try:
            duration = int(spec.get('duration', 400) or 400)
        except Exception:
            duration = 400
        easing = spec.get('easing')
        if not isinstance(easing, QEasingCurve):
            easing = QEasingCurve.InOutCubic

        entry: dict[str, Any] = {'widget': widget}

        if anim_type == 'fade':
            try:
                start = float(spec.get('start', 0.0))
            except Exception:
                start = 0.0
            try:
                end = float(spec.get('end', 1.0))
            except Exception:
                end = 1.0
            remove_effect = bool(spec.get('remove_effect', True))
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
            try:
                effect.setOpacity(start)
            except Exception:
                effect.setOpacity(0.0)
            animation = QPropertyAnimation(effect, b'opacity', widget)
            animation.setDuration(duration)
            animation.setStartValue(start)
            animation.setEndValue(end)
            animation.setEasingCurve(easing)
            entry['effect'] = effect

            def cleanup(end_value=end, remove=remove_effect, effect_ref=effect, widget_ref=widget):
                try:
                    effect_ref.setOpacity(end_value)
                except Exception:
                    pass
                if remove:
                    try:
                        widget_ref.setGraphicsEffect(None)
                    except Exception:
                        pass
                if entry in getattr(self, '_running_page_anims', []):
                    try:
                        self._running_page_anims.remove(entry)
                    except ValueError:
                        pass

        elif anim_type in {'slide', 'slide_fade'}:
            try:
                offset = float(spec.get('offset', 36.0))
            except Exception:
                offset = 36.0
            offset = abs(offset)
            direction = str(spec.get('direction', 'down') or 'down').lower()
            if direction not in {'down', 'up'}:
                direction = 'down'
            fade_enabled = anim_type == 'slide_fade'
            fade_enabled = bool(spec.get('fade', fade_enabled))
            effect = SlideFadeEffect(direction=direction, offset=offset, fade_enabled=fade_enabled, parent=widget)
            widget.setGraphicsEffect(effect)
            effect.progress = 0.0
            animation = QPropertyAnimation(effect, b'progress', widget)
            animation.setDuration(duration)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setEasingCurve(easing)
            entry['effect'] = effect
            remove_effect = bool(spec.get('remove_effect', True))

            def cleanup(end_value=1.0, remove=remove_effect, effect_ref=effect, widget_ref=widget):
                if isinstance(effect_ref, SlideFadeEffect):
                    try:
                        effect_ref.progress = end_value
                    except Exception:
                        pass
                if remove and isinstance(effect_ref, QGraphicsOpacityEffect):
                    try:
                        widget_ref.setGraphicsEffect(None)
                    except Exception:
                        pass
                if entry in getattr(self, '_running_page_anims', []):
                    try:
                        self._running_page_anims.remove(entry)
                    except ValueError:
                        pass

        else:
            return None

        prepare = spec.get('prepare')
        if callable(prepare):
            effect_obj = entry.get('effect')
            try:
                prepare(widget, effect_obj)
            except TypeError:
                try:
                    prepare(widget)
                except TypeError:
                    prepare()

        entry['animation'] = animation
        entry['cleanup'] = cleanup
        animation.finished.connect(cleanup)
        return entry

    def _switch_page(self, stack, index):
        if index == stack.currentIndex():
            return
        stack.setCurrentIndex(index)
        current_widget = stack.currentWidget()
        if isinstance(current_widget, QWidget):
            self._force_full_opacity(current_widget)
        self._play_page_animations(index)

    def _play_page_animations(self, index: int) -> None:
        stack = getattr(self, 'stack', None)
        if stack is None:
            return
        widget = stack.widget(index)
        if isinstance(widget, QWidget):
            self._force_full_opacity(widget)
        specs = self._page_animations.get(index, [])
        if not hasattr(self, '_running_page_anims'):
            self._running_page_anims = []
        if hasattr(self, '_page_anim_group'):
            group = getattr(self, '_page_anim_group', None)
            if isinstance(group, QParallelAnimationGroup):
                try:
                    group.stop()
                except Exception:
                    pass
            for entry in list(getattr(self, '_running_page_anims', [])):
                cleanup = entry.get('cleanup')
                if callable(cleanup):
                    cleanup()
            self._running_page_anims.clear()
            try:
                if isinstance(group, QParallelAnimationGroup):
                    group.deleteLater()
            except Exception:
                pass
            self._page_anim_group = None
        if not specs:
            return
        group = QParallelAnimationGroup(self)
        self._page_anim_group = group
        for spec in specs:
            entry = self._build_animation_entry(spec)
            if not entry:
                continue
            animation = entry.get('animation')
            if animation is None:
                continue
            try:
                animation.stop()
            except Exception:
                pass
            try:
                animation.setDirection(QAbstractAnimation.Forward)
            except Exception:
                pass
            self._running_page_anims.append(entry)
            try:
                delay = int(spec.get('delay', 0) or 0)
            except Exception:
                delay = 0
            if delay > 0:
                seq = QSequentialAnimationGroup(group)
                seq.addPause(delay)
                seq.addAnimation(animation)
                group.addAnimation(seq)
                entry['wrapper'] = seq
            else:
                group.addAnimation(animation)

        def finish_group(grp=group):
            for entry in list(getattr(self, '_running_page_anims', [])):
                cleanup = entry.get('cleanup')
                if callable(cleanup):
                    cleanup()
            self._running_page_anims.clear()
            if getattr(self, '_page_anim_group', None) is grp:
                self._page_anim_group = None
            try:
                grp.deleteLater()
            except Exception:
                pass

        group.finished.connect(finish_group)
        group.start()

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
        tables = {'notif_table': ['Hora', 'Mensaje'], 'table_health': ['Fecha', 'PA', 'BPM', 'SpO₂', 'Temp', 'FR']}
        for attr, headers in tables.items():
            tbl = getattr(self, attr, None)
            if tbl:
                tbl.setHorizontalHeaderLabels([mapping.get(h, h) for h in headers])
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
            return 'Información.svg'
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
                icon_name = 'Dispositivos.svg'
                for key, fname in self._device_icon_map.items():
                    # Match against the original name to preserve the icon assignment
                    if key in original:
                        icon_name = fname
                        break
                return icon_name
        if t.startswith('Recordatorio') or t.startswith('Reminder'):
            return 'Recordatorios.svg'
        if 'Alarma' in t or 'Alarm' in t:
            return 'Alarmas.svg'
        if 'Timer' in t:
            return 'Timers.svg'
        return 'Información.svg'

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
        icon_file = resolve_icon_path(icon_name)
        self.popup_label.setTextFormat(Qt.RichText)
        if icon_file:
            rich_text = f"<img src='{icon_file}' width='20' height='20' style='vertical-align:middle;margin-right:6px;'/> {display}"
        else:
            rich_text = display
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
        due = [rem for rem in list(self.recordatorios) if rem.when <= now]
        if not due:
            return
        mapping = TRANSLATIONS_EN if self.lang == 'en' else {}
        for reminder in due:
            self.recordatorios.remove(reminder)
            if hasattr(self, 'username') and self.username:
                try:
                    database.delete_reminder(self.username, reminder)
                except Exception:
                    pass
            if self.notifications_enabled:
                text = mapping.get(reminder.message, reminder.message)
                self.popup_label.setText('🔔 ' + text)
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
                self._add_notification(f'Recordatorio: {reminder.message}')
        self._after_reminders_changed()

    def _open_new_reminder_dialog(self) -> None:
        dialog = ReminderEditorDialog(parent=self)
        if dialog.exec_() != QDialog.Accepted or dialog.was_deleted:
            return
        reminder = dialog.result_state()
        if hasattr(self, 'username') and self.username:
            try:
                database.save_reminder(self.username, reminder)
            except Exception:
                pass
            try:
                database.log_action(self.username, f'Recordatorio añadido: {reminder.message} @ {reminder.when.isoformat()}')
            except Exception:
                pass
        self.recordatorios.append(reminder)
        self._after_reminders_changed()
        self._add_notification('Recordatorio Añadido')

    def _edit_reminder(self, reminder: ReminderState) -> None:
        dialog = ReminderEditorDialog(reminder, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        if dialog.was_deleted:
            self._delete_reminder(reminder)
            return
        updated = dialog.result_state()
        reminder.when = updated.when
        reminder.message = updated.message
        reminder.reminder_id = updated.reminder_id
        if hasattr(self, 'username') and self.username:
            try:
                database.save_reminder(self.username, reminder)
            except Exception:
                pass
            try:
                database.log_action(self.username, f'Recordatorio editado: {reminder.message}')
            except Exception:
                pass
        self._after_reminders_changed()
        self._add_notification('Recordatorio Actualizado')

    def _delete_reminder(self, reminder: ReminderState, *, notify: bool = True, log: bool = True, refresh: bool = True) -> None:
        if reminder in self.recordatorios:
            self.recordatorios.remove(reminder)
        if hasattr(self, 'username') and self.username:
            try:
                database.delete_reminder(self.username, reminder)
            except Exception:
                pass
            if log:
                try:
                    database.log_action(self.username, f'Recordatorio eliminado: {reminder.message}')
                except Exception:
                    pass
        if refresh:
            self._after_reminders_changed()
        if notify:
            self._add_notification('Recordatorio Eliminado')

    def _refresh_reminder_table(self) -> None:
        table = getattr(self, 'reminder_table', None)
        if table is None:
            return
        reminders = sorted(self.recordatorios, key=lambda r: r.when)
        table.setRowCount(len(reminders))
        for row, reminder in enumerate(reminders):
            message_item = QTableWidgetItem(reminder.message or 'Recordatorio')
            message_item.setData(Qt.UserRole, reminder)
            message_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, 0, message_item)

            date_item = QTableWidgetItem(reminder.when.strftime('%d %b %Y'))
            date_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, 1, date_item)

            time_item = QTableWidgetItem(reminder.when.strftime('%H:%M'))
            time_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, 2, time_item)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(6)

            edit_btn = QToolButton()
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(
                f"QToolButton {{ background:{CLR_SURFACE}; border:none; border-radius:12px; padding:6px; color:{CLR_TEXT_IDLE}; }}"
                f"QToolButton:hover {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; }}"
            )
            edit_icon = icon('pen-to-square.svg')
            if not edit_icon.isNull():
                edit_btn.setIcon(edit_icon)
                edit_btn.setIconSize(QSize(18, 18))
            else:
                edit_btn.setText('✏')
            edit_btn.clicked.connect(lambda _, r=reminder: self._edit_reminder(r))
            actions_layout.addWidget(edit_btn)

            delete_btn = QToolButton()
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet(
                f"QToolButton {{ background:{CLR_SURFACE}; border:none; border-radius:12px; padding:6px; color:{CLR_TEXT_IDLE}; }}"
                f"QToolButton:hover {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; }}"
            )
            delete_icon = icon('trash-can.svg')
            if not delete_icon.isNull():
                delete_btn.setIcon(delete_icon)
                delete_btn.setIconSize(QSize(18, 18))
            else:
                delete_btn.setText('🗑')
            delete_btn.clicked.connect(lambda _, r=reminder: self._delete_reminder(r))
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch(1)
            table.setCellWidget(row, 3, actions_widget)

            table.setRowHeight(row, 54)

    def _reminder_for_row(self, row: int) -> ReminderState | None:
        table = getattr(self, 'reminder_table', None)
        if table is None or row < 0 or row >= table.rowCount():
            return None
        item = table.item(row, 0)
        reminder = item.data(Qt.UserRole) if item else None
        return reminder if isinstance(reminder, ReminderState) else None

    def _on_reminder_cell_double_clicked(self, row: int, column: int) -> None:
        reminder = self._reminder_for_row(row)
        if reminder is not None:
            self._edit_reminder(reminder)

    def _update_reminder_summary(self) -> None:
        has_reminders = bool(self.recordatorios)
        if hasattr(self, 'reminder_empty_label'):
            self.reminder_empty_label.setVisible(not has_reminders)
        table = getattr(self, 'reminder_table', None)
        if table is not None:
            table.setVisible(True)
        if hasattr(self, 'record_count_badge'):
            self.record_count_badge.setText(f"{len(self.recordatorios)} activos")
        if hasattr(self, 'next_record_label'):
            if has_reminders:
                upcoming = min(self.recordatorios, key=lambda r: r.when)
                self.next_record_label.setText(
                    f"Próximo: {upcoming.when.strftime('%d %b · %H:%M')} · {upcoming.message}"
                )
            else:
                self.next_record_label.setText('Sin recordatorios programados')

    def _after_reminders_changed(self) -> None:
        self.recordatorios.sort(key=lambda r: r.when)
        self._refresh_reminder_table()
        self._update_reminder_summary()
        try:
            self._refresh_calendar_events()
        except Exception:
            pass
        try:
            self._refresh_account_info()
        except Exception:
            pass

    def _show_popup_message(self, message: str) -> None:
        self.popup_label.setText(message)
        self.popup_label.adjustSize()
        try:
            parent_width = self.parent().width() if self.parent() else self.width()
        except Exception:
            parent_width = self.width()
        x = max(0, parent_width - self.popup_label.width() - 40)
        self.popup_label.move(x, 20)
        self.hide_anim.stop()
        self.popup_label.show()
        self.show_anim.setStartValue(0.0)
        self.show_anim.setEndValue(1.0)
        self.show_anim.start()
        QTimer.singleShot(
            3000,
            lambda: (
                self.hide_anim.setStartValue(1.0),
                self.hide_anim.setEndValue(0.0),
                self.hide_anim.start(),
            ),
        )

    def _notify_timer_finished(self, timer: TimerState) -> None:
        mapping = TRANSLATIONS_EN if self.lang == 'en' else {}
        label = mapping.get(timer.label, timer.label)
        if self.notifications_enabled:
            self._show_popup_message('⏰ ' + label)
        self._add_notification(f'Timer {label} completado')

    def _update_timers(self) -> None:
        now = datetime.now()
        changed = False
        for timer in self.timers:
            if timer.running:
                if timer.runtime_anchor is None:
                    timer.runtime_anchor = now
                elapsed = int((now - timer.runtime_anchor).total_seconds())
                if elapsed > 0:
                    timer.remaining = max(0, timer.remaining - elapsed)
                    timer.runtime_anchor = now
                    changed = True
                    if timer.remaining == 0:
                        if timer.loop and timer.duration > 0:
                            timer.remaining = timer.duration
                            timer.last_started = now
                            timer.runtime_anchor = now
                            if hasattr(self, 'username') and self.username:
                                try:
                                    database.save_timer(self.username, timer)
                                except Exception:
                                    pass
                        else:
                            timer.running = False
                            timer.last_started = None
                            timer.runtime_anchor = None
                            self._notify_timer_finished(timer)
                            if hasattr(self, 'username') and self.username:
                                try:
                                    database.save_timer(self.username, timer)
                                except Exception:
                                    pass
        if changed:
            self._refresh_timer_cards()

    def _open_new_alarm_dialog(self):
        dlg = AlarmEditorDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted and not dlg.was_deleted:
            alarm = dlg.result_state()
            self.alarms.append(alarm)
            self._add_notification('Alarma Añadida')
            if hasattr(self, 'username') and self.username:
                try:
                    database.save_alarm(self.username, alarm)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Alarma añadida: {alarm.label}')
                except Exception:
                    pass
            self._refresh_alarm_cards()
            self._refresh_calendar_events()
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _edit_alarm(self, alarm: AlarmState):
        dlg = AlarmEditorDialog(alarm, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            if dlg.was_deleted:
                self._delete_alarm(alarm)
                return
            updated = dlg.result_state()
            alarm.label = updated.label
            alarm.trigger = updated.trigger
            alarm.repeat_days = updated.repeat_days
            alarm.sound = updated.sound
            alarm.snooze_minutes = updated.snooze_minutes
            if hasattr(self, 'username') and self.username:
                try:
                    database.save_alarm(self.username, alarm)
                except Exception:
                    pass
            self._refresh_alarm_cards()
            self._refresh_calendar_events()

    def _delete_alarm(self, alarm: AlarmState):
        if alarm in self.alarms:
            self.alarms.remove(alarm)
            self._add_notification('Alarma Eliminada')
            self._refresh_alarm_cards()
            self._refresh_calendar_events()
            if hasattr(self, 'username') and self.username and alarm.alarm_id is not None:
                try:
                    database.delete_alarm(self.username, alarm.alarm_id)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Alarma eliminada: {alarm.label}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _toggle_alarm_enabled(self, alarm: AlarmState, enabled: bool):
        alarm.enabled = enabled
        if hasattr(self, 'username') and self.username:
            try:
                database.save_alarm(self.username, alarm)
            except Exception:
                pass
        self._refresh_alarm_cards()
        self._refresh_calendar_events()

    def _open_new_timer_dialog(self):
        dlg = TimerEditorDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted and not dlg.was_deleted:
            timer = dlg.result_state()
            if timer.duration <= 0:
                return
            timer.remaining = timer.duration
            timer.running = False
            timer.runtime_anchor = None
            self.timers.append(timer)
            self._add_notification('Timer Añadido')
            if hasattr(self, 'username') and self.username:
                try:
                    database.save_timer(self.username, timer)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Timer añadido: {timer.label}')
                except Exception:
                    pass
            self._refresh_timer_cards()
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _edit_timer(self, timer: TimerState):
        dlg = TimerEditorDialog(timer, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            if dlg.was_deleted:
                self._delete_timer(timer)
                return
            updated = dlg.result_state()
            timer.label = updated.label
            timer.duration = updated.duration
            timer.remaining = min(updated.remaining, updated.duration)
            timer.loop = updated.loop
            timer.running = updated.running
            timer.last_started = updated.last_started
            timer.runtime_anchor = None
            if hasattr(self, 'username') and self.username:
                try:
                    database.save_timer(self.username, timer)
                except Exception:
                    pass
            self._refresh_timer_cards()

    def _delete_timer(self, timer: TimerState):
        if timer in self.timers:
            self.timers.remove(timer)
            self._add_notification('Timer Eliminado')
            self._refresh_timer_cards()
            if hasattr(self, 'username') and self.username and timer.timer_id is not None:
                try:
                    database.delete_timer(self.username, timer.timer_id)
                except Exception:
                    pass
            if hasattr(self, 'username') and self.username:
                try:
                    database.log_action(self.username, f'Timer eliminado: {timer.label}')
                except Exception:
                    pass
            try:
                self._refresh_account_info()
            except Exception:
                pass

    def _toggle_timer_loop(self, timer: TimerState, enabled: bool):
        timer.loop = enabled
        if hasattr(self, 'username') and self.username:
            try:
                database.save_timer(self.username, timer)
            except Exception:
                pass
        self._refresh_timer_cards()

    def _play_timer(self, timer: TimerState):
        if timer.duration <= 0:
            return
        timer.running = True
        timer.last_started = datetime.now()
        timer.runtime_anchor = timer.last_started
        if hasattr(self, 'username') and self.username:
            try:
                database.save_timer(self.username, timer)
            except Exception:
                pass
        self._refresh_timer_cards()

    def _pause_timer(self, timer: TimerState):
        timer.running = False
        timer.runtime_anchor = None
        timer.last_started = None
        if hasattr(self, 'username') and self.username:
            try:
                database.save_timer(self.username, timer)
            except Exception:
                pass
        self._refresh_timer_cards()

    def _reset_timer(self, timer: TimerState):
        timer.running = False
        timer.remaining = timer.duration
        timer.runtime_anchor = None
        timer.last_started = None
        if hasattr(self, 'username') and self.username:
            try:
                database.save_timer(self.username, timer)
            except Exception:
                pass
        self._refresh_timer_cards()

    def _play_fullscreen_timer(self):
        if self._timer_fullscreen_timer is not None:
            self._play_timer(self._timer_fullscreen_timer)

    def _pause_fullscreen_timer(self):
        if self._timer_fullscreen_timer is not None:
            self._pause_timer(self._timer_fullscreen_timer)

    def _reset_fullscreen_timer(self):
        if self._timer_fullscreen_timer is not None:
            self._reset_timer(self._timer_fullscreen_timer)

    def _style_mode_button(self, button: QToolButton, active: bool) -> None:
        button.setStyleSheet(pill_button_style(active))

    def _set_timer_edit_mode(self, active: bool) -> None:
        self._timer_edit_mode = active
        if hasattr(self, 'edit_timer_mode_btn'):
            self._style_mode_button(self.edit_timer_mode_btn, active)
        for card in self._timer_card_widgets.values():
            card.set_edit_mode(active)

    def _set_alarm_edit_mode(self, active: bool) -> None:
        self._alarm_edit_mode = active
        if hasattr(self, 'edit_alarm_mode_btn'):
            self._style_mode_button(self.edit_alarm_mode_btn, active)
        for card in self._alarm_card_widgets.values():
            card.set_edit_mode(active)

    def _format_timer_finish(self, timer: TimerState) -> str:
        if timer.remaining == 0:
            return 'Completado'
        return ''

    def _refresh_timer_cards(self):
        if not hasattr(self, 'timer_cards_layout'):
            return
        layout = self.timer_cards_layout
        now = datetime.now()
        keep: set[int] = set()
        active_timer = self._timer_fullscreen_timer
        active_key = id(active_timer) if active_timer is not None else None
        ordered_cards: list[TimerCard] = []
        for timer in self.timers:
            key = id(timer)
            keep.add(key)
            card = self._timer_card_widgets.get(key)
            if card is None:
                card = TimerCard()
                self._timer_card_widgets[key] = card
                card.playRequested.connect(lambda c, t=timer: self._play_timer(t))
                card.pauseRequested.connect(lambda c, t=timer: self._pause_timer(t))
                card.resetRequested.connect(lambda c, t=timer: self._reset_timer(t))
                card.loopToggled.connect(lambda c, state, t=timer: self._toggle_timer_loop(t, state))
                card.editRequested.connect(lambda c, t=timer: self._edit_timer(t))
                card.deleteRequested.connect(lambda c, t=timer: self._delete_timer(t))
                card.fullscreenRequested.connect(lambda c, t=timer: self._show_timer_fullscreen(t))
                card.clicked.connect(lambda c, t=timer: setattr(self, '_last_selected_timer', t))
            progress = timer.progress if timer.duration else 0.0
            finish_text = self._format_timer_finish(timer)
            card.set_state(timer, progress, finish_text, timer.running)
            card.set_edit_mode(self._timer_edit_mode)
            if active_key == key:
                self._update_timer_fullscreen_state(timer)
            ordered_cards.append(card)
        for idx, card in enumerate(ordered_cards):
            row = idx // 2
            col = idx % 2
            layout.addWidget(card, row, col)
        for key, card in list(self._timer_card_widgets.items()):
            if key not in keep:
                card.setParent(None)
                card.deleteLater()
                del self._timer_card_widgets[key]
        if active_key is not None and active_key not in keep:
            self._close_timer_fullscreen()
        has_timers = bool(self.timers)
        if hasattr(self, 'timer_empty_label'):
            self.timer_empty_label.setVisible(not has_timers)
        if hasattr(self, 'timer_cards_widget'):
            self.timer_cards_widget.setVisible(has_timers)
        if not has_timers:
            self._close_timer_fullscreen()

    def _ensure_timer_fullscreen_dialog(self) -> bool:
        if not hasattr(self, 'timer_fullscreen_view'):
            return False
        if self.timer_fullscreen_dialog is None:
            dialog = TimerPopupDialog(self)
            dialog.setModal(False)
            dialog.setObjectName('timerFullscreenDialog')
            dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            dialog.setAttribute(Qt.WA_TranslucentBackground, True)
            dialog.setAttribute(Qt.WA_DeleteOnClose, False)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            frame = QFrame(dialog)
            frame.setObjectName('timerFullscreenFrame')
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(8, 8, 8, 8)
            frame_layout.setSpacing(0)
            if hasattr(self, 'timer_fullscreen_view'):
                self.timer_fullscreen_view.set_compact_mode(True)
            frame_layout.addWidget(self.timer_fullscreen_view)
            layout.addWidget(frame)
            dialog.register_drag_handle(frame)
            frame_radius = 28
            dialog.setStyleSheet(
                "QDialog#timerFullscreenDialog { background: transparent; }"
                f"QFrame#timerFullscreenFrame {{ background:{CLR_PANEL}; border-radius:{frame_radius}px; border:3px solid {CLR_TITLE}; }}"
            )
            dialog.setFixedSize(256, 256)
            dialog.rejected.connect(self._close_timer_fullscreen)
            self.timer_fullscreen_dialog = dialog
        return True

    def _show_timer_fullscreen(self, timer: TimerState) -> None:
        if not self._ensure_timer_fullscreen_dialog():
            return
        self._timer_fullscreen_timer = timer
        self._update_timer_fullscreen_state(timer)
        if self.timer_fullscreen_dialog is not None:
            self.timer_fullscreen_dialog.show()
            self.timer_fullscreen_dialog.raise_()
            self.timer_fullscreen_dialog.activateWindow()
            self.timer_fullscreen_dialog.position_top_right()

    def _update_timer_fullscreen_state(self, timer: TimerState) -> None:
        if not hasattr(self, 'timer_fullscreen_view'):
            return
        progress = timer.progress if timer.duration else 0.0
        finish_text = self._format_timer_finish(timer)
        self.timer_fullscreen_view.set_state(timer, progress, finish_text, timer.running)

    def _close_timer_fullscreen(self) -> None:
        self._timer_fullscreen_timer = None
        dialog = getattr(self, 'timer_fullscreen_dialog', None)
        if dialog is not None and dialog.isVisible():
            dialog.hide()

    def _format_alarm_countdown(self, alarm: AlarmState, now: datetime) -> str:
        next_trigger = alarm.next_trigger_after(now)
        if next_trigger is None:
            return 'Desactivada'
        delta = next_trigger - now
        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            return 'ahora'
        hours, rem = divmod(total_seconds, 3600)
        minutes, _ = divmod(rem, 60)
        parts = []
        if hours:
            parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")
        if not parts:
            parts.append('menos de un minuto')
        return 'en ' + ', '.join(parts)

    def _refresh_alarm_cards(self):
        if not hasattr(self, 'alarm_cards_layout'):
            return
        layout = self.alarm_cards_layout
        now = datetime.now()
        keep: set[int] = set()
        for alarm in self.alarms:
            key = id(alarm)
            keep.add(key)
            card = self._alarm_card_widgets.get(key)
            if card is None:
                card = AlarmCard()
                self._alarm_card_widgets[key] = card
                card.toggleRequested.connect(lambda c, state, a=alarm: self._toggle_alarm_enabled(a, state))
                card.editRequested.connect(lambda c, a=alarm: self._edit_alarm(a))
                card.deleteRequested.connect(lambda c, a=alarm: self._delete_alarm(a))
                card.clicked.connect(lambda c, a=alarm: setattr(self, '_last_selected_alarm', a))
                insert_pos = max(0, layout.count() - 1)
                layout.insertWidget(insert_pos, card)
            countdown = self._format_alarm_countdown(alarm, now)
            repeat_mask = [(i in alarm.repeat_days) for i in range(7)]
            card.set_state(alarm, alarm.trigger.strftime('%H:%M'), countdown, repeat_mask)
            card.set_edit_mode(self._alarm_edit_mode)
        for key, card in list(self._alarm_card_widgets.items()):
            if key not in keep:
                card.setParent(None)
                card.deleteLater()
                del self._alarm_card_widgets[key]
        has_alarms = bool(self.alarms)
        if hasattr(self, 'alarm_empty_label'):
            self.alarm_empty_label.setVisible(not has_alarms)

    def _setup_alarm_timer_controls(self):
        if hasattr(self, 'add_timer_btn'):
            self.add_timer_btn.clicked.connect(self._open_new_timer_dialog)
        if hasattr(self, 'edit_timer_mode_btn'):
            self.edit_timer_mode_btn.setCheckable(True)
            self.edit_timer_mode_btn.toggled.connect(self._set_timer_edit_mode)
            self._style_mode_button(self.edit_timer_mode_btn, False)
        if hasattr(self, 'add_alarm_btn'):
            self.add_alarm_btn.clicked.connect(self._open_new_alarm_dialog)
        if hasattr(self, 'edit_alarm_mode_btn'):
            self.edit_alarm_mode_btn.setCheckable(True)
            self.edit_alarm_mode_btn.toggled.connect(self._set_alarm_edit_mode)
            self._style_mode_button(self.edit_alarm_mode_btn, False)
        if hasattr(self, 'add_reminder_btn'):
            self.add_reminder_btn.clicked.connect(self._open_new_reminder_dialog)
        if hasattr(self, 'reminder_table'):
            self.reminder_table.cellDoubleClicked.connect(self._on_reminder_cell_double_clicked)
        if hasattr(self, 'timer_fullscreen_view'):
            view: TimerFullscreenView = self.timer_fullscreen_view
            view.playRequested.connect(self._play_fullscreen_timer)
            view.pauseRequested.connect(self._pause_fullscreen_timer)
            view.resetRequested.connect(self._reset_fullscreen_timer)
            view.closeRequested.connect(self._close_timer_fullscreen)

    def _populate_notif_table(self):
        data = self.notifications
        tbl = self.notif_table
        tbl.setRowCount(len(data))
        for i, (ts, txt) in enumerate(data):
            tbl.setItem(i, 0, QTableWidgetItem(ts))
            icon_name = self._get_notification_icon_name(txt)
            item = QTableWidgetItem(self._translate_notif(txt))
            icon_file = resolve_icon_path(icon_name)
            if icon_file:
                item.setIcon(QIcon(icon_file))
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
                # Resolve the path to the icon within the known icon directories.
                icon_file = resolve_icon_path(icon_name)
                if icon_file:
                    pix = QPixmap(icon_file)
                    if not pix.isNull():
                        pix = pix.scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        icon_lbl.setPixmap(pix)
                    else:
                        icon_lbl.clear()
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
        if p.isActive():
            p.end()

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
        menu_items = [
            ('Inicio', 'Inicio.svg'),
            ('Dispositivos', 'Dispositivos.svg'),
            ('Más', 'Más.svg'),
            ('Salud', 'Salud.svg'),
            ('Configuración', 'Configuración.svg'),
        ]
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

        account_label, account_icon = 'Cuenta', 'Cuenta.svg'
        account_btn = QPushButton()
        account_btn.base_text = account_label
        account_btn.setText(f'   {account_label}')
        account_btn.setIcon(icon(account_icon))
        account_btn.setIconSize(QSize(24, 24))
        account_btn.setCheckable(True)
        account_btn.setAutoExclusive(True)
        account_btn.setCursor(Qt.PointingHandCursor)
        account_btn.setMinimumHeight(38)
        account_btn.setStyleSheet(
            f"\n                QPushButton {{ color:{CLR_TEXT_IDLE}; background:transparent;\n   border:none; padding:8px 16px; border-radius:5px;\n                  font:700 18px '{FONT_FAM}'; text-align:left; }}\n         QPushButton:checked {{ background:{CLR_ITEM_ACT}; color:{CLR_TITLE}; }}\n            "
        )
        account_index = len(self.buttons)
        account_btn.clicked.connect(lambda _, ix=account_index: self._switch_page(self.stack, ix))
        menu_l.addWidget(account_btn)
        self.buttons.append(account_btn)
        scroll = QScrollArea()
        scroll.setWidget(menu_w)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        vp.addWidget(scroll, 1)
        ver_lbl = QLabel('Versión 1.0')
        ver_lbl.setStyleSheet(f"color:{CLR_TITLE}; font:700 18px '{FONT_FAM}';")
        vp.addWidget(ver_lbl, alignment=Qt.AlignHCenter | Qt.AlignBottom)
        self.stack = QStackedWidget()
        self.stack.addWidget(build_home_page(self, MetricGauge, load_icon_pixmap, tint_pixmap))
        self.stack.addWidget(build_devices_page(self))
        self.stack.addWidget(build_more_page(self))
        self._setup_alarm_timer_controls()
        self.stack.addWidget(build_health_page(self))
        self.stack.addWidget(build_config_page(self))
        self.stack.addWidget(build_account_page(self))
        self.buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)
        animation_builders = [
            create_home_animations,
            create_devices_animations,
            create_more_animations,
            create_health_animations,
            create_config_animations,
            create_account_animations,
        ]
        self._page_animations: dict[int, list[dict[str, object]]] = {}
        for idx, builder in enumerate(animation_builders):
            try:
                specs = builder(self)
            except Exception:
                specs = []
            self._page_animations[idx] = specs
        self._running_page_anims: list[dict[str, Any]] = []
        self.stack.currentChanged.connect(self._play_page_animations)
        self._play_page_animations(self.stack.currentIndex())
        right = QWidget()
        vr = QVBoxLayout(right)
        vr.setContentsMargins(30, 0, 30, 20)
        vr.setSpacing(10)
        vr.addWidget(self.stack)
        vr.addStretch(1)
        root.addWidget(panel, 1)
        root.addWidget(right, 4)

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
        icon_override = 'Dispositivos.svg'
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
                icon_override = 'Dispositivos.svg'
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
        self.recordatorios = user_rems
        try:
            self._after_reminders_changed()
        except Exception:
            pass
        try:
            self.alarms = database.get_alarms(user)
        except Exception:
            self.alarms = []
        self._set_alarm_edit_mode(self._alarm_edit_mode)
        self._refresh_alarm_cards()
        try:
            self.timers = database.get_timers(user)
        except Exception:
            self.timers = []
        for timer in self.timers:
            timer.runtime_anchor = None
        self._set_timer_edit_mode(self._timer_edit_mode)
        self._refresh_timer_cards()
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
        alarm_events = [(alarm.trigger, alarm.label) for alarm in self.alarms]
        reminder_events = [(rem.when, rem.message) for rem in self.recordatorios]
        combined = reminder_events + alarm_events
        self.selected_day_events = [(dt, txt) for dt, txt in combined if dt.date() == date]

    def _refresh_calendar_events(self):
        if self.calendar_widget:
            alarm_dates = [alarm.trigger.date() for alarm in self.alarms]
            rec_dates = [rem.when.date() for rem in self.recordatorios]
            self.calendar_widget.update_events(rec_dates + alarm_dates)

    def _refresh_account_info(self) -> None:
        if not hasattr(self, 'account_page'):
            return
        total_devices = len(getattr(self, 'device_rows', []))
        active_devices = sum((1 for r in getattr(self, 'device_rows', []) if getattr(r.btn, 'isChecked', lambda: False)()))
        if hasattr(self, 'account_username_label'):
            username_text = getattr(self, 'username', None) or 'Usuario TechHome'
            try:
                self.account_username_label.setText(username_text)
            except Exception:
                pass
        if hasattr(self, 'account_email_label'):
            email_text = getattr(self, 'user_email', None) or 'usuario@techhome.app'
            try:
                self.account_email_label.setText(email_text)
            except Exception:
                pass
        if hasattr(self, 'account_status_label'):
            status_text = 'Activa' if getattr(self, 'username', None) else 'Sin sesión'
            try:
                self.account_status_label.setText(status_text)
            except Exception:
                pass
        if hasattr(self, 'account_plan_label'):
            plan_text = getattr(self, 'account_plan', None) or 'TechHome Familiar'
            try:
                self.account_plan_label.setText(plan_text)
            except Exception:
                pass
        self.acc_dev_label.setText(f'{total_devices} ({active_devices} activos)')
        if hasattr(self, 'account_devices_label'):
            try:
                self.account_devices_label.setText(f'Dispositivos activos: {active_devices} de {total_devices}')
            except Exception:
                pass
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
                theme_icon_name = 'Luna.svg' if getattr(self, 'theme', 'dark') == 'dark' else 'Sol.svg'
                theme_icon_path = os.path.join(fa_solid_dir, theme_icon_name)
                if os.path.isfile(theme_icon_path):
                    ico = QIcon(theme_icon_path)
                    pm = ico.pixmap(QSize(18, 18))
                    pm_tinted = tint_pixmap(pm, QColor(CLR_TITLE))
                    self.acc_theme_loc_label.setPixmap(pm_tinted)
        if hasattr(self, 'acc_lang_label'):
            self.acc_lang_label.setText(lang_txt)
            if hasattr(self, 'acc_lang_loc_label'):
                lang_pm = load_icon_pixmap('Idioma.svg', QSize(18, 18))
                if not lang_pm.isNull():
                    self.acc_lang_loc_label.setPixmap(tint_pixmap(lang_pm, QColor(CLR_TITLE)))
        if hasattr(self, 'acc_time_label'):
            self.acc_time_label.setText(time_txt)
            if hasattr(self, 'acc_time_loc_label'):
                time_pm = load_icon_pixmap('Hora.svg', QSize(18, 18))
                if not time_pm.isNull():
                    self.acc_time_loc_label.setPixmap(tint_pixmap(time_pm, QColor(CLR_TITLE)))
        if hasattr(self, 'acc_notif_label'):
            self.acc_notif_label.setText(notif_txt)
            if hasattr(self, 'acc_notif_loc_label'):
                notif_icon_name = 'Notificaciones.svg' if getattr(self, 'notifications_enabled', True) else 'Notificaciones Inactivas.svg'
                notif_pm = load_icon_pixmap(notif_icon_name, QSize(18, 18))
                if not notif_pm.isNull():
                    self.acc_notif_loc_label.setPixmap(tint_pixmap(notif_pm, QColor(CLR_TITLE)))

class MainWindow(QMainWindow):

    def __init__(self, username: str, login_time: datetime):
        super().__init__()
        self.username = username
        self.login_time = login_time
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(1100, 700)
        self._drag = None
        self.setWindowOpacity(0.0)
        self._show_anim: QPropertyAnimation | None = None
        self._show_anim_played = False
        self.setCentralWidget(AnimatedBackground(self, username=username, login_time=login_time))

    def showEvent(self, event):
        super().showEvent(event)
        if self._show_anim_played:
            return
        self._show_anim_played = True
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(420)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            self._show_anim = None

        anim.finished.connect(_cleanup)
        self._show_anim = anim
        anim.start()

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
    splash_specs = create_splash_animations(splash)
    for spec in splash_specs:
        if not isinstance(spec, dict):
            continue
        prepare = spec.get('prepare')
        if callable(prepare):
            try:
                prepare()
            except Exception:
                pass
        anim = spec.get('animation')
        if anim is None:
            continue
        delay = 0
        try:
            delay = int(spec.get('delay', 0) or 0)
        except Exception:
            delay = 0

        def start_anim(animation=anim):
            try:
                animation.stop()
            except Exception:
                pass
            if hasattr(animation, 'setDirection'):
                try:
                    animation.setDirection(QAbstractAnimation.Forward)
                except Exception:
                    pass
            animation.start()

        if delay > 0:
            QTimer.singleShot(delay, start_anim)
        else:
            start_anim()
    splash.exec_()
    login = LoginDialog(
        init_callback=database.init_db,
        authenticate_callback=database.authenticate,
        create_user_callback=database.create_user,
        log_action_callback=database.log_action,
    )
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
