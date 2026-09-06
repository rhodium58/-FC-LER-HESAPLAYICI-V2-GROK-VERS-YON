"""Cifciler Hesaplayici v2.0"""
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

Window.clearcolor = (0.10, 0.11, 0.13, 1)

DEMIR_KG = {
    "Fi 8": 0.395, "Fi 10": 0.617, "Fi 12": 0.888, "Fi 14": 1.208,
    "Fi 16": 1.578, "Fi 18": 2.000, "Fi 20": 2.466, "Fi 22": 2.984,
    "Fi 24": 3.551, "Fi 26": 4.168, "Fi 28": 4.834, "Fi 32": 6.313,
}


def _num(txt, default=0.0):
    t = (txt or "").strip().replace(",", ".")
    if not t:
        return default
    return float(t)


def _ceil(x):
    return int(math.ceil(x - 1e-9))


def pack(text, miktar, birim):
    return {"text": text, "miktar": float(miktar), "birim": birim}


def calc_beton(hacim, fire):
    f = hacim * (1 + fire)
    return pack("Net Beton: {:.2f} m3\nFire dahil: {:.2f} m3".format(hacim, f), f, "m3")


def calc_sap(alan, kalinlik_m, fire):
    h = alan * kalinlik_m
    f = h * (1 + fire)
    t = "Alan: {:.2f} m2\nKalinlik: {:.1f} cm\nNet Sap: {:.3f} m3\nFire dahil: {:.3f} m3".format(
        alan, kalinlik_m * 100, h, f)
    return pack(t, f, "m3")


def calc_karisim(hacim, fire):
    h = hacim * (1 + fire)
    cim = 350 * h
    t = ("Beton: {:.2f} m3 (fire dahil)\nCimento: {:.0f} kg ({:.1f} torba 50kg)\n"
         "Kum: {:.2f} m3\nMicir: {:.2f} m3\nSu: {:.0f} litre").format(
        h, cim, cim / 50.0, 0.50 * h, 0.80 * h, 175 * h)
    return pack(t, h, "m3")


def calc_kagir(alan, adet_m2, fire, isim):
    net = _ceil(alan * adet_m2)
    f = _ceil(net * (1 + fire))
    t = "Duvar Alani: {:.2f} m2\nNet {}: {} Adet\nFire dahil: {} Adet".format(alan, isim, net, f)
    return pack(t, f, "adet")


def calc_fayans(alan, parca, olcu, kutu_adet, fire):
    net = _ceil(alan / parca)
    f = _ceil(alan * (1 + fire) / parca)
    kutu = _ceil(f / float(kutu_adet))
    km2 = kutu_adet * parca
    t = ("Alan: {:.2f} m2\nNet: {} Adet ({})\nFire dahil: {} Adet\n"
         "Kutu: {} ({}/kutu ~ {:.2f} m2)\nKutu toplami: {} adet / {:.2f} m2").format(
        alan, net, olcu, f, kutu, kutu_adet, km2, kutu * kutu_adet, kutu * km2)
    return pack(t, kutu, "kutu")


def calc_yapistirici(alan, kg_m2, fire, isim):
    f = alan * kg_m2 * (1 + fire)
    torba = _ceil(f / 25.0)
    t = "{}\nAlan: {:.2f} m2\nFire dahil: {:.1f} kg\n25kg torba: {} adet".format(isim, alan, f, torba)
    return pack(t, f, "kg")


def calc_parke(alan, paket_alani, isim, fire):
    paket = _ceil(alan * (1 + fire) / paket_alani)
    t = "Alan: {:.2f} m2\n{}: {} Paket\nToplam: {:.2f} m2".format(alan, isim, paket, paket * paket_alani)
    return pack(t, paket, "paket")


def calc_alcipan(alan, fire):
    net = _ceil(alan / 3.0)
    f = _ceil(alan * (1 + fire) / 3.0)
    return pack("Alan: {:.2f} m2\nNet: {} Plaka\nFire dahil: {} Plaka".format(alan, net, f), f, "plaka")


