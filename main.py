# -*- coding: utf-8 -*-
"""Cifciler Insaat v3.0 — Android (Kivy) metraj / kesif / santiye."""
import math
from datetime import datetime

from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

Window.clearcolor = (0.07, 0.07, 0.06, 1)

DEMIR_KG = {
    "Fi 8": 0.395, "Fi 10": 0.617, "Fi 12": 0.888, "Fi 14": 1.208,
    "Fi 16": 1.578, "Fi 18": 2.000, "Fi 20": 2.466, "Fi 22": 2.984,
    "Fi 24": 3.551, "Fi 26": 4.168, "Fi 28": 4.834, "Fi 32": 6.313,
}
MIX = {
    "C16": {"cim": 260, "kum": 0.55, "micir": 0.85, "su": 180},
    "C20": {"cim": 300, "kum": 0.52, "micir": 0.82, "su": 175},
    "C25": {"cim": 350, "kum": 0.50, "micir": 0.80, "su": 175},
    "C30": {"cim": 380, "kum": 0.48, "micir": 0.78, "su": 170},
}
PHASES = [
    "Hafriyat ve zemin", "Temel ve grobeton", "Kaba yapi", "Duvar",
    "Cati", "Tesisat kaba", "Elektrik kaba", "Siva", "Mantolama",
    "Ince isler", "Boya", "Temizlik ve teslim",
]


def _num(txt, default=0.0):
    t = (txt or "").strip().replace(",", ".")
    if not t:
        return default
    return float(t)


def _ceil(x):
    return int(math.ceil(x - 1e-9))


def pack(text, miktar, birim, gun=0.0):
    return {"text": text, "miktar": float(miktar), "birim": birim, "gun": float(gun)}


def alan_of(a):
    return max(a["x"] * a["y"] - a["open"], 0.0)


def vol_of(a):
    return max(alan_of(a) * a["z"], 0.0)


def calc_kazi(a):
    v = vol_of(a)
    nak = v * 1.25 * (1 + a["fire"])
    t = "Net kazi: {:.2f} m3\nNakliye (sisme 1.25 + fire): {:.2f} m3".format(v, nak)
    return pack(t, nak, "m3", v / 25.0)


def calc_dolgu(a):
    v = vol_of(a) * (1 + a["fire"])
    return pack("Dolgu: {:.2f} m3".format(v), v, "m3", v / 30.0)


def calc_grobeton(a):
    v = vol_of(a) * (1 + a["fire"])
    t = "Kalinlik: {:.1f} cm\nGrobeton: {:.3f} m3".format(a["z"] * 100, v)
    return pack(t, v, "m3", v / 12.0)


def calc_beton(a):
    n = vol_of(a)
    f = n * (1 + a["fire"])
    return pack("Net: {:.2f} m3\nFire dahil: {:.2f} m3".format(n, f), f, "m3", f / 20.0)


def calc_sap(a):
    alan = alan_of(a)
    n = alan * a["z"]
    f = n * (1 + a["fire"])
    t = "Alan: {:.2f} m2\nKalinlik: {:.1f} cm\nNet: {:.3f} m3\nFire dahil: {:.3f} m3".format(
        alan, a["z"] * 100, n, f)
    return pack(t, f, "m3", alan / 40.0)


def calc_kalip(a):
    alan = alan_of(a) * (1 + a["fire"])
    return pack("Kalip: {:.2f} m2".format(alan), alan, "m2", alan / 25.0)


def make_mix(cls, m):
    def _fn(a):
        h = vol_of(a) * (1 + a["fire"])
        cim = m["cim"] * h
        t = (
            "{} beton: {:.2f} m3\nCimento: {:.0f} kg ({:.1f} torba)\n"
            "Kum: {:.2f} m3\nMicir: {:.2f} m3\nSu: {:.0f} litre"
        ).format(cls, h, cim, cim / 50.0, m["kum"] * h, m["micir"] * h, m["su"] * h)
        return pack(t, h, "m3", h / 8.0)
    return _fn


def calc_kagir(adet_m2, isim, usta=10):
    def _fn(a):
        alan = alan_of(a)
        net = _ceil(alan * adet_m2)
        f = _ceil(net * (1 + a["fire"]))
        t = "Duvar alani: {:.2f} m2\nNet {}: {} adet\nFire dahil: {} adet".format(
            alan, isim, net, f)
        return pack(t, f, "adet", alan / float(usta))
    return _fn


