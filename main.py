"""ÇİFCİLER HESAPLAYICI v1.2
Kategorili menü: Beton-Şap, BİMS, Tuğla, Fayans, Parke, Alçıpan, Şilte.
"""
import math

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput


def calc_beton(hacim):
    fireli = hacim * 1.05
    return (
        "Net Beton Hacmi: {:.2f} m³\n"
        "Önerilen (%5 Fire): {:.2f} m³"
    ).format(hacim, fireli)


def calc_sap(alan, kalinlik_m):
    hacim = alan * kalinlik_m
    fireli = hacim * 1.10
    kalinlik_cm = kalinlik_m * 100
    return (
        "Alan: {:.2f} m²\n"
        "Kalınlık: {:.1f} cm\n"
        "Net Şap: {:.3f} m³\n"
        "Önerilen (%10 Fire): {:.3f} m³"
    ).format(alan, kalinlik_cm, hacim, fireli)


def calc_kagir(alan, adet_m2, fire_oran, isim):
    net = math.ceil(alan * adet_m2)
    fire = math.ceil(net * (1 + fire_oran))
    return (
        "Duvar Alanı: {:.2f} m²\n"
        "Net {}: {} Adet\n"
        "Önerilen (%{} Fire): {} Adet"
    ).format(alan, isim, net, int(fire_oran * 100), fire)


def calc_fayans(alan, parca_alani, olcu, kutu_adet):
    net = math.ceil(alan / parca_alani)
    fire = math.ceil(alan * 1.10 / parca_alani)
    kutu = math.ceil(fire / float(kutu_adet))
    kutu_m2 = kutu_adet * parca_alani
    return (
        "Zemin Alanı: {:.2f} m²\n"
        "Net Fayans: {} Adet ({})\n"
        "Önerilen (%10 Fire): {} Adet\n"
        "Kutu: {} Kutu ({} adet/kutu ≈ {:.2f} m²)\n"
        "Kutu Toplamı: {} Adet / {:.2f} m²"
    ).format(
        alan, net, olcu, fire, kutu, kutu_adet, kutu_m2,
        kutu * kutu_adet, kutu * kutu_m2
    )


def calc_alcipan(alan):
    plaka_alani = 3.00
    net = math.ceil(alan / plaka_alani)
    fire = math.ceil(alan * 1.05 / plaka_alani)
    return (
        "Kaplama Alanı: {:.2f} m²\n"
        "Net Alçıpan: {} Plaka\n"
        "Önerilen (%5 Fire): {} Plaka"
    ).format(alan, net, fire)


def calc_parke(alan, paket_alani, isim):
    paket = math.ceil(alan * 1.10 / paket_alani)
    return (
        "Alan: {:.2f} m²\n"
        "Gereken: {} Paket ({})\n"
        "Toplam Metraj: {:.2f} m²"
    ).format(alan, paket, isim, paket * paket_alani)


def calc_silte(alan):
    silte_m2 = alan * 1.05
    rulo = math.ceil(silte_m2 / 15.0)
    return (
        "Net Zemin: {:.2f} m²\n"
        "Gereken Şilte (%5 Fire): {:.2f} m²\n"
        "Rulo Sayısı (15 m²): {} Rulo"
    ).format(alan, silte_m2, rulo)


