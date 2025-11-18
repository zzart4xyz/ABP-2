from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Set

__all__ = [
    "TimerState",
    "AlarmState",
    "ReminderState",
    "encode_repeat_days",
    "decode_repeat_days",
    "weekday_index",
    "WEEKDAY_ORDER",
]

WEEKDAY_ORDER = ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sa"]


def weekday_index(symbol: str) -> int:
    """Return the index of a weekday symbol within :data:`WEEKDAY_ORDER`."""
    try:
        return WEEKDAY_ORDER.index(symbol)
    except ValueError:
        raise KeyError(symbol) from None


def encode_repeat_days(days: Iterable[int]) -> str:
    """Encode a collection of weekday indices into a seven-character mask."""
    mask = ["0"] * 7
    for idx in days:
        if 0 <= idx < 7:
            mask[idx] = "1"
    return "".join(mask)


def decode_repeat_days(mask: str | None) -> Set[int]:
    """Decode a weekday mask (``"1010101"``) into a set of indices."""
    if not mask:
        return set()
    cleaned = mask.strip()
    if len(cleaned) != 7 or any(ch not in "01" for ch in cleaned):
        return set()
    return {i for i, ch in enumerate(cleaned) if ch == "1"}


@dataclass(slots=True)
class ReminderState:
    message: str
    when: datetime
    reminder_id: int | None = None

    def formatted_date(self) -> str:
        return self.when.strftime("%d %b")

    def formatted_time(self) -> str:
        return self.when.strftime("%H:%M")


@dataclass(slots=True)
class TimerState:
    label: str
    duration: int
    remaining: int
    running: bool
    loop: bool = False
    timer_id: int | None = None
    last_started: datetime | None = None
    runtime_anchor: datetime | None = field(default=None, repr=False, compare=False)

    def normalise(self) -> None:
        self.duration = max(0, int(self.duration))
        self.remaining = max(0, min(self.duration if self.duration else self.remaining, int(self.remaining)))

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 0.0
        done = self.duration - self.remaining
        return max(0.0, min(1.0, done / self.duration))

    def snapshot(self) -> dict[str, object]:
        return {
            "label": self.label,
            "duration": self.duration,
            "remaining": self.remaining,
            "running": self.running,
            "loop": self.loop,
            "timer_id": self.timer_id,
            "last_started": self.last_started,
        }


@dataclass(slots=True)
class AlarmState:
    label: str
    trigger: datetime
    enabled: bool = True
    repeat_days: Set[int] = field(default_factory=set)
    sound: str = ""
    snooze_minutes: int = 5
    alarm_id: int | None = None

    def encode_repeat(self) -> str:
        return encode_repeat_days(self.repeat_days)

    def next_trigger_after(self, ref: datetime) -> datetime | None:
        if not self.enabled:
            return None
        if not self.repeat_days:
            return self.trigger if self.trigger >= ref else None
        # Repeat: compute next occurrence using the stored time-of-day
        base_time = self.trigger.time()
        ref_date = ref.date()
        # Start searching from today, include ref day if time still ahead
        for offset in range(8):
            day = ref_date + timedelta(days=offset)
            weekday = day.weekday()
            # WEEKDAY_ORDER uses Sunday first -> map
            if weekday == 6:
                mask_idx = 0
            else:
                mask_idx = weekday + 1
            if mask_idx in self.repeat_days:
                candidate = datetime.combine(day, base_time)
                if candidate >= ref:
                    return candidate
        # If not found in a week, return None
        return None

    def formatted_time(self) -> str:
        return self.trigger.strftime("%H:%M")