def calc_fayans(parca, olcu, kutu_adet):
    def _fn(a):
        alan = alan_of(a)
        net = _ceil(alan / parca)
        f = _ceil(alan * (1 + a["fire"]) / parca)
        kutu = _ceil(f / float(kutu_adet))
        km2 = kutu_adet * parca
        t = (
            "Alan: {:.2f} m2\nNet: {} adet ({})\nFire dahil: {} adet\n"
            "Kutu: {} ({}/kutu ~ {:.2f} m2)"
        ).format(alan, net, olcu, f, kutu, kutu_adet, km2)
        return pack(t, kutu, "kutu", alan / 14.0)
    return _fn


def calc_kg(kg_m2, isim, torba=25, usta=18):
    def _fn(a):
        alan = alan_of(a)
        f = alan * kg_m2 * (1 + a["fire"])
        t = "{}\nAlan: {:.2f} m2\nFire dahil: {:.1f} kg\n{} kg torba: {}".format(
            isim, alan, f, torba, _ceil(f / float(torba)))
        return pack(t, f, "kg", alan / float(usta))
    return _fn


def calc_parke(paket_alani, isim):
    def _fn(a):
        alan = alan_of(a)
        p = _ceil(alan * (1 + a["fire"]) / paket_alani)
        t = "Alan: {:.2f} m2\n{}: {} paket\nToplam: {:.2f} m2".format(
            alan, isim, p, p * paket_alani)
        return pack(t, p, "paket", alan / 22.0)
    return _fn


def calc_alcipan(a):
    alan = alan_of(a)
    net = _ceil(alan / 3.0)
    f = _ceil(alan * (1 + a["fire"]) / 3.0)
    t = "Alan: {:.2f} m2\nNet: {} plaka\nFire dahil: {} plaka".format(alan, net, f)
    return pack(t, f, "plaka", alan / 18.0)


def calc_boya(m2_lt, kat, isim):
    def _fn(a):
        alan = alan_of(a)
        lt = alan * kat / float(m2_lt) * (1 + a["fire"])
        t = "{}\nAlan: {:.2f} m2\nFire dahil: {:.2f} litre".format(isim, alan, lt)
        return pack(t, lt, "lt", alan / 45.0)
    return _fn


def calc_manto(a):
    alan = alan_of(a)
    levha = alan * (1 + a["fire"])
    t = (
        "Levha: {:.2f} m2\nFile: {:.2f} m2\nDubel: {} adet\nSiva: {:.1f} kg"
    ).format(levha, alan * 1.10, _ceil(alan * 6), alan * 4.0 * (1 + a["fire"]))
    return pack(t, levha, "m2", alan / 12.0)


def calc_kiremit(a):
    alan = alan_of(a)
    f = _ceil(alan * 15 * (1 + a["fire"]))
    return pack("Cati: {:.2f} m2\nKiremit: {} adet".format(alan, f), f, "adet", alan / 18.0)


def calc_membran(a):
    f = alan_of(a) * (1 + a["fire"])
    return pack("Membran: {:.2f} m2".format(f), f, "m2", f / 50.0)


def calc_osb(a):
    f = _ceil(alan_of(a) * (1 + a["fire"]) / 3.125)
    return pack("OSB 125x250: {} plaka".format(f), f, "plaka", alan_of(a) / 30.0)


def calc_mahya(a):
    m = a["x"] * (1 + a["fire"])
    ad = _ceil(m / 0.33)
    return pack("Mahya: {:.2f} m\nAdet: {}".format(m, ad), ad, "adet", m / 40.0)


def calc_metre(isim):
    def _fn(a):
        f = a["x"] * (1 + a["fire"])
        return pack("{}: {:.2f} m".format(isim, f), f, "m", f / 30.0)
    return _fn


def calc_adet(isim, fire_on=True):
    def _fn(a):
        n = _ceil(a["y"] * (1 + a["fire"])) if fire_on else int(round(a["y"]))
        return pack("{}: {} adet".format(isim, n), n, "adet", 0)
    return _fn


