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
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QStackedWidget, QLineEdit, QComboBox, QScrollBar, QTableWidget, QTableWidgetItem, QTabWidget, QListWidget, QListWidgetItem, QDialog, QTextEdit, QDateTimeEdit, QSpinBox, QCalendarWidget, QCheckBox, QStyledItemDelegate, QStyle, QToolButton, QTableView, QHeaderView, QAbstractSpinBox, QSizePolicy, QProgressBar, QGraphicsOpacityEffect
from constants import *
from models import AlarmState, ReminderState, TimerState, WEEKDAY_ORDER


from constants import *
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
import database
from models import AlarmState, ReminderState, TimerState, WEEKDAY_ORDER

METHODS_B = {}

def _toggle_timer_loop(self, timer: TimerState, enabled: bool):
    timer.loop = enabled
    if hasattr(self, 'username') and self.username:
        try:
            database.save_timer(self.username, timer)
        except Exception:
            pass
    self._refresh_timer_cards()

METHODS_B["_toggle_timer_loop"] = _toggle_timer_loop

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

METHODS_B["_play_timer"] = _play_timer

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

METHODS_B["_pause_timer"] = _pause_timer

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

METHODS_B["_reset_timer"] = _reset_timer

def _play_fullscreen_timer(self):
    if self._timer_fullscreen_timer is not None:
        self._play_timer(self._timer_fullscreen_timer)

METHODS_B["_play_fullscreen_timer"] = _play_fullscreen_timer

def _pause_fullscreen_timer(self):
    if self._timer_fullscreen_timer is not None:
        self._pause_timer(self._timer_fullscreen_timer)

METHODS_B["_pause_fullscreen_timer"] = _pause_fullscreen_timer

def _reset_fullscreen_timer(self):
    if self._timer_fullscreen_timer is not None:
        self._reset_timer(self._timer_fullscreen_timer)

METHODS_B["_reset_fullscreen_timer"] = _reset_fullscreen_timer

def _style_mode_button(self, button: QToolButton, active: bool) -> None:
    button.setStyleSheet(pill_button_style(active))

METHODS_B["_style_mode_button"] = _style_mode_button

def _set_timer_edit_mode(self, active: bool) -> None:
    self._timer_edit_mode = active
    if hasattr(self, 'edit_timer_mode_btn'):
        self._style_mode_button(self.edit_timer_mode_btn, active)
    for card in self._timer_card_widgets.values():
        card.set_edit_mode(active)

METHODS_B["_set_timer_edit_mode"] = _set_timer_edit_mode

def _set_alarm_edit_mode(self, active: bool) -> None:
    self._alarm_edit_mode = active
    if hasattr(self, 'edit_alarm_mode_btn'):
        self._style_mode_button(self.edit_alarm_mode_btn, active)
    for card in self._alarm_card_widgets.values():
        card.set_edit_mode(active)

METHODS_B["_set_alarm_edit_mode"] = _set_alarm_edit_mode

def _format_timer_finish(self, timer: TimerState) -> str:
    if timer.remaining == 0:
        return 'Completado'
    return ''

METHODS_B["_format_timer_finish"] = _format_timer_finish

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

METHODS_B["_refresh_timer_cards"] = _refresh_timer_cards

def _ensure_timer_fullscreen_dialog(self) -> bool:
    if not hasattr(self, 'timer_fullscreen_view'):
        return False
    if self.timer_fullscreen_dialog is None:
        dialog = TimerPopupDialog(self)
        dialog.setModal(False)
        dialog.setObjectName('timerFullscreenDialog')
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

METHODS_B["_ensure_timer_fullscreen_dialog"] = _ensure_timer_fullscreen_dialog

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

METHODS_B["_show_timer_fullscreen"] = _show_timer_fullscreen

def _update_timer_fullscreen_state(self, timer: TimerState) -> None:
    if not hasattr(self, 'timer_fullscreen_view'):
        return
    progress = timer.progress if timer.duration else 0.0
    finish_text = self._format_timer_finish(timer)
    self.timer_fullscreen_view.set_state(timer, progress, finish_text, timer.running)

METHODS_B["_update_timer_fullscreen_state"] = _update_timer_fullscreen_state

