from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

import background
from presets import add_preset, delete_preset, describe, load_presets, save_presets
from settings import load_settings, save_settings
from timer_logic import (MAX_SECONDS, CountdownTimer, IntervalTimer, format_time,
                         parse_duration, split_minutes_seconds)

# Work/Rest defaults: work seconds, rest seconds, rounds
DEFAULT_INTERVAL = (40, 20, 5)
ADJUST_BUTTONS = (("-1 min", -60), ("+1 min", 60), ("-1 sec", -1), ("+1 sec", 1))
MAX_ROUNDS = 99
PHASE_COLORS = {
    "work": (0.3, 0.85, 0.4, 1),
    "rest": (1.0, 0.65, 0.2, 1),
    "done": (0.5, 0.75, 1.0, 1),
}

# label -> seconds. Edit this to change the presets.
PRESETS = {
    "30 sec": 30,
    "1 min": 60,
    "3 min": 180,
    "5 min": 300,
    "10 min": 600,
    "15 min": 900,
    "25 min (Pomodoro)": 1500,
}
PRESET_TITLE = "Presets"

Window.clearcolor = (0.08, 0.09, 0.11, 1)

SOUND_DIR = Path(__file__).parent / "sounds"
_sounds = {}


def load_sound(name):
    sound = _sounds.get(name)
    if sound is None:
        sound = _sounds[name] = SoundLoader.load(str(SOUND_DIR / f"{name}.wav"))
    return sound


def preload_sounds():
    """Load files up front so the first beep isn't delayed by disk/decoder work."""
    try:
        for name in ("short_beep", "long_beep"):
            load_sound(name)
    except Exception:
        pass


def play_sound(name):
    """Play sounds/<name>.wav; silently skip if audio is unavailable."""
    try:
        sound = load_sound(name)
        if sound:
            sound.stop()
            sound.play()
    except Exception:
        pass


def notify_finished():
    play_sound("long_beep")
    try:
        from plyer import vibration
        vibration.vibrate(time=1.2)  # same length as long_beep.wav
    except Exception:
        pass  # not on Android / plyer missing


class Beeper:
    """Plays beeps in-app, or leaves them to the background service when it has taken over."""

    def __init__(self):
        self.background_enabled = False
        self.external = False

    def begin(self, durations):
        """Call when a countdown starts or resumes; `durations` = seconds left per phase."""
        self.external = self.background_enabled and background.start(durations)

    def cancel(self):
        if self.external:
            background.stop()
        self.external = False

    def finished(self):
        """The countdown ended on its own; the service stops itself after its last beep."""
        self.external = False

    def short(self):
        if not self.external:
            play_sound("short_beep")

    def long(self):
        if not self.external:
            notify_finished()


beeper = Beeper()


class TimeField(TextInput):
    """Numeric box (max 3 digits), editable by tapping it."""

    def __init__(self, **kwargs):
        options = dict(
            multiline=False, input_filter="int", halign="center",
            font_size="64sp", write_tab=False, cursor_color=(1, 1, 1, 1),
            background_color=(0.15, 0.16, 0.2, 1), foreground_color=(1, 1, 1, 1))
        options.update(kwargs)
        super().__init__(**options)
        self.bind(size=self._center_text, focus=self._select_on_focus)

    def _center_text(self, *_):
        pad = max(0, (self.height - self.line_height) / 2)
        self.padding = [0, pad, 0, pad]

    def _select_on_focus(self, _field, focused):
        if focused:
            Clock.schedule_once(lambda _dt: self.select_all())  # type to replace

    def insert_text(self, substring, from_undo=False):
        if len(self.text) - len(self.selection_text) >= 3:
            return super().insert_text("", from_undo=from_undo)
        return super().insert_text(substring, from_undo=from_undo)


def labeled(widget, caption):
    box = BoxLayout(orientation="vertical", spacing=4)
    box.add_widget(Label(text=caption, size_hint_y=0.15, color=(0.7, 0.7, 0.75, 1)))
    box.add_widget(widget)
    return box