def calc_demir(cap, kg_m):
    def _fn(a):
        metre = a["x"] * a["y"]
        kg = metre * kg_m * (1 + a["fire"])
        t = (
            "{}\nCubuk: {} x {:.2f} m\nToplam: {:.1f} m\n"
            "Agirlik: {:.1f} kg\nBag teli: {:.2f} kg"
        ).format(cap, int(a["y"]), a["x"], metre, kg, kg * 0.01)
        return pack(t, kg, "kg", kg / 400.0)
    return _fn


def calc_opening(isim):
    def _fn(a):
        alan = a["y"] * a["x"] * a["z"]
        t = "{}: {} adet\nOlcu: {:.2f} x {:.2f} m\nToplam: {:.2f} m2".format(
            isim, int(a["y"]), a["x"], a["z"], alan)
        return pack(t, alan, "m2", a["y"] * 0.4)
    return _fn


def calc_cevre(a):
    cev = max(2 * (a["x"] + a["y"]) - a["open"], 0.0) * (1 + a["fire"])
    return pack("Cevre fire dahil: {:.2f} m".format(cev), cev, "m", cev / 40.0)


def calc_silte(a):
    alan = alan_of(a) * (1 + a["fire"])
    r = _ceil(alan / 15.0)
    t = "Silte: {:.2f} m2\nRulo 15 m2: {}".format(alan, r)
    return pack(t, r, "rulo", alan / 80.0)


CATEGORIES = {
    "Hafriyat": {
        "Kazi (sisme 1.25)": calc_kazi,
        "Dolgu / Stabilize": calc_dolgu,
        "Grobeton": calc_grobeton,
    },
    "Beton ve Sap": {
        "Hazir beton": calc_beton,
        "Sap": calc_sap,
        "Kalip": calc_kalip,
    },
    "Beton Karisim": {k + " karisim": make_mix(k, v) for k, v in MIX.items()},
    "BIMS": {
        "BIMS 10cm": calc_kagir(12.5, "BIMS"),
        "BIMS 15cm": calc_kagir(12.5, "BIMS"),
        "BIMS 20cm": calc_kagir(12.5, "BIMS"),
        "BIMS 25cm": calc_kagir(12.5, "BIMS"),
        "BIMS 30cm": calc_kagir(12.5, "BIMS"),
    },
    "Tugla": {
        "Tugla 8.5cm": calc_kagir(25, "Tugla", 9),
        "Tugla 13.5cm": calc_kagir(25, "Tugla", 9),
        "Tugla 19cm": calc_kagir(25, "Tugla", 8),
        "Izo tugla 20cm": calc_kagir(16, "Izo tugla", 10),
        "Izo tugla 25cm": calc_kagir(16, "Izo tugla", 10),
        "Yigma tugla": calc_kagir(22, "Yigma tugla", 8),
    },
    "Fayans": {
        "30x30 fayans": calc_fayans(0.09, "30x30", 11),
        "30x60 fayans": calc_fayans(0.18, "30x60", 8),
        "40x40 fayans": calc_fayans(0.16, "40x40", 6),
        "60x60 fayans": calc_fayans(0.36, "60x60", 4),
        "60x120 fayans": calc_fayans(0.72, "60x120", 2),
    },
    "Yapistirici Derz": {
        "Seramik yapistirici": calc_kg(4.5, "Yapistirici"),
        "Derz dolgu": calc_kg(0.5, "Derz", 5, 40),
        "Astar": calc_kg(0.2, "Astar", 20, 80),
    },
    "Parke": {
        "32. sinif parke 8mm": calc_parke(1.83, "32. sinif"),
        "33. sinif parke": calc_parke(1.50, "33. sinif"),
        "Silte": calc_silte,
    },
    "Alcipan": {
        "Alcipan 120x250": calc_alcipan,
        "Derz pastasi": calc_kg(0.4, "Derz pastasi", 20, 30),
    },
    "Siva ve Boya": {
        "Cimento sivasi": calc_kg(22, "Cimento sivasi", 25, 16),
        "Alci siva": calc_kg(9, "Alci siva", 25, 20),
        "Saten alci": calc_kg(1.2, "Saten", 25, 35),
        "Ic cephe boya 2 kat": calc_boya(10, 2, "Ic cephe boya"),
        "Dis cephe boya 2 kat": calc_boya(8, 2, "Dis cephe boya"),
    },
    "Mantolama": {"Mantolama paketi": calc_manto},
    "Cati": {
        "Marsilya kiremit": calc_kiremit,
        "Mahya": calc_mahya,
        "Membran": calc_membran,
        "OSB": calc_osb,
        "Yagmur olugu": calc_metre("Oluk"),
    },
    "Demir": {k: calc_demir(k, v) for k, v in DEMIR_KG.items()},
    "Kapi Pencere": {
        "Kapi": calc_opening("Kapi"),
        "Pencere": calc_opening("Pencere"),
    },
    "Supurgelik": {"Supurgelik cevre": calc_cevre},
    "Tesisat": {
        "PPR / PVC temiz su": calc_metre("Boru"),
        "Atik PVC": calc_metre("Atik boru"),
        "Dirsek": calc_adet("Dirsek", False),
        "Te": calc_adet("Te", False),
        "Tesisat noktasi": calc_adet("Nokta", False),
    },
    "Elektrik": {
        "Kablo": calc_metre("Kablo"),
        "Priz": calc_adet("Priz", False),
        "Anahtar": calc_adet("Anahtar", False),
        "Oluklu boru": calc_metre("Oluklu"),
    },
    "Sarf": {
        "Vida": calc_adet("Vida"),
        "Dubel": calc_adet("Dubel"),
        "Kosebent": calc_adet("Kosebent", False),
    },
}

