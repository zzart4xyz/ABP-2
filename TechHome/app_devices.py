"""Support routines for AnimatedBackground (app_devices)."""
from __future__ import annotations

from app_common import *

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

def _make_devices_page(self):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 20, 0, 0)
    v.setSpacing(20)
    hh = QHBoxLayout()
    lbl = QLabel('Dispositivos')
    lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:700 24px '{FONT_FAM}'; border:none;")
    plus = QPushButton()
    plus.setIcon(icon('Mas.svg'))
    plus.setIconSize(QSize(24, 24))
    plus.setFixedSize(32, 32)
    plus.setFlat(True)
    plus.setStyleSheet('border:none; background:transparent;')
    plus.clicked.connect(self._add_device)
    hh.addWidget(lbl)
    hh.addStretch(1)
    hh.addWidget(plus)
    v.addLayout(hh)
    g_lbl = QLabel('Grupos')
    g_lbl.setStyleSheet(f"color:{CLR_TEXT_IDLE}; font:600 18px '{FONT_FAM}'; border:none;")
    v.addWidget(g_lbl)
    grp_w = QWidget()
    grp_w.setStyleSheet('background:transparent;')
    gl = QHBoxLayout(grp_w)
    gl.setContentsMargins(0, 0, 0, 0)
    gl.setSpacing(16)
    self.grp_layout = gl
    self.group_cards = []
    groups = [('Todo', 'Dispositivos.svg'), ('Dormitorio', 'bed-front.svg'), ('Baño', 'toilet.svg'), ('Sala', 'tv.svg'), ('Comedor', 'utensils.svg'), ('Cocina', 'hat-chef.svg')]
    for title, icon_name in groups:
        card = GroupCard(title, icon_name, rename_callback=self._rename_group, select_callback=None)
        gl.addWidget(card)
        self.group_cards.append(card)
    self.add_group_card = GroupCard('Grupo Nuevo', 'Mas.svg', add_callback=self._add_group)
    gl.addWidget(self.add_group_card)
    grp_scroll = QScrollArea()
    grp_scroll.setWidget(grp_w)
    grp_scroll.setWidgetResizable(True)
    grp_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    grp_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    grp_scroll.setFrameShape(QFrame.NoFrame)
    grp_scroll.setHorizontalScrollBar(CustomScrollBar(Qt.Horizontal))
    grp_scroll.setStyleSheet('background:transparent;')
    grp_scroll.viewport().setStyleSheet('background:transparent;')
    v.addWidget(grp_scroll)
    self.group_indicator = QLabel('Grupo Actual: Todo')
    self.group_indicator.setStyleSheet(f"background:{CLR_HOVER}; color:{CLR_TITLE}; font:700 16px '{FONT_FAM}'; padding:4px 8px; border-radius:5px;")
    v.addWidget(self.group_indicator)
    fh = QHBoxLayout()
    search = QLineEdit()
    search.setFixedHeight(40)
    search.setPlaceholderText('Buscar')
    search.setCursor(Qt.PointingHandCursor)
    search.setStyleSheet(f"\n            QLineEdit {{ background:{CLR_SURFACE}; border:2px solid #1A2B3C;\n                         border-radius:5px; padding:0 40px 0 12px;\n                         color:{CLR_TEXT_IDLE}; font:700 16px '{FONT_FAM}'; }}\n            QLineEdit:focus {{ border-color:{CLR_TITLE}; }}\n        ")
    search.addAction(icon('Search.svg'), QLineEdit.LeadingPosition)
    cb1 = QComboBox()
    cb1.addItems(['Tech', 'Interruptores', 'Otro'])
    cb2 = QComboBox()
    cb2.addItems(['De La A A La Z', 'De La Z A La A'])
    self.device_category_cb = cb1
    self.device_sort_cb = cb2
    for cb in (cb1, cb2):
        cb.setFixedHeight(40)
        cb.setStyleSheet(f"\n                QComboBox {{ background:{CLR_SURFACE};color:{CLR_TEXT_IDLE};\n                              font:700 16px '{FONT_FAM}';border:2px solid {CLR_TITLE};\n                              border-radius:5px;padding:0 12px; }}\n                QComboBox::drop-down {{ border:none; }}\n                QComboBox QAbstractItemView {{ background:{CLR_PANEL};\n                              border:2px solid {CLR_TITLE};\n                              selection-background-color:{CLR_ITEM_ACT};\n                              color:{CLR_TEXT_IDLE};outline:none;padding:4px; }}\n                QComboBox QAbstractItemView::item {{ height:30px;padding-left:10px; }}\n                QComboBox QAbstractItemView::item:hover {{ background:{CLR_ITEM_ACT}; }}\n            ")
    cb1.currentIndexChanged.connect(self._on_device_category_changed)
    cb2.currentIndexChanged.connect(self._on_device_sort_changed)
    fh.addWidget(search, 1)
    fh.addWidget(cb1)
    fh.addWidget(cb2)
    v.addLayout(fh)
    dev_w = QWidget()
    dev_w.setStyleSheet('background:transparent;')
    dl = QVBoxLayout(dev_w)
    dl.setContentsMargins(0, 0, 0, 0)
    dl.setSpacing(12)
    self.device_filter_container = dl
    self.devices_buttons = []
    self.device_rows = []
    devices = [('Luz Dormitorio', 'Dormitorio'), ('Lámpara Noche', 'Dormitorio'), ('Ventilador Dormitorio', 'Dormitorio'), ('Aire Acondicionado Dormitorio', 'Dormitorio'), ('Cortinas Dormitorio', 'Dormitorio'), ('Enchufe Cama', 'Dormitorio'), ('Luz Baño', 'Baño'), ('Extractor', 'Baño'), ('Calentador Agua', 'Baño'), ('Espejo Iluminado', 'Baño'), ('Ducha Automática', 'Baño'), ('Enchufe Afeitadora', 'Baño'), ('Luces Sala', 'Sala'), ('Televisor', 'Sala'), ('Consola Juegos', 'Sala'), ('Equipo Sonido', 'Sala'), ('Ventilador Sala', 'Sala'), ('Enchufe Ventana', 'Sala'), ('Luz Comedor', 'Comedor'), ('Calefactor Comedor', 'Comedor'), ('Enchufe Comedor', 'Comedor'), ('Luz Barra', 'Comedor'), ('Persianas Comedor', 'Comedor'), ('Ventilador Techo', 'Comedor'), ('Refrigerador', 'Cocina'), ('Horno', 'Cocina'), ('Microondas', 'Cocina'), ('Lavavajillas', 'Cocina'), ('Licuadora', 'Cocina'), ('Cafetera', 'Cocina')]
    for name, grp in devices:
        # Determine the correct icon based on the original device name.  If the
        # device has been renamed, use the original name from the rename map
        # so the icon remains consistent across renames and restarts.
        try:
            original = name
            if hasattr(self, '_renamed_devices'):
                original = self._renamed_devices.get(name, name)
        except Exception:
            original = name
        icon_override = 'Dispositivos.svg'
        for key, fname in self._device_icon_map.items():
            if key in original:
                icon_override = fname
                break
        row = DeviceRow(name, grp, toggle_callback=self._device_toggled,
                        rename_callback=self._rename_device,
                        icon_override=icon_override)
        dl.addWidget(row)
        self.device_rows.append(row)
        self.devices_buttons.append(row.btn)
    dev_scroll = QScrollArea()
    dev_scroll.setWidget(dev_w)
    dev_scroll.setWidgetResizable(True)
    dev_scroll.setFrameShape(QFrame.NoFrame)
    dev_scroll.setVerticalScrollBar(CustomScrollBar(Qt.Vertical))
    dev_scroll.setStyleSheet('background:transparent;')
    dev_scroll.viewport().setStyleSheet('background:transparent;')
    v.addWidget(dev_scroll, 1)
    self.active_group = 'Todo'

    def filter_dev():
        t = search.text().lower()
        rows = []
        for row in self.device_rows:
            match = t in row.base_name.lower()
            grp_ok = self.active_group == 'Todo' or row.group == self.active_group
            if match and grp_ok:
                rows.append(row)
            dl.removeWidget(row)
        asc = cb2.currentText() == 'De La A A La Z'
        rows.sort(key=lambda r: r.base_name.lower(), reverse=not asc)
        for row in self.device_rows:
            row.setVisible(False)
        for row in rows:
            row.setVisible(True)
            dl.addWidget(row)
    search.textChanged.connect(lambda _: filter_dev())
    self._filter_devices = filter_dev

    def sort_dev(_):
        asc = cb2.currentText() == 'De La A A La Z'
        self.device_rows.sort(key=lambda r: r.base_name.lower(), reverse=not asc)
        filter_dev()
    cb2.currentIndexChanged.connect(sort_dev)
    sort_dev(0)

    def select_group(card):
        self.active_group = card.base_name
        display = card.label.text()
        self.group_indicator.setText(f'Grupo Actual: {display}')
        for ccard in self.group_cards:
            ccard.set_selected(ccard is card)
        filter_dev()
    self._group_select_func = select_group
    for card in self.group_cards:
        card.select_callback = self._group_select_func
    select_group(self.group_cards[0])
    return w
