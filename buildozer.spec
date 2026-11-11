[app]
title = Timer
package.name = timerapp
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav
source.exclude_patterns = test_*.py
version = 0.4
requirements = python3,kivy,pyjnius,android,charset_normalizer==3.4.4
orientation = portrait
fullscreen = 0
services = Timer:service.py:foreground:foregroundServiceType=mediaPlayback
android.permissions = VIBRATE,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MEDIA_PLAYBACK,POST_NOTIFICATIONS
android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
