"""Pantalla de carga y componentes asociados."""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt, QTimer, QRectF, QEasingCurve, QPropertyAnimation
from PyQt5.QtGui import QColor, QConicalGradient, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QWidget,
    QGraphicsOpacityEffect,
)

import constants as c
from ui_helpers import apply_rounded_mask, crop_pixmap_to_content, find_pixmap_centroid


class CircularProgress(QWidget):
    """Indicador circular de progreso con icono central."""

    def __init__(self, icon_path: str, diameter: int = 200, stroke_width: int = 10, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0
        self._max_value = 100
        self.diameter = diameter
        self.stroke_width = stroke_width
        size = int(diameter * 0.6)
        pix = QPixmap()
        try:
            if icon_path and icon_path.lower().endswith('.svg'):
                try:
                    from PyQt5.QtSvg import QSvgRenderer
                except Exception:
                    QSvgRenderer = None
                if QSvgRenderer is not None and os.path.isfile(icon_path):
                    renderer = QSvgRenderer(icon_path)
                    if renderer.isValid():
                        pm = QPixmap(size, size)
                        pm.fill(Qt.transparent)
                        painter = QPainter(pm)
                        renderer.render(painter)
                        painter.end()
                        pix = pm
            if pix.isNull() and icon_path and os.path.isfile(icon_path):
                pix = QPixmap(icon_path)
        except Exception:
            pass
        if not pix.isNull():
            cropped = crop_pixmap_to_content(pix)
            self.icon_pixmap = cropped.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            self.icon_pixmap = QPixmap()
        self.setMinimumSize(diameter, diameter)
        self.setMaximumSize(diameter, diameter)

    def setValue(self, value: int) -> None:
        self._value = max(0, min(self._max_value, value))
        self.update()

    def value(self) -> int:
        return self._value

    def maxValue(self) -> int:
        return self._max_value

    def setMaxValue(self, max_value: int) -> None:
        self._max_value = max(1, max_value)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        margin = self.stroke_width / 2.0
        rect = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
        bg_pen = QPen(QColor(c.CLR_SURFACE))
        bg_pen.setWidth(self.stroke_width)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)
        progress_angle = (self._value / self._max_value) * 360.0
        grad = QConicalGradient(self.diameter / 2.0, self.diameter / 2.0, -90)
        grad.setColorAt(0.0, QColor(0, 191, 255))
        grad.setColorAt(0.5, QColor(0, 128, 255))
        grad.setColorAt(1.0, QColor(0, 70, 205))
        progress_pen = QPen()
        progress_pen.setWidth(self.stroke_width)
        progress_pen.setBrush(grad)
        progress_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(progress_pen)
        start_angle = -90 * 16
        span_angle = -int(progress_angle * 16)
        painter.drawArc(rect, start_angle, span_angle)
        if not self.icon_pixmap.isNull():
            cx, cy = find_pixmap_centroid(self.icon_pixmap)
            offset_x = (self.icon_pixmap.width() / 2.0) - cx
            offset_y = (self.icon_pixmap.height() / 2.0) - cy
            ix = (self.diameter - self.icon_pixmap.width()) / 2.0 + offset_x
            iy = (self.diameter - self.icon_pixmap.height()) / 2.0 + offset_y
            painter.drawPixmap(int(ix), int(iy), self.icon_pixmap)
        painter.end()