class SimpleTimerView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=14, **kwargs)
        self.timer = CountdownTimer()
        self.timer.set_duration(300)

        self.min_field = TimeField()
        self.sec_field = TimeField()
        for f in (self.min_field, self.sec_field):
            f.bind(focus=self.on_field_focus)
            f.bind(on_text_validate=lambda *_: self.commit())

        self.presets = Spinner(text=PRESET_TITLE, values=list(PRESETS),
                               size_hint_y=0.055)
        self.presets.bind(text=self.on_preset)
        self.add_widget(self.presets)

        display = BoxLayout(size_hint_y=0.3, spacing=8)
        display.add_widget(labeled(self.min_field, "minutes"))
        display.add_widget(Label(text=":", font_size="64sp", size_hint_x=0.15))
        display.add_widget(labeled(self.sec_field, "seconds"))
        self.add_widget(display)

        adjust = BoxLayout(size_hint_y=0.15, spacing=8)
        for text, delta in ADJUST_BUTTONS:
            adjust.add_widget(Button(
                text=text, on_release=lambda _b, d=delta: self.adjust(d)))
        self.add_widget(adjust)
        self.add_widget(Label(size_hint_y=0.1))  # spacer

        controls = BoxLayout(size_hint_y=0.2, spacing=8)
        self.start_btn = Button(text="Start", font_size="24sp",
                                on_release=self.toggle,
                                background_color=(0.2, 0.7, 0.3, 1))
        controls.add_widget(self.start_btn)
        controls.add_widget(Button(text="Reset", font_size="24sp",
                                   on_release=self.reset, size_hint_x=0.5))
        self.add_widget(controls)

        self.refresh()
        Clock.schedule_interval(self.tick, 0)  # every frame, for accurate beeps

    def commit(self):
        """Apply whatever is typed in the fields (only while stopped)."""
        if self.timer.running:
            return
        self.timer.set_duration(parse_duration(self.min_field.text,
                                               self.sec_field.text))
        self.refresh(force=True)

    def on_field_focus(self, _field, focused):
        if not focused:
            self.commit()

    def on_preset(self, _spinner, text):
        if text in PRESETS:
            self.timer.set_duration(PRESETS[text])
            self.refresh(force=True)
            self.presets.text = PRESET_TITLE

    def adjust(self, delta):
        if self.timer.running:
            return
        self.commit()
        new = min(MAX_SECONDS, max(0, self.timer.duration + delta))
        self.timer.set_duration(new)
        self.refresh(force=True)

    def toggle(self, *_):
        if self.timer.running:
            self.timer.pause()
            beeper.cancel()
        else:
            self.commit()
            self.timer.start()
            if self.timer.running:
                beeper.begin(self.timer.remaining_phases())
        self.refresh(force=True)

    def reset(self, *_):
        self.timer.reset()
        beeper.cancel()
        self.refresh(force=True)

    def pause(self):
        self.timer.pause()
        beeper.cancel()
        self.refresh(force=True)

    def tick(self, _dt):
        if self.timer.poll_countdown_beep():
            beeper.short()
        finished = self.timer.stop_if_finished()
        if finished:
            beeper.long()
            beeper.finished()
            self.timer.reset()  # back to the time that was set
        if self.timer.running or finished:
            self.refresh(force=True)

    def refresh(self, force=False):
        running = self.timer.running
        m, s = split_minutes_seconds(self.timer.remaining)
        for field, value in ((self.min_field, m), (self.sec_field, s)):
            field.readonly = running
            if force or not field.focus:
                field.text = f"{value:02d}"
        self.start_btn.text = "Pause" if running else "Start"


class RepeatButton(Button):
    """Calls `action` on press, then keeps repeating while held down."""

    def __init__(self, action, **kwargs):
        super().__init__(**kwargs)
        self.action = action
        self._event = None

    def on_state(self, _button, state):
        if self._event:
            self._event.cancel()
            self._event = None
        if state == "down":
            self.action()
            self._event = Clock.schedule_once(self._start_repeat, 0.5)

    def _start_repeat(self, _dt):
        self._event = Clock.schedule_interval(lambda _d: self.action(), 0.08)