CATEGORIES = {
    "Beton ve Sap": {
        "Hazir Beton (m3)": lambda x, y, z, alan, hacim: calc_beton(hacim),
        "Sap (m3)": lambda x, y, z, alan, hacim: calc_sap(alan, z),
    },
    "BIMS": {
        "BIMS 10cm (10x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BIMS"),
        "BIMS 15cm (15x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BIMS"),
        "BIMS 20cm (20x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BIMS"),
        "BIMS 25cm (25x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BIMS"),
        "BIMS 30cm (30x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BIMS"),
    },
    "Tugla": {
        "Tugla 8.5cm (8.5x19x19)": lambda x, y, z, alan, hacim: calc_kagir(alan, 25, 0.08, "Tugla"),
        "Tugla 13.5cm (13.5x19x19)": lambda x, y, z, alan, hacim: calc_kagir(alan, 25, 0.08, "Tugla"),
        "Tugla 19cm (19x19x19)": lambda x, y, z, alan, hacim: calc_kagir(alan, 25, 0.08, "Tugla"),
        "Izo Tugla 20cm (20x24x23.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 16, 0.08, "Izo Tugla"),
        "Izo Tugla 25cm (25x24x23.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 16, 0.08, "Izo Tugla"),
        "Yigma Tugla (20x30x14)": lambda x, y, z, alan, hacim: calc_kagir(alan, 22, 0.08, "Yigma Tugla"),
    },
    "Fayans": {
        "30x30 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.09, "30x30", 11),
        "30x60 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.18, "30x60", 8),
        "40x40 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.16, "40x40", 6),
        "60x60 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.36, "60x60", 4),
        "60x120 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.72, "60x120", 2),
    },
    "Parke": {
        "32. Sinif Parke (8mm)": lambda x, y, z, alan, hacim: calc_parke(alan, 1.83, "32. Sinif Parke"),
        "33. Sinif Parke (10-12mm)": lambda x, y, z, alan, hacim: calc_parke(alan, 1.50, "33. Sinif Parke"),
    },
    "Alcipan": {
        "Alcipan Plakasi (120x250 cm)": lambda x, y, z, alan, hacim: calc_alcipan(alan),
    },
    "Silte": {
        "Silte Metresi (m2)": lambda x, y, z, alan, hacim: calc_silte(alan),
    },
}

CATEGORY_ORDER = ["Beton ve Sap", "BIMS", "Tugla", "Fayans", "Parke", "Alcipan", "Silte"]
CATEGORY_LABELS = {
    "Beton ve Sap": "BETON VE SAP",
    "BIMS": "BIMS",
    "Tugla": "TUGLA",
    "Fayans": "FAYANS",
    "Parke": "PARKE",
    "Alcipan": "ALCIPAN",
    "Silte": "SILTE",
}


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        layout = BoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(18), dp(16), dp(24)],
            spacing=dp(12),
            size_hint_y=None,
        )
        layout.bind(minimum_height=layout.setter("height"))

        title = Label(
            text="[b]CIFCILER HESAPLAYICI[/b]",
            markup=True,
            font_size=sp(24),
            size_hint_y=None,
            height=dp(50),
            halign="center",
            valign="middle",
        )
        title.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        layout.add_widget(title)

        ver = Label(
            text="v1.2  •  malzeme grubu sec",
            font_size=sp(14),
            size_hint_y=None,
            height=dp(28),
            halign="center",
        )
        layout.add_widget(ver)

        for name in CATEGORY_ORDER:
            btn = Button(
                text=CATEGORY_LABELS[name],
                font_size=sp(18),
                bold=True,
                size_hint_y=None,
                height=dp(58),
            )
            btn.bind(on_press=self._make_open(name))
            layout.add_widget(btn)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def _make_open(self, category):
        def _open(instance):
            hesap = self.manager.get_screen("hesap")
            hesap.set_category(category)
            self.manager.transition = SlideTransition(direction="left")
            self.manager.current = "hesap"
        return _open


