# timerApp – project context

Android training timer written in Python with Kivy, packaged with Buildozer.
Developed and tested on Windows; the APK is built through WSL (Ubuntu) because Buildozer only runs on Linux.

## Features
- **Timer tab:** minutes/seconds boxes (tap to type), -1/+1 min and sec buttons, Presets dropdown (30 sec ... 25 min Pomodoro).
- **Work / Rest tab:** automatic cycle work -> rest -> work ... for N rounds (no rest after the last round). Setup screen has WORK, REST and ROUNDS blocks, each with its label centered above it. A Presets button at the top opens a popup to save, load and delete named work/rest/rounds profiles. Defaults: Tabata (20/10 x 8) and Circuit (40/20 x 5).
- **Settings tab:** "Always work in background" switch (on by default).
- **Beeps:** one short beep per second in the last 5 seconds of every phase, a long beep plus vibration at each phase switch and at the end.
- **Background mode (Android only):** when the countdown starts, the whole beep schedule is computed and handed to a foreground service (`service.py`) that plays it with MediaPlayer, holds a wake lock and vibrates. The app stays silent while the service is in charge. Pause, Reset and switching tabs stop the service.

## Files
- `main.py` – Kivy UI: SimpleTimerView, IntervalView, PresetsPopup, SettingsView, TimerRoot, TimerApp, Beeper.
- `timer_logic.py` – UI-free logic: CountdownTimer, IntervalTimer, plan_beeps, play_schedule, parsing/formatting.
- `presets.py` – saved Work/Rest profiles (JSON, validated on load).
- `settings.py` – persistent settings (JSON).
- `background.py` – starts/stops the Android service from the app (no-op off Android).
- `service.py` – the Android foreground service.
- `make_sounds.py` – generates `sounds/short_beep.wav` and `sounds/long_beep.wav`.
- `buildozer.spec` – Android build config (service declaration, permissions, requirements).
- `test_timer_logic.py`, `test_presets.py` – pytest unit tests.

## Run
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python main.py          # run on desktop
.\.venv\Scripts\python -m pytest -q     # tests
```
Never copy a `.venv` between folders; recreate it.

## Conventions and decisions
- Keep logic testable and out of the UI: put it in `timer_logic.py` / `presets.py` / `settings.py` and add pytest tests.
- Timers use an injectable monotonic clock so tests can use a fake clock.
- UI ticks every frame (`Clock.schedule_interval(..., 0)`) so beeps are on time; sounds are preloaded at startup.
- Keep the menus simple: few buttons, labels centered above their blocks.
- Presets and settings are stored in the app's `user_data_dir` (`presets.json`, `settings.json`), never in the project.
- `background.py` hard-codes the service class `org.example.timerapp.ServiceTimer`; it must match `package.domain`, `package.name` and the `services` line in `buildozer.spec`.

## Status
- Everything runs and is tested on the desktop (19 unit tests pass).
- **Not yet tested on a phone:** the Android service, foreground notification, wake lock, MediaPlayer beeps, vibration and the notification permission prompt. Some phones (Xiaomi, Samsung, Huawei) may need battery optimization turned off for the app.
- **Next step:** build the APK in WSL (`buildozer android debug`), install it on a phone and test the background mode.
