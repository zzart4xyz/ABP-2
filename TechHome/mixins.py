"""Reusable mixins for shared UI behaviors in TechHome."""

from __future__ import annotations

from typing import Any


class PlayPauseMixin:
    """Provide a shared play/pause click handler for timer-like widgets."""

    @staticmethod
    def _emit_signal(signal, payload: Any) -> None:
        """Emit ``payload`` if accepted, otherwise emit without arguments."""

        try:
            signal.emit(payload)
        except TypeError:
            signal.emit()

    def _on_play_clicked(self) -> None:
        state = getattr(self, "_state", None)
        if state is None:
            state = getattr(self, "state", None)
        if state is None:
            self._emit_signal(getattr(self, "playRequested"), self)
            return

        running = bool(getattr(state, "running", False))
        remaining = int(getattr(state, "remaining", 0))
        if running and remaining > 0:
            self._emit_signal(getattr(self, "pauseRequested"), self)
        else:
            self._emit_signal(getattr(self, "playRequested"), self)
