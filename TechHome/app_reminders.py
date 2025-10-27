"""Support routines for AnimatedBackground (app_reminders)."""
from __future__ import annotations

from TechHome.app_common import *

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

def _on_calendar_date_selected(self):
    date = self.calendar_widget.selectedDate().toPyDate()
    self.selected_day_events = [(dt, txt) for dt, txt in self.recordatorios + self.alarms if dt.date() == date]

def _refresh_calendar_events(self):
    if self.calendar_widget:
        dates = [dt.date() for dt, _ in self.recordatorios + self.alarms]
        self.calendar_widget.update_events(dates)
