# -*- coding: utf-8 -*-
"""Cifciler Insaat v5.1 — Android acilis duzeltmesi, DXF, PDF."""
import math
import os
import traceback
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


def pack(text, miktar, birim, gun=0.0, metraj=None, metraj_birim=None):
    m = float(miktar) if metraj is None else float(metraj)
    mb = birim if metraj_birim is None else metraj_birim
    if metraj_birim and metraj_birim != birim:
        text = text + "\nIscilik metraji: {:.2f} {}".format(m, mb)
    return {
        "text": text, "miktar": float(miktar), "birim": birim, "gun": float(gun),
        "metraj": m, "metraj_birim": mb,
    }


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
        return pack(t, f, "adet", alan / float(usta), alan, "m2")
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
        return pack(t, kutu, "kutu", alan / 14.0, alan, "m2")
    return _fn


def calc_kg(kg_m2, isim, torba=25, usta=18):
    def _fn(a):
        alan = alan_of(a)
        f = alan * kg_m2 * (1 + a["fire"])
        t = "{}\nAlan: {:.2f} m2\nFire dahil: {:.1f} kg\n{} kg torba: {}".format(
            isim, alan, f, torba, _ceil(f / float(torba)))
        return pack(t, f, "kg", alan / float(usta), alan, "m2")
    return _fn


def calc_parke(paket_alani, isim):
    def _fn(a):
        alan = alan_of(a)
        p = _ceil(alan * (1 + a["fire"]) / paket_alani)
        t = "Alan: {:.2f} m2\n{}: {} paket\nToplam: {:.2f} m2".format(
            alan, isim, p, p * paket_alani)
        return pack(t, p, "paket", alan / 22.0, alan, "m2")
    return _fn


def calc_alcipan(a):
    alan = alan_of(a)
    net = _ceil(alan / 3.0)
    f = _ceil(alan * (1 + a["fire"]) / 3.0)
    t = "Alan: {:.2f} m2\nNet: {} plaka\nFire dahil: {} plaka".format(alan, net, f)
    return pack(t, f, "plaka", alan / 18.0, alan, "m2")


def calc_boya(m2_lt, kat, isim):
    def _fn(a):
        alan = alan_of(a)
        lt = alan * kat / float(m2_lt) * (1 + a["fire"])
        t = "{}\nAlan: {:.2f} m2\nFire dahil: {:.2f} litre".format(isim, alan, lt)
        return pack(t, lt, "lt", alan / 45.0, alan, "m2")
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
    return pack("Cati: {:.2f} m2\nKiremit: {} adet".format(alan, f), f, "adet", alan / 18.0, alan, "m2")


def calc_membran(a):
    f = alan_of(a) * (1 + a["fire"])
    return pack("Membran: {:.2f} m2".format(f), f, "m2", f / 50.0)


def calc_osb(a):
    f = _ceil(alan_of(a) * (1 + a["fire"]) / 3.125)
    return pack("OSB 125x250: {} plaka".format(f), f, "plaka", alan_of(a) / 30.0, alan_of(a), "m2")


def calc_mahya(a):
    m = a["x"] * (1 + a["fire"])
    ad = _ceil(m / 0.33)
    return pack("Mahya: {:.2f} m\nAdet: {}".format(m, ad), ad, "adet", m / 40.0, m, "m")


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


def calc_supurgelik(cm):
    def _fn(a):
        boy = max(2 * (a["x"] + a["y"]) - a["open"], 0.0) * (1 + a["fire"])
        t = "Supurgelik {} cm\nBoy: {:.2f} m".format(cm, boy)
        return pack(t, boy, "m", boy / 40.0)
    return _fn


def calc_silte(a):
    alan = alan_of(a) * (1 + a["fire"])
    r = _ceil(alan / 15.0)
    t = "Silte: {:.2f} m2\nRulo 15 m2: {}".format(alan, r)
    return pack(t, r, "rulo", alan / 80.0, alan, "m2")


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
    "Supurgelik": {
        "Supurgelik 10cm": calc_supurgelik(10),
        "Supurgelik 15cm": calc_supurgelik(15),
        "Supurgelik 20cm": calc_supurgelik(20),
        "Supurgelik 30cm": calc_supurgelik(30),
    },
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
    "Hafriyat": "Uzunluk x genislik x derinlik. Iscilik TL/m3 (kazi/nakliye).",
    "Beton ve Sap": "Hacim icin 3 olcu. Sap kalinligi ornek: 0.05 (5 cm).",
    "Beton Karisim": "Santiye karişimi. 3 olcu ile m3.",
    "BIMS": "Duvar uzunlugu x yukseklik. Kapi/pencere m2 dusulur.",
    "Tugla": "Duvar uzunlugu x yukseklik. Kapi/pencere m2 dusulur.",
    "Fayans": "Alan. Istersen bosluk dus. Iscilik TL/m2, malzeme TL/kutu.",
    "Yapistirici Derz": "Alan. Malzeme TL/kg, iscilik TL/m2.",
    "Parke": "Oda alani. Malzeme paket/rulo, iscilik TL/m2.",
    "Alcipan": "Alan. Plaka veya kg.",
    "Siva ve Boya": "Duvar/tavan alani. Kapi-pencere dusulur.",
    "Mantolama": "Cephe alani. Pencere dusumu m2.",
    "Cati": "Kiremit/OSB/membran: alan. Mahya ve oluk: sadece metre.",
    "Demir": "Cubuk boyu ve adet. Fiyat TL/kg.",
    "Kapi Pencere": "En, boy, adet.",
    "Supurgelik": "Oda eni x boyu. Kapi eni dusulur. Sonuc: supurgelik boyu.",
    "Tesisat": "Boru: metre. Dirsek/te/nokta: adet.",
    "Elektrik": "Kablo/oluklu: metre. Priz/anahtar: adet.",
    "Sarf": "Sadece adet ve malzeme fiyati.",
}