def _close_timer_fullscreen(self) -> None:
    self._timer_fullscreen_timer = None
    dialog = getattr(self, 'timer_fullscreen_dialog', None)
    if dialog is not None and dialog.isVisible():
        dialog.hide()

METHODS_B["_close_timer_fullscreen"] = _close_timer_fullscreen

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

METHODS_B["_format_alarm_countdown"] = _format_alarm_countdown

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

METHODS_B["_refresh_alarm_cards"] = _refresh_alarm_cards

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
    if hasattr(self, 'edit_reminder_btn'):
        self.edit_reminder_btn.clicked.connect(self._edit_selected_reminder)
    if hasattr(self, 'delete_reminder_btn'):
        self.delete_reminder_btn.clicked.connect(self._delete_selected_reminder)
    if hasattr(self, 'reminder_table'):
        self.reminder_table.cellDoubleClicked.connect(self._on_reminder_cell_double_clicked)
        self.reminder_table.itemSelectionChanged.connect(self._on_reminder_selection_changed)
        self._update_reminder_action_buttons()
    if hasattr(self, 'timer_fullscreen_view'):
        view: TimerFullscreenView = self.timer_fullscreen_view
        view.playRequested.connect(self._play_fullscreen_timer)
        view.pauseRequested.connect(self._pause_fullscreen_timer)
        view.resetRequested.connect(self._reset_fullscreen_timer)
        view.closeRequested.connect(self._close_timer_fullscreen)

METHODS_B["_setup_alarm_timer_controls"] = _setup_alarm_timer_controls

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

METHODS_B["_populate_notif_table"] = _populate_notif_table

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

METHODS_B["_populate_health_table"] = _populate_health_table

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

METHODS_B["_refresh_home_notifications"] = _refresh_home_notifications

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

METHODS_B["_update_metrics"] = _update_metrics

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

METHODS_B["_device_toggled"] = _device_toggled

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

METHODS_B["_open_more_section"] = _open_more_section

def _back_from_more(self):
    if getattr(self, 'from_home_more', False):
        self._switch_page(self.stack, 0)
        self.from_home_more = False
    self._switch_page(self.more_stack, 0)

METHODS_B["_back_from_more"] = _back_from_more

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

METHODS_B["_record_health_history"] = _record_health_history

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

METHODS_B["_open_metrics_details"] = _open_metrics_details

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

METHODS_B["_open_notifications_details"] = _open_notifications_details

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

METHODS_B["paintEvent"] = paintEvent

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

METHODS_B["_build_ui"] = _build_ui

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

METHODS_B["_on_list_selected"] = _on_list_selected

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

METHODS_B["_on_add_list_item"] = _on_add_list_item

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

METHODS_B["_on_add_list"] = _on_add_list

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

METHODS_B["_add_note"] = _add_note

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

METHODS_B["_restore_lists"] = _restore_lists

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

METHODS_B["_restore_notes"] = _restore_notes

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

METHODS_B["_add_group"] = _add_group

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

METHODS_B["_add_device"] = _add_device

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

METHODS_B["_load_persistent_state"] = _load_persistent_state

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

METHODS_B["_load_user_settings"] = _load_user_settings

def _rename_group(self, card, name):
    names = {c.base_name for c in self.group_cards if c is not card}
    return bool(name) and name not in names

METHODS_B["_rename_group"] = _rename_group

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

METHODS_B["_rename_device"] = _rename_device

def _on_calendar_date_selected(self):
    date = self.calendar_widget.selectedDate().toPyDate()
    alarm_events = [(alarm.trigger, alarm.label) for alarm in self.alarms]
    reminder_events = [(rem.when, rem.message) for rem in self.recordatorios]
    combined = reminder_events + alarm_events
    self.selected_day_events = [(dt, txt) for dt, txt in combined if dt.date() == date]

METHODS_B["_on_calendar_date_selected"] = _on_calendar_date_selected

def _refresh_calendar_events(self):
    if self.calendar_widget:
        alarm_dates = [alarm.trigger.date() for alarm in self.alarms]
        rec_dates = [rem.when.date() for rem in self.recordatorios]
        self.calendar_widget.update_events(rec_dates + alarm_dates)

METHODS_B["_refresh_calendar_events"] = _refresh_calendar_events

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

METHODS_B["_refresh_account_info"] = _refresh_account_info