class DurationBlock(BoxLayout):
    """A caption and [mm] : [ss] boxes, with -1/+1 min/sec buttons underneath."""

    def __init__(self, caption, seconds, color, **kwargs):
        super().__init__(orientation="vertical", spacing=6, **kwargs)
        self.min_field = TimeField(font_size="40sp")
        self.sec_field = TimeField(font_size="40sp")
        for f in (self.min_field, self.sec_field):
            f.bind(focus=lambda _f, focused: None if focused else self.commit())
            f.bind(on_text_validate=lambda *_: self.commit())

        self.add_widget(Label(text=caption, font_size="18sp", bold=True,
                              color=color, size_hint_y=0.2))
        top = BoxLayout(size_hint_y=0.45, spacing=6)
        top.add_widget(self.min_field)
        top.add_widget(Label(text=":", font_size="40sp", size_hint_x=0.12))
        top.add_widget(self.sec_field)
        self.add_widget(top)

        buttons = BoxLayout(size_hint_y=0.35, spacing=6)
        for text, delta in ADJUST_BUTTONS:
            buttons.add_widget(RepeatButton(lambda d=delta: self.nudge(d), text=text))
        self.add_widget(buttons)
        self.value = seconds

    @property
    def value(self):
        return parse_duration(self.min_field.text, self.sec_field.text)

    @value.setter
    def value(self, seconds):
        m, s = divmod(max(0, min(MAX_SECONDS, int(seconds))), 60)
        self.min_field.text, self.sec_field.text = f"{m:02d}", f"{s:02d}"

    def commit(self):
        self.value = self.value  # normalises e.g. 00:75 -> 01:15

    def nudge(self, delta):
        self.value = self.value + delta


class CountRow(BoxLayout):
    """Centered caption above a '-  [05]  +' row."""

    def __init__(self, caption, count, **kwargs):
        super().__init__(orientation="vertical", spacing=6, **kwargs)
        self.field = TimeField(font_size="32sp")
        self.field.bind(focus=lambda _f, focused: None if focused else self.commit())
        self.field.bind(on_text_validate=lambda *_: self.commit())
        self.add_widget(Label(text=caption, font_size="18sp", bold=True,
                              color=PHASE_COLORS["done"], size_hint_y=0.35))
        row = BoxLayout(spacing=6)
        row.add_widget(RepeatButton(lambda: self.nudge(-1), text="-",
                                    size_hint_x=0.25))
        row.add_widget(self.field)
        row.add_widget(RepeatButton(lambda: self.nudge(1), text="+",
                                    size_hint_x=0.25))
        self.add_widget(row)
        self.value = count

    @property
    def value(self):
        try:
            n = int(self.field.text)
        except ValueError:
            n = 1
        return max(1, min(MAX_ROUNDS, n))

    @value.setter
    def value(self, count):
        self.field.text = f"{max(1, min(MAX_ROUNDS, int(count))):02d}"

    def commit(self):
        self.value = self.value

    def nudge(self, delta):
        self.value = self.value + delta


class PresetsPopup(Popup):
    """Save the current Work/Rest setup under a name, or load/delete a saved one."""

    def __init__(self, view, **kwargs):
        self.view = view
        self.items = load_presets(view.presets_path)
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)

        # dp (not raw pixels) so rows stay tall enough on high-density phone screens
        save_row = BoxLayout(size_hint_y=None, height=dp(64), spacing=8)
        self.name_input = TextInput(hint_text="Name (optional)", multiline=False,
                                    write_tab=False, font_size="18sp",
                                    padding=(dp(10), dp(22), dp(10), dp(10)),
                                    background_color=(0.15, 0.16, 0.2, 1),
                                    foreground_color=(1, 1, 1, 1),
                                    hint_text_color=(0.6, 0.6, 0.65, 1),
                                    cursor_color=(1, 1, 1, 1))
        self.name_input.bind(on_text_validate=lambda *_: self.save_current())
        save_row.add_widget(self.name_input)
        save_row.add_widget(Button(text="Save current", size_hint_x=0.45,
                                   on_release=lambda *_: self.save_current()))
        content.add_widget(save_row)

        scroll = ScrollView()
        self.list = GridLayout(cols=1, spacing=6, size_hint_y=None)
        self.list.bind(minimum_height=self.list.setter("height"))
        scroll.add_widget(self.list)
        content.add_widget(scroll)

        content.add_widget(Button(text="Close", size_hint_y=None, height=dp(56),
                                  on_release=lambda *_: self.dismiss()))
        super().__init__(title="Presets", content=content, size_hint=(0.94, 0.85),
                         **kwargs)
        self.rebuild()

    def rebuild(self):
        self.list.clear_widgets()
        if not self.items:
            self.list.add_widget(Label(text="No saved presets yet", size_hint_y=None,
                                       height=dp(60), color=(0.7, 0.7, 0.75, 1)))
        for preset in self.items:
            row = BoxLayout(size_hint_y=None, height=dp(88), spacing=6)
            row.add_widget(Button(
                text=f"{preset['name']}\n[size=14sp]{describe(preset)}[/size]",
                markup=True, halign="center", valign="middle", font_size="18sp",
                on_size=lambda b, size: setattr(b, "text_size", (size[0] - dp(16), size[1])),
                on_release=lambda _b, p=preset: self.load(p)))
            row.add_widget(Button(
                text="X", size_hint_x=0.18, background_color=(0.8, 0.3, 0.3, 1),
                on_release=lambda _b, p=preset: self.delete(p)))
            self.list.add_widget(row)

    def save_current(self):
        work, rest, rounds = self.view.current_setup()
        name = self.name_input.text.strip() or describe(
            {"work": work, "rest": rest, "rounds": rounds})
        self.items = add_preset(self.items, name, work, rest, rounds)
        save_presets(self.view.presets_path, self.items)
        self.name_input.text = ""
        self.rebuild()

    def load(self, preset):
        self.view.apply_setup(preset["work"], preset["rest"], preset["rounds"])
        self.dismiss()

    def delete(self, preset):
        self.items = delete_preset(self.items, preset["name"])
        save_presets(self.view.presets_path, self.items)
        self.rebuild()