def form_spec(cat, mat):
    """open: None | 'm2' | 'kapi_en'   z_unit: None | 'm' | 'cm'"""
    def f(x=None, y=None, z=None, open_=None, malzeme=None, iscilik=None, z_unit=None):
        return {
            "x": x, "y": y, "z": z, "open": open_,
            "malzeme": malzeme, "iscilik": iscilik, "z_unit": z_unit,
        }

    if cat == "Hafriyat":
        if mat == "Grobeton":
            return f("Uzunluk (m)", "Genislik (m)", "Kalinlik", None, None, "Iscilik / nakliye (TL/m3)", "cm")
        return f("Uzunluk (m)", "Genislik (m)", "Derinlik", None, None, "Iscilik / nakliye (TL/m3)", "m")
    if cat == "Beton ve Sap":
        if mat == "Kalip":
            return f("Uzunluk (m)", "Genislik (m)", None, None, "Kalip (TL/m2)", "Iscilik (TL/m2)")
        if mat == "Sap":
            return f("Uzunluk (m)", "Genislik (m)", "Kalinlik", None, "Sap (TL/m3)", "Iscilik (TL/m3)", "cm")
        return f("Uzunluk (m)", "Genislik (m)", "Kalinlik / yukseklik", None, "Beton (TL/m3)", "Iscilik (TL/m3)", "cm")
    if cat == "Beton Karisim":
        return f("Uzunluk (m)", "Genislik (m)", "Kalinlik", None, "Beton (TL/m3)", "Iscilik (TL/m3)", "cm")
    if cat in ("BIMS", "Tugla"):
        return f("Duvar uzunlugu (m)", "Duvar yuksekligi (m)", None, "m2", "Malzeme (TL/adet)", "Iscilik (TL/m2)")
    if cat == "Fayans":
        return f("Uzunluk (m)", "Genislik (m)", None, "m2", "Malzeme (TL/kutu)", "Iscilik (TL/m2)")
    if cat == "Yapistirici Derz":
        return f("Uzunluk (m)", "Genislik (m)", None, "m2", "Malzeme (TL/kg)", "Iscilik (TL/m2)")
    if cat == "Parke":
        mal = "Malzeme (TL/rulo)" if mat == "Silte" else "Malzeme (TL/paket)"
        return f("Uzunluk (m)", "Genislik (m)", None, "m2", mal, "Iscilik (TL/m2)")
    if cat == "Alcipan":
        mal = "Malzeme (TL/kg)" if "pasta" in mat.lower() else "Malzeme (TL/plaka)"
        return f("Uzunluk (m)", "Genislik (m)", None, "m2", mal, "Iscilik (TL/m2)")
    if cat == "Siva ve Boya":
        mal = "Boya (TL/lt)" if "boya" in mat.lower() else "Malzeme (TL/kg)"
        return f("Uzunluk (m)", "Yukseklik / genislik (m)", None, "m2", mal, "Iscilik (TL/m2)")
    if cat == "Mantolama":
        return f("Uzunluk (m)", "Yukseklik (m)", None, "m2", "Malzeme (TL/m2)", "Iscilik (TL/m2)")
    if cat == "Cati":
        if mat in ("Mahya", "Yagmur olugu"):
            mal = "Malzeme (TL/adet)" if mat == "Mahya" else "Malzeme (TL/m)"
            return f("Metre", None, None, None, mal, "Iscilik (TL/m)")
        if mat == "Marsilya kiremit":
            mal = "Malzeme (TL/adet)"
        elif mat == "OSB":
            mal = "Malzeme (TL/plaka)"
        else:
            mal = "Malzeme (TL/m2)"
        return f("Uzunluk (m)", "Genislik (m)", None, None, mal, "Iscilik (TL/m2)")
    if cat == "Demir":
        return f("Cubuk boyu (m)", "Adet", None, None, "Demir (TL/kg)", "Iscilik (TL/kg)")
    if cat == "Kapi Pencere":
        return f("En (m)", "Adet", "Boy", None, "Malzeme (TL/m2)", "Iscilik (TL/m2)", "m")
    if cat == "Supurgelik":
        return f("Oda eni (m)", "Oda boyu (m)", None, "kapi_en", "Malzeme (TL/m)", "Iscilik (TL/m)")
    if cat == "Tesisat":
        if mat in ("Dirsek", "Te", "Tesisat noktasi"):
            return f(None, "Adet", None, None, "Malzeme (TL/adet)", "Iscilik (TL/adet)")
        return f("Boru (m)", None, None, None, "Malzeme (TL/m)", "Iscilik (TL/m)")
    if cat == "Elektrik":
        if mat in ("Priz", "Anahtar"):
            return f(None, "Adet", None, None, "Malzeme (TL/adet)", "Iscilik (TL/adet)")
        return f("Metre", None, None, None, "Malzeme (TL/m)", "Iscilik (TL/m)")
    if cat == "Sarf":
        return f(None, "Adet", None, None, "Malzeme (TL/adet)", None)
    return f("Uzunluk (m)", "Genislik (m)", "Derinlik", None, "Malzeme (TL)", "Iscilik (TL)", "m")


def cart_item(kat, malzeme, res, mahal=""):
    text = res["text"]
    if mahal:
        text = "[{}]\n{}".format(mahal, text)
    return {
        "kat": kat, "malzeme": malzeme, "sonuc": text,
        "miktar": res["miktar"], "birim": res["birim"],
        "metraj": res.get("metraj", res["miktar"]),
        "metraj_birim": res.get("metraj_birim", res["birim"]),
        "malzeme_tutar": 0.0, "iscilik_tutar": 0.0, "kdv": 0.0, "genel": 0.0,
        "mahal": mahal,
    }


def mahal_wall_args(m, fire):
    opn = m.get("ke", 0) * m.get("kb", 0) + m.get("pe", 0) * m.get("pb", 0)
    return {"x": 2 * (m["en"] + m["boy"]), "y": m["h"], "z": 1.0, "open": opn, "fire": fire}


def mahal_floor_args(m, fire):
    return {"x": m["en"], "y": m["boy"], "z": 1.0, "open": 0.0, "fire": fire}


def mahal_sup_args(m, fire):
    return {"x": m["en"], "y": m["boy"], "z": 1.0, "open": m.get("ke", 0), "fire": fire}


def run_mahal_paket(m, picks, fire):
    items = []
    name = m.get("ad", "Mahal")
    wall = mahal_wall_args(m, fire)
    floor = mahal_floor_args(m, fire)
    sup = mahal_sup_args(m, fire)

    def add(kat, mat, args):
        fn = CATEGORIES.get(kat, {}).get(mat)
        if not fn:
            return
        try:
            items.append(cart_item(kat, mat, fn(args), name))
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            return

    if picks.get("duvar"):
        kat, mat = picks["duvar"]
        add(kat, mat, wall)
    if picks.get("siva"):
        add("Siva ve Boya", picks["siva"], wall)
    if picks.get("saten"):
        add("Siva ve Boya", picks["saten"], wall)
    if picks.get("boya"):
        add("Siva ve Boya", picks["boya"], wall)
    if picks.get("zemin"):
        kat, mat = picks["zemin"]
        add(kat, mat, floor)
        if kat == "Fayans":
            add("Yapistirici Derz", "Seramik yapistirici", floor)
            add("Yapistirici Derz", "Derz dolgu", floor)
        if kat == "Parke" and mat != "Silte":
            add("Parke", "Silte", floor)
    if picks.get("tavan"):
        add("Alcipan", picks["tavan"], floor)
    if picks.get("sup"):
        add("Supurgelik", picks["sup"], sup)
    return items


