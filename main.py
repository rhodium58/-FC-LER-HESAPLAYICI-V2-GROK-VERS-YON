"""ÇİFCİLER HESAPLAYICI
Basit bir yapı malzemesi / metraj hesaplama uygulaması.
Kullanıcı uzunluk, genişlik ve (gerekirse) derinlik girer, bir malzeme
seçer; uygulama net miktarı ve fire payı eklenmiş miktarı hesaplar.
"""
import math
from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput


def calc_beton(hacim: float) -> str:
    fireli = hacim * 1.05
    return (
        f"Net Beton Hacmi: {hacim:.2f} m³\n"
        f"Önerilen (%5 Fire): {fireli:.2f} m³"
    )


def calc_kagir(alan: float, adet_m2: float, fire_oran: float, isim: str) -> str:
    """BİMS, tuğla, izo tuğla, yığma tuğla gibi 'adet/m²' ile hesaplananlar."""
    net = math.ceil(alan * adet_m2)
    fire = math.ceil(net * (1 + fire_oran))
    return (
        f"Duvar Alanı: {alan:.2f} m²\n"
        f"Net {isim}: {net} Adet\n"
        f"Önerilen (%{int(fire_oran * 100)} Fire): {fire} Adet"
    )


def calc_fayans(alan: float, parca_alani: float, olcu: str, kutu_adet: int) -> str:
    """kutu_adet: Türkiye'de o ebat için en sık görülen kutu içi adet."""
    net = math.ceil(alan / parca_alani)
    fire = math.ceil(alan * 1.10 / parca_alani)
    kutu = math.ceil(fire / kutu_adet)
    kutu_m2 = kutu_adet * parca_alani
    return (
        f"Zemin Alanı: {alan:.2f} m²\n"
        f"Net Fayans: {net} Adet ({olcu})\n"
        f"Önerilen (%10 Fire): {fire} Adet\n"
        f"Kutu: {kutu} Kutu ({kutu_adet} adet/kutu ≈ {kutu_m2:.2f} m²)\n"
        f"Kutu Toplamı: {kutu * kutu_adet} Adet / {kutu * kutu_m2:.2f} m²"
    )


def calc_alcipan(alan: float) -> str:
    plaka_alani = 3.00  # 120x250 cm
    net = math.ceil(alan / plaka_alani)
    fire = math.ceil(alan * 1.05 / plaka_alani)
    return (
        f"Kaplama Alanı: {alan:.2f} m²\n"
        f"Net Alçıpan: {net} Plaka\n"
        f"Önerilen (%5 Fire): {fire} Plaka"
    )


def calc_parke(alan: float, paket_alani: float, isim: str) -> str:
    paket = math.ceil(alan * 1.10 / paket_alani)
    return (
        f"Alan: {alan:.2f} m²\n"
        f"Gereken: {paket} Paket ({isim})\n"
        f"Toplam Metraj: {paket * paket_alani:.2f} m²"
    )


def calc_silte(alan: float) -> str:
    silte_m2 = alan * 1.05
    rulo = math.ceil(silte_m2 / 15.0)
    return (
        f"Net Zemin: {alan:.2f} m²\n"
        f"Gereken Şilte (%5 Fire): {silte_m2:.2f} m²\n"
        f"Rulo Sayısı (15 m²): {rulo} Rulo"
    )


MATERIALS = {
    "1- Hazır Beton (m³)": lambda x, y, z, alan, hacim: calc_beton(hacim),
    "2- BİMS 10cm (10x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BİMS"),
    "3- BİMS 15cm (15x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BİMS"),
    "4- BİMS 20cm (20x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BİMS"),
    "5- BİMS 25cm (25x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BİMS"),
    "6- BİMS 30cm (30x39x18.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 12.5, 0.07, "BİMS"),
    "7- Tuğla 8.5cm (8.5x19x19)": lambda x, y, z, alan, hacim: calc_kagir(alan, 25, 0.08, "Tuğla"),
    "8- Tuğla 13.5cm (13.5x19x19)": lambda x, y, z, alan, hacim: calc_kagir(alan, 25, 0.08, "Tuğla"),
    "9- Tuğla 19cm (19x19x19)": lambda x, y, z, alan, hacim: calc_kagir(alan, 25, 0.08, "Tuğla"),
    "10- İzo Tuğla 20cm (20x24x23.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 16, 0.08, "İzo Tuğla"),
    "11- İzo Tuğla 25cm (25x24x23.5)": lambda x, y, z, alan, hacim: calc_kagir(alan, 16, 0.08, "İzo Tuğla"),
    "12- Yığma Tuğla (20x30x14)": lambda x, y, z, alan, hacim: calc_kagir(alan, 22, 0.08, "Yığma Tuğla"),
    "13- 30x30 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.09, "30×30", 11),
    "14- 30x60 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.18, "30×60", 8),
    "15- 40x40 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.16, "40×40", 6),
    "16- 60x60 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.36, "60×60", 4),
    "17- 60x120 cm Fayans": lambda x, y, z, alan, hacim: calc_fayans(alan, 0.72, "60×120", 2),
    "18- Alçıpan Plakası (120x250 cm)": lambda x, y, z, alan, hacim: calc_alcipan(alan),
    "19- 32. Sınıf Parke (8mm)": lambda x, y, z, alan, hacim: calc_parke(alan, 1.83, "32. Sınıf Parke"),
    "20- 33. Sınıf Parke (10-12mm)": lambda x, y, z, alan, hacim: calc_parke(alan, 1.50, "33. Sınıf Parke"),
    "21- Şilte Metresi (m²)": lambda x, y, z, alan, hacim: calc_silte(alan),
}

