[app]
title = Cifciler Hesaplayici
package.name = cifciler
package.domain = org.cifciler
version = 2.0

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas

requirements = python3,kivy==2.2.1

orientation = portrait
fullscreen = 0

android.permissions =
android.api = 31
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.url = https://github.com/kivy/python-for-android.git
p4a.branch = v2024.01.21
p4a.commit = 2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