class IntervalView(BoxLayout):
    """Work/Rest cycle: set it up, press Start, then it runs by itself."""

    def __init__(self, presets_path, **kwargs):
        super().__init__(orientation="vertical", spacing=14, **kwargs)
        self.presets_path = presets_path
        self.interval = IntervalTimer(*DEFAULT_INTERVAL)
        self.in_session = False

        self.work_row = DurationBlock("WORK", self.interval.work, PHASE_COLORS["work"],
                                      size_hint_y=0.36)
        self.rest_row = DurationBlock("REST", self.interval.rest, PHASE_COLORS["rest"],
                                      size_hint_y=0.36)
        self.rounds_row = CountRow("ROUNDS", self.interval.rounds, size_hint_y=0.19)
        self.setup_panel = BoxLayout(orientation="vertical", spacing=12)
        self.setup_panel.add_widget(Button(
            text="Presets", size_hint_y=0.09,
            on_release=lambda *_: PresetsPopup(self).open()))
        for row in (self.work_row, self.rest_row, self.rounds_row):
            self.setup_panel.add_widget(row)

        self.status = Label(font_size="48sp", bold=True, size_hint_y=0.2)
        self.round_label = Label(font_size="24sp", size_hint_y=0.12)
        self.time_label = Label(font_size="96sp", size_hint_y=0.4)
        self.next_label = Label(font_size="20sp", size_hint_y=0.12,
                                color=(0.7, 0.7, 0.75, 1))
        self.run_panel = BoxLayout(orientation="vertical", spacing=6)
        for w in (self.status, self.round_label, self.time_label, self.next_label):
            self.run_panel.add_widget(w)

        self.body = BoxLayout(size_hint_y=0.7)
        self.body.add_widget(self.setup_panel)
        self.add_widget(self.body)

        self.add_widget(Label(size_hint_y=0.02))  # spacer
        controls = BoxLayout(size_hint_y=0.2, spacing=8)
        self.start_btn = Button(text="Start", font_size="24sp",
                                on_release=self.toggle,
                                background_color=(0.2, 0.7, 0.3, 1))
        controls.add_widget(self.start_btn)
        controls.add_widget(Button(text="Reset", font_size="24sp",
                                   on_release=self.reset, size_hint_x=0.5))
        self.add_widget(controls)

        Clock.schedule_interval(self.tick, 0)  # every frame, for accurate beeps

    def show(self, panel):
        self.body.clear_widgets()
        self.body.add_widget(panel)

    def current_setup(self):
        """(work, rest, rounds) as currently entered, with typed text applied."""
        for row in (self.work_row, self.rest_row, self.rounds_row):
            row.commit()
        return max(1, self.work_row.value), self.rest_row.value, self.rounds_row.value

    def apply_setup(self, work, rest, rounds):
        self.work_row.value = work
        self.rest_row.value = rest
        self.rounds_row.value = rounds

    def begin(self):
        for row in (self.work_row, self.rest_row, self.rounds_row):
            row.commit()
        self.interval.configure(self.work_row.value, self.rest_row.value,
                                self.rounds_row.value)
        self.work_row.value = self.interval.work  # work can't be 0
        self.in_session = True
        self.show(self.run_panel)

    def toggle(self, *_):
        if self.interval.running:
            self.interval.pause()
            beeper.cancel()
        else:
            if not self.in_session:
                self.begin()
            self.interval.start()
            beeper.begin(self.interval.remaining_phases())
        self.refresh()

    def reset(self, *_):
        self.interval.reset()
        beeper.cancel()
        self.in_session = False
        self.show(self.setup_panel)
        self.refresh()

    def pause(self):
        self.interval.pause()
        beeper.cancel()
        self.refresh()

    def tick(self, _dt):
        if not self.in_session:
            return
        beep, event = self.interval.tick()
        if beep:
            beeper.short()
        if event:
            beeper.long()
            if event == "done":
                beeper.finished()
                self.reset()  # back to the setup screen
                return
        self.refresh()

    def refresh(self):
        it = self.interval
        if self.in_session:
            self.status.text = it.phase.upper()
            self.status.color = PHASE_COLORS[it.phase]
            if it.done:
                self.round_label.text = f"{it.rounds} rounds complete"
            else:
                self.round_label.text = f"Round {it.current_round} / {it.rounds}"
            self.time_label.text = format_time(it.remaining)
            nxt = it.next_phase
            self.next_label.text = (
                f"Next: {nxt[0].capitalize()} {format_time(nxt[1])}" if nxt else
                "" if it.done else "Last interval")
        if it.running:
            self.start_btn.text = "Pause"
        elif it.done:
            self.start_btn.text = "Restart"
        else:
            self.start_btn.text = "Resume" if self.in_session else "Start"


