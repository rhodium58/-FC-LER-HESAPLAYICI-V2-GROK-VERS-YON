
[app]
title = Cifciler Insaat
package.name = cifciler
package.domain = org.cifciler
version = 5.2

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
source.filename = main.py

requirements = python3,kivy==2.2.1

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,VIBRATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_DOCUMENTS,READ_MEDIA_IMAGES
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.wakelock = False

p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 0
