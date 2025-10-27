"""Support routines for AnimatedBackground (app_notifications)."""
from __future__ import annotations

from app_common import *

def _toggle_notifications(self, enabled):
    if not getattr(self, 'loading_settings', False) and getattr(self, 'username', None):
        try:
            database.save_setting(self.username, 'notifications_enabled', '1' if enabled else '0')
        except Exception:
            pass
    self.notifications_enabled = enabled
    if not enabled:
        self.popup_label.hide()

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
