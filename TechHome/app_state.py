"""Persistence and state helpers for AnimatedBackground."""
from __future__ import annotations

from TechHome.app_common import *

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
