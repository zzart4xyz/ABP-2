import random
import sys
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient, QConicalGradient
from PyQt5.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout

import constants as c

"""
Health-related widgets including the circular BPM gauge and metrics
panel.  These widgets rely on centralised constants for colours and
layout.  The gauge emits a signal with freshly simulated medical
readings once a measurement cycle completes.
"""


class MetricsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(110)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(24)
        self.keys = ["PA", "BPM", "SpO₂", "T", "FR"]
        self.boxes = {}
        for k in self.keys:
            f = QFrame()
            f.setFixedSize(140, 110)
            f.setStyleSheet(
                f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c.CLR_HEADER_BG},stop:1 {c.CLR_HOVER});border:2px solid {c.CLR_TITLE};border-radius:5px;"
            )
            c.make_shadow(f, 30, 6, 200)
            vl = QVBoxLayout(f)
            vl.setContentsMargins(12, 12, 12, 12)
            vl.setSpacing(6)
            t = QLabel(k)
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:600 16px '{c.FONT_FAM}';")
            v = QLabel("--")
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 28px '{c.FONT_FAM}';")
            vl.addWidget(t)
            vl.addWidget(v)
            lay.addWidget(f)
            self.boxes[k] = v
        lay.addStretch(1)

    def update_values(self, pa, bpm, spo2, temp, fr):
        for k, val in zip(self.keys, (pa, bpm, spo2, temp, fr)):
            self.boxes[k].setText(str(val))


class BPMGauge(QWidget):
    calculationFinished = pyqtSignal(object, object, object, object, object)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(c.MIN_GAUGE, c.MIN_GAUGE)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._state = 'idle'
        self._angles = [random.uniform(0, 360) for _ in range(5)]
        self._orig_spd = [0.05, 0.07, 0.09, 0.11, 0.13]
        self._speeds = list(self._orig_spd)
        self._ring_spans = [random.randint(252, 324) for _ in range(5)]
        self._anim = QTimer(self)
        self._anim.timeout.connect(self._update_anim)
        self._anim.start(30)
        self._hover = QTimer(self)
        self._hover.setSingleShot(True)
        self._hover.timeout.connect(self._pause_echo)
        self._calc = QTimer(self)
        self._calc.setSingleShot(True)
        self._calc.timeout.connect(self._finish_calc)

    def _update_anim(self):
        self._angles = [(a + s) % 360 for a, s in zip(self._angles, self._speeds)]
        self.update()

    def enterEvent(self, e):
        if self._state == 'idle':
            self._state = 'hovering'
            self._speeds = [-s * 10 for s in self._orig_spd]
            self._hover.start(500)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self._state in ('idle', 'hovering'):
            self._hover.stop()
            self._speeds = list(self._orig_spd)
            self._state = 'idle'
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._state in ('idle', 'hovering'):
                self._state = 'calculating'
                self._speeds = [random.uniform(2, 4) for _ in range(5)]
                self._calc.start(5000)
            elif self._state == 'done':
                # reset gauge and emit dummy values to clear metrics
                self.calculationFinished.emit("--", "--", "--", "--", "--")
                self._state = 'idle'
                self._speeds = list(self._orig_spd)
        super().mousePressEvent(e)

    def _pause_echo(self):
        if self._state == 'hovering':
            self._speeds = [0] * 5
            self._state = 'idle'

    def _finish_calc(self):
        if self._state == 'calculating':
            self._state = 'done'
            self._speeds = [0] * 5
            sys_, dia = random.randint(115, 125), random.randint(75, 85)
            bpm = random.randint(65, 75)
            spo2 = random.randint(96, 99)
            temp = round(random.uniform(36.5, 37.0), 1)
            fr = random.randint(14, 18)
            self.calculationFinished.emit(f"{sys_}/{dia}", bpm, spo2, temp, fr)

    def _draw_text(self, p, rect, txt, font, dy=0):
        p.setFont(font)
        p.setPen(QColor(0, 0, 0, 120))
        p.drawText(rect.translated(1, 1 + dy), Qt.AlignCenter, txt)
        p.setPen(QColor(c.CLR_TITLE))
        p.drawText(rect.translated(0, dy), Qt.AlignCenter, txt)

    def paintEvent(self, e):
        w, h = self.width(), self.height()
        if not w or not h:
            return
        r = int(min(w, h) * c.GAUGE_CONTENT_FACTOR / 2)
        halo = r + 30
        shift = int(h * c.SHIFT_FACTOR)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(w / 2, h / 2 - shift)
        # background radial gradient
        grad = QConicalGradient(QPointF(0, 0), 0)
        # adjust gradient colours based on theme
        if c.CURRENT_THEME == "light":
            colors = [
                (0, QColor(255, 255, 255)),
                (0.25, QColor(224, 224, 224)),
                (0.5, QColor(255, 255, 255)),
                (0.75, QColor(224, 224, 224)),
                (1.0, QColor(255, 255, 255)),
            ]
        else:
            colors = [
                (0, QColor(7, 16, 27)),
                (0.25, QColor(20, 30, 60)),
                (0.5, QColor(7, 16, 27)),
                (0.75, QColor(20, 30, 60)),
                (1.0, QColor(7, 16, 27)),
            ]
        rad = QRadialGradient(QPointF(0, 0), halo)
        for pos, col in colors:
            rad.setColorAt(pos, col)
        p.setBrush(QBrush(rad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), halo, halo)
        thick = 24
        for i in range(5):
            ang = self._angles[i]
            rad_len = r + (i - 1) * thick
            span = 360 if i == 0 else self._ring_spans[i]
            gradc = QConicalGradient(QPointF(0, 0), -90)
            for pos, col in c.GRAD_STOPS:
                # darken outer rings for depth
                qcol = QColor(col)
                if i != 0:
                    qcol = qcol.darker(150 + i * 30)
                gradc.setColorAt(pos, qcol)
            pen = QPen(QBrush(gradc), thick, Qt.SolidLine, Qt.RoundCap)
            p.save()
            p.rotate(ang)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(-rad_len, -rad_len, 2 * rad_len, 2 * rad_len), 45 * 16, -span * 16)
            p.restore()
        # inner static ring
        p.setPen(QPen(QColor(c.CLR_TRACK), 16, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(QPointF(0, 0), r, r)
        gradc = QConicalGradient(QPointF(0, 0), -90)
        for pos, col in c.GRAD_STOPS:
            gradc.setColorAt(pos, QColor(col))
        p.setPen(QPen(QBrush(gradc), 24, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(-r, -r, 2 * r, 2 * r), 90 * 16, -360 * 16)
        # glow
        glow = QRadialGradient(QPointF(0, 0), halo + 40)
        glow.setColorAt(0.7, QColor(0, 191, 255, 30))
        glow.setColorAt(1.0, QColor(0, 191, 255, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), halo + 40, halo + 40)
        # inner fill
        p.setBrush(QBrush(QColor(c.CLR_ITEM_ACT)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), r - 30, r - 30)
        # text in centre
        txt_map = {'idle': "Iniciar", 'hovering': "Iniciar", 'calculating': "--", 'done': "Siguiente"}
        txt = txt_map[self._state]
        font_size = int(r * (0.3 if txt != "--" else 0.45))
        self._draw_text(p, QRectF(-r, -r, 2 * r, 2 * r), txt,
                        QFont(c.FONT_FAM, font_size, QFont.Bold))
        p.end()
