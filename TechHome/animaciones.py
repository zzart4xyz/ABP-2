"""Utilidades comunes para animaciones de deslizamiento y desvanecido."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PyQt5.QtCore import QEasingCurve


@dataclass
class SlideSpec:
    """Especificación de una animación de tipo slide/slide_fade."""

    target_getter: Callable[[], object]
    order: int = 0
    duration: int = 220
    offset: float = 22.0
    direction: str = "down"
    step: int = 30
    fade: bool = True
    remove_effect: Optional[bool] = None


def slide_fade(spec: SlideSpec) -> dict[str, object]:
    """Devuelve un diccionario de animación con retraso según el orden."""

    payload: dict[str, object] = {
        "type": "slide_fade" if spec.fade else "slide",
        "target": spec.target_getter,
        "delay": max(0, spec.order) * spec.step,
        "duration": spec.duration,
        "offset": spec.offset,
        "direction": spec.direction,
        "easing": QEasingCurve.OutCubic,
        "fade": spec.fade,
    }

    if spec.remove_effect is not None:
        payload["remove_effect"] = spec.remove_effect

    return payload
