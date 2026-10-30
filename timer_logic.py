"""UI-independent countdown timer logic (easy to unit-test)."""
import math
import time


def format_time(seconds: float) -> str:
    total = max(0, int(seconds + 0.999))  # round up so 0:00 only shows at the end
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


MAX_SECONDS = 999 * 60 + 59


def split_minutes_seconds(seconds: float) -> tuple[int, int]:
    total = max(0, int(seconds + 0.999))
    return divmod(total, 60)


def parse_duration(minutes_text: str, seconds_text: str) -> int:
    """Blank/invalid fields count as 0; seconds above 59 carry into minutes."""
    def to_int(text):
        try:
            return max(0, int(text))
        except ValueError:
            return 0
    return min(MAX_SECONDS, to_int(minutes_text) * 60 + to_int(seconds_text))


class CountdownTimer:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self.duration = 0.0
        self._remaining = 0.0
        self._end_at = None  # set only while running
        self._last_beep = None
        self.overshoot = 0.0  # seconds past zero when the last run completed

    def set_duration(self, seconds: float) -> None:
        self.duration = self._remaining = max(0.0, float(seconds))
        self._end_at = None
        self._last_beep = None

    @property
    def running(self) -> bool:
        return self._end_at is not None

    @property
    def remaining(self) -> float:
        if self._end_at is None:
            return self._remaining
        return max(0.0, self._end_at - self._clock())

    @property
    def finished(self) -> bool:
        return self.duration > 0 and self.remaining <= 0

    def start(self, offset: float = 0.0) -> None:
        """Start/resume. `offset` seconds are treated as already elapsed."""
        if self._remaining > 0 and not self.running:
            self._end_at = self._clock() + self._remaining - offset

    def pause(self) -> None:
        if self.running:
            self._remaining = self.remaining
            self._end_at = None

    def reset(self) -> None:
        self._remaining = self.duration
        self._end_at = None
        self._last_beep = None

    def poll_countdown_beep(self, window: int = 5) -> bool:
        """True once for each whole second left in the last `window` seconds."""
        if not self.running:
            return False
        left = math.ceil(self.remaining)
        if 1 <= left <= window and left != self._last_beep:
            self._last_beep = left
            return True
        return False

    def stop_if_finished(self) -> bool:
        """Stop the clock when it hits zero. Returns True once, on completion."""
        if self.running and self.remaining <= 0:
            self.overshoot = max(0.0, self._clock() - self._end_at)
            self._remaining = 0.0
            self._end_at = None
            return True
        return False

    def remaining_phases(self) -> list[float]:
        return [self.remaining] if self.remaining > 0 else []


def plan_beeps(durations, start, window=5):
    """Beep schedule [(time, 'short'|'long')] for back-to-back phases from `start`.

    Matches the live behaviour: one short beep per whole second left in the last
    `window` seconds of each phase, and a long beep when the phase ends.
    """
    events = []
    t = start
    for d in durations:
        if d <= 0:
            continue
        end = t + d
        for k in range(min(window, math.ceil(d)), 0, -1):
            events.append((max(t, end - k), "short"))
        events.append((end, "long"))
        t = end
    return events


def play_schedule(events, play, clock=time.time, sleep=time.sleep,
                  should_stop=lambda: False, max_late=1.0):
    """Block until every event has been played. Events later than `max_late` are skipped."""
    for when, kind in sorted(events):
        while not should_stop():
            wait = when - clock()
            if wait <= 0:
                break
            sleep(min(wait, 0.05))
        if should_stop():
            return
        if clock() - when <= max_late:
            play(kind)


class IntervalTimer:
    """Work/rest cycle: work, rest, work, ... for `rounds` (no rest after the last)."""

    def __init__(self, work=40, rest=20, rounds=5, clock=time.monotonic):
        self.timer = CountdownTimer(clock)
        self.configure(work, rest, rounds)

    def configure(self, work: int, rest: int, rounds: int) -> None:
        self.work = max(1, int(work))
        self.rest = max(0, int(rest))
        self.rounds = max(1, int(rounds))
        self._phases = []  # (name, round_number, seconds)
        for r in range(1, self.rounds + 1):
            self._phases.append(("work", r, self.work))
            if self.rest and r < self.rounds:
                self._phases.append(("rest", r, self.rest))
        self._index = 0
        self.done = False
        self.timer.set_duration(self._phases[0][2])

    @property
    def phase(self) -> str:
        return "done" if self.done else self._phases[self._index][0]

    @property
    def current_round(self) -> int:
        return self._phases[self._index][1]

    @property
    def next_phase(self):
        """(name, seconds) of the upcoming phase, or None on the last one."""
        if self.done or self._index + 1 >= len(self._phases):
            return None
        name, _, seconds = self._phases[self._index + 1]
        return name, seconds

    @property
    def running(self) -> bool:
        return self.timer.running

    def remaining_phases(self) -> list[float]:
        """Seconds left in the current phase followed by every later phase."""
        if self.done:
            return []
        later = [seconds for _, _, seconds in self._phases[self._index + 1:]]
        return [self.timer.remaining] + later

    @property
    def remaining(self) -> float:
        return self.timer.remaining

    def start(self) -> None:
        if self.done:
            self.configure(self.work, self.rest, self.rounds)
        self.timer.start()

    def pause(self) -> None:
        self.timer.pause()

    def reset(self) -> None:
        self.configure(self.work, self.rest, self.rounds)

    def tick(self) -> tuple[bool, str | None]:
        """Returns (short_beep_due, event); event is 'switch', 'done' or None."""
        beep = self.timer.poll_countdown_beep()
        if not self.timer.stop_if_finished():
            return beep, None
        if self._index + 1 < len(self._phases):
            self._index += 1
            carry = self.timer.overshoot
            self.timer.set_duration(self._phases[self._index][2])
            self.timer.start(offset=carry)
            return beep, "switch"
        self.done = True
        return beep, "done"
