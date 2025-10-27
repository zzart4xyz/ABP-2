"""Application window definitions for TechHome."""
from __future__ import annotations

from TechHome.app_common import *
from TechHome import (
    app_core,
    app_devices,
    app_layout,
    app_lists,
    app_metrics,
    app_notifications,
    app_reminders,
    app_state,
)

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
    def _on_timeout(self, *args, **kwargs):
        return app_core._on_timeout(self, *args, **kwargs)

    def current_time(self, *args, **kwargs):
        return app_core.current_time(self, *args, **kwargs)

    def format_datetime(self, *args, **kwargs):
        return app_core.format_datetime(self, *args, **kwargs)

    def _set_time_format(self, *args, **kwargs):
        return app_core._set_time_format(self, *args, **kwargs)

    def _set_theme(self, *args, **kwargs):
        return app_core._set_theme(self, *args, **kwargs)

    def resizeEvent(self, *args, **kwargs):
        return app_core.resizeEvent(self, *args, **kwargs)

    def _switch_page(self, *args, **kwargs):
        return app_core._switch_page(self, *args, **kwargs)

    def _change_language(self, *args, **kwargs):
        return app_core._change_language(self, *args, **kwargs)

    def _translate_name(self, *args, **kwargs):
        return app_core._translate_name(self, *args, **kwargs)

    def _apply_language(self, *args, **kwargs):
        return app_core._apply_language(self, *args, **kwargs)

    def _style_popup_label(self, *args, **kwargs):
        return app_layout._style_popup_label(self, *args, **kwargs)

    def _build_ui(self, *args, **kwargs):
        return app_layout._build_ui(self, *args, **kwargs)

    def _make_home_page(self, *args, **kwargs):
        return app_layout._make_home_page(self, *args, **kwargs)

    def _make_more_page(self, *args, **kwargs):
        return app_layout._make_more_page(self, *args, **kwargs)

    def _make_config_page(self, *args, **kwargs):
        return app_layout._make_config_page(self, *args, **kwargs)

    def paintEvent(self, *args, **kwargs):
        return app_layout.paintEvent(self, *args, **kwargs)

    def _open_more_section(self, *args, **kwargs):
        return app_layout._open_more_section(self, *args, **kwargs)

    def _back_from_more(self, *args, **kwargs):
        return app_layout._back_from_more(self, *args, **kwargs)

    def _load_persistent_state(self, *args, **kwargs):
        return app_state._load_persistent_state(self, *args, **kwargs)

    def _load_user_settings(self, *args, **kwargs):
        return app_state._load_user_settings(self, *args, **kwargs)

    def _refresh_account_info(self, *args, **kwargs):
        return app_state._refresh_account_info(self, *args, **kwargs)

    def _toggle_notifications(self, *args, **kwargs):
        return app_notifications._toggle_notifications(self, *args, **kwargs)

    def _translate_notif(self, *args, **kwargs):
        return app_notifications._translate_notif(self, *args, **kwargs)

    def _get_notification_icon_name(self, *args, **kwargs):
        return app_notifications._get_notification_icon_name(self, *args, **kwargs)

    def _add_notification(self, *args, **kwargs):
        return app_notifications._add_notification(self, *args, **kwargs)

    def _refresh_home_notifications(self, *args, **kwargs):
        return app_notifications._refresh_home_notifications(self, *args, **kwargs)

    def _populate_notif_table(self, *args, **kwargs):
        return app_notifications._populate_notif_table(self, *args, **kwargs)

    def _open_notifications_details(self, *args, **kwargs):
        return app_notifications._open_notifications_details(self, *args, **kwargs)

    def _on_device_category_changed(self, *args, **kwargs):
        return app_devices._on_device_category_changed(self, *args, **kwargs)

    def _on_device_sort_changed(self, *args, **kwargs):
        return app_devices._on_device_sort_changed(self, *args, **kwargs)

    def _device_toggled(self, *args, **kwargs):
        return app_devices._device_toggled(self, *args, **kwargs)

    def _add_group(self, *args, **kwargs):
        return app_devices._add_group(self, *args, **kwargs)

    def _add_device(self, *args, **kwargs):
        return app_devices._add_device(self, *args, **kwargs)

    def _rename_group(self, *args, **kwargs):
        return app_devices._rename_group(self, *args, **kwargs)

    def _rename_device(self, *args, **kwargs):
        return app_devices._rename_device(self, *args, **kwargs)

    def _make_devices_page(self, *args, **kwargs):
        return app_devices._make_devices_page(self, *args, **kwargs)

    def _on_list_selected(self, *args, **kwargs):
        return app_lists._on_list_selected(self, *args, **kwargs)

    def _on_add_list_item(self, *args, **kwargs):
        return app_lists._on_add_list_item(self, *args, **kwargs)

    def _on_add_list(self, *args, **kwargs):
        return app_lists._on_add_list(self, *args, **kwargs)

    def _add_note(self, *args, **kwargs):
        return app_lists._add_note(self, *args, **kwargs)

    def _restore_lists(self, *args, **kwargs):
        return app_lists._restore_lists(self, *args, **kwargs)

    def _restore_notes(self, *args, **kwargs):
        return app_lists._restore_notes(self, *args, **kwargs)

    def _check_reminders(self, *args, **kwargs):
        return app_reminders._check_reminders(self, *args, **kwargs)

    def _add_recordatorio(self, *args, **kwargs):
        return app_reminders._add_recordatorio(self, *args, **kwargs)

    def _populate_record_table(self, *args, **kwargs):
        return app_reminders._populate_record_table(self, *args, **kwargs)

    def _delete_selected_recordatorio(self, *args, **kwargs):
        return app_reminders._delete_selected_recordatorio(self, *args, **kwargs)

    def _update_timers(self, *args, **kwargs):
        return app_reminders._update_timers(self, *args, **kwargs)

    def _add_alarm(self, *args, **kwargs):
        return app_reminders._add_alarm(self, *args, **kwargs)

    def _populate_alarm_table(self, *args, **kwargs):
        return app_reminders._populate_alarm_table(self, *args, **kwargs)

    def _delete_selected_alarm(self, *args, **kwargs):
        return app_reminders._delete_selected_alarm(self, *args, **kwargs)

    def _add_timer(self, *args, **kwargs):
        return app_reminders._add_timer(self, *args, **kwargs)

    def _populate_timer_table(self, *args, **kwargs):
        return app_reminders._populate_timer_table(self, *args, **kwargs)

    def _delete_selected_timer(self, *args, **kwargs):
        return app_reminders._delete_selected_timer(self, *args, **kwargs)

    def _on_calendar_date_selected(self, *args, **kwargs):
        return app_reminders._on_calendar_date_selected(self, *args, **kwargs)

    def _refresh_calendar_events(self, *args, **kwargs):
        return app_reminders._refresh_calendar_events(self, *args, **kwargs)

    def _make_health_page(self, *args, **kwargs):
        return app_metrics._make_health_page(self, *args, **kwargs)

    def _update_metrics(self, *args, **kwargs):
        return app_metrics._update_metrics(self, *args, **kwargs)

    def _record_health_history(self, *args, **kwargs):
        return app_metrics._record_health_history(self, *args, **kwargs)

    def _open_metrics_details(self, *args, **kwargs):
        return app_metrics._open_metrics_details(self, *args, **kwargs)

    def _populate_health_table(self, *args, **kwargs):
        return app_metrics._populate_health_table(self, *args, **kwargs)


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
