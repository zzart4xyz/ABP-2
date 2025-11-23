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

METHODS_A = {}

def _on_timeout(self):
    self._angle = (self._angle + 1) % 360
    self.update()

METHODS_A["_on_timeout"] = _on_timeout

def current_time(self, sec=False):
    fmt = '%H:%M:%S' if sec else '%H:%M'
    if not self.time_24h:
        fmt = '%I:%M:%S %p' if sec else '%I:%M %p'
    return datetime.now().strftime(fmt)

METHODS_A["current_time"] = current_time

def format_datetime(self, dt, sec=False):
    fmt = '%d/%m/%Y ' + ('%H:%M:%S' if sec else '%H:%M')
    if not self.time_24h:
        fmt = '%d/%m/%Y ' + ('%I:%M:%S %p' if sec else '%I:%M %p')
    return dt.strftime(fmt)

METHODS_A["format_datetime"] = format_datetime

def _set_time_format(self, is24):
    if not getattr(self, 'loading_settings', False) and getattr(self, 'username', None):
        try:
            database.save_setting(self.username, 'time_24h', '1' if is24 else '0')
        except Exception:
            pass
    self.time_24h = is24
    if hasattr(self, 'home_time_label'):
        self.home_time_label.setText(self.current_time())

METHODS_A["_set_time_format"] = _set_time_format

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

METHODS_A["_set_theme"] = _set_theme

def resizeEvent(self, event) -> None:
    # Call QWidget's resizeEvent directly because this function is injected
    # into AnimatedBackground after definition; using super() here would
    # require a __class__ cell that is not available in this context.
    QWidget.resizeEvent(self, event)
    if hasattr(self, 'popup_label'):
        try:
            x = self.width() - self.popup_label.width() - 40
            y = 20
            if x < 0:
                x = 0
            self.popup_label.move(x, y)
        except Exception:
            pass

METHODS_A["resizeEvent"] = resizeEvent

def _toggle_notifications(self, enabled):
    if not getattr(self, 'loading_settings', False) and getattr(self, 'username', None):
        try:
            database.save_setting(self.username, 'notifications_enabled', '1' if enabled else '0')
        except Exception:
            pass
    self.notifications_enabled = enabled
    if not enabled:
        self.popup_label.hide()

METHODS_A["_toggle_notifications"] = _toggle_notifications

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

METHODS_A["_on_device_category_changed"] = _on_device_category_changed

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

METHODS_A["_on_device_sort_changed"] = _on_device_sort_changed

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

METHODS_A["_force_full_opacity"] = _force_full_opacity

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

METHODS_A["_resolve_animation_widget"] = _resolve_animation_widget

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

METHODS_A["_build_animation_entry"] = _build_animation_entry

def _switch_page(self, stack, index):
    if index == stack.currentIndex():
        return
    stack.setCurrentIndex(index)
    current_widget = stack.currentWidget()
    if isinstance(current_widget, QWidget):
        self._force_full_opacity(current_widget)
    self._play_page_animations(index)

METHODS_A["_switch_page"] = _switch_page

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

METHODS_A["_play_page_animations"] = _play_page_animations

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

METHODS_A["_change_language"] = _change_language

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

METHODS_A["_translate_name"] = _translate_name

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

METHODS_A["_apply_language"] = _apply_language

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

METHODS_A["_translate_notif"] = _translate_notif

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

METHODS_A["_get_notification_icon_name"] = _get_notification_icon_name

def _style_popup_label(self):
    self.popup_label.setStyleSheet(f"QLabel {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {CLR_HEADER_BG}, stop:1 {CLR_HOVER}); border:2px solid {CLR_TITLE}; border-radius:5px; padding:8px 12px; color:{CLR_TEXT_IDLE}; font:600 14px '{FONT_FAM}'; }}")
    make_shadow(self.popup_label, 15, 4, 180)

METHODS_A["_style_popup_label"] = _style_popup_label

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

METHODS_A["_add_notification"] = _add_notification

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

METHODS_A["_check_reminders"] = _check_reminders

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

METHODS_A["_open_new_reminder_dialog"] = _open_new_reminder_dialog

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

METHODS_A["_edit_reminder"] = _edit_reminder

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

METHODS_A["_delete_reminder"] = _delete_reminder

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

        table.setRowHeight(row, 54)

    table.clearSelection()
    self._update_reminder_action_buttons()

