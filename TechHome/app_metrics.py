"""Support routines for AnimatedBackground (app_metrics)."""
from __future__ import annotations

from app_common import *

def _make_health_page(self):
    w = QWidget()
    l = QVBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(10)
    gauge = BPMGauge()
    metrics = MetricsPanel()
    gauge.calculationFinished.connect(metrics.update_values)
    gauge.calculationFinished.connect(self._record_health_history)
    l.addStretch(1)
    l.addWidget(gauge, alignment=Qt.AlignHCenter)
    l.addWidget(metrics, alignment=Qt.AlignHCenter)
    l.addStretch(1)
    return w

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
