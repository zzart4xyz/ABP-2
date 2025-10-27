"""Support routines for AnimatedBackground (app_core)."""
from __future__ import annotations

from app_common import *

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