METHODS_A["_refresh_reminder_table"] = _refresh_reminder_table

def _reminder_for_row(self, row: int) -> ReminderState | None:
    table = getattr(self, 'reminder_table', None)
    if table is None or row < 0 or row >= table.rowCount():
        return None
    item = table.item(row, 0)
    reminder = item.data(Qt.UserRole) if item else None
    return reminder if isinstance(reminder, ReminderState) else None

METHODS_A["_reminder_for_row"] = _reminder_for_row

def _selected_reminder(self) -> ReminderState | None:
    table = getattr(self, 'reminder_table', None)
    if table is None:
        return None
    return self._reminder_for_row(table.currentRow())

METHODS_A["_selected_reminder"] = _selected_reminder

def _edit_selected_reminder(self) -> None:
    reminder = self._selected_reminder()
    if reminder is not None:
        self._edit_reminder(reminder)

METHODS_A["_edit_selected_reminder"] = _edit_selected_reminder

def _delete_selected_reminder(self) -> None:
    reminder = self._selected_reminder()
    if reminder is not None:
        self._delete_reminder(reminder)

METHODS_A["_delete_selected_reminder"] = _delete_selected_reminder

def _on_reminder_cell_double_clicked(self, row: int, column: int) -> None:
    reminder = self._reminder_for_row(row)
    if reminder is not None:
        self._edit_reminder(reminder)

METHODS_A["_on_reminder_cell_double_clicked"] = _on_reminder_cell_double_clicked

def _on_reminder_selection_changed(self) -> None:
    self._update_reminder_action_buttons()

METHODS_A["_on_reminder_selection_changed"] = _on_reminder_selection_changed

def _update_reminder_action_buttons(self) -> None:
    reminder = self._selected_reminder()
    enabled = reminder is not None
    if hasattr(self, 'edit_reminder_btn'):
        self.edit_reminder_btn.setEnabled(enabled)
    if hasattr(self, 'delete_reminder_btn'):
        self.delete_reminder_btn.setEnabled(enabled)

METHODS_A["_update_reminder_action_buttons"] = _update_reminder_action_buttons

def _update_reminder_summary(self) -> None:
    table = getattr(self, 'reminder_table', None)
    if table is not None:
        table.setVisible(True)
    if hasattr(self, 'record_count_badge'):
        self.record_count_badge.setText(f"{len(self.recordatorios)} activos")

METHODS_A["_update_reminder_summary"] = _update_reminder_summary

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

METHODS_A["_after_reminders_changed"] = _after_reminders_changed

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

METHODS_A["_show_popup_message"] = _show_popup_message

def _notify_timer_finished(self, timer: TimerState) -> None:
    mapping = TRANSLATIONS_EN if self.lang == 'en' else {}
    label = mapping.get(timer.label, timer.label)
    if self.notifications_enabled:
        self._show_popup_message('⏰ ' + label)
    self._add_notification(f'Timer {label} completado')

METHODS_A["_notify_timer_finished"] = _notify_timer_finished

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

METHODS_A["_update_timers"] = _update_timers

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

METHODS_A["_open_new_alarm_dialog"] = _open_new_alarm_dialog

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

METHODS_A["_edit_alarm"] = _edit_alarm

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

METHODS_A["_delete_alarm"] = _delete_alarm

def _toggle_alarm_enabled(self, alarm: AlarmState, enabled: bool):
    alarm.enabled = enabled
    if hasattr(self, 'username') and self.username:
        try:
            database.save_alarm(self.username, alarm)
        except Exception:
            pass
    self._refresh_alarm_cards()
    self._refresh_calendar_events()

METHODS_A["_toggle_alarm_enabled"] = _toggle_alarm_enabled

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

METHODS_A["_open_new_timer_dialog"] = _open_new_timer_dialog

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

METHODS_A["_edit_timer"] = _edit_timer

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

METHODS_A["_delete_timer"] = _delete_timer


class AnimatedBackgroundMixinA:
    """Mixin que agrupa los métodos auxiliares de AnimatedBackground."""


for _name, _func in METHODS_A.items():
    setattr(AnimatedBackgroundMixinA, _name, _func)


__all__ = ["AnimatedBackgroundMixinA"]