CATEGORY_ORDER = [
    "Hafriyat", "Beton ve Sap", "Beton Karisim", "BIMS", "Tugla", "Fayans",
    "Yapistirici Derz", "Parke", "Alcipan", "Siva ve Boya", "Mantolama",
    "Cati", "Demir", "Kapi Pencere", "Supurgelik", "Tesisat", "Elektrik", "Sarf",
]

HINTS = {
    "Demir": "Uzunluk = cubuk boyu (m), Genislik = adet.",
    "Kapi Pencere": "Uzunluk = en (m), Genislik = adet, Derinlik = boy (m).",
    "Tesisat": "Uzunluk = boru metre, Genislik = parca adedi.",
    "Elektrik": "Uzunluk = kablo metre, Genislik = priz/anahtar adedi.",
    "Sarf": "Genislik = adet.",
    "Supurgelik": "Uzunluk = oda eni, Genislik = oda boyu. Kapı dusumu aciklik kutusuna m.",
    "Cati": "Mahya ve oluk icin Uzunluk = metre. Digerleri alan.",
}


def ui_label(text, size=14, h=26, bold=False):
    lab = Label(
        text=("[b]{}[/b]".format(text) if bold else text),
        markup=True, font_size=sp(size), size_hint_y=None, height=dp(h),
        halign="left", valign="middle", color=(0.95, 0.94, 0.90, 1),
    )
    lab.bind(size=lambda inst, val: setattr(inst, "text_size", val))
    return lab


def ui_btn(text, handler, h=52, size=16):
    b = Button(text=text, font_size=sp(size), bold=True, size_hint_y=None, height=dp(h))
    b.bind(on_press=handler)
    return b


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        scroll = ScrollView(do_scroll_x=False)
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        box.add_widget(ui_label("CIFCILER INSAAT", 24, 46, True))
        box.add_widget(ui_label("v3.0  •  Android metraj / kesif / santiye", 13, 28))
        box.add_widget(ui_btn("SEPET / KESIF", self.go_sepet, 50, 17))
        box.add_widget(ui_btn("SANTIYE PROGRAMI", self.go_santiye, 50, 17))
        box.add_widget(ui_btn("AYARLAR", self.go_ayar, 50, 17))
        for name in CATEGORY_ORDER:
            box.add_widget(ui_btn(name.upper(), self._open(name), 52, 17))
        scroll.add_widget(box)
        self.add_widget(scroll)

    def _open(self, cat):
        def _h(_inst):
            self.manager.get_screen("hesap").set_category(cat)
            self.manager.transition = SlideTransition(direction="left")
            self.manager.current = "hesap"
        return _h

    def go_sepet(self, _inst):
        self.manager.get_screen("sepet").refresh()
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "sepet"

    def go_ayar(self, _inst):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "ayar"

    def go_santiye(self, _inst):
        self.manager.get_screen("santiye").refresh()
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "santiye"


