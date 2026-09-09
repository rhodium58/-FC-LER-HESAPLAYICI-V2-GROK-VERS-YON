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


def storage_roots():
    roots = ["/storage/emulated/0", "/sdcard", "/storage/self/primary"]
    try:
        from android.storage import primary_external_storage_path, secondary_external_storage_paths
        p = primary_external_storage_path()
        if p:
            roots.insert(0, p)
        for s in (secondary_external_storage_paths() or []):
            if s:
                roots.append(s)
    except Exception:
        pass
    try:
        app = App.get_running_app()
        if app and getattr(app, "user_data_dir", None):
            roots.append(app.user_data_dir)
    except Exception:
        pass
    try:
        if os.path.isdir("/storage"):
            for name in os.listdir("/storage"):
                if name in ("self", "emulated"):
                    continue
                p = os.path.join("/storage", name)
                if os.path.isdir(p):
                    roots.append(p)
    except Exception:
        pass
    out, seen = [], set()
    for r in roots:
        try:
            rp = os.path.realpath(r)
        except Exception:
            rp = r
        if rp in seen or not os.path.isdir(r):
            continue
        seen.add(rp)
        out.append(r)
    return out


def _skip_dir(name):
    low = (name or "").lower()
    if low.startswith("."):
        return True
    if low in SKIP_DIRS:
        return True
    if "thumbnail" in low:
        return True
    return False


def scan_phone_cad(max_files=150, max_dirs=8000, max_depth=12):
    dxf, dwg = [], []
    dirs = 0
    for root in storage_roots():
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                dirs += 1
                if dirs > max_dirs:
                    return dxf, dwg
                rel = dirpath[len(root):].replace("\\", "/").strip("/")
                depth = rel.count("/") + (1 if rel else 0)
                if depth > max_depth:
                    dirnames[:] = []
                    continue
                lowp = dirpath.lower().replace("\\", "/")
                if "/android/data" in lowp or "/android/obb" in lowp:
                    dirnames[:] = []
                    continue
                dirnames[:] = [d for d in dirnames if not _skip_dir(d)]
                for name in filenames:
                    low = name.lower()
                    path = os.path.join(dirpath, name)
                    if low.endswith(".dxf") or low.endswith(".cad"):
                        dxf.append(path)
                    elif low.endswith(".dwg"):
                        dwg.append(path)
                    if len(dxf) + len(dwg) >= max_files:
                        return dxf, dwg
        except Exception:
            continue
    return dxf, dwg


def looks_like_dxf(path):
    try:
        with open(path, "rb") as f:
            head = f.read(120)
        if b"AutoCAD Binary" in head or head.startswith(b"AC10"):
            return False
        chunk = head.decode("latin-1", errors="ignore")
        if "SECTION" in chunk.upper():
            return True
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            more = f.read(8000)
        up = more.upper()
        return "SECTION" in up and ("ENTITIES" in up or "HEADER" in up)
    except Exception:
        return False


def parse_cad_file(path):
    if not looks_like_dxf(path):
        raise ValueError("DWG binary okunmaz")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return parse_dxf(text)


def companion_dxf(dwg_path):
    base, _ext = os.path.splitext(dwg_path)
    for ext in (".dxf", ".DXF", ".Dxf"):
        cand = base + ext
        if os.path.isfile(cand):
            return cand
    return ""
