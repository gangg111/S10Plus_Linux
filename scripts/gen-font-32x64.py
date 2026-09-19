#!/usr/bin/env python3
"""Czcionka konsoli 32x64 z polskimi znakami, zrobiona z istniejacej 16x32.

Dwie rzeczy naraz, bo obie dotykaja tych samych danych.

1. POWIEKSZENIE. Na panelu 1440 na 3040 najwieksza czcionka, jaka U-Boot ma
   (Terminus 16x32), daje znak szerokosci 0,74 mm. Na ekranie ponad 500 pikseli
   na cal jest to na granicy czytelnosci golym okiem. Konsola wektorowa odpada:
   rasteryzator liczy na zmiennoprzecinkowych, a U-Boot na arm64 buduje sie
   z -mgeneral-regs-only. Skalowania w rendererze konsoli tez nie ma. Wiec kazdy
   piksel staje sie kwadratem 2 na 2. Ksztalt liter bez zmian, rozmiar podwojny.

2. POLSKIE ZNAKI. Konsola indeksuje czcionke jako CP437 (console_normal.c:81
   wola console_utf_to_cp437), a lib/charset.c:528 dla znaku spoza tablicy
   podstawia znak zapytania. W CP437 z polskich liter jest tylko o z kreska,
   wiec bez tego wyszloby "J?zyk". Szesnascie brakujacych glifow wstawiamy na
   pozycje 0xB0 do 0xBF, czyli w miejsce ramek blokowych, ktorych ten port nie
   uzywa (nasze ramki sa z ASCII: plus, minus, kreska pionowa).

   Glify sa SKLADANE z materialu tej samej czcionki, nie rysowane z palca:
   kreska ukosna jest wyjmowana z gotowego "a z kreska" (CP437 0xA0), a kropka
   z kropki nad "i". Dzieki temu grubosc i ksztalt znakow diakrytycznych
   zgadzaja sie z reszta kroju. Ogonek i kreska ukosna przez "l" nie maja
   zrodla w CP437 i sa jedynymi rysowanymi recznie.

Uklad danych, z include/video_font_data.h:
    byte_width(w)     = w/8 zaokraglone w gore
    size(chars, w, h) = chars * height * byte_width
Bity ida od lewej: najstarszy bit bajtu to skrajnie lewy piksel.

Uzycie:
    gen-font-32x64.py             zapisz naglowek do drzewa U-Boota
    gen-font-32x64.py --check     porownaj to, co w drzewie, z wynikiem
    gen-font-32x64.py --preview   wypisz zlozone glify jako ASCII do obejrzenia

Kod: 0 zgodne albo zapisane, 1 rozjazd, 2 brak wejscia (bramka nieuruchomiona)
"""

import os
import re
import sys
from pathlib import Path

UBOOT = Path(os.environ.get("UBOOT_TREE", str(Path.home() / "u-boot-upstream")))
ZRODLO = UBOOT / "include/video_font_ter16x32.h"
CEL = UBOOT / "include/video_font_2x_32x64.h"

ZNAKOW = 256
SZER_ZR, WYS_ZR = 16, 32
SZER_DO, WYS_DO = 32, 64

# Pozycja CP437 -> (nazwa, litera bazowa, rodzaj znaku diakrytycznego).
# Kolejnosc: male z kreska i ogonkiem, potem wielkie, po osiem.
POLSKIE = [
    (0xB0, "a z ogonkiem",  "a", "ogonek"),
    (0xB1, "c z kreska",    "c", "kreska"),
    (0xB2, "e z ogonkiem",  "e", "ogonek"),
    (0xB3, "l z kreska",    "l", "przekreslenie"),
    (0xB4, "n z kreska",    "n", "kreska"),
    (0xB5, "s z kreska",    "s", "kreska"),
    (0xB6, "z z kreska",    "z", "kreska"),
    (0xB7, "z z kropka",    "z", "kropka"),
    (0xB8, "A z ogonkiem",  "A", "ogonek"),
    (0xB9, "C z kreska",    "C", "kreska"),
    (0xBA, "E z ogonkiem",  "E", "ogonek"),
    (0xBB, "L z kreska",    "L", "przekreslenie"),
    (0xBC, "N z kreska",    "N", "kreska"),
    (0xBD, "S z kreska",    "S", "kreska"),
    (0xBE, "Z z kreska",    "Z", "kreska"),
    (0xBF, "Z z kropka",    "Z", "kropka"),
]

# Ogonek: hak schodzacy spod prawej strony litery i zaginajacy sie w lewo.
# Nie ma go w CP437, wiec jest rysowany; zapis pikselami, bo tak widac ksztalt.
# Skrajnie prawa kolumna wzoru trafia na prawa krawedz litery.
OGONEK = [
    "..##.",
    "..##.",
    "..##.",
    ".##..",
    "###..",
]