class SettingsView(BoxLayout):
    """Settings screen. Currently one option: keep timing/beeping in the background."""

    def __init__(self, settings, on_change, **kwargs):
        super().__init__(orientation="vertical", spacing=14, padding=[0, 20, 0, 0], **kwargs)
        self.settings = settings
        self.on_change = on_change

        row = BoxLayout(size_hint_y=None, height=60, spacing=10)
        row.add_widget(Label(text="Always work in background", font_size="20sp",
                             halign="left", valign="middle"))
        self.switch = Switch(active=settings["background"], size_hint_x=0.35,
                             disabled=not background.available())
        self.switch.bind(active=self._toggled)
        row.add_widget(self.switch)
        self.add_widget(row)

        note = ("Beeps and vibration keep working when the screen is off or you "
                "switch to another app. Shows a small notification while running."
                if background.available() else
                "Only available on Android; has no effect on this device.")
        self.note = Label(text=note, font_size="15sp", color=(0.7, 0.7, 0.75, 1),
                          halign="left", valign="top", size_hint_y=None, height=90)
        self.note.bind(width=lambda lbl, w: setattr(lbl, "text_size", (w, None)))
        self.add_widget(self.note)
        self.add_widget(Label())  # pushes content to the top

    def _toggled(self, _switch, active):
        self.settings["background"] = active
        self.on_change(self.settings)

    def pause(self):
        pass


class TimerRoot(BoxLayout):
    """Top-level screen: a 'Timer | Work / Rest | Settings' switch above the active view."""

    def __init__(self, settings, on_settings_change, presets_path, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=12, **kwargs)
        self.simple = SimpleTimerView()
        self.interval_view = IntervalView(presets_path)
        self.settings_view = SettingsView(settings, on_settings_change)
        self.views = {"Timer": self.simple, "Work / Rest": self.interval_view,
                      "Settings": self.settings_view}
        self.current = None

        tabs = BoxLayout(size_hint_y=0.08, spacing=8)
        for i, name in enumerate(self.views):
            tabs.add_widget(ToggleButton(
                text=name, group="mode", allow_no_selection=False,
                state="down" if i == 0 else "normal",
                on_release=lambda _b, n=name: self.show(n)))
        self.add_widget(tabs)
        self.body = BoxLayout()
        self.add_widget(self.body)
        self.show("Timer")

    def show(self, name):
        if name == self.current:
            return
        for view in self.views.values():
            view.pause()  # never keep a hidden timer running
        self.current = name
        self.body.clear_widgets()
        self.body.add_widget(self.views[name])


class TimerApp(App):
    title = "Timer"

    def build(self):
        preload_sounds()
        self.settings_path = Path(self.user_data_dir) / "settings.json"
        settings = load_settings(self.settings_path)
        self.apply_settings(settings, save=False)
        background.stop()  # drop any beeps left over from a previous run
        return TimerRoot(settings, self.apply_settings,
                         Path(self.user_data_dir) / "presets.json")

    def apply_settings(self, settings, save=True):
        beeper.background_enabled = settings["background"]
        if save:
            save_settings(self.settings_path, settings)

    def on_start(self):
        if beeper.background_enabled:
            background.request_notification_permission()


if __name__ == "__main__":
    TimerApp().run()
