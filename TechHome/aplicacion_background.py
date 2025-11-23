import sys
import random
import csv
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import importlib.util
from typing import Any, Callable
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
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QStackedWidget,
    QLineEdit,
    QComboBox,
    QScrollBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QTextEdit,
    QDateTimeEdit,
    QSpinBox,
    QCalendarWidget,
    QCheckBox,
    QStyledItemDelegate,
    QStyle,
    QToolButton,
    QTableView,
    QHeaderView,
    QAbstractSpinBox,
    QSizePolicy,
    QProgressBar,
    QGraphicsOpacityEffect,
)
from constants import *
from models import AlarmState, ReminderState, TimerState, WEEKDAY_ORDER
from aplicacion_componentes import (
    AlarmCard,
    BPMGauge,
    CardButton,
    CustomScrollBar,
    CurrentMonthCalendar,
    DeviceRow,
    DraggableNote,
    GraphWidget,
    GroupCard,
    LoginDialog,
    MetricGauge,
    MetricSpec,
    MetricsDetailsDialog,
    NoFocusDelegate,
    NotesManager,
    QuickAccessButton,
    SplashScreen,
    TimerCard,
    TimerFullscreenView,
    TimerPopupDialog,
    clamp,
    create_account_animations,
    create_config_animations,
    create_devices_animations,
    create_health_animations,
    create_home_animations,
    create_more_animations,
    style_table,
    build_account_page,
    build_config_page,
    build_devices_page,
    build_health_page,
    build_home_page,
    build_more_page,
    create_splash_animations,
    BPMGauge,
    MetricsPanel,
    NotificationsDetailsDialog,
    SlideFadeEffect,
)
from aplicacion_background_methods_a import AnimatedBackgroundMixinA
from aplicacion_background_methods_b import AnimatedBackgroundMixinB
import database


class AnimatedBackground(AnimatedBackgroundMixinA, AnimatedBackgroundMixinB, QWidget):

    def __init__(self, parent=None, *, username: str | None = None, login_time: datetime | None = None):
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
        self.popup_label.setStyleSheet(
            f"QLabel {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {CLR_HEADER_BG}, stop:1 {CLR_HOVER}); "
            f"border:2px solid {CLR_TITLE}; border-radius:5px; padding:8px 12px; color:{CLR_TEXT_IDLE}; font:600 14px '{FONT_FAM}'; }}"
        )
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
        self._renamed_devices: dict[str, str] = {}
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
            if getattr(self, 'username', None):
                try:
                    self.notifications = database.get_notifications(self.username)
                except Exception:
                    pass
                try:
                    renamed = database.get_renamed_devices(self.username)
                    if hasattr(self, '_renamed_devices') and isinstance(renamed, dict):
                        self._renamed_devices.update(renamed)
                except Exception:
                    pass
                try:
                    from constants import MAX_NOTIFICATIONS
                    if isinstance(self.notifications, list):
                        self.notifications = self.notifications[-MAX_NOTIFICATIONS:]
                except Exception:
                    if isinstance(self.notifications, list):
                        self.notifications = self.notifications[-100:]
                try:
                    self._refresh_home_notifications()
                except Exception:
                    pass