def bajty_na_znak(szerokosc, wysokosc):
    return wysokosc * (szerokosc // 8 + (1 if szerokosc % 8 else 0))


def wczytaj(sciezka):
    tekst = sciezka.read_text()
    poczatek = tekst.index("video_fontdata_16x32")
    poczatek = tekst.index("{", poczatek)
    koniec = tekst.index("};", poczatek)
    cialo = re.sub(r"/\*.*?\*/", " ", tekst[poczatek:koniec], flags=re.S)
    bajty = [int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", cialo)]
    oczekiwane = ZNAKOW * bajty_na_znak(SZER_ZR, WYS_ZR)
    if len(bajty) != oczekiwane:
        raise SystemExit(f"blad: bajtow {len(bajty)}, oczekiwano {oczekiwane}")
    return bajty


# --- praca na glifie jako liscie 32 szesnastobitowych wierszy ----------------

def glif(bajty, kod):
    baza = kod * bajty_na_znak(SZER_ZR, WYS_ZR)
    return [(bajty[baza + 2 * r] << 8) | bajty[baza + 2 * r + 1]
            for r in range(WYS_ZR)]


def wstaw(bajty, kod, wiersze):
    baza = kod * bajty_na_znak(SZER_ZR, WYS_ZR)
    for r, w in enumerate(wiersze):
        bajty[baza + 2 * r] = (w >> 8) & 0xFF
        bajty[baza + 2 * r + 1] = w & 0xFF


def zakres_pionowy(wiersze):
    niepuste = [i for i, w in enumerate(wiersze) if w]
    return (niepuste[0], niepuste[-1]) if niepuste else (0, 0)


def zakres_poziomy(wiersze):
    maska = 0
    for w in wiersze:
        maska |= w
    if not maska:
        return 0, 0
    lewa = 15 - maska.bit_length() + 1
    prawa = 15 - ((maska & -maska).bit_length() - 1)
    return lewa, prawa


def przesun_pionowo(wiersze, o_ile):
    pusty = [0] * WYS_ZR
    wynik = pusty[:]
    for i, w in enumerate(wiersze):
        j = i + o_ile
        if 0 <= j < WYS_ZR:
            wynik[j] = w
    return wynik


def przesun_poziomo(wiersze, o_ile):
    if o_ile >= 0:
        return [(w >> o_ile) & 0xFFFF for w in wiersze]
    return [(w << -o_ile) & 0xFFFF for w in wiersze]


def zloz(a, b):
    return [x | y for x, y in zip(a, b)]


# --- skladanie polskich glifow ----------------------------------------------

def wytnij_kreske(bajty):
    """Kreska ukosna wyjeta z gotowego 'a z kreska' (CP437 0xA0)."""
    a = glif(bajty, ord("a"))
    a_kreska = glif(bajty, 0xA0)
    gora_a, _ = zakres_pionowy(a)
    return [w if i < gora_a else 0 for i, w in enumerate(a_kreska)]


def wytnij_kropke(bajty):
    """Kropka wyjeta znad 'i': pierwszy zwarty kawalek od gory."""
    i_glif = glif(bajty, ord("i"))
    gora, _ = zakres_pionowy(i_glif)
    koniec = gora
    while koniec < WYS_ZR and i_glif[koniec]:
        koniec += 1
    return [w if gora <= r < koniec else 0 for r, w in enumerate(i_glif)]


def nad_litera(znak, baza):
    """Przesuwa znak diakrytyczny tak, by siedzial tuz nad litera i byl wysrodkowany."""
    z_gora, z_dol = zakres_pionowy(znak)
    b_gora, _ = zakres_pionowy(baza)
    znak = przesun_pionowo(znak, (b_gora - 1) - z_dol)

    z_lewa, z_prawa = zakres_poziomy(znak)
    b_lewa, b_prawa = zakres_poziomy(baza)
    srodek_znaku = (z_lewa + z_prawa) // 2
    srodek_bazy = (b_lewa + b_prawa) // 2
    return przesun_poziomo(znak, srodek_znaku - srodek_bazy)


def dodaj_ogonek(baza):
    _, dol = zakres_pionowy(baza)
    _, prawa = zakres_poziomy(baza)
    szer = len(OGONEK[0])
    hak = [0] * WYS_ZR
    for i, wzor in enumerate(OGONEK):
        r = dol + 1 + i
        if r >= WYS_ZR:
            break
        bity = 0
        for k, znak in enumerate(wzor):
            if znak == "#":
                kolumna = prawa - (szer - 1) + k
                if 0 <= kolumna < SZER_ZR:
                    bity |= 1 << (15 - kolumna)
        hak[r] = bity
    return zloz(baza, hak)


def dodaj_przekreslenie(baza):
    """Kreska ukosna PRZEZ laske. Nie ma zrodla w CP437, wiec rysowana.

    Liczona od samej laski, nie od krawedzi glifu: przy 'L' krawedz glifu to
    dolna poprzeczka, wiec kreska wyszlaby obok laski zamiast przez nia.
    """
    gora, dol = zakres_pionowy(baza)
    srodek = (gora + dol) // 2
    laska_lewa, _ = zakres_poziomy([baza[srodek]])

    kreska = [0] * WYS_ZR
    for i in range(4):
        r = srodek - 2 + i
        if not 0 <= r < WYS_ZR:
            continue
        for k in range(3):
            # od prawej u gory do lewej na dole, czyli kreska w ksztalcie "/"
            kolumna = laska_lewa + 3 - 2 * i + k
            if 0 <= kolumna < SZER_ZR:
                kreska[r] |= 1 << (15 - kolumna)
    return zloz(baza, kreska)


def dodaj_polskie(bajty):
    kreska = wytnij_kreske(bajty)
    kropka = wytnij_kropke(bajty)

    for kod, _nazwa, litera, rodzaj in POLSKIE:
        baza = glif(bajty, ord(litera))
        if rodzaj == "kreska":
            wynik = zloz(baza, nad_litera(kreska, baza))
        elif rodzaj == "kropka":
            wynik = zloz(baza, nad_litera(kropka, baza))
        elif rodzaj == "ogonek":
            wynik = dodaj_ogonek(baza)
        elif rodzaj == "przekreslenie":
            wynik = dodaj_przekreslenie(baza)
        else:
            raise SystemExit(f"nieznany rodzaj: {rodzaj}")
        wstaw(bajty, kod, wynik)

    return bajty


# --- powiekszenie dwa razy ---------------------------------------------------

def podwoj(bajty):
    bw_zr = SZER_ZR // 8
    wynik = []
    for znak in range(ZNAKOW):
        baza = znak * bajty_na_znak(SZER_ZR, WYS_ZR)
        for wiersz in range(WYS_ZR):
            pocz = baza + wiersz * bw_zr
            piksele = []
            for bajt in bajty[pocz:pocz + bw_zr]:
                for bit in range(7, -1, -1):
                    piksele.append((bajt >> bit) & 1)

            podwojone = [p for piksel in piksele for p in (piksel, piksel)]
            wiersz_bajtow = []
            for i in range(0, SZER_DO, 8):
                v = 0
                for j in range(8):
                    v = (v << 1) | podwojone[i + j]
                wiersz_bajtow.append(v)

            wynik.extend(wiersz_bajtow)
            wynik.extend(wiersz_bajtow)
        assert len(wynik) == (znak + 1) * bajty_na_znak(SZER_DO, WYS_DO)
    return wynik


def naglowek(bajty):
    linie = [
        "/* SPDX-License-Identifier: GPL-2.0 */",
        "/*",
        " * WYGENEROWANE, NIE EDYTOWAC RECZNIE.",
        " * Zrodlo: include/video_font_ter16x32.h, kazdy piksel na kwadrat 2 na 2,",
        " * plus szesnascie polskich liter na pozycjach 0xB0 do 0xBF.",
        " * Generator: scripts/gen-font-32x64.py w repozytorium portu.",
        " */",
        "",
        "#ifndef _VIDEO_FONT_2X_32X64_",
        "#define _VIDEO_FONT_2X_32X64_",
        "",
        "#include <video_font_data.h>",
        "",
        "static unsigned char video_fontdata_32x64[VIDEO_FONT_SIZE(256, 32, 64)] = {",
    ]
    na_znak = bajty_na_znak(SZER_DO, WYS_DO)
    for znak in range(ZNAKOW):
        kawalek = bajty[znak * na_znak:(znak + 1) * na_znak]
        for i in range(0, na_znak, 8):
            osiem = ", ".join(f"0x{b:02x}" for b in kawalek[i:i + 8])
            ogon = f",\t/* {znak} */" if i + 8 >= na_znak else ","
            linie.append(f"\t{osiem}{ogon}")
    linie += ["};", "", "#endif /* _VIDEO_FONT_2X_32X64_ */", ""]
    return "\n".join(linie)


def podglad(bajty):
    for kod, nazwa, litera, rodzaj in POLSKIE:
        print(f"\n  0x{kod:02X}  {nazwa}   (baza '{litera}', {rodzaj})")
        for w in glif(bajty, kod):
            print("    " + "".join("#" if (w >> b) & 1 else "." for b in range(15, -1, -1)))


def main():
    if not ZRODLO.exists():
        print(f"gen-font-32x64: BRAMKA NIEURUCHOMIONA, brak {ZRODLO}")
        return 2

    surowe = dodaj_polskie(wczytaj(ZRODLO))

    if "--preview" in sys.argv:
        podglad(surowe)
        return 0

    tresc = naglowek(podwoj(surowe))

    if "--check" in sys.argv:
        if not CEL.exists():
            print(f"gen-font-32x64: brak {CEL}, a generator go produkuje")
            return 1
        if CEL.read_text() != tresc:
            print("gen-font-32x64: plik w drzewie ROZJECHAL SIE z generatorem")
            return 1
        print(f"gen-font-32x64: zgodne, {ZNAKOW} znakow po "
              f"{bajty_na_znak(SZER_DO, WYS_DO)} B, w tym {len(POLSKIE)} polskich")
        return 0

    CEL.write_text(tresc)
    print(f"gen-font-32x64: zapisane {CEL.name} "
          f"({ZNAKOW} znakow, {ZNAKOW * bajty_na_znak(SZER_DO, WYS_DO)} B, "
          f"{len(POLSKIE)} polskich liter na 0xB0-0xBF)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
