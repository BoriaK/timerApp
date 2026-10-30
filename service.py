"""Android foreground service: plays a pre-computed beep schedule while the app is in the background.

The app passes the schedule as JSON: [[unix_time, "short" | "long"], ...].
"""
import json
import time
from os import environ
from pathlib import Path

from jnius import autoclass

from timer_logic import play_schedule

SOUND_DIR = Path(__file__).parent / "sounds"
VIBRATE_MS = 1200  # same length as long_beep.wav

PythonService = autoclass("org.kivy.android.PythonService")
Context = autoclass("android.content.Context")
MediaPlayer = autoclass("android.media.MediaPlayer")
PowerManager = autoclass("android.os.PowerManager")
service = PythonService.mService


def make_player(name):
    player = MediaPlayer()
    player.setDataSource(str(SOUND_DIR / f"{name}.wav"))
    player.prepare()
    return player


def vibrate():
    try:
        vibrator = service.getSystemService(Context.VIBRATOR_SERVICE)
        Build = autoclass("android.os.Build$VERSION")
        if Build.SDK_INT >= 26:
            Effect = autoclass("android.os.VibrationEffect")
            vibrator.vibrate(Effect.createOneShot(VIBRATE_MS, Effect.DEFAULT_AMPLITUDE))
        else:
            vibrator.vibrate(VIBRATE_MS)
    except Exception:
        pass


def main():
    events = json.loads(environ.get("PYTHON_SERVICE_ARGUMENT") or "[]")
    if not events:
        return
    players = {"short": make_player("short_beep"), "long": make_player("long_beep")}

    def play(kind):
        player = players[kind]
        player.seekTo(0)
        player.start()
        if kind == "long":
            vibrate()

    # Keeps the CPU awake with the screen off; the timeout is a safety net.
    wake_lock = service.getSystemService(Context.POWER_SERVICE).newWakeLock(
        PowerManager.PARTIAL_WAKE_LOCK, "timerapp:beeps")
    wake_lock.acquire(int((max(t for t, _ in events) - time.time() + 10) * 1000))
    try:
        play_schedule(events, play)
        time.sleep(VIBRATE_MS / 1000)  # let the final beep finish
    finally:
        wake_lock.release()
        for player in players.values():
            player.release()
        service.stopSelf()


main()
