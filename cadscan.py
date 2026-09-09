# -*- coding: utf-8 -*-
"""CAD oto tarama (v5.3)."""
import os
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp as kvsp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from main import (
    _num, parse_dxf, DEFAULT_PAKET, run_mahal_paket, export_liste_pdf, ui_label, ui_btn,
)

SKIP_DIRS = {
    "android", "cache", "thumbnails", ".thumbnails", "lost.dir",
    "obb", "code_cache", "dalvik-cache", ".trashed", "miui",
    "tencent", "alipay", "recycle bin", ".recycle", "node_modules",
}


def request_storage_perm():
    try:
        from android.permissions import request_permissions, Permission
        plist = [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
        for extra in ("READ_MEDIA_IMAGES", "READ_MEDIA_DOCUMENTS", "READ_MEDIA_VIDEO"):
            if hasattr(Permission, extra):
                plist.append(getattr(Permission, extra))
        request_permissions(plist)
    except Exception:
        pass


def open_all_files_settings():
    try:
        from jnius import autoclass
        Environment = autoclass("android.os.Environment")
        if Environment.isExternalStorageManager():
            return False
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        pkg = PythonActivity.mActivity.getPackageName()
        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
        intent.setData(Uri.parse("package:" + pkg))
        PythonActivity.mActivity.startActivity(intent)
        return True
    except Exception:
        return False