def aggregate_list(cart):
    agg = {}
    order = []
    for it in cart:
        key = (it.get("kat", ""), it.get("malzeme", ""), it.get("birim", ""))
        if key not in agg:
            agg[key] = {
                "miktar": 0.0, "metraj": 0.0,
                "mb": it.get("metraj_birim", it.get("birim", "")),
                "mal": 0.0, "isc": 0.0,
            }
            order.append(key)
        agg[key]["miktar"] += float(it.get("miktar") or 0)
        agg[key]["metraj"] += float(it.get("metraj") or 0)
        agg[key]["mal"] += float(it.get("malzeme_tutar") or 0)
        agg[key]["isc"] += float(it.get("iscilik_tutar") or 0)
    return order, agg


def format_liste(cart, proje=""):
    if not cart:
        return "Liste bos. Mahal paketi veya metrajdan kalem ekle."
    lines = ["CIFCILER INSAAT v5.1", "MALZEME LISTESI"]
    if proje:
        lines.append("Proje: " + proje)
    lines.append(datetime.now().strftime("%d.%m.%Y %H:%M"))
    lines.append("")
    order, agg = aggregate_list(cart)
    last_kat = None
    m_tot = i_tot = 0.0
    for kat, mat, birim in order:
        if kat != last_kat:
            lines.append("-- {} --".format(kat))
            last_kat = kat
        a = agg[(kat, mat, birim)]
        lines.append("  {}: {:.2f} {}".format(mat, a["miktar"], birim))
        m_tot += a["mal"]
        i_tot += a["isc"]
    lines.append("")
    lines.append("==== TOPLAM ====")
    if m_tot or i_tot:
        lines.append("Malzeme: {:.2f} TL".format(m_tot))
        lines.append("Iscilik: {:.2f} TL".format(i_tot))
        lines.append("GENEL: {:.2f} TL".format(m_tot + i_tot))
    lines.append("Kalem: {}".format(len(cart)))
    return "\n".join(lines)


def _ascii_tr(s):
    rep = {
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U",
        "×": "x", "–": "-", "—": "-", "•": "-",
    }
    out = []
    for ch in s or "":
        ch = rep.get(ch, ch)
        o = ord(ch)
        out.append(ch if 32 <= o < 127 else "?")
    return "".join(out)


def write_simple_pdf(filepath, text, title="Cifciler Insaat"):
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    rows = [_ascii_tr(title), datetime.now().strftime("%d.%m.%Y %H:%M"), ""]
    rows += [_ascii_tr(x)[:92] for x in (text or "").split("\n")]
    per = 48
    chunks = [rows[i:i + per] for i in range(0, max(len(rows), 1), per)] or [[""]]
    streams = []
    for ch in chunks:
        parts = ["BT", "/F1 11 Tf", "50 800 Td", "14 TL"]
        for i, line in enumerate(ch):
            cmd = "({}) Tj".format(esc(line or " "))
            parts.append(cmd if i == 0 else "T* " + cmd)
        parts.append("ET")
        streams.append("\n".join(parts).encode("latin-1"))

    n = len(streams)
    page_ids = [4 + i for i in range(n)]
    cont_ids = [4 + n + i for i in range(n)]
    bodies = []
    bodies.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join("%d 0 R" % i for i in page_ids)
    bodies.append(("<< /Type /Pages /Count %d /Kids [%s] >>" % (n, kids)).encode("ascii"))
    bodies.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for cid in cont_ids:
        bodies.append((
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            "/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>"
        ) % cid)
    for st in streams:
        bodies.append(b"<< /Length %d >>\nstream\n" % len(st) + st + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(bodies, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i
        out += body if isinstance(body, (bytes, bytearray)) else body.encode("latin-1")
        out += b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(bodies) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(bodies) + 1, xref)
    folder = os.path.dirname(filepath)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(out)
    return filepath


def pdf_target(name="cifciler_liste.pdf"):
    cands = []
    try:
        from android.storage import primary_external_storage_path
        cands.append(os.path.join(primary_external_storage_path(), "Download", name))
    except Exception:
        pass
    cands.append("/storage/emulated/0/Download/" + name)
    try:
        app = App.get_running_app()
        if app:
            cands.append(os.path.join(app.user_data_dir, name))
    except Exception:
        pass
    cands.append(os.path.join(os.getcwd(), name))
    cands.append(os.path.join("/tmp", name))
    for path in cands:
        folder = os.path.dirname(path) or "."
        try:
            os.makedirs(folder, exist_ok=True)
            test = path + ".tmp"
            with open(test, "wb") as f:
                f.write(b"0")
            os.remove(test)
            return path
        except Exception:
            continue
    return name


def export_liste_pdf(cart, proje=""):
    text = format_liste(cart, proje)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe = _ascii_tr(proje or "liste").replace(" ", "_")[:24] or "liste"
    path = pdf_target("Cifciler_{}_{}.pdf".format(safe, stamp))
    write_simple_pdf(path, text, title="Cifciler Insaat v5.1")
    return path, text


def _shoelace(pts):
    n = len(pts)
    s = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) * 0.5


