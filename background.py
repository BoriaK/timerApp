"""Starts/stops the Android beep service from the app (does nothing off Android)."""
import json
import time

from kivy.utils import platform

from timer_logic import plan_beeps

PACKAGE = "org.example.timerapp"  # package.domain + package.name in buildozer.spec
SERVICE_CLASS = f"{PACKAGE}.ServiceTimer"  # 'Timer' comes from `services` in buildozer.spec
NOTIFICATIONS = "android.permission.POST_NOTIFICATIONS"


def available() -> bool:
    return platform == "android"


def _service():
    from jnius import autoclass
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    return autoclass(SERVICE_CLASS), activity


def request_notification_permission():
    """Android 13+ needs this for the service's notification to be shown."""
    if not available():
        return
    try:
        from android.permissions import request_permissions
        request_permissions([NOTIFICATIONS])
    except Exception:
        pass


def start(durations) -> bool:
    """Hand the whole beep schedule to the service. Returns True if it took over."""
    if not available():
        return False
    try:
        service, activity = _service()
        events = plan_beeps(durations, time.time())
        service.start(activity, json.dumps(events))
        return True
    except Exception:
        return False  # fall back to in-app beeps


def stop() -> None:
    if not available():
        return
    try:
        service, activity = _service()
        service.stop(activity)
    except Exception:
        pass
