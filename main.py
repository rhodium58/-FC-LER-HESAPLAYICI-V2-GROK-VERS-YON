from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import ListProperty
import math

BG = (0.95, 0.96, 0.98, 1)
CARD = (1, 1, 1, 1)
TEXT = (0.10, 0.13, 0.18, 1)
MUTED = (0.40, 0.44, 0.50, 1)
PRIMARY = (0.08, 0.45, 0.33, 1)
PRIMARY_DARK = (0.05, 0.32, 0.23, 1)

class RoundedBox(BoxLayout):
    bg_color = ListProperty(CARD)

    def __init__(self, **kwargs):
        padding = kwargs.pop("padding", [0, 0])
        super().__init__(padding=padding, **kwargs)
        with self.canvas.before:
            self._color = Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._update_rect, size=self._update_rect, bg_color=self._update_color)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _update_color(self, *args):
        self._color.rgba = self.bg_color

class HesaplaApp(App):
    def build(self):
        self.title = "ÇİFCİLER HESAPLAYICI"

        root = ScrollView(do_scroll_x=False, bar_width=dp(4))
        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(14), dp(16), dp(14), dp(24)],
            spacing=dp(12),
        )
        content.bind(minimum_height=content.setter("height"))

        header = RoundedBox(
            orientation="vertical", size_hint_y=None, height=dp(94),
            padding=[dp(18), dp(13)], spacing=dp(3),
            bg_color=list(PRIMARY_DARK)
        )
        header.add_widget(Label(
            text="[b]ÇİFCİLER HESAPLAYICI[/b]", markup=True,
            color=(1,1,1,1), font_size=sp(22),
            size_hint_y=None, height=dp(34),
            halign="left", valign="middle"))
        header.add_widget(Label(
            text="İnşaat ve zemin malzemesi metraj hesaplama",
            color=(0.88,0.96,0.92,1), font_size=sp(13),
            size_hint_y=None, height=dp(28),
            halign="left", valign="middle"))
        content.add_widget(header)

        measures = RoundedBox(
            orientation="vertical", size_hint_y=None, height=dp(245),
            padding=[dp(15), dp(12)], spacing=dp(7))
        measures.add_widget(self.section_title("ÖLÇÜLER"))

        self.input_uzunluk = self.make_input("Uzunluk / Metraj (m)")
        measures.add_widget(self.field(self.input_uzunluk, "Örn: 5.50"))

        self.input_genislik = self.make_input("Genişlik / En (m)")
        measures.add_widget(self.field(self.input_genislik, "Örn: 4.20"))

        self.input_derinlik = self.make_input("Derinlik / Yükseklik (m)", "1")
        measures.add_widget(self.field(self.input_derinlik, "Beton için kullanılır"))
        content.add_widget(measures)

        material = RoundedBox(
            orientation="vertical", size_hint_y=None, height=dp(158),
            padding=[dp(15), dp(12)], spacing=dp(8))
        material.add_widget(self.section_title("MALZEME"))

        self.spinner = Spinner(
            text="1- Hazır Beton (m³)",
            values=(
                "1- Hazır Beton (m³)",
                "2- BİMS 10cm (10x39x18.5)",
                "3- BİMS 15cm (15x39x18.5)",
                "4- BİMS 20cm (20x39x18.5)",
                "5- BİMS 25cm (25x39x18.5)",
                "6- BİMS 30cm (30x39x18.5)",
                "7- Tuğla 8.5cm (8.5x19x19)",
                "8- Tuğla 13.5cm (13.5x19x19)",
                "9- Tuğla 19cm (19x19x19)",
                "10- İzo Tuğla 20cm (20x24x23.5)",
                "11- İzo Tuğla 25cm (25x24x23.5)",
                "12- Yığma Tuğla (20x30x14)",
                "13- Fayans 30x30 cm",
                "14- Fayans 30x60 cm",
                "15- Fayans 40x40 cm",
                "16- Fayans 60x60 cm",
                "17- Fayans 60x120 cm",
                "18- Alçıpan Plakası (120x250 cm)",
                "19- 32. Sınıf Parke (8mm)",
                "20- 33. Sınıf Parke (10-12mm)",
                "21- Şilte Metresi (m²)",
            ),
            size_hint_y=None, height=dp(52),
            font_size=sp(15), color=TEXT,
            background_color=(0.94,0.95,0.97,1))
        material.add_widget(self.spinner)
        material.add_widget(Label(
            text="Fayanslarda %10 fire uygulanır ve paket + adet gösterilir.",
            color=MUTED, font_size=sp(11.5),
            size_hint_y=None, height=dp(38),
            halign="left", valign="middle"))
        content.add_widget(material)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None,
            height=dp(56), spacing=dp(10))
        clear_btn = Button(
            text="TEMİZLE", font_size=sp(15), bold=True,
            background_normal="", background_color=(0.72,0.74,0.78,1),
            color=TEXT)
        clear_btn.bind(on_press=self.temizle)

        calc_btn = Button(
            text="HESAPLA", font_size=sp(18), bold=True,
            background_normal="", background_color=PRIMARY,
            color=(1,1,1,1))
        calc_btn.bind(on_press=self.hesapla)

        buttons.add_widget(clear_btn)
        buttons.add_widget(calc_btn)
        content.add_widget(buttons)

        result = RoundedBox(
            orientation="vertical", size_hint_y=None, height=dp(280),
            padding=[dp(15), dp(12)], spacing=dp(4))
        result.add_widget(self.section_title("SONUÇ"))
        self.lbl_sonuc = Label(
            text="Ölçüleri girip HESAPLA butonuna basın.",
            color=TEXT, font_size=sp(15),
            halign="left", valign="top", markup=True)
        self.lbl_sonuc.bind(size=lambda inst, v: setattr(inst, "text_size", (v[0], v[1])))
        result.add_widget(self.lbl_sonuc)
        content.add_widget(result)

        root.add_widget(content)
        return root

    def section_title(self, text):
        return Label(
            text=f"[b]{text}[/b]", markup=True, color=PRIMARY_DARK,
            font_size=sp(13), size_hint_y=None, height=dp(25),
            halign="left", valign="middle")

    def make_input(self, hint, default=""):
        return TextInput(
            text=default, hint_text=hint,
            foreground_color=TEXT, hint_text_color=MUTED,
            background_normal="", background_color=(0.95,0.96,0.98,1),
            cursor_color=PRIMARY, font_size=sp(17),
            multiline=False, input_filter="float",
            padding=[dp(12), dp(10)],
            size_hint_y=None, height=dp(48))

    def field(self, widget, hint):
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(69), spacing=dp(2))
        box.add_widget(widget)
        box.add_widget(Label(
            text=hint, color=MUTED, font_size=sp(10.5),
            size_hint_y=None, height=dp(18),
            halign="left", valign="middle"))
        return box

    @staticmethod
    def parse_number(value):
        return float(value.strip().replace(",", "."))

    def temizle(self, instance):
        self.input_uzunluk.text = ""
        self.input_genislik.text = ""
        self.input_derinlik.text = "1"
        self.spinner.text = "1- Hazır Beton (m³)"
        self.lbl_sonuc.text = "Ölçüleri girip HESAPLA butonuna basın."

    def hesapla(self, instance):
        try:
            x = self.parse_number(self.input_uzunluk.text)
            y = self.parse_number(self.input_genislik.text)
            z = self.parse_number(self.input_derinlik.text or "1")
            if x <= 0 or y <= 0 or z <= 0:
                raise ValueError

            alan = x * y
            hacim = alan * z
            secim = self.spinner.text

            if secim.startswith("1-"):
                self.lbl_sonuc.text = (
                    f"[b]BETON METRAJI[/b]\n\n"
                    f"Ebatlar: {x:g} m × {y:g} m × {z:g} m\n"
                    f"Net Beton: {hacim:.2f} m³\n"
                    f"Önerilen (%5 fire): [b]{hacim*1.05:.2f} m³[/b]"
                )
            elif "BİMS" in secim:
                net = math.ceil(alan * 12.5)
                self.lbl_sonuc.text = (
                    f"[b]BİMS METRAJI[/b]\n\nDuvar Alanı: {alan:.2f} m²\n"
                    f"Net: {net} adet\nÖnerilen (%7 fire): [b]{math.ceil(net*1.07)} adet[/b]"
                )
            elif any(t in secim for t in ("Tuğla 8.5cm", "Tuğla 13.5cm", "Tuğla 19cm")):
                net = math.ceil(alan * 25)
                self.lbl_sonuc.text = (
                    f"[b]TUĞLA METRAJI[/b]\n\nDuvar Alanı: {alan:.2f} m²\n"
                    f"Net: {net} adet\nÖnerilen (%8 fire): [b]{math.ceil(net*1.08)} adet[/b]"
                )
            elif "İzo Tuğla" in secim:
                net = math.ceil(alan * 16)
                self.lbl_sonuc.text = (
                    f"[b]İZO TUĞLA METRAJI[/b]\n\nDuvar Alanı: {alan:.2f} m²\n"
                    f"Net: {net} adet\nÖnerilen (%8 fire): [b]{math.ceil(net*1.08)} adet[/b]"
                )
            elif "Yığma Tuğla" in secim:
                net = math.ceil(alan * 22)
                self.lbl_sonuc.text = (
                    f"[b]YIĞMA TUĞLA METRAJI[/b]\n\nDuvar Alanı: {alan:.2f} m²\n"
                    f"Net: {net} adet\nÖnerilen (%8 fire): [b]{math.ceil(net*1.08)} adet[/b]"
                )
            elif "Fayans" in secim:
                tile_info = {
                    "30x30": (0.09, 9),
                    "30x60": (0.18, 7),
                    "40x40": (0.16, 6),
                    "60x60": (0.36, 4),
                    "60x120": (0.72, 2),
                }
                size = next(k for k in tile_info if k in secim)
                tile_area, per_package = tile_info[size]
                fire_area = alan * 1.10
                net_tiles = math.ceil(alan / tile_area)
                required_tiles = math.ceil(fire_area / tile_area)
                packages = math.ceil(required_tiles / per_package)
                total_tiles = packages * per_package
                total_area = total_tiles * tile_area
                self.lbl_sonuc.text = (
                    f"[b]FAYANS METRAJI — {size} cm[/b]\n\n"
                    f"Zemin Alanı: {alan:.2f} m²\n"
                    f"Fireli Alan (%10): {fire_area:.2f} m²\n"
                    f"Net Fayans: {net_tiles} adet\n"
                    f"Fayans / Paket: {per_package} adet\n"
                    f"Gereken: [b]{packages} paket[/b]\n"
                    f"Paketlerden Gelen: {total_tiles} adet / {total_area:.2f} m²"
                )
            elif "Alçıpan" in secim:
                n = math.ceil(alan/3)
                self.lbl_sonuc.text = (
                    f"[b]ALÇIPAN METRAJI[/b]\n\nKaplama: {alan:.2f} m²\n"
                    f"Net: {n} plaka\nÖnerilen (%5 fire): [b]{math.ceil(n*1.05)} plaka[/b]"
                )
            elif "32. Sınıf" in secim:
                p = math.ceil((alan*1.10)/1.83)
                self.lbl_sonuc.text = f"[b]PARKE METRAJI[/b]\n\nAlan: {alan:.2f} m²\nGereken: [b]{p} paket[/b]\nToplam: {p*1.83:.2f} m²"
            elif "33. Sınıf" in secim:
                p = math.ceil((alan*1.10)/1.50)
                self.lbl_sonuc.text = f"[b]PARKE METRAJI[/b]\n\nAlan: {alan:.2f} m²\nGereken: [b]{p} paket[/b]\nToplam: {p*1.50:.2f} m²"
            elif "Şilte" in secim:
                m2 = alan*1.05
                rulo = math.ceil(m2/15)
                self.lbl_sonuc.text = f"[b]ŞİLTE METRAJI[/b]\n\nNet: {alan:.2f} m²\nGerekli: {m2:.2f} m²\nRulo (15 m²): [b]{rulo} rulo[/b]"
        except (ValueError, StopIteration):
            self.lbl_sonuc.text = "[b]HATA[/b]\n\nLütfen sıfırdan büyük geçerli ölçüler giriniz."

if __name__ == "__main__":
    HesaplaApp().run()
