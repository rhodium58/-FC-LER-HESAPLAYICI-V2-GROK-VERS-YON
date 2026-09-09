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


class CadScreen(Screen):
    def __init__(self, **kwargs):
        super(CadScreen, self).__init__(**kwargs)
        self.found = []
        self.dxf_files = []
        self.dwg_files = []
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.add_widget(ui_label("CAD OTO TARAMA", 22, 40, True))
        root.add_widget(ui_btn("< ANA MENU", self.go_menu, 44, 15))
        root.add_widget(ui_label(
            "Tum telefon hafizasi taranir. Dosya secmezsin. DWG binary okunmaz; yaninda DXF varsa o okunur.",
            13, 56))
        self.in_h = TextInput(
            text="2.70", hint_text="Varsayilan yukseklik m", input_filter="float",
            multiline=False, font_size=kvsp(16), size_hint_y=None, height=dp(44),
            padding=[dp(10), dp(8)])
        root.add_widget(self.in_h)
        self.sp_kapi = Spinner(
            text="Varsayilan kapi/pencere: Evet",
            values=["Varsayilan kapi/pencere: Evet", "Kapi/pencere yok"],
            size_hint_y=None, height=dp(46), font_size=kvsp(14))
        root.add_widget(self.sp_kapi)
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        row.add_widget(ui_btn("YENIDEN TARA", self.auto_tara, 48, 14))
        row.add_widget(ui_btn("TUM DOSYA IZNI", self.izin, 48, 13))
        root.add_widget(row)
        root.add_widget(ui_btn("MAHALE AKTAR", self.aktar, 50, 16))
        root.add_widget(ui_btn("KOMPLE LISTE (FIYATSIZ)", self.komple, 50, 16))
        self.lbl = Label(
            text="Hafiza taranıyor...", font_size=kvsp(14), halign="left", valign="top",
            color=(0.95, 0.94, 0.90, 1))
        self.lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        sc = ScrollView()
        sc.add_widget(self.lbl)
        root.add_widget(sc)
        self.add_widget(root)

    def on_pre_enter(self, *_a):
        self.lbl.text = "Hafiza taranıyor..."
        Clock.schedule_once(self._tara_ve_oku, 0.12)

    def auto_tara(self, _inst=None):
        self.lbl.text = "Hafiza taranıyor..."
        Clock.schedule_once(self._tara_ve_oku, 0.05)

    def izin(self, _inst=None):
        request_storage_perm()
        opened = open_all_files_settings()
        if opened:
            self.lbl.text = "Ayarlar acildi: Bu uygulama icin 'Tum dosyalara erisim' ver, sonra YENIDEN TARA."
        else:
            self.lbl.text = "Izin istendi. Verildiyse YENIDEN TARA."

    def go_menu(self, _inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def _apply_defaults(self, found):
        h = _num(self.in_h.text, 2.70) or 2.70
        kapi = self.sp_kapi.text.startswith("Varsayilan")
        out = []
        for m in found:
            n = dict(m)
            n["h"] = h
            if kapi:
                n["ke"], n["kb"] = 0.90, 2.10
                n["pe"], n["pb"] = 1.20, 1.40
            out.append(n)
        return out

    def _readable_paths(self, dxf, dwg):
        paths, seen = [], set()
        for p in dxf:
            if p not in seen:
                seen.add(p)
                paths.append(p)
        for p in dwg:
            twin = companion_dxf(p)
            if twin and twin not in seen:
                seen.add(twin)
                paths.append(twin)
            elif p not in seen:
                seen.add(p)
                paths.append(p)
        readable, binary = [], []
        for p in paths:
            (readable if looks_like_dxf(p) else binary).append(p)
        return readable, binary

    def _tara_ve_oku(self, *_a):
        request_storage_perm()
        try:
            dxf, dwg = scan_phone_cad()
        except Exception as e:
            self.found = []
            self.lbl.text = "Tarama hatasi: {}".format(e)
            return
        self.dxf_files, self.dwg_files = dxf, dwg
        readable, binary = self._readable_paths(dxf, dwg)
        mahals, errors = [], []
        for path in readable:
            try:
                rooms = parse_cad_file(path)
            except Exception as e:
                errors.append("{}: {}".format(os.path.basename(path), e))
                continue
            base = os.path.splitext(os.path.basename(path))[0]
            for r in rooms:
                n = dict(r)
                if len(readable) > 1:
                    n["ad"] = "{} / {}".format(base, n.get("ad", "Mahal"))
                mahals.append(n)
        self.found = mahals
        lines = ["Tarama bitti. DXF: {}  DWG: {}".format(len(dxf), len(dwg))]
        if not dxf and not dwg:
            lines += ["", "CAD dosyasi yok. WhatsApp/Download/Documents icinde .dxf veya .dwg ara.", "Android 11+: TUM DOSYA IZNI ver, sonra YENIDEN TARA."]
        else:
            for p in (dxf + dwg)[:20]:
                lines.append("- [{}] {}".format("OK" if p in readable else "DWG-binary", p))
            if len(dxf) + len(dwg) > 20:
                lines.append("... +{} dosya".format(len(dxf) + len(dwg) - 20))
        if binary:
            lines += ["", "Binary DWG okunmaz ({} adet). AutoCAD: Farkli Kaydet -> DXF ASCII.".format(len(binary))]
        if errors:
            lines += [""] + errors[:6]
        lines.append("")
        if mahals:
            lines.append("{} mahal otomatik okundu:".format(len(mahals)))
            for m in mahals:
                lines.append("- {}  {:.2f} x {:.2f} m  (~{:.1f} m2)".format(m["ad"], m["en"], m["boy"], m.get("alan", m["en"] * m["boy"])))
            lines += ["", "MAHALE AKTAR veya KOMPLE LISTE."]
        elif readable:
            lines.append("Dosya okundu ama kapali oda (polyline) yok.")
        self.lbl.text = "\n".join(lines)

    def oku(self, _inst=None):
        self.auto_tara()

    def aktar(self, _inst):
        if not self.found:
            self._tara_ve_oku()
        if not self.found:
            return
        app = App.get_running_app()
        app.mahals.extend(self._apply_defaults(self.found))
        if not app.proje:
            app.proje = "CAD proje"
        app.save_mahals()
        self.manager.get_screen("mahal").refresh()
        self.manager.current = "mahal"

    def komple(self, _inst):
        if not self.found:
            self._tara_ve_oku()
        if not self.found:
            return
        app = App.get_running_app()
        mahals = self._apply_defaults(self.found)
        app.mahals.extend(mahals)
        if not app.proje:
            app.proje = "CAD proje"
        app.save_mahals()
        fire = {"%5 Fire": 0.05, "%10 Fire": 0.10, "%15 Fire": 0.15}.get(app.fire_label, 0.10)
        all_items = []
        for m in mahals:
            all_items.extend(run_mahal_paket(m, dict(DEFAULT_PAKET), fire))
        app.cart.extend(all_items)
        app.save_cart()
        try:
            path, _txt = export_liste_pdf(app.cart, app.proje)
            self.lbl.text = "Liste olustu.\nPDF: {}".format(path)
        except Exception as e:
            self.lbl.text = "Liste olustu, PDF yazilamadi: {}".format(e)
        self.manager.get_screen("liste").refresh()
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "liste"
