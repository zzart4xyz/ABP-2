"""Shared UI helper utilities for TechHome widgets and dialogs."""

from __future__ import annotations

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QPainterPath, QPixmap, QRegion
from PyQt5.QtWidgets import QWidget


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