DEFAULT_MATERIAL = next(iter(MATERIALS))


class HesaplaApp(App):
    def build(self):
        self.title = "ÇİFCİLER HESAPLAYICI"
        Window.softinput_mode = "below_target"

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        layout = BoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(18), dp(16), dp(24)],
            spacing=dp(10),
            size_hint_y=None,
        )
        layout.bind(minimum_height=layout.setter("height"))

        layout.add_widget(self._baslik())
        layout.add_widget(self._alt_baslik())

        layout.add_widget(self.section_label("ÖLÇÜLER"))
        self.input_uzunluk = self.add_input(layout, "Uzunluk / Metraj (m)")
        self.input_genislik = self.add_input(layout, "Genişlik / En (m)")
        self.input_derinlik = self.add_input(layout, "Derinlik / Yükseklik (m)", "1")

        layout.add_widget(self.section_label("MALZEME"))
        self.spinner = Spinner(
            text=DEFAULT_MATERIAL,
            values=tuple(MATERIALS.keys()),
            size_hint_y=None,
            height=dp(54),
            font_size=sp(14),
        )
        layout.add_widget(self.spinner)

        layout.add_widget(self._buton_satiri())

        layout.add_widget(self.section_label("SONUÇ"))
        self.lbl_sonuc = Label(
            text="Ölçüleri girip HESAPLA butonuna basın.",
            font_size=sp(16),
            size_hint_y=None,
            height=dp(210),
            halign="center",
            valign="middle",
        )
        self.lbl_sonuc.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        layout.add_widget(self.lbl_sonuc)

        footer = Label(
            text="ÇİFCİLER HESAPLAYICI • Metraj yardımcı uygulaması",
            font_size=sp(11),
            size_hint_y=None,
            height=dp(30),
            halign="center",
        )
        layout.add_widget(footer)

        scroll.add_widget(layout)
        return scroll

    def _baslik(self):
        title = Label(
            text="[b]ÇİFCİLER HESAPLAYICI[/b]",
            markup=True,
            font_size=sp(24),
            size_hint_y=None,
            height=dp(52),
            halign="center",
            valign="middle",
        )
        title.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        return title

    def _alt_baslik(self):
        subtitle = Label(
            text="Yapı malzemesi ve metraj hesabı",
            font_size=sp(14),
            size_hint_y=None,
            height=dp(28),
            halign="center",
            valign="middle",
        )
        subtitle.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        return subtitle

    def _buton_satiri(self):
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(10),
        )
        clear_btn = Button(text="TEMİZLE", font_size=sp(16), bold=True)
        clear_btn.bind(on_press=self.temizle)
        calc_btn = Button(text="HESAPLA", font_size=sp(18), bold=True)
        calc_btn.bind(on_press=self.hesapla)
        btn_row.add_widget(clear_btn)
        btn_row.add_widget(calc_btn)
        return btn_row

    def section_label(self, text):
        return Label(
            text=f"[b]{text}[/b]",
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
        label.bind(size=lambda instance, value: setattr(instance, "text_size", value))
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

    def temizle(self, instance):
        self.input_uzunluk.text = ""
        self.input_genislik.text = ""
        self.input_derinlik.text = "1"
        self.spinner.text = DEFAULT_MATERIAL
        self.lbl_sonuc.text = "Ölçüleri girip HESAPLA butonuna basın."

    def hesapla(self, instance):
        try:
            x = float(self.input_uzunluk.text.replace(",", "."))
            y = float(self.input_genislik.text.replace(",", "."))
            z = float(self.input_derinlik.text.replace(",", ".")) if self.input_derinlik.text else 1.0
            if x <= 0 or y <= 0 or z <= 0:
                raise ValueError
            alan = x * y
            hacim = x * y * z
            hesapla_fn = MATERIALS[self.spinner.text]
            self.lbl_sonuc.text = hesapla_fn(x, y, z, alan, hacim)
        except (ValueError, TypeError, KeyError):
            self.lbl_sonuc.text = "Lütfen 0'dan büyük, geçerli sayılar giriniz."


if __name__ == "__main__":
    HesaplaApp().run()