class SplashScreen(QDialog):
    """Pantalla de carga inicial de la aplicación."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(420, 600)
        frame = QFrame(self)
        frame.setObjectName("splash")
        frame.setStyleSheet(
            f"QFrame#splash {{ background:{c.CLR_PANEL}; border:2px solid {c.CLR_TITLE}; border-radius:20px; }}"
        )
        frame.setGeometry(0, 0, self.width(), self.height())
        apply_rounded_mask(self, c.FRAME_RAD)
        apply_rounded_mask(self, 20)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        self.title_lbl = QLabel("TechHome", self)
        self.title_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 30px '{c.FONT_FAM}';")
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch(1)
        self.close_btn = QPushButton("", self)
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background:transparent;
                border:2px solid {c.CLR_TITLE};
                border-radius:5px;
            }}
            QPushButton:hover {{
                background:{c.CLR_TITLE};
            }}
            """
        )
        self.close_btn.clicked.connect(self.reject)
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)
        self.ring = CircularProgress(c.LOGO_PATH, diameter=220, stroke_width=14)
        self.ring.setFixedSize(240, 240)
        layout.addStretch(1)
        layout.addWidget(self.ring, alignment=Qt.AlignHCenter)
        layout.addSpacing(8)
        self.status_lbl = QLabel("Cargando…", self)
        self.status_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 26px '{c.FONT_FAM}';")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_lbl)
        self.sub_status_lbl = QLabel("Preparando panel", self)
        self.sub_status_lbl.setStyleSheet(f"color:{c.CLR_TEXT_IDLE}; font:500 18px '{c.FONT_FAM}';")
        self.sub_status_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sub_status_lbl)
        layout.addSpacing(12)
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background:{c.CLR_SURFACE}; border-radius:10px; height:18px; }}"
            f"QProgressBar::chunk {{ border-radius:10px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #00BFFF, stop:1 #0066FF); }}"
        )
        progress_layout.addWidget(self.progress_bar, 1)
        self.percent_lbl = QLabel("0%", self)
        self.percent_lbl.setStyleSheet(f"color:{c.CLR_TITLE}; font:700 18px '{c.FONT_FAM}';")
        progress_layout.addWidget(self.percent_lbl)
        layout.addLayout(progress_layout)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.pause_btn = QPushButton("Pausar", self)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setFixedSize(140, 40)
        self.pause_btn.setStyleSheet(
            f"""
            QPushButton {{
                background:transparent;
                color:{c.CLR_TITLE};
                border:2px solid {c.CLR_TITLE};
                border-radius:10px;
                font:600 18px '{c.FONT_FAM}';
            }}
            QPushButton:hover {{
                background:{c.CLR_HOVER};
            }}
            """
        )
        self.pause_btn.clicked.connect(self._toggle_pause)
        btn_layout.addWidget(self.pause_btn)
        self.continue_btn = QPushButton("Continuar", self)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setFixedSize(140, 40)
        self.continue_btn.setStyleSheet(
            f"""
            QPushButton {{
                background:qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00BFFF, stop:1 #0066FF);
                color:{c.CLR_BG};
                border:none;
                border-radius:10px;
                font:600 18px '{c.FONT_FAM}';
            }}
            QPushButton:disabled {{
                background:{c.CLR_SURFACE};
                color:{c.CLR_PLACEHOLDER};
            }}
            QPushButton:hover:!disabled {{
                background:qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00BFFF, stop:1 #0070FF);
            }}
            """
        )
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.continue_btn)
        layout.addLayout(btn_layout)
        self._progress_value = 0
        self._dot_step = 0
        self._tasks = [
            (0, "Preparando panel"),
            (25, "Cargando dispositivos"),
            (50, "Iniciando servicios"),
            (75, "Estableciendo conexión"),
            (100, "Completado"),
        ]
        self._paused = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(30)

    def _advance(self):
        if getattr(self, '_paused', False):
            return
        self._progress_value = min(100, self._progress_value + 1)
        self.ring.setValue(self._progress_value)
        self.progress_bar.setValue(self._progress_value)
        self.percent_lbl.setText(f"{self._progress_value}%")
        self._dot_step += 1
        dots = self._dot_step % 4
        self.status_lbl.setText("Cargando" + "." * dots)
        desc = self._tasks[0][1]
        for threshold, text in self._tasks:
            if self._progress_value >= threshold:
                desc = text
        self.sub_status_lbl.setText(desc)
        if self._progress_value >= 100:
            self._progress_value = 100
            self.ring.setValue(100)
            self.progress_bar.setValue(100)
            self.percent_lbl.setText("100%")
            self.status_lbl.setText("Cargando...")
            self.sub_status_lbl.setText(self._tasks[-1][1])
            self._timer.stop()
            self.continue_btn.setEnabled(True)

    def _toggle_pause(self):
        if self._progress_value >= 100:
            return
        if not getattr(self, '_paused', False):
            self._paused = True
            self._timer.stop()
            self.pause_btn.setText("Reanudar")
        else:
            self._paused = False
            self._timer.start(30)
            self.pause_btn.setText("Pausar")


# ------------------------------------------------------------------
# Animaciones
# ------------------------------------------------------------------

def create_splash_animations(splash: SplashScreen) -> list[dict[str, object]]:
    """Crear animaciones suaves asociadas a la pantalla de carga."""

    animations: list[dict[str, object]] = []

    labels = [getattr(splash, "status_lbl", None), getattr(splash, "sub_status_lbl", None)]
    for idx, label in enumerate(filter(None, labels)):
        effect = label.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(label)
            label.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity", splash)
        fade.setDuration(600)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.InOutCubic)
        try:
            fade.finished.connect(lambda eff=effect: eff.setOpacity(1.0))
        except Exception:
            pass
        animations.append(
            {
                "animation": fade,
                "prepare": (lambda eff=effect: eff.setOpacity(0.0)),
                "effect": effect,
                "widget": label,
                "delay": idx * 120,
            }
        )

    if hasattr(splash, "continue_btn"):
        btn = splash.continue_btn
        effect = btn.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(btn)
            btn.setGraphicsEffect(effect)
        btn_anim = QPropertyAnimation(effect, b"opacity", splash)
        btn_anim.setDuration(500)
        btn_anim.setStartValue(0.0)
        btn_anim.setEndValue(1.0)
        btn_anim.setEasingCurve(QEasingCurve.InOutCubic)
        try:
            btn_anim.finished.connect(lambda eff=effect: eff.setOpacity(1.0))
        except Exception:
            pass
        animations.append(
            {
                "animation": btn_anim,
                "prepare": (lambda eff=effect: eff.setOpacity(0.0)),
                "effect": effect,
                "widget": btn,
                "delay": 300,
            }
        )

    return animations