def calc_siva(alan, kg_m2, fire, isim):
    f = alan * kg_m2 * (1 + fire)
    torba = _ceil(f / 25.0)
    t = "{}\nAlan: {:.2f} m2\nFire dahil: {:.1f} kg\n25kg torba: {} adet".format(isim, alan, f, torba)
    return pack(t, f, "kg")


def calc_boya(alan, kat, m2_lt, fire):
    lt = alan * kat / float(m2_lt) * (1 + fire)
    t = "Alan: {:.2f} m2\nKat: {}\nFire dahil: {:.2f} litre".format(alan, int(kat), lt)
    return pack(t, lt, "litre")


def calc_manto(alan, fire):
    levha = alan * (1 + fire)
    t = ("Mantolama alani: {:.2f} m2\nLevha: {:.2f} m2\nFile: {:.2f} m2\n"
         "Dubel: {} adet\nSiva: {:.1f} kg").format(
        alan, levha, alan * 1.10, _ceil(alan * 6), alan * 4.0 * (1 + fire))
    return pack(t, levha, "m2")


def calc_kiremit(alan, adet_m2, fire):
    f = _ceil(alan * adet_m2 * (1 + fire))
    return pack("Cati alani: {:.2f} m2\nKiremit: {} Adet".format(alan, f), f, "adet")


def calc_membran(alan, fire):
    f = alan * (1 + fire)
    return pack("Membran: {:.2f} m2 (fire dahil)".format(f), f, "m2")


def calc_osb(alan, fire):
    f = _ceil(alan * (1 + fire) / 3.125)
    return pack("Alan: {:.2f} m2\nOSB 125x250: {} Plaka".format(alan, f), f, "plaka")


def calc_demir(boy, adet, kg_m, fire, cap):
    metre = boy * adet
    kg = metre * kg_m * (1 + fire)
    t = ("{}\nCubuk: {} adet x {:.2f} m\nToplam: {:.1f} m\n"
         "Agirlik (fire dahil): {:.1f} kg\nBag teli (~%1): {:.2f} kg").format(
        cap, int(adet), boy, metre, kg, kg * 0.01)
    return pack(t, kg, "kg")


def calc_metre(uzunluk, fire, isim):
    f = uzunluk * (1 + fire)
    return pack("{}: {:.2f} m (fire dahil)".format(isim, f), f, "m")


def calc_adet(adet, fire, isim):
    f = _ceil(adet * (1 + fire)) if fire else int(round(adet))
    return pack("{}: {} Adet".format(isim, f), f, "adet")


def calc_cevre(x, y, fire, isim):
    cev = 2 * (x + y) * (1 + fire)
    t = "En: {:.2f}  Boy: {:.2f}\nCevre: {:.2f} m\n{} fire dahil: {:.2f} m".format(
        x, y, 2 * (x + y), isim, cev)
    return pack(t, cev, "m")


def calc_kalip(alan, fire):
    f = alan * (1 + fire)
    return pack("Kalip alani: {:.2f} m2\nFire dahil: {:.2f} m2".format(alan, f), f, "m2")


def calc_kapi_pencere(adet, en, boy, isim):
    alan = adet * en * boy
    t = "{}: {} adet\nOlcu: {:.2f} x {:.2f} m\nToplam: {:.2f} m2".format(isim, int(adet), en, boy, alan)
    return pack(t, alan, "m2")


