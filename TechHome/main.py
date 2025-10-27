"""TechHome application entry point."""
from __future__ import annotations

import sys
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog

import database

try:
    from app_window import MainWindow
    from dialogs import LoginDialog, SplashScreen
except ModuleNotFoundError:  # pragma: no cover - fallback when executed as package
    from .app_window import MainWindow
    from .dialogs import LoginDialog, SplashScreen

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.exec_()
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        username = getattr(login, "current_user", None)
        login_ts = datetime.now()
        if username:
            try:
                database.log_action(username, "Inicio de sesión")
            except Exception:
                pass
        window = MainWindow(username, login_ts)
        window.show()
        sys.exit(app.exec_())
