from settings import load_settings, save_settings
from timer_logic import (CountdownTimer, IntervalTimer, MAX_SECONDS, format_time,
                         parse_duration, plan_beeps, play_schedule,
                         split_minutes_seconds)


def test_countdown_beeps():
    clock = FakeClock()
    t = CountdownTimer(clock)
    t.set_duration(8)
    t.start()
    beeps = []
    for step in range(0, 81):  # 0.1 s ticks
        clock.t = step / 10
        if t.poll_countdown_beep():
            beeps.append(round(t.remaining))
    assert beeps == [5, 4, 3, 2, 1]


def test_no_beeps_when_paused():
    clock = FakeClock()
    t = CountdownTimer(clock)
    t.set_duration(3)
    assert t.poll_countdown_beep() is False


def test_interval_sequence():
    clock = FakeClock()
    it = IntervalTimer(work=3, rest=2, rounds=2, clock=clock)
    assert it.phase == "work" and it.current_round == 1
    assert it.next_phase == ("rest", 2)
    it.start()
    events, beeps = [], 0
    for step in range(0, 25):  # 0.5 s ticks, 12 s
        clock.t = step / 2
        beep, event = it.tick()
        beeps += beep
        if event:
            events.append((clock.t, event, it.phase, it.current_round))
    # work 3s, rest 2s, work 3s (no rest after the last round)
    assert events == [(3.0, "switch", "rest", 1),
                      (5.0, "switch", "work", 2),
                      (8.0, "done", "done", 2)]
    assert beeps == 3 + 2 + 3  # whole seconds left in each phase
    assert not it.running


def test_interval_carries_overshoot():
    clock = FakeClock()
    it = IntervalTimer(work=2, rest=1, rounds=2, clock=clock)
    it.start()
    clock.t = 2.25
    assert it.tick()[1] == "switch"
    assert abs(it.remaining - 0.75) < 1e-9  # 0.25 s already used up


def test_interval_pause_and_restart():
    clock = FakeClock()
    it = IntervalTimer(work=4, rest=0, rounds=2, clock=clock)
    assert it.next_phase == ("work", 4)  # rest 0 -> straight to next work
    it.start()
    clock.t = 1
    it.pause()
    clock.t = 50
    assert it.remaining == 3
    it.start()
    clock.t = 53
    assert it.tick()[1] == "switch"
    clock.t = 57
    assert it.tick()[1] == "done" and it.done
    it.start()  # restarts from the beginning
    assert not it.done and it.running and it.current_round == 1


def test_plan_beeps_matches_live_countdown():
    ev = plan_beeps([8], start=100.0)
    assert ev == [(103.0, "short"), (104.0, "short"), (105.0, "short"),
                  (106.0, "short"), (107.0, "short"), (108.0, "long")]


def test_plan_beeps_short_and_chained_phases():
    ev = plan_beeps([3, 2.5], start=0.0)
    assert ev == [(0.0, "short"), (1.0, "short"), (2.0, "short"), (3.0, "long"),
                  (3.0, "short"), (3.5, "short"), (4.5, "short"), (5.5, "long")]
    assert plan_beeps([0, -1], start=0.0) == []


def test_plan_matches_interval_timer_events():
    clock = FakeClock()
    it = IntervalTimer(work=6, rest=3, rounds=2, clock=clock)
    it.start()
    planned = plan_beeps(it.remaining_phases(), 0.0)
    live = []
    for step in range(0, 181):  # 0.1 s ticks
        clock.t = step / 10
        beep, event = it.tick()
        if beep:
            live.append((round(clock.t), "short"))
        if event:
            live.append((round(clock.t), "long"))
    assert [(round(t), k) for t, k in planned] == live


def test_remaining_phases():
    clock = FakeClock()
    it = IntervalTimer(work=6, rest=3, rounds=2, clock=clock)
    assert it.remaining_phases() == [6, 3, 6]
    it.start()
    clock.t = 2
    assert it.remaining_phases() == [4, 3, 6]
    t = CountdownTimer(clock)
    assert t.remaining_phases() == []
    t.set_duration(10)
    assert t.remaining_phases() == [10]


def test_play_schedule_timing_and_stop():
    clock = FakeClock()
    played = []

    def sleep(dt):
        clock.t += dt

    events = [(1.0, "short"), (2.0, "long")]
    play_schedule(events, lambda k: played.append((round(clock.t, 2), k)),
                  clock=clock, sleep=sleep)
    assert played == [(1.0, "short"), (2.0, "long")]

    played.clear()
    clock.t = 10.0  # everything is long past -> skipped
    play_schedule(events, played.append, clock=clock, sleep=sleep)
    assert played == []

    clock.t = 0.0
    play_schedule(events, played.append, clock=clock, sleep=sleep,
                  should_stop=lambda: True)
    assert played == []


def test_settings_roundtrip(tmp_path):
    path = tmp_path / "s.json"
    assert load_settings(path) == {"background": True}  # missing file
    save_settings(path, {"background": False})
    assert load_settings(path) == {"background": False}
    path.write_text("not json")
    assert load_settings(path) == {"background": True}
    path.write_text('{"background": "yes"}')
    assert load_settings(path) == {"background": True}  # wrong type ignored


def test_split_and_parse():
    assert split_minutes_seconds(125) == (2, 5)
    assert split_minutes_seconds(4.2) == (0, 5)
    assert parse_duration("2", "5") == 125
    assert parse_duration("", "90") == 90
    assert parse_duration("abc", "-5") == 0
    assert parse_duration("5000", "0") == MAX_SECONDS


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_format():
    assert format_time(300) == "05:00"
    assert format_time(3661) == "1:01:01"
    assert format_time(0) == "00:00"


def test_run_pause_resume_finish():
    clock = FakeClock()
    t = CountdownTimer(clock)
    t.set_duration(10)
    t.start()
    clock.t = 4
    t.pause()
    assert t.remaining == 6
    clock.t = 100  # time passing while paused must not count
    assert t.remaining == 6
    t.start()
    clock.t = 106
    assert t.stop_if_finished() is True
    assert t.stop_if_finished() is False
    assert t.finished and not t.running


def test_reset():
    clock = FakeClock()
    t = CountdownTimer(clock)
    t.set_duration(10)
    t.start()
    clock.t = 3
    t.reset()
    assert t.remaining == 10 and not t.running
