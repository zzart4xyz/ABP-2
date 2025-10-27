"""Support routines for AnimatedBackground (app_lists)."""
from __future__ import annotations

from app_common import *

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