class HesapScreen(Screen):
    def __init__(self, **kwargs):
        super(HesapScreen, self).__init__(**kwargs)
        self.category = CATEGORY_ORDER[0]
        self.materials = CATEGORIES[self.category]
        self.last = None
        scroll = ScrollView(do_scroll_x=False)
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        self.lbl_baslik = ui_label("HESAP", 22, 40, True)
        box.add_widget(self.lbl_baslik)
        box.add_widget(ui_btn("< ANA MENU", self.go_menu, 44, 15))
        self.lbl_hint = ui_label("", 13, 48)
        box.add_widget(self.lbl_hint)
        box.add_widget(ui_label("OLCULER", 15, 28, True))
        self.in_x = self._field(box, "Uzunluk / En / Cubuk boyu / Metre")
        self.in_y = self._field(box, "Genislik / Adet")
        self.in_z = self._field(box, "Derinlik / Yukseklik / Boy (m)", "1")
        self.in_open = self._field(box, "Kapi + pencere dusumu (m2)", "0")
        box.add_widget(ui_label("MALZEME / FIRE / FIYAT", 15, 28, True))
        self.spinner = Spinner(text="", values=[], size_hint_y=None, height=dp(50), font_size=sp(14))
        box.add_widget(self.spinner)
        self.sp_fire = Spinner(
            text="%10 Fire", values=["%5 Fire", "%10 Fire", "%15 Fire"],
            size_hint_y=None, height=dp(46), font_size=sp(14))
        box.add_widget(self.sp_fire)
        self.in_fiyat_m = self._field(box, "Malzeme birim fiyati (TL)", "0")
        self.in_fiyat_i = self._field(box, "Iscilik birim fiyati (TL)", "0")
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        row.add_widget(ui_btn("TEMIZLE", self.temizle, 52, 15))
        row.add_widget(ui_btn("HESAPLA", self.hesapla, 52, 16))
        box.add_widget(row)
        row2 = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        row2.add_widget(ui_btn("SEPETE EKLE", self.sepete, 52, 15))
        row2.add_widget(ui_btn("KOPYALA", self.kopyala, 52, 15))
        box.add_widget(row2)
        box.add_widget(ui_label("SONUC", 15, 28, True))
        self.lbl_sonuc = Label(
            text="Olcu gir, HESAPLA'ya bas.", font_size=sp(15),
            size_hint_y=None, height=dp(250), halign="center", valign="top",
            color=(0.95, 0.94, 0.90, 1))
        self.lbl_sonuc.bind(size=lambda i, v: setattr(i, "text_size", v))
        box.add_widget(self.lbl_sonuc)
        scroll.add_widget(box)
        self.add_widget(scroll)

    def _field(self, box, caption, default=""):
        box.add_widget(ui_label(caption, 13, 22))
        f = TextInput(
            text=default, input_filter="float", multiline=False, font_size=sp(18),
            size_hint_y=None, height=dp(46), padding=[dp(10), dp(8)])
        box.add_widget(f)
        return f

    def set_category(self, cat):
        app = App.get_running_app()
        self.category = cat
        self.materials = CATEGORIES[cat]
        keys = list(self.materials.keys())
        self.lbl_baslik.text = "[b]{}[/b]".format(cat.upper())
        self.lbl_hint.text = HINTS.get(
            cat, "Uzunluk x Genislik = alan. Derinlik hacim icindir. Kapi/pencere dusulur.")
        self.spinner.values = keys
        self.spinner.text = keys[0]
        self.sp_fire.text = app.fire_label
        self.temizle(None)

    def go_menu(self, _inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def _fire(self):
        return {"%5 Fire": 0.05, "%10 Fire": 0.10, "%15 Fire": 0.15}.get(self.sp_fire.text, 0.10)

    def _args(self):
        x = _num(self.in_x.text)
        y = _num(self.in_y.text)
        z = _num(self.in_z.text, 1.0)
        return {"x": x, "y": y, "z": z, "open": _num(self.in_open.text), "fire": self._fire()}

    def hesapla(self, _inst):
        app = App.get_running_app()
        try:
            args = self._args()
            res = self.materials[self.spinner.text](args)
            if res["miktar"] <= 0:
                raise ValueError
            fm = _num(self.in_fiyat_m.text)
            fi = _num(self.in_fiyat_i.text)
            mal = res["miktar"] * fm
            isc = res["miktar"] * fi
            ara = mal + isc
            kdv = ara * app.kdv if app.kdv_on else 0.0
            extra = ""
            if res.get("gun", 0) > 0:
                extra += "\nUsta gunu (tahmini): {:.1f}".format(res["gun"])
            if fm or fi:
                extra += (
                    "\n---\nMiktar: {:.2f} {}\nMalzeme: {:.2f} TL\nIscilik: {:.2f} TL"
                    "\nAra toplam: {:.2f} TL"
                ).format(res["miktar"], res["birim"], mal, isc, ara)
                if app.kdv_on:
                    extra += "\nKDV %20: {:.2f} TL\nGenel: {:.2f} TL".format(kdv, ara + kdv)
            text = res["text"] + extra
            self.lbl_sonuc.text = text
            self.last = {
                "kat": self.category, "malzeme": self.spinner.text, "sonuc": text,
                "miktar": res["miktar"], "birim": res["birim"],
                "malzeme_tutar": mal, "iscilik_tutar": isc, "kdv": kdv,
                "genel": (ara + kdv) if (fm or fi) else 0.0,
            }
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            self.last = None
            self.lbl_sonuc.text = "Gecerli sayi gir. Adet/metre menulerinde ilgili kutuyu doldur."

    def sepete(self, _inst):
        if not self.last:
            self.hesapla(None)
        if not self.last:
            self.lbl_sonuc.text = "Once hesapla, sonra sepete ekle."
            return
        App.get_running_app().cart.append(dict(self.last))
        App.get_running_app().save_cart()
        self.lbl_sonuc.text = self.last["sonuc"] + "\n\n[ Sepete eklendi ]"

    def kopyala(self, _inst):
        txt = self.lbl_sonuc.text or ""
        Clipboard.copy(txt)
        self.lbl_sonuc.text = txt + "\n\n[ Panoya kopyalandi ]"

    def temizle(self, _inst):
        self.in_x.text = ""
        self.in_y.text = ""
        self.in_z.text = "1"
        self.in_open.text = "0"
        keys = list(self.materials.keys())
        if keys:
            self.spinner.text = keys[0]
        self.last = None
        self.lbl_sonuc.text = "Olcu gir, HESAPLA'ya bas."


class SepetScreen(Screen):
    def __init__(self, **kwargs):
        super(SepetScreen, self).__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.add_widget(ui_label("SEPET / KESIF", 22, 40, True))
        root.add_widget(ui_btn("< ANA MENU", self.go_menu, 44, 15))
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        row.add_widget(ui_btn("KOPYALA", self.kopyala, 46, 14))
        row.add_widget(ui_btn("TEMIZLE", self.temizle, 46, 14))
        root.add_widget(row)
        self.lbl = Label(
            text="", font_size=sp(14), halign="left", valign="top",
            color=(0.95, 0.94, 0.90, 1))
        self.lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        sc = ScrollView()
        sc.add_widget(self.lbl)
        root.add_widget(sc)
        self.add_widget(root)

    def go_menu(self, _inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def _text(self):
        app = App.get_running_app()
        if not app.cart:
            return "Sepet bos. Metrajdan kalem ekle."
        lines = ["CIFCILER INSAAT v3.0", datetime.now().strftime("%d.%m.%Y %H:%M"), ""]
        m_tot = i_tot = k_tot = g_tot = 0.0
        for i, it in enumerate(app.cart, 1):
            lines.append("{}. {} / {}".format(i, it["kat"], it["malzeme"]))
            lines.append(it["sonuc"])
            lines.append("")
            m_tot += it.get("malzeme_tutar", 0)
            i_tot += it.get("iscilik_tutar", 0)
            k_tot += it.get("kdv", 0)
            g_tot += it.get("genel", 0)
        lines.extend([
            "==== TOPLAM ====",
            "Malzeme: {:.2f} TL".format(m_tot),
            "Iscilik: {:.2f} TL".format(i_tot),
            "KDV: {:.2f} TL".format(k_tot),
            "GENEL: {:.2f} TL".format(g_tot if g_tot else m_tot + i_tot + k_tot),
        ])
        return "\n".join(lines)

    def refresh(self):
        self.lbl.text = self._text()

    def kopyala(self, _inst):
        Clipboard.copy(self._text())
        self.lbl.text = self._text() + "\n\n[ Panoya kopyalandi ]"

    def temizle(self, _inst):
        App.get_running_app().cart = []
        App.get_running_app().save_cart()
        self.refresh()


class AyarScreen(Screen):
    def __init__(self, **kwargs):
        super(AyarScreen, self).__init__(**kwargs)
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        box.add_widget(ui_label("AYARLAR", 22, 40, True))
        box.add_widget(ui_btn("< ANA MENU", self.go_menu, 44, 15))
        box.add_widget(ui_label("Varsayilan fire", 14, 24))
        self.sp_fire = Spinner(
            text="%10 Fire", values=["%5 Fire", "%10 Fire", "%15 Fire"],
            size_hint_y=None, height=dp(48))
        box.add_widget(self.sp_fire)
        box.add_widget(ui_label("KDV", 14, 24))
        self.sp_kdv = Spinner(
            text="KDV %20 Acik", values=["KDV Yok", "KDV %20 Acik"],
            size_hint_y=None, height=dp(48))
        box.add_widget(self.sp_kdv)
        box.add_widget(ui_btn("KAYDET", self.kaydet, 52, 16))
        box.add_widget(Label())
        self.add_widget(box)

    def on_pre_enter(self, *_a):
        app = App.get_running_app()
        self.sp_fire.text = app.fire_label
        self.sp_kdv.text = "KDV %20 Acik" if app.kdv_on else "KDV Yok"

    def kaydet(self, _inst):
        app = App.get_running_app()
        app.fire_label = self.sp_fire.text
        app.kdv_on = self.sp_kdv.text != "KDV Yok"
        app.save_settings()
        self.go_menu(None)

    def go_menu(self, _inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"


class SantiyeScreen(Screen):
    def __init__(self, **kwargs):
        super(SantiyeScreen, self).__init__(**kwargs)
        self.phase_btns = []
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.add_widget(ui_label("SANTIYE PROGRAMI", 22, 40, True))
        root.add_widget(ui_btn("< ANA MENU", self.go_menu, 44, 15))
        scroll = ScrollView(do_scroll_x=False)
        box = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        for name in PHASES:
            b = Button(text=name, font_size=sp(15), size_hint_y=None, height=dp(48))
            b.bind(on_press=self._toggle(name))
            self.phase_btns.append((name, b))
            box.add_widget(b)
        scroll.add_widget(box)
        root.add_widget(scroll)
        self.add_widget(root)

    def _toggle(self, name):
        def _h(_inst):
            app = App.get_running_app()
            app.phases[name] = not app.phases.get(name, False)
            app.save_settings()
            self.refresh()
        return _h

    def refresh(self):
        app = App.get_running_app()
        for name, b in self.phase_btns:
            done = app.phases.get(name, False)
            b.text = ("[x] " if done else "[ ] ") + name

    def go_menu(self, _inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"


class HesaplaApp(App):
    def build(self):
        self.title = "Cifciler Insaat"
        Window.softinput_mode = "below_target"
        self.store = JsonStore("cifciler.json")
        self.cart = []
        self.fire_label = "%10 Fire"
        self.kdv_on = True
        self.kdv = 0.20
        self.phases = {p: False for p in PHASES}
        self.load_state()
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(HesapScreen(name="hesap"))
        sm.add_widget(SepetScreen(name="sepet"))
        sm.add_widget(AyarScreen(name="ayar"))
        sm.add_widget(SantiyeScreen(name="santiye"))
        return sm

    def load_state(self):
        if self.store.exists("ayar"):
            a = self.store.get("ayar")
            self.fire_label = a.get("fire_label", "%10 Fire")
            self.kdv_on = a.get("kdv_on", True)
            self.phases.update(a.get("phases", {}))
        if self.store.exists("sepet"):
            self.cart = self.store.get("sepet").get("items", [])

    def save_settings(self):
        self.store.put(
            "ayar", fire_label=self.fire_label, kdv_on=self.kdv_on, phases=self.phases)

    def save_cart(self):
        self.store.put("sepet", items=self.cart)


if __name__ == "__main__":
    HesaplaApp().run()