CATEGORIES = {
    "Beton ve Sap": {
        "Hazir Beton": lambda a: calc_beton(a["hacim"], a["fire"]),
        "Sap": lambda a: calc_sap(a["alan"], a["z"], a["fire"]),
        "Kalip": lambda a: calc_kalip(a["alan"], a["fire"]),
    },
    "Beton Karisim": {
        "C25 Karisim (cim/kum/micir/su)": lambda a: calc_karisim(a["hacim"], a["fire"]),
    },
    "BIMS": {
        "BIMS 10cm": lambda a: calc_kagir(a["alan"], 12.5, a["fire"], "BIMS"),
        "BIMS 15cm": lambda a: calc_kagir(a["alan"], 12.5, a["fire"], "BIMS"),
        "BIMS 20cm": lambda a: calc_kagir(a["alan"], 12.5, a["fire"], "BIMS"),
        "BIMS 25cm": lambda a: calc_kagir(a["alan"], 12.5, a["fire"], "BIMS"),
        "BIMS 30cm": lambda a: calc_kagir(a["alan"], 12.5, a["fire"], "BIMS"),
    },
    "Tugla": {
        "Tugla 8.5cm": lambda a: calc_kagir(a["alan"], 25, a["fire"], "Tugla"),
        "Tugla 13.5cm": lambda a: calc_kagir(a["alan"], 25, a["fire"], "Tugla"),
        "Tugla 19cm": lambda a: calc_kagir(a["alan"], 25, a["fire"], "Tugla"),
        "Izo Tugla 20cm": lambda a: calc_kagir(a["alan"], 16, a["fire"], "Izo Tugla"),
        "Izo Tugla 25cm": lambda a: calc_kagir(a["alan"], 16, a["fire"], "Izo Tugla"),
        "Yigma Tugla": lambda a: calc_kagir(a["alan"], 22, a["fire"], "Yigma Tugla"),
    },
    "Fayans": {
        "30x30 Fayans": lambda a: calc_fayans(a["alan"], 0.09, "30x30", 11, a["fire"]),
        "30x60 Fayans": lambda a: calc_fayans(a["alan"], 0.18, "30x60", 8, a["fire"]),
        "40x40 Fayans": lambda a: calc_fayans(a["alan"], 0.16, "40x40", 6, a["fire"]),
        "60x60 Fayans": lambda a: calc_fayans(a["alan"], 0.36, "60x60", 4, a["fire"]),
        "60x120 Fayans": lambda a: calc_fayans(a["alan"], 0.72, "60x120", 2, a["fire"]),
    },
    "Yapistirici Derz": {
        "Seramik Yapistirici": lambda a: calc_yapistirici(a["alan"], 4.5, a["fire"], "Yapistirici"),
        "Derz Dolgu": lambda a: calc_yapistirici(a["alan"], 0.50, a["fire"], "Derz"),
    },
    "Parke": {
        "32. Sinif Parke 8mm": lambda a: calc_parke(a["alan"], 1.83, "32. Sinif", a["fire"]),
        "33. Sinif Parke 10-12mm": lambda a: calc_parke(a["alan"], 1.50, "33. Sinif", a["fire"]),
    },
    "Alcipan": {
        "Alcipan 120x250": lambda a: calc_alcipan(a["alan"], a["fire"]),
    },
    "Siva ve Boya": {
        "Cimento Sivasi": lambda a: calc_siva(a["alan"], 22, a["fire"], "Cimento sivasi"),
        "Alci Siva": lambda a: calc_siva(a["alan"], 9, a["fire"], "Alci siva"),
        "Saten Alci": lambda a: calc_siva(a["alan"], 1.2, a["fire"], "Saten"),
        "Boya 2 Kat": lambda a: calc_boya(a["alan"], 2, 10, a["fire"]),
    },
    "Mantolama": {
        "Mantolama Paketi": lambda a: calc_manto(a["alan"], a["fire"]),
    },
    "Cati": {
        "Marsilya Kiremit": lambda a: calc_kiremit(a["alan"], 15, a["fire"]),
        "Membran": lambda a: calc_membran(a["alan"], a["fire"]),
        "OSB": lambda a: calc_osb(a["alan"], a["fire"]),
    },
    "Demir": {k: (lambda a, cap=k, kg=v: calc_demir(a["x"], a["y"], kg, a["fire"], cap)) for k, v in DEMIR_KG.items()},
    "Kapi Pencere": {
        "Kapi": lambda a: calc_kapi_pencere(a["y"], a["x"], a["z"], "Kapi"),
        "Pencere": lambda a: calc_kapi_pencere(a["y"], a["x"], a["z"], "Pencere"),
    },
    "Supurgelik": {
        "Supurgelik Cevre": lambda a: calc_cevre(a["x"], a["y"], a["fire"], "Supurgelik"),
    },
    "Tesisat": {
        "PPR/PVC Boru": lambda a: calc_metre(a["x"], a["fire"], "Boru"),
        "Dirsek": lambda a: calc_adet(a["y"], 0, "Dirsek"),
        "Te": lambda a: calc_adet(a["y"], 0, "Te"),
    },
    "Elektrik": {
        "Kablo": lambda a: calc_metre(a["x"], a["fire"], "Kablo"),
        "Priz": lambda a: calc_adet(a["y"], 0, "Priz"),
        "Anahtar": lambda a: calc_adet(a["y"], 0, "Anahtar"),
    },
    "Sarf": {
        "Vida": lambda a: calc_adet(a["y"], a["fire"], "Vida"),
        "Dubel": lambda a: calc_adet(a["y"], a["fire"], "Dubel"),
        "Kosebent": lambda a: calc_adet(a["y"], a["fire"], "Kosebent"),
    },
}