def parse_dxf(text):
    """ASCII DXF icinden kapali polyline mahal cikar. DWG/binary olmaz."""
    head = text[:80]
    if "AutoCAD Binary" in head or head.startswith("AC10"):
        raise ValueError("Bu DWG/binary. AutoCAD: Farkli Kaydet -> DXF (ASCII).")
    raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    pairs = []
    i = 0
    while i + 1 < len(raw):
        try:
            code = int(raw[i].strip())
        except ValueError:
            i += 1
            continue
        pairs.append((code, raw[i + 1].strip()))
        i += 2

    polys = []
    i = 0
    n = len(pairs)
    while i < n:
        code, val = pairs[i]
        if code == 0 and val.upper() == "LWPOLYLINE":
            layer, closed, pts = "Mahal", False, []
            i += 1
            while i < n and pairs[i][0] != 0:
                c, v = pairs[i]
                if c == 8:
                    layer = v
                elif c == 70:
                    try:
                        closed = bool(int(float(v)) & 1)
                    except ValueError:
                        pass
                elif c == 10:
                    try:
                        x = float(v.replace(",", "."))
                    except ValueError:
                        x = 0.0
                    y = 0.0
                    if i + 1 < n and pairs[i + 1][0] == 20:
                        try:
                            y = float(pairs[i + 1][1].replace(",", "."))
                        except ValueError:
                            y = 0.0
                        i += 1
                    pts.append((x, y))
                i += 1
            if closed and len(pts) >= 3:
                polys.append((layer, pts))
            continue
        if code == 0 and val.upper() == "POLYLINE":
            layer, closed, pts = "Mahal", False, []
            i += 1
            while i < n:
                c, v = pairs[i]
                if c == 0 and v.upper() == "SEQEND":
                    i += 1
                    break
                if c == 0 and v.upper() == "VERTEX":
                    i += 1
                    vx = vy = None
                    while i < n and pairs[i][0] != 0:
                        if pairs[i][0] == 10:
                            try:
                                vx = float(pairs[i][1].replace(",", "."))
                            except ValueError:
                                vx = 0.0
                        elif pairs[i][0] == 20:
                            try:
                                vy = float(pairs[i][1].replace(",", "."))
                            except ValueError:
                                vy = 0.0
                        i += 1
                    if vx is not None and vy is not None:
                        pts.append((vx, vy))
                    continue
                if c == 8:
                    layer = v
                elif c == 70:
                    try:
                        closed = bool(int(float(v)) & 1)
                    except ValueError:
                        pass
                i += 1
            if len(pts) >= 3:
                dx = pts[0][0] - pts[-1][0]
                dy = pts[0][1] - pts[-1][1]
                if closed or (dx * dx + dy * dy) < 1e-2:
                    polys.append((layer, pts))
            continue
        i += 1

    spans = []
    for _, pts in polys:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        spans.append(max(max(xs) - min(xs), max(ys) - min(ys)))
    scale = 1.0
    if spans:
        med = sorted(spans)[len(spans) // 2]
        if med > 200:
            scale = 0.001
        elif med > 60:
            scale = 0.01

    mahals = []
    for idx, (layer, pts) in enumerate(polys, 1):
        pts_m = [(x * scale, y * scale) for x, y in pts]
        xs = [p[0] for p in pts_m]
        ys = [p[1] for p in pts_m]
        en = max(xs) - min(xs)
        boy = max(ys) - min(ys)
        alan = _shoelace(pts_m)
        if alan < 1.5 or alan > 400 or en < 1.2 or boy < 1.2:
            continue
        ad = layer if layer and layer.upper() not in ("0", "DEFPOINTS", "MAHAL") else "Mahal {}".format(len(mahals) + 1)
        mahals.append({
            "ad": ad, "en": round(en, 2), "boy": round(boy, 2), "h": 2.70,
            "ke": 0.0, "kb": 0.0, "pe": 0.0, "pb": 0.0,
            "alan": round(alan, 2),
        })
    mahals.sort(key=lambda m: m["ad"])
    return mahals


DEFAULT_PAKET = {
    "duvar": ("BIMS", "BIMS 20cm"),
    "siva": "Alci siva",
    "saten": "Saten alci",
    "boya": "Ic cephe boya 2 kat",
    "zemin": ("Fayans", "60x60 fayans"),
    "tavan": "Alcipan 120x250",
    "sup": "Supurgelik 10cm",
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
        box.add_widget(ui_label("v5.1  •  DXF + PDF malzeme listesi", 13, 28))
        box.add_widget(ui_btn("CAD / DXF YUKLE", self.go_cad, 50, 17))
        box.add_widget(ui_btn("MAHALLER", self.go_mahal, 50, 17))
        box.add_widget(ui_btn("MALZEME LISTESI", self.go_liste, 50, 17))
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

    def go_cad(self, _inst):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "cad"

    def go_mahal(self, _inst):
        self.manager.get_screen("mahal").refresh()
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "mahal"

    def go_liste(self, _inst):
        self.manager.get_screen("liste").refresh()
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "liste"

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
        self.lab_x, self.in_x = self._field(box, "Uzunluk (m)")
        self.lab_y, self.in_y = self._field(box, "Genislik (m)")
        zrow = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(8))
        self.lab_z = ui_label("Derinlik", 13, 22)
        zrow.add_widget(self.lab_z)
        self.sp_zunit = Spinner(
            text="metre", values=["metre", "cm"],
            size_hint_x=0.42, size_hint_y=None, height=dp(22), font_size=sp(12))
        zrow.add_widget(self.sp_zunit)
        box.add_widget(zrow)
        self.zrow = zrow
        self.in_z = TextInput(
            text="1", input_filter="float", multiline=False, font_size=sp(18),
            size_hint_y=None, height=dp(46), padding=[dp(10), dp(8)])
        box.add_widget(self.in_z)
        self.lab_kapi = ui_label("KAPI (en x boy, m)", 13, 22)
        box.add_widget(self.lab_kapi)
        krow = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.in_ke = TextInput(text="", hint_text="en", input_filter="float", multiline=False, font_size=sp(16), padding=[dp(8), dp(8)])
        self.in_kb = TextInput(text="", hint_text="boy", input_filter="float", multiline=False, font_size=sp(16), padding=[dp(8), dp(8)])
        krow.add_widget(self.in_ke)
        krow.add_widget(self.in_kb)
        box.add_widget(krow)
        self.krow = krow
        self.lab_pen = ui_label("PENCERE (en x boy, m)", 13, 22)
        box.add_widget(self.lab_pen)
        prow = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.in_pe = TextInput(text="", hint_text="en", input_filter="float", multiline=False, font_size=sp(16), padding=[dp(8), dp(8)])
        self.in_pb = TextInput(text="", hint_text="boy", input_filter="float", multiline=False, font_size=sp(16), padding=[dp(8), dp(8)])
        prow.add_widget(self.in_pe)
        prow.add_widget(self.in_pb)
        box.add_widget(prow)
        self.prow = prow
        box.add_widget(ui_label("MALZEME / FIRE / FIYAT", 15, 28, True))
        self.spinner = Spinner(text="", values=[], size_hint_y=None, height=dp(50), font_size=sp(14))
        self.spinner.bind(text=self._on_mat)
        box.add_widget(self.spinner)
        self.sp_fire = Spinner(
            text="%10 Fire", values=["%5 Fire", "%10 Fire", "%15 Fire"],
            size_hint_y=None, height=dp(46), font_size=sp(14))
        box.add_widget(self.sp_fire)
        self.lab_fm, self.in_fiyat_m = self._field(box, "Malzeme fiyati", "0")
        self.lab_fi, self.in_fiyat_i = self._field(box, "Iscilik metraj fiyati", "0")
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
        lab = ui_label(caption, 13, 22)
        box.add_widget(lab)
        f = TextInput(
            text=default, input_filter="float", multiline=False, font_size=sp(18),
            size_hint_y=None, height=dp(46), padding=[dp(10), dp(8)])
        box.add_widget(f)
        return lab, f

    def _toggle(self, lab, inp, label, fallback):
        if label:
            lab.text = label
            lab.height = dp(22)
            lab.opacity = 1
            inp.disabled = False
            inp.opacity = 1
            inp.height = dp(46)
        else:
            lab.text = ""
            lab.height = 0
            lab.opacity = 0
            inp.disabled = True
            inp.opacity = 0
            inp.height = 0
            inp.text = fallback

    def _toggle_row(self, lab, row, show, lab_text=""):
        if show:
            lab.text = lab_text
            lab.height = dp(22)
            lab.opacity = 1
            row.height = dp(46)
            row.opacity = 1
            row.disabled = False
        else:
            lab.text = ""
            lab.height = 0
            lab.opacity = 0
            row.height = 0
            row.opacity = 0
            row.disabled = True

    def apply_form(self):
        if not getattr(self, "spinner", None) or not self.spinner.text:
            return
        spec = form_spec(self.category, self.spinner.text)
        self._toggle(self.lab_x, self.in_x, spec["x"], "")
        self._toggle(self.lab_y, self.in_y, spec["y"], "")
        if spec["z"]:
            self.lab_z.text = spec["z"]
            self.lab_z.height = dp(22)
            self.lab_z.opacity = 1
            self.zrow.height = dp(22)
            self.zrow.opacity = 1
            self.sp_zunit.opacity = 1
            self.sp_zunit.disabled = False
            self.in_z.disabled = False
            self.in_z.opacity = 1
            self.in_z.height = dp(46)
            unit = spec.get("z_unit") or "m"
            self.sp_zunit.text = "cm" if unit == "cm" else "metre"
        else:
            self.lab_z.text = ""
            self.lab_z.height = 0
            self.zrow.height = 0
            self.zrow.opacity = 0
            self.sp_zunit.opacity = 0
            self.sp_zunit.disabled = True
            self.in_z.disabled = True
            self.in_z.opacity = 0
            self.in_z.height = 0
            self.in_z.text = "1"
        om = spec["open"]
        self._toggle_row(self.lab_kapi, self.krow, om in ("m2", "kapi_en"),
                         "KAPI ENI (m)" if om == "kapi_en" else "KAPI (en x boy, m)")
        self._toggle_row(self.lab_pen, self.prow, om == "m2", "PENCERE (en x boy, m)")
        if om == "m2":
            self.in_kb.size_hint_x = 1
            self.in_kb.opacity = 1
            self.in_kb.disabled = False
        else:
            self.in_kb.size_hint_x = 0
            self.in_kb.width = 0
            self.in_kb.opacity = 0
            self.in_kb.disabled = True
            self.in_kb.text = ""
            self.in_pe.text = ""
            self.in_pb.text = ""
        self._toggle(self.lab_fm, self.in_fiyat_m, spec["malzeme"], "0")
        self._toggle(self.lab_fi, self.in_fiyat_i, spec["iscilik"], "0")

    def _on_mat(self, _inst, _val):
        if not self.spinner.text:
            return
        self.apply_form()

    def set_category(self, cat):
        app = App.get_running_app()
        self.category = cat
        self.materials = CATEGORIES[cat]
        keys = list(self.materials.keys())
        self.lbl_baslik.text = "[b]{}[/b]".format(cat.upper())
        self.lbl_hint.text = HINTS.get(cat, "")
        self.spinner.values = keys
        self.spinner.text = keys[0]
        self.sp_fire.text = app.fire_label
        self.apply_form()
        spec = form_spec(cat, keys[0])
        self.in_x.text = "" if spec["x"] else self.in_x.text
        self.in_y.text = "" if spec["y"] else self.in_y.text
        if spec["z"]:
            if spec.get("z_unit") == "cm":
                self.in_z.text = "5" if "Sap" in keys[0] else "15"
            else:
                self.in_z.text = "1"
        self.in_ke.text = ""
        self.in_kb.text = ""
        self.in_pe.text = ""
        self.in_pb.text = ""
        self.in_fiyat_m.text = "0"
        self.in_fiyat_i.text = "0"
        self.last = None
        self.lbl_sonuc.text = "Olcu gir, HESAPLA'ya bas."

    def go_menu(self, _inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def _fire(self):
        return {"%5 Fire": 0.05, "%10 Fire": 0.10, "%15 Fire": 0.15}.get(self.sp_fire.text, 0.10)

    def _args(self):
        spec = form_spec(self.category, self.spinner.text)
        x = _num(self.in_x.text)
        y = _num(self.in_y.text)
        z_raw = _num(self.in_z.text, 1.0)
        if spec["z"] and self.sp_zunit.text == "cm":
            z = z_raw / 100.0
        elif spec["z"]:
            z = z_raw
        else:
            z = 1.0
        om = spec["open"]
        if om == "m2":
            opn = _num(self.in_ke.text) * _num(self.in_kb.text) + _num(self.in_pe.text) * _num(self.in_pb.text)
        elif om == "kapi_en":
            opn = _num(self.in_ke.text)
        else:
            opn = 0.0
        return {"x": x, "y": y, "z": z, "open": opn, "fire": self._fire()}

    def hesapla(self, _inst):
        app = App.get_running_app()
        try:
            args = self._args()
            res = self.materials[self.spinner.text](args)
            if res["miktar"] <= 0:
                raise ValueError
            fm = _num(self.in_fiyat_m.text) if form_spec(self.category, self.spinner.text)["malzeme"] else 0.0
            fi = _num(self.in_fiyat_i.text) if form_spec(self.category, self.spinner.text)["iscilik"] else 0.0
            spec = form_spec(self.category, self.spinner.text)
            mal = res["miktar"] * fm
            met = res.get("metraj", res["miktar"])
            mb = res.get("metraj_birim", res["birim"])
            isc = met * fi
            ara = mal + isc
            kdv = ara * app.kdv if app.kdv_on else 0.0
            extra = ""
            if args.get("open", 0) > 0 and spec["open"] == "m2":
                extra += "\nDusum: {:.2f} m2".format(args["open"])
            if args.get("open", 0) > 0 and spec["open"] == "kapi_en":
                extra += "\nKapi dusumu: {:.2f} m".format(args["open"])
            if spec["z"] and self.sp_zunit.text == "cm":
                extra += "\nKalinlik: {:.0f} cm".format(args["z"] * 100)
            if res.get("gun", 0) > 0:
                extra += "\nUsta gunu (tahmini): {:.1f}".format(res["gun"])
            if fm or fi:
                extra += "\n---"
                if spec["malzeme"]:
                    extra += "\nMalzeme: {:.2f} {} x {:.2f} = {:.2f} TL".format(
                        res["miktar"], res["birim"], fm, mal)
                if spec["iscilik"]:
                    extra += "\nIscilik: {:.2f} {} x {:.2f} = {:.2f} TL".format(met, mb, fi, isc)
                extra += "\nAra toplam: {:.2f} TL".format(ara)
                if app.kdv_on:
                    extra += "\nKDV %20: {:.2f} TL\nGenel: {:.2f} TL".format(kdv, ara + kdv)
            text = res["text"] + extra
            self.lbl_sonuc.text = text
            self.last = {
                "kat": self.category, "malzeme": self.spinner.text, "sonuc": text,
                "miktar": res["miktar"], "birim": res["birim"],
                "metraj": met, "metraj_birim": mb,
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
        spec = form_spec(self.category, self.spinner.text)
        if spec["x"]:
            self.in_x.text = ""
        if spec["y"]:
            self.in_y.text = ""
        if spec["z"]:
            self.in_z.text = "5" if spec.get("z_unit") == "cm" and "Sap" in self.spinner.text else (
                "15" if spec.get("z_unit") == "cm" else "1")
        self.in_ke.text = ""
        self.in_kb.text = ""
        self.in_pe.text = ""
        self.in_pb.text = ""
        if spec["malzeme"]:
            self.in_fiyat_m.text = "0"
        if spec["iscilik"]:
            self.in_fiyat_i.text = "0"
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
        lines = ["CIFCILER INSAAT v5.1", datetime.now().strftime("%d.%m.%Y %H:%M"), ""]
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


class MahalScreen(Screen):
    def __init__(self, **kwargs):
        super(MahalScreen, self).__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.add_widget(ui_label("MAHALLER", 22, 40, True))
        root.add_widget(ui_btn("< ANA MENU", self.go_menu, 44, 15))
        self.in_proje = TextInput(
            hint_text="Proje adi", multiline=False, font_size=sp(16),
            size_hint_y=None, height=dp(44), padding=[dp(10), dp(8)])
        root.add_widget(self.in_proje)
        self.in_ad = TextInput(
            hint_text="Mahal adi (Salon, Mutfak...)", multiline=False, font_size=sp(16),
            size_hint_y=None, height=dp(44), padding=[dp(10), dp(8)])
        root.add_widget(self.in_ad)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.in_en = TextInput(hint_text="en m", input_filter="float", multiline=False, font_size=sp(15), padding=[dp(8), dp(8)])
        self.in_boy = TextInput(hint_text="boy m", input_filter="float", multiline=False, font_size=sp(15), padding=[dp(8), dp(8)])
        self.in_h = TextInput(hint_text="yukseklik m", input_filter="float", multiline=False, font_size=sp(15), padding=[dp(8), dp(8)])
        row.add_widget(self.in_en)
        row.add_widget(self.in_boy)
        row.add_widget(self.in_h)
        root.add_widget(row)
        root.add_widget(ui_label("Kapi en x boy (m)", 13, 20))
        krow = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.in_ke = TextInput(hint_text="kapi en", input_filter="float", multiline=False, font_size=sp(15), padding=[dp(8), dp(8)])
        self.in_kb = TextInput(hint_text="kapi boy", input_filter="float", multiline=False, font_size=sp(15), padding=[dp(8), dp(8)])
        krow.add_widget(self.in_ke)
        krow.add_widget(self.in_kb)
        root.add_widget(krow)
        root.add_widget(ui_label("Pencere en x boy (m)", 13, 20))
        prow = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.in_pe = TextInput(hint_text="pencere en", input_filter="float", multiline=False, font_size=sp(15), padding=[dp(8), dp(8)])
        self.in_pb = TextInput(hint_text="pencere boy", input_filter="float", multiline=False, font_size=sp(15), padding=[dp(8), dp(8)])
        prow.add_widget(self.in_pe)
        prow.add_widget(self.in_pb)
        root.add_widget(prow)
        root.add_widget(ui_btn("MAHAL EKLE", self.ekle, 48, 16))
        sc = ScrollView(do_scroll_x=False)
        self.list_box = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        sc.add_widget(self.list_box)
        root.add_widget(sc)
        self.add_widget(root)

    def go_menu(self, _inst):
        App.get_running_app().proje = self.in_proje.text.strip()
        App.get_running_app().save_mahals()
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def ekle(self, _inst):
        ad = (self.in_ad.text or "").strip() or "Mahal"
        en, boy, h = _num(self.in_en.text), _num(self.in_boy.text), _num(self.in_h.text, 2.7)
        if en <= 0 or boy <= 0 or h <= 0:
            return
        app = App.get_running_app()
        app.proje = self.in_proje.text.strip()
        app.mahals.append({
            "ad": ad, "en": en, "boy": boy, "h": h,
            "ke": _num(self.in_ke.text), "kb": _num(self.in_kb.text),
            "pe": _num(self.in_pe.text), "pb": _num(self.in_pb.text),
        })
        app.save_mahals()
        self.in_ad.text = ""
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.in_proje.text = app.proje
        self.list_box.clear_widgets()
        if not app.mahals:
            self.list_box.add_widget(ui_label("Henuz mahal yok.", 14, 36))
            return
        for i, m in enumerate(app.mahals):
            txt = "{}  {:.2f}x{:.2f}x{:.2f} m".format(m["ad"], m["en"], m["boy"], m["h"])
            self.list_box.add_widget(ui_label(txt, 14, 28, True))
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            row.add_widget(ui_btn("PAKET", self._paket(i), 44, 14))
            row.add_widget(ui_btn("SIL", self._sil(i), 44, 14))
            self.list_box.add_widget(row)

    def _paket(self, idx):
        def _h(_inst):
            self.manager.get_screen("paket").set_mahal(idx)
            self.manager.transition = SlideTransition(direction="left")
            self.manager.current = "paket"
        return _h

    def _sil(self, idx):
        def _h(_inst):
            app = App.get_running_app()
            if 0 <= idx < len(app.mahals):
                app.mahals.pop(idx)
                app.save_mahals()
                self.refresh()
        return _h


class PaketScreen(Screen):
    def __init__(self, **kwargs):
        super(PaketScreen, self).__init__(**kwargs)
        self.idx = 0
        scroll = ScrollView(do_scroll_x=False)
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        self.lbl = ui_label("PAKET", 22, 40, True)
        box.add_widget(self.lbl)
        box.add_widget(ui_btn("< MAHALLER", self.go_back, 44, 15))
        box.add_widget(ui_label("Duvar, zemin, siva... sec. Yok birakilanlar eklenmez.", 13, 40))
        duvar = ["Yok"] + ["BIMS / " + k for k in CATEGORIES["BIMS"]] + ["Tugla / " + k for k in CATEGORIES["Tugla"]]
        zemin = ["Yok"] + ["Fayans / " + k for k in CATEGORIES["Fayans"]] + ["Parke / " + k for k in CATEGORIES["Parke"] if k != "Silte"]
        self.sp_duvar = self._spin(box, "Duvar", duvar)
        self.sp_siva = self._spin(box, "Siva", ["Yok", "Cimento sivasi", "Alci siva"])
        self.sp_saten = self._spin(box, "Saten", ["Yok", "Saten alci"])
        self.sp_boya = self._spin(box, "Boya", ["Yok", "Ic cephe boya 2 kat"])
        self.sp_zemin = self._spin(box, "Zemin", zemin)
        self.sp_tavan = self._spin(box, "Tavan", ["Yok", "Alcipan 120x250"])
        self.sp_sup = self._spin(box, "Supurgelik", ["Yok"] + list(CATEGORIES["Supurgelik"].keys()))
        box.add_widget(ui_btn("LISTEYE EKLE", self.uygula, 52, 16))
        box.add_widget(ui_btn("TUM MAHALLERE UYGULA", self.uygula_hepsi, 52, 16))
        self.lbl_sonuc = Label(
            text="", font_size=sp(14), size_hint_y=None, height=dp(220),
            halign="left", valign="top", color=(0.95, 0.94, 0.90, 1))
        self.lbl_sonuc.bind(size=lambda i, v: setattr(i, "text_size", v))
        box.add_widget(self.lbl_sonuc)
        scroll.add_widget(box)
        self.add_widget(scroll)

    def _spin(self, box, caption, values):
        box.add_widget(ui_label(caption, 13, 22))
        sp = Spinner(text=values[0], values=values, size_hint_y=None, height=dp(46), font_size=sp(14))
        box.add_widget(sp)
        return sp

    def set_mahal(self, idx):
        self.idx = idx
        app = App.get_running_app()
        m = app.mahals[idx]
        self.lbl.text = "[b]PAKET — {}[/b]".format(m["ad"])
        self.lbl_sonuc.text = "{:.2f} x {:.2f} x {:.2f} m\nDuvar+zemin+siva+boya sec, LISTEYE EKLE.".format(
            m["en"], m["boy"], m["h"])

    def _split(self, txt):
        if not txt or txt == "Yok":
            return None
        if " / " in txt:
            kat, mat = txt.split(" / ", 1)
            return kat, mat
        return txt

    def _picks(self):
        picks = {}
        d = self._split(self.sp_duvar.text)
        if isinstance(d, tuple):
            picks["duvar"] = d
        if self.sp_siva.text != "Yok":
            picks["siva"] = self.sp_siva.text
        if self.sp_saten.text != "Yok":
            picks["saten"] = self.sp_saten.text
        if self.sp_boya.text != "Yok":
            picks["boya"] = self.sp_boya.text
        z = self._split(self.sp_zemin.text)
        if isinstance(z, tuple):
            picks["zemin"] = z
        if self.sp_tavan.text != "Yok":
            picks["tavan"] = self.sp_tavan.text
        if self.sp_sup.text != "Yok":
            picks["sup"] = self.sp_sup.text
        return picks

    def uygula(self, _inst):
        app = App.get_running_app()
        if self.idx >= len(app.mahals):
            return
        fire = {"%5 Fire": 0.05, "%10 Fire": 0.10, "%15 Fire": 0.15}.get(app.fire_label, 0.10)
        picks = self._picks()
        items = run_mahal_paket(app.mahals[self.idx], picks, fire)
        if not items:
            self.lbl_sonuc.text = "En az bir kalem sec."
            return
        app.cart.extend(items)
        app.save_cart()
        self.lbl_sonuc.text = "{} kalem eklendi.\n\n{}".format(
            len(items), format_liste(items, app.mahals[self.idx]["ad"]))

    def uygula_hepsi(self, _inst):
        app = App.get_running_app()
        if not app.mahals:
            self.lbl_sonuc.text = "Once mahal ekle veya DXF yukle."
            return
        fire = {"%5 Fire": 0.05, "%10 Fire": 0.10, "%15 Fire": 0.15}.get(app.fire_label, 0.10)
        picks = self._picks()
        if not picks:
            picks = dict(DEFAULT_PAKET)
        all_items = []
        for m in app.mahals:
            all_items.extend(run_mahal_paket(m, picks, fire))
        if not all_items:
            self.lbl_sonuc.text = "En az bir kalem sec."
            return
        app.cart.extend(all_items)
        app.save_cart()
        try:
            path, _txt = export_liste_pdf(app.cart, app.proje)
            self.lbl_sonuc.text = "{} mahal, {} kalem.\nPDF: {}\n\n{}".format(
                len(app.mahals), len(all_items), path, format_liste(app.cart, app.proje))
        except Exception as e:
            self.lbl_sonuc.text = "{} mahal, {} kalem. PDF yazilamadi: {}\n\n{}".format(
                len(app.mahals), len(all_items), e, format_liste(app.cart, app.proje))

    def go_back(self, _inst):
        self.manager.get_screen("mahal").refresh()
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "mahal"


class CadScreen(Screen):
    def __init__(self, **kwargs):
        super(CadScreen, self).__init__(**kwargs)
        self.found = []
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.add_widget(ui_label("CAD / DXF", 22, 40, True))
        root.add_widget(ui_btn("< ANA MENU", self.go_menu, 44, 15))
        root.add_widget(ui_label(
            "DWG acilmaz. AutoCAD: Farkli Kaydet -> DXF (ASCII). Dosyayi Download klasorune koy.",
            13, 56))
        self.sp_dosya = Spinner(
            text="DXF dosyasi sec",
            values=["DXF dosyasi sec"],
            size_hint_y=None, height=dp(48), font_size=sp(13))
        root.add_widget(self.sp_dosya)
        self.in_path = TextInput(
            text="", hint_text="veya tam yol /storage/emulated/0/Download/plan.dxf",
            multiline=False, font_size=sp(13), size_hint_y=None, height=dp(44),
            padding=[dp(10), dp(8)])
        root.add_widget(self.in_path)
        root.add_widget(ui_btn("DOWNLOAD TARA", self.tara, 46, 14))
        self.in_h = TextInput(
            text="2.70", hint_text="Varsayilan yukseklik m", input_filter="float",
            multiline=False, font_size=sp(16), size_hint_y=None, height=dp(44),
            padding=[dp(10), dp(8)])
        root.add_widget(self.in_h)
        self.sp_kapi = Spinner(
            text="Varsayilan kapi/pencere: Evet",
            values=["Varsayilan kapi/pencere: Evet", "Kapi/pencere yok"],
            size_hint_y=None, height=dp(46), font_size=sp(14))
        root.add_widget(self.sp_kapi)
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        row.add_widget(ui_btn("OKU", self.oku, 48, 15))
        row.add_widget(ui_btn("MAHALE AKTAR", self.aktar, 48, 14))
        root.add_widget(row)
        root.add_widget(ui_btn("KOMPLE LISTE (FIYATSIZ)", self.komple, 50, 16))
        self.lbl = Label(
            text="DXF sec, OKU.", font_size=sp(14), halign="left", valign="top",
            color=(0.95, 0.94, 0.90, 1))
        self.lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        sc = ScrollView()
        sc.add_widget(self.lbl)
        root.add_widget(sc)
        self.add_widget(root)

    def on_pre_enter(self, *_a):
        self.tara(None)

    def _dxf_roots(self):
        roots = [
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads",
            "/sdcard/Download",
            "/storage/emulated/0/Documents",
            "/sdcard/Documents",
            os.getcwd(),
        ]
        try:
            app = App.get_running_app()
            if app:
                roots.append(app.user_data_dir)
        except Exception:
            pass
        out = []
        for p in roots:
            if p and p not in out and os.path.isdir(p):
                out.append(p)
        return out

    def tara(self, _inst):
        found = []
        for root in self._dxf_roots():
            try:
                for name in os.listdir(root):
                    low = name.lower()
                    if low.endswith((".dxf", ".txt", ".cad")):
                        found.append(os.path.join(root, name))
            except Exception:
                continue
        found = sorted(set(found))
        if found:
            self.sp_dosya.values = found
            if self.sp_dosya.text not in found:
                self.sp_dosya.text = found[0]
            self.lbl.text = "{} DXF bulundu. Sec, OKU.".format(len(found))
        else:
            self.sp_dosya.values = ["DXF yok — Download'a kopyala"]
            self.sp_dosya.text = "DXF yok — Download'a kopyala"
            self.lbl.text = "Download klasorunde DXF yok.\nplan.dxf dosyasini Telefona > Download icine koy, sonra DOWNLOAD TARA."

    def _secili_yol(self):
        p = (self.in_path.text or "").strip()
        if p and os.path.isfile(p):
            return p
        t = self.sp_dosya.text or ""
        if t and os.path.isfile(t):
            return t
        return ""

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

    def oku(self, _inst):
        path = self._secili_yol()
        if not path:
            self.tara(None)
            path = self._secili_yol()
        if not path:
            self.lbl.text = "Once DXF sec veya tam yolu yaz. Dosya Download icinde olsun."
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            self.found = parse_dxf(text)
        except ValueError as e:
            self.found = []
            self.lbl.text = str(e)
            return
        except Exception as e:
            self.found = []
            self.lbl.text = "Okunamadi: {}".format(e)
            return
        if not self.found:
            self.lbl.text = "Kapali oda bulunamadi. Odalar kapali polyline olsun, mm/m olcek otomatik."
            return
        lines = ["{} mahal bulundu:".format(len(self.found)), ""]
        for m in self.found:
            lines.append("- {}  {:.2f} x {:.2f} m  (~{:.1f} m2)".format(
                m["ad"], m["en"], m["boy"], m.get("alan", m["en"] * m["boy"])))
        self.lbl.text = "\n".join(lines)

    def aktar(self, _inst):
        if not self.found:
            self.oku(None)
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
            self.oku(None)
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


class ListeScreen(Screen):
    def __init__(self, **kwargs):
        super(ListeScreen, self).__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.add_widget(ui_label("MALZEME LISTESI", 22, 40, True))
        root.add_widget(ui_btn("< ANA MENU", self.go_menu, 44, 15))
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        row.add_widget(ui_btn("KOPYALA", self.kopyala, 46, 14))
        row.add_widget(ui_btn("PDF INDIR", self.pdf, 46, 14))
        row.add_widget(ui_btn("SEPETE GIT", self.go_sepet, 46, 14))
        root.add_widget(row)
        self.lbl = Label(
            text="", font_size=sp(14), halign="left", valign="top",
            color=(0.95, 0.94, 0.90, 1))
        self.lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        sc = ScrollView()
        sc.add_widget(self.lbl)
        root.add_widget(sc)
        self.add_widget(root)

    def on_pre_enter(self, *_a):
        self.refresh(True)

    def refresh(self, auto_pdf=False):
        app = App.get_running_app()
        text = format_liste(app.cart, app.proje)
        self.lbl.text = text
        if auto_pdf and app.cart:
            try:
                path, _t = export_liste_pdf(app.cart, app.proje)
                self.lbl.text = text + "\n\nPDF kaydedildi:\n" + path
            except Exception as e:
                self.lbl.text = text + "\n\nPDF yazilamadi: {}".format(e)

    def pdf(self, _inst):
        app = App.get_running_app()
        if not app.cart:
            self.lbl.text = "Liste bos."
            return
        try:
            path, _t = export_liste_pdf(app.cart, app.proje)
            self.lbl.text = format_liste(app.cart, app.proje) + "\n\nPDF:\n" + path
        except Exception as e:
            self.lbl.text = "PDF yazilamadi: {}".format(e)

    def kopyala(self, _inst):
        Clipboard.copy(self.lbl.text or "")
        self.lbl.text = (self.lbl.text or "") + "\n\n[ Panoya kopyalandi ]"

    def go_menu(self, _inst):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"

    def go_sepet(self, _inst):
        self.manager.get_screen("sepet").refresh()
        self.manager.current = "sepet"


class HesaplaApp(App):
    def build(self):
        self.title = "Cifciler Insaat"
        try:
            return self._build_ui()
        except Exception:
            box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
            lab = Label(
                text="Acilis hatasi:\n" + traceback.format_exc()[:1800],
                font_size=sp(13), halign="left", valign="top",
                color=(0.95, 0.94, 0.90, 1))
            lab.bind(size=lambda i, v: setattr(i, "text_size", v))
            box.add_widget(lab)
            return box

    def on_start(self):
        try:
            Window.clearcolor = (0.07, 0.07, 0.06, 1)
            Window.softinput_mode = "below_target"
        except Exception:
            pass

    def _store_path(self):
        try:
            d = self.user_data_dir
            os.makedirs(d, exist_ok=True)
            return os.path.join(d, "cifciler.json")
        except Exception:
            return "cifciler.json"

    def _build_ui(self):
        self.store = JsonStore(self._store_path())
        self.cart = []
        self.mahals = []
        self.proje = ""
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
        sm.add_widget(MahalScreen(name="mahal"))
        sm.add_widget(PaketScreen(name="paket"))
        sm.add_widget(CadScreen(name="cad"))
        sm.add_widget(ListeScreen(name="liste"))
        return sm

    def load_state(self):
        try:
            if self.store.exists("ayar"):
                a = self.store.get("ayar")
                self.fire_label = a.get("fire_label", "%10 Fire")
                self.kdv_on = a.get("kdv_on", True)
                self.phases.update(a.get("phases", {}) or {})
            if self.store.exists("sepet"):
                items = self.store.get("sepet").get("items", [])
                self.cart = items if isinstance(items, list) else []
            if self.store.exists("mahal"):
                mh = self.store.get("mahal")
                items = mh.get("items", [])
                self.mahals = items if isinstance(items, list) else []
                self.proje = mh.get("proje", "") or ""
        except Exception:
            if not isinstance(self.cart, list):
                self.cart = []
            if not isinstance(self.mahals, list):
                self.mahals = []

    def save_settings(self):
        try:
            self.store.put(
                "ayar", fire_label=self.fire_label, kdv_on=self.kdv_on, phases=self.phases)
        except Exception:
            pass

    def save_cart(self):
        try:
            self.store.put("sepet", items=self.cart if isinstance(self.cart, list) else [])
        except Exception:
            pass

    def save_mahals(self):
        try:
            self.store.put("mahal", items=self.mahals if isinstance(self.mahals, list) else [], proje=self.proje)
        except Exception:
            pass


if __name__ == "__main__":
    HesaplaApp().run()
