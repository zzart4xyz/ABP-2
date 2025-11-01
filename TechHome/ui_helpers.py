"""Shared UI helper utilities for TechHome widgets and dialogs."""

from __future__ import annotations

from typing import Iterable, Tuple

from PyQt5.QtCore import QRectF, QSize, Qt
from PyQt5.QtGui import QPainterPath, QPixmap, QRegion
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import constants as c


def crop_pixmap_to_content(pixmap: QPixmap) -> QPixmap:
    """Return a cropped copy of *pixmap* that removes transparent margins."""
    if pixmap.isNull():
        return pixmap
    img = pixmap.toImage()
    width, height = img.width(), img.height()
    left, right = width, -1
    top, bottom = height, -1
    for yy in range(height):
        for xx in range(width):
            if img.pixelColor(xx, yy).alpha() > 0:
                if xx < left:
                    left = xx
                if xx > right:
                    right = xx
                if yy < top:
                    top = yy
                if yy > bottom:
                    bottom = yy
    if right < left or bottom < top:
        return pixmap
    return pixmap.copy(left, top, right - left + 1, bottom - top + 1)


def find_pixmap_centroid(pixmap: QPixmap) -> tuple[float, float]:
    """Return the alpha-weighted centroid of *pixmap* (cx, cy)."""
    if pixmap.isNull():
        return pixmap.width() / 2.0, pixmap.height() / 2.0
    img = pixmap.toImage()
    width, height = img.width(), img.height()
    sum_x = 0.0
    sum_y = 0.0
    total_alpha = 0.0
    for yy in range(height):
        for xx in range(width):
            alpha = img.pixelColor(xx, yy).alpha()
            if alpha > 0:
                total_alpha += alpha
                sum_x += xx * alpha
                sum_y += yy * alpha
    if total_alpha == 0:
        return width / 2.0, height / 2.0
    return sum_x / total_alpha, sum_y / total_alpha


def apply_rounded_mask(widget: QWidget, radius: int) -> None:
    """Clip *widget* to a rounded rectangle mask with *radius* pixels."""
    try:
        r_val = int(max(0, radius))
    except Exception:
        r_val = 10
    path = QPainterPath()
    path.addRoundedRect(QRectF(widget.rect()), r_val, r_val)
    region = QRegion(path.toFillPolygon().toPolygon())
    widget.setMask(region)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _normalize_margins(margins: int | Iterable[int]) -> Tuple[int, int, int, int]:
    if isinstance(margins, int):
        return (margins, margins, margins, margins)
    values = tuple(int(v) for v in margins)  # type: ignore[arg-type]
    if len(values) == 2:
        return (values[0], values[1], values[0], values[1])
    if len(values) == 4:
        return values  # type: ignore[return-value]
    return (12, 12, 12, 12)


def build_page_styles(object_name: str, extra: str = "") -> str:
    hero_grad = (
        "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
        f" stop:0 {c.with_alpha(c.CLR_TITLE, 0.28)},"
        f" stop:1 {c.with_alpha(c.CLR_TITLE, 0.08)})"
    )
    card_grad = (
        "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
        f" stop:0 {c.with_alpha(c.CLR_TITLE, 0.12)},"
        f" stop:1 {c.with_alpha(c.CLR_BG, 0.6)})"
    )
    row_grad = (
        "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
        f" stop:0 {c.with_alpha(c.CLR_TITLE, 0.10)},"
        f" stop:1 {c.with_alpha(c.CLR_TITLE, 0.04)})"
    )
    return (
        f"""
        QWidget#{object_name} {{
            background:transparent;
        }}
        QFrame[class='card'] {{
            background:{card_grad};
            border:none;
            border-radius:18px;
        }}
        QFrame[class='card'][data-role='hero'] {{
            background:{hero_grad};
            border:none;
        }}
        QFrame[class='header'] {{
            background:transparent;
        }}
        QFrame[class='row'] {{
            background:{row_grad};
            border:none;
            border-radius:14px;
        }}
        QLabel[class='title'] {{
            color:{c.CLR_TITLE};
            font:700 22px '{c.FONT_FAM}';
        }}
        QLabel[class='subtitle'] {{
            color:{c.CLR_TEXT_IDLE};
            font:600 16px '{c.FONT_FAM}';
        }}
        QLabel[class='value'] {{
            color:{c.CLR_TEXT_IDLE};
            font:600 16px '{c.FONT_FAM}';
        }}
        QPushButton[class='icon'] {{
            background:{c.with_alpha(c.CLR_TITLE, 0.12)};
            border:none;
            border-radius:10px;
            padding:6px;
        }}
        QPushButton[class='icon']:hover {{
            background:{c.with_alpha(c.CLR_TITLE, 0.20)};
        }}
        """ + extra
    )


def init_page(
    object_name: str,
    *,
    margins: int | Iterable[int] = (0, 24, 0, 24),
    spacing: int = 20,
    extra_style: str = "",
) -> tuple[QWidget, QVBoxLayout]:
    widget = QWidget()
    widget.setObjectName(object_name)
    widget.setStyleSheet(build_page_styles(object_name, extra_style))
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(*_normalize_margins(margins))
    layout.setSpacing(spacing)
    return widget, layout


def create_card(
    *,
    role: str | None = None,
    orientation: str = "v",
    margins: int | Iterable[int] = 16,
    spacing: int = 12,
) -> tuple[QFrame, QVBoxLayout | QHBoxLayout]:
    frame = QFrame()
    frame.setProperty("class", "card")
    if role:
        frame.setProperty("data-role", role)
    layout_cls = QHBoxLayout if orientation == "h" else QVBoxLayout
    layout = layout_cls(frame)
    layout.setContentsMargins(*_normalize_margins(margins))
    layout.setSpacing(spacing)
    # Apply a gentle drop shadow to separate the card from the background.
    c.make_shadow(frame, radius=28, offset=12, alpha=120)
    return frame, layout


def create_header(
    text: str,
    *,
    icon_name: str | None = None,
    callback = None,
    icon_size: int = 26,
) -> tuple[QFrame, QLabel, QPushButton | None]:
    frame = QFrame()
    frame.setProperty("class", "header")
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    label = QLabel(text)
    label.setProperty("class", "title")
    layout.addWidget(label)
    layout.addStretch(1)
    button: QPushButton | None = None
    if icon_name:
        button = QPushButton()
        button.setProperty("class", "icon")
        button.setCursor(Qt.PointingHandCursor)
        button.setIcon(c.icon(icon_name))
        button.setIconSize(QSize(icon_size, icon_size))
        if callback:
            button.clicked.connect(callback)
        layout.addWidget(button)
    return frame, label, button


def create_row(
    *,
    role: str = "row",
    orientation: str = "h",
    margins: int | Iterable[int] = (12, 10, 12, 10),
    spacing: int = 10,
) -> tuple[QFrame, QVBoxLayout | QHBoxLayout]:
    frame = QFrame()
    frame.setProperty("class", role)
    layout_cls = QHBoxLayout if orientation == "h" else QVBoxLayout
    layout = layout_cls(frame)
    layout.setContentsMargins(*_normalize_margins(margins))
    layout.setSpacing(spacing)
    return frame, layout