CATEGORY_ORDER = [
    "Beton ve Sap", "Beton Karisim", "BIMS", "Tugla", "Fayans",
    "Yapistirici Derz", "Parke", "Alcipan", "Siva ve Boya", "Mantolama",
    "Cati", "Demir", "Kapi Pencere", "Supurgelik", "Tesisat", "Elektrik", "Sarf",
]

HINTS = {
    "Demir": "Uzunluk = cubuk boyu (m), Genislik = adet.",
    "Kapi Pencere": "Uzunluk = en (m), Genislik = adet, Derinlik = boy (m).",
    "Tesisat": "Uzunluk = boru metre, Genislik = dirsek/te adedi.",
    "Elektrik": "Uzunluk = kablo metre, Genislik = priz/anahtar adedi.",
    "Sarf": "Genislik kutusuna adet yaz.",
    "Supurgelik": "Uzunluk = oda eni, Genislik = oda boyu.",
}


def ui_label(text, size=14, h=26, bold=False):
    lab = Label(
        text=("[b]{}[/b]".format(text) if bold else text), markup=True,
        font_size=sp(size), size_hint_y=None, height=dp(h),
        halign="left", valign="middle", color=(0.95, 0.95, 0.95, 1),
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
        box.add_widget(ui_label("CIFCILER HESAPLAYICI", 24, 46, True))
        box.add_widget(ui_label("v2.0  •  grup sec, sepete ekle, fiyatla", 14, 28))
        box.add_widget(ui_btn("SEPET / KESIF", self.go_sepet, 50, 17))
        box.add_widget(ui_btn("AYARLAR", self.go_ayar, 50, 17))
        for name in CATEGORY_ORDER:
            box.add_widget(ui_btn(name.upper(), self._open(name), 52, 17))
        scroll.add_widget(box)
        self.add_widget(scroll)

    def _open(self, cat):
        def _h(inst):
            self.manager.get_screen("hesap").set_category(cat)
            self.manager.transition = SlideTransition(direction="left")
            self.manager.current = "hesap"
        return _h

    def go_sepet(self, inst):
        self.manager.get_screen("sepet").refresh()
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "sepet"

    def go_ayar(self, inst):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "ayar"


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
        self.lbl_hint = ui_label("", 13, 40)
        box.add_widget(self.lbl_hint)
        box.add_widget(ui_label("OLCULER", 15, 28, True))
        self.in_x = self._field(box, "Uzunluk / En / Cubuk boyu")
        self.in_y = self._field(box, "Genislik / Adet")
        self.in_z = self._field(box, "Derinlik / Yukseklik / Boy", "1")
        self.in_kapi = self._field(box, "Kapi alani dus (m2)", "0")
        self.in_penc = self._field(box, "Pencere alani dus (m2)", "0")
        box.add_widget(ui_label("MALZEME / FIRE / FIYAT", 15, 28, True))
        self.spinner = Spinner(text="", values=[], size_hint_y=None, height=dp(50), font_size=sp(14))
        box.add_widget(self.spinner)
        self.sp_fire = Spinner(text="%10 Fire", values=["%5 Fire", "%10 Fire", "%15 Fire"],
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
        self.lbl_sonuc = Label(text="Olcu gir, HESAPLA'ya bas.", font_size=sp(15),
                               size_hint_y=None, height=dp(240), halign="center", valign="top",
                               color=(0.95, 0.95, 0.95, 1))
        self.lbl_sonuc.bind(size=lambda i, v: setattr(i, "text_size", v))
        box.add_widget(self.lbl_sonuc)
        scroll.add_widget(box)
        self.add_widget(scroll)

    def _field(self, box, caption, default=""):
        box.add_widget(ui_label(caption, 13, 22))
        f = TextInput(text=default, input_filter="float", multiline=False, font_size=sp(18),
                      size_hint_y=None, height=dp(46), padding=[dp(10), dp(8)])
        box.add_widget(f)
        return f

    def set_category(self, cat):
        app = App.get_running_app()
        self.category = cat
        self.materials = CATEGORIES[cat]
        keys = list(self.materials.keys())
        self.lbl_baslik.text = "[b]{}[/b]".format(cat.upper())
        self.lbl_hint.text = HINTS.get(cat, "Uzunluk x Genislik = alan. Kapi/pencere duvar alanindan duser.")
        self.spinner.values = keys
        self.spinner.text = keys[0]
        self.sp_fire.text = app.fire_label
        self.temizle(None)

    def go_menu(self, inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def _fire(self):
        return {"%5 Fire": 0.05, "%10 Fire": 0.10, "%15 Fire": 0.15}.get(self.sp_fire.text, 0.10)

    def _args(self):
        app = App.get_running_app()
        x = _num(self.in_x.text)
        y = _num(self.in_y.text)
        z = _num(self.in_z.text, 1.0)
        if app.unit == "cm":
            x, y, z = x / 100.0, y / 100.0, z / 100.0
        alan = max(x * y - _num(self.in_kapi.text) - _num(self.in_penc.text), 0.0)
        return {"x": x, "y": y, "z": z, "alan": alan, "hacim": max(alan * z, 0.0), "fire": self._fire()}

    def hesapla(self, inst):
        app = App.get_running_app()
        try:
            args = self._args()
            if self.category not in ("Tesisat", "Elektrik", "Sarf", "Demir", "Kapi Pencere", "Supurgelik"):
                if args["x"] <= 0 or args["y"] <= 0:
                    raise ValueError
            res = self.materials[self.spinner.text](args)
            fm = _num(self.in_fiyat_m.text)
            fi = _num(self.in_fiyat_i.text)
            mal = res["miktar"] * fm
            isc = res["miktar"] * fi
            ara = mal + isc
            kdv = ara * app.kdv if app.kdv_on else 0.0
            genel = ara + kdv
            extra = ""
            if fm or fi:
                extra = ("\n---\nMiktar: {:.2f} {}\nMalzeme: {:.2f} TL\nIscilik: {:.2f} TL\n"
                         "Ara toplam: {:.2f} TL").format(res["miktar"], res["birim"], mal, isc, ara)
                if app.kdv_on:
                    extra += "\nKDV %{:.0f}: {:.2f} TL\nGenel toplam: {:.2f} TL".format(
                        app.kdv * 100, kdv, genel)
            text = res["text"] + extra
            self.lbl_sonuc.text = text
            self.last = {"kat": self.category, "malzeme": self.spinner.text, "sonuc": text,
                         "miktar": res["miktar"], "birim": res["birim"], "malzeme_tutar": mal,
                         "iscilik_tutar": isc, "kdv": kdv, "genel": genel if (fm or fi) else 0.0}
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            self.last = None
            self.lbl_sonuc.text = "Gecerli sayi gir."

    def sepete(self, inst):
        if not self.last:
            self.hesapla(None)
        if not self.last:
            self.lbl_sonuc.text = "Once hesapla, sonra sepete ekle."
            return
        App.get_running_app().cart.append(dict(self.last))
        App.get_running_app().save_cart()
        self.lbl_sonuc.text = self.last["sonuc"] + "\n\n[ Sepete eklendi ]"

    def kopyala(self, inst):
        txt = self.lbl_sonuc.text or ""
        Clipboard.copy(txt)
        self.lbl_sonuc.text = txt + "\n\n[ Panoya kopyalandi ]"

    def temizle(self, inst):
        self.in_x.text = ""
        self.in_y.text = ""
        self.in_z.text = "1"
        self.in_kapi.text = "0"
        self.in_penc.text = "0"
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
        self.lbl = Label(text="", font_size=sp(14), halign="left", valign="top",
                         color=(0.95, 0.95, 0.95, 1))
        self.lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        sc = ScrollView()
        sc.add_widget(self.lbl)
        root.add_widget(sc)
        self.add_widget(root)

    def go_menu(self, inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def _text(self):
        app = App.get_running_app()
        if not app.cart:
            return "Sepet bos."
        lines = ["CIFCILER HESAPLAYICI v2.0", datetime.now().strftime("%d.%m.%Y %H:%M"), ""]
        m_tot = i_tot = k_tot = g_tot = 0.0
        for i, it in enumerate(app.cart, 1):
            lines.append("{}. {} / {}".format(i, it["kat"], it["malzeme"]))
            lines.append(it["sonuc"])
            lines.append("")
            m_tot += it.get("malzeme_tutar", 0)
            i_tot += it.get("iscilik_tutar", 0)
            k_tot += it.get("kdv", 0)
            g_tot += it.get("genel", 0)
        lines.append("==== TOPLAM ====")
        lines.append("Malzeme: {:.2f} TL".format(m_tot))
        lines.append("Iscilik: {:.2f} TL".format(i_tot))
        lines.append("KDV: {:.2f} TL".format(k_tot))
        lines.append("GENEL: {:.2f} TL".format(g_tot if g_tot else m_tot + i_tot + k_tot))
        return "\n".join(lines)

    def refresh(self):
        self.lbl.text = self._text()

    def kopyala(self, inst):
        Clipboard.copy(self._text())
        self.lbl.text = self._text() + "\n\n[ Panoya kopyalandi ]"

    def temizle(self, inst):
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
        self.sp_fire = Spinner(text="%10 Fire", values=["%5 Fire", "%10 Fire", "%15 Fire"],
                               size_hint_y=None, height=dp(48))
        box.add_widget(self.sp_fire)
        box.add_widget(ui_label("Birim", 14, 24))
        self.sp_unit = Spinner(text="m", values=["m", "cm"], size_hint_y=None, height=dp(48))
        box.add_widget(self.sp_unit)
        box.add_widget(ui_label("KDV", 14, 24))
        self.sp_kdv = Spinner(text="KDV %20 Acik", values=["KDV Yok", "KDV %20 Acik"],
                              size_hint_y=None, height=dp(48))
        box.add_widget(self.sp_kdv)
        box.add_widget(ui_btn("KAYDET", self.kaydet, 52, 16))
        box.add_widget(Label())
        self.add_widget(box)

    def on_pre_enter(self, *a):
        app = App.get_running_app()
        self.sp_fire.text = app.fire_label
        self.sp_unit.text = app.unit
        self.sp_kdv.text = "KDV %20 Acik" if app.kdv_on else "KDV Yok"

    def kaydet(self, inst):
        app = App.get_running_app()
        app.fire_label = self.sp_fire.text
        app.unit = self.sp_unit.text
        app.kdv_on = self.sp_kdv.text != "KDV Yok"
        app.save_settings()
        self.go_menu(None)

    def go_menu(self, inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"


class HesaplaApp(App):
    def build(self):
        self.title = "Cifciler Hesaplayici"
        Window.softinput_mode = "below_target"
        self.store = JsonStore("cifciler.json")
        self.cart = []
        self.fire_label = "%10 Fire"
        self.unit = "m"
        self.kdv_on = True
        self.kdv = 0.20
        self.load_state()
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(HesapScreen(name="hesap"))
        sm.add_widget(SepetScreen(name="sepet"))
        sm.add_widget(AyarScreen(name="ayar"))
        return sm

    def load_state(self):
        if self.store.exists("ayar"):
            a = self.store.get("ayar")
            self.fire_label = a.get("fire_label", "%10 Fire")
            self.unit = a.get("unit", "m")
            self.kdv_on = a.get("kdv_on", True)
        if self.store.exists("sepet"):
            self.cart = self.store.get("sepet").get("items", [])

    def save_settings(self):
        self.store.put("ayar", fire_label=self.fire_label, unit=self.unit, kdv_on=self.kdv_on)

    def save_cart(self):
        self.store.put("sepet", items=self.cart)


if __name__ == "__main__":
    HesaplaApp().run()
