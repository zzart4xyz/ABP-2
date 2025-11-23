import sys
import random
import csv
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import importlib.util
from typing import Any, Callable
from PyQt5.QtCore import (
    Qt,
    QPoint,
    QTimer,
    QDate,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    QSize,
    QPointF,
    QRectF,
    QAbstractAnimation,
    QParallelAnimationGroup,
    QSequentialAnimationGroup,
    QPauseAnimation,
    QEvent,
)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QConicalGradient, QPixmap, QIcon, QPainterPath, QLinearGradient
try:
    from PyQt5.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QStackedWidget, QLineEdit, QComboBox, QScrollBar, QTableWidget, QTableWidgetItem, QTabWidget, QListWidget, QListWidgetItem, QDialog, QTextEdit, QDateTimeEdit, QSpinBox, QCalendarWidget, QCheckBox, QStyledItemDelegate, QStyle, QToolButton, QTableView, QHeaderView, QAbstractSpinBox, QSizePolicy, QProgressBar, QGraphicsOpacityEffect
from constants import *
from models import AlarmState, ReminderState, TimerState, WEEKDAY_ORDER


from aplicacion_background import AnimatedBackground
from aplicacion_componentes import LoginDialog, SplashScreen, create_splash_animations
import database
from mixins import FramelessWindowMixin

class MainWindow(FramelessWindowMixin, QMainWindow):

    def __init__(self, username: str, login_time: datetime):
        super().__init__()
        self.username = username
        self.login_time = login_time
        self._init_frameless(as_dialog=False)
        self.setMinimumSize(1100, 700)
        self._drag = None
        self.setWindowOpacity(0.0)
        self._show_anim: QPropertyAnimation | None = None
        self._show_anim_played = False
        self.setCentralWidget(AnimatedBackground(self, username=username, login_time=login_time))

    def showEvent(self, event):
        super().showEvent(event)
        if self._show_anim_played:
            return
        self._show_anim_played = True
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(420)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            self._show_anim = None

        anim.finished.connect(_cleanup)
        self._show_anim = anim
        anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None
def run_app() -> None:
    """Inicializar la aplicación y ejecutar el bucle principal."""

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash_specs = create_splash_animations(splash)
    for spec in splash_specs:
        if not isinstance(spec, dict):
            continue
        prepare = spec.get('prepare')
        if callable(prepare):
            try:
                prepare()
            except Exception:
                pass
        anim = spec.get('animation')
        if anim is None:
            continue
        delay = 0
        try:
            delay = int(spec.get('delay', 0) or 0)
        except Exception:
            delay = 0

        def start_anim(animation=anim):
            try:
                animation.stop()
            except Exception:
                pass
            if hasattr(animation, 'setDirection'):
                try:
                    animation.setDirection(QAbstractAnimation.Forward)
                except Exception:
                    pass
            animation.start()

        if delay > 0:
            QTimer.singleShot(delay, start_anim)
        else:
            start_anim()
    splash.exec_()
    login = LoginDialog(
        init_callback=database.init_db,
        authenticate_callback=database.authenticate,
        create_user_callback=database.create_user,
        log_action_callback=database.log_action,
    )
    if login.exec_() == QDialog.Accepted:
        username = getattr(login, 'current_user', None)
        login_ts = datetime.now()
        if username:
            try:
                database.log_action(username, 'Inicio de sesión')
            except Exception:
                pass
        win = MainWindow(username, login_ts)
        win.show()
        sys.exit(app.exec_())