class HesapScreen(Screen):
    def __init__(self, **kwargs):
        super(HesapScreen, self).__init__(**kwargs)
        self.category = CATEGORY_ORDER[0]
        self.materials = CATEGORIES[self.category]

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        layout = BoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(18), dp(16), dp(24)],
            spacing=dp(10),
            size_hint_y=None,
        )
        layout.bind(minimum_height=layout.setter("height"))

        self.lbl_baslik = Label(
            text="[b]HESAP[/b]",
            markup=True,
            font_size=sp(22),
            size_hint_y=None,
            height=dp(44),
            halign="center",
            valign="middle",
        )
        self.lbl_baslik.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        layout.add_widget(self.lbl_baslik)

        geri = Button(
            text="< ANA MENU",
            font_size=sp(15),
            bold=True,
            size_hint_y=None,
            height=dp(46),
        )
        geri.bind(on_press=self.go_menu)
        layout.add_widget(geri)

        layout.add_widget(self._section("OLCULER"))
        self.input_uzunluk = self.add_input(layout, "Uzunluk / Metraj (m)")
        self.input_genislik = self.add_input(layout, "Genislik / En (m)")
        self.input_derinlik = self.add_input(layout, "Derinlik / Yukseklik / Kalinlik (m)", "1")

        layout.add_widget(self._section("MALZEME"))
        self.spinner = Spinner(
            text="",
            values=[],
            size_hint_y=None,
            height=dp(54),
            font_size=sp(14),
        )
        layout.add_widget(self.spinner)

        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(10),
        )
        clear_btn = Button(text="TEMIZLE", font_size=sp(16), bold=True)
        clear_btn.bind(on_press=self.temizle)
        calc_btn = Button(text="HESAPLA", font_size=sp(18), bold=True)
        calc_btn.bind(on_press=self.hesapla)
        btn_row.add_widget(clear_btn)
        btn_row.add_widget(calc_btn)
        layout.add_widget(btn_row)

        layout.add_widget(self._section("SONUC"))
        self.lbl_sonuc = Label(
            text="Olculeri girip HESAPLA butonuna basin.",
            font_size=sp(16),
            size_hint_y=None,
            height=dp(210),
            halign="center",
            valign="middle",
        )
        self.lbl_sonuc.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        layout.add_widget(self.lbl_sonuc)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def _section(self, text):
        return Label(
            text="[b]{}[/b]".format(text),
            markup=True,
            font_size=sp(15),
            size_hint_y=None,
            height=dp(32),
            halign="left",
            valign="middle",
        )

    def add_input(self, layout, label_text, default=""):
        label = Label(
            text=label_text,
            font_size=sp(14),
            size_hint_y=None,
            height=dp(26),
            halign="left",
            valign="middle",
        )
        label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        layout.add_widget(label)
        field = TextInput(
            text=default,
            input_filter="float",
            multiline=False,
            font_size=sp(20),
            size_hint_y=None,
            height=dp(52),
            padding=[dp(12), dp(10)],
        )
        layout.add_widget(field)
        return field

    def set_category(self, category):
        self.category = category
        self.materials = CATEGORIES[category]
        keys = list(self.materials.keys())
        self.lbl_baslik.text = "[b]{}[/b]".format(CATEGORY_LABELS[category])
        self.spinner.values = keys
        self.spinner.text = keys[0]
        self.temizle(None)

    def go_menu(self, instance):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def temizle(self, instance):
        self.input_uzunluk.text = ""
        self.input_genislik.text = ""
        self.input_derinlik.text = "1"
        keys = list(self.materials.keys())
        if keys:
            self.spinner.text = keys[0]
        self.lbl_sonuc.text = "Olculeri girip HESAPLA butonuna basin."

    def hesapla(self, instance):
        try:
            x = float(self.input_uzunluk.text.replace(",", "."))
            y = float(self.input_genislik.text.replace(",", "."))
            ztxt = self.input_derinlik.text.strip()
            z = float(ztxt.replace(",", ".")) if ztxt else 1.0
            if x <= 0 or y <= 0 or z <= 0:
                raise ValueError
            alan = x * y
            hacim = x * y * z
            fn = self.materials[self.spinner.text]
            self.lbl_sonuc.text = fn(x, y, z, alan, hacim)
        except (ValueError, TypeError, KeyError):
            self.lbl_sonuc.text = "Lutfen 0'dan buyuk, gecerli sayilar giriniz."


class HesaplaApp(App):
    def build(self):
        self.title = "Cifciler Hesaplayici"
        Window.softinput_mode = "below_target"
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(HesapScreen(name="hesap"))
        return sm


if __name__ == "__main__":
    HesaplaApp().run()
