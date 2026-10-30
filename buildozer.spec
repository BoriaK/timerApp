[app]
title = Timer
package.name = timerapp
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav
source.exclude_patterns = test_*.py
version = 0.1
requirements = python3,kivy,plyer,pyjnius,android
orientation = portrait
fullscreen = 0
services = Timer:service.py:foreground:foregroundServiceType=mediaPlayback
android.permissions = VIBRATE,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MEDIA_PLAYBACK,POST_NOTIFICATIONS
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
