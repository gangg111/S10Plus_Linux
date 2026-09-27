#!/usr/bin/env python3
"""Wypisuje naglowek C z czcionka bitmapowa dla klawiatury ekranowej.

Zrodlem jest czcionka Terminus 16x32, ktora lezy w jadrze jako
lib/fonts/font_ter16x32.c: 256 glifow po 64 bajty, dwa bajty na wiersz,
bit starszy po lewej. Ta sama czcionka jest ustawiona na konsoli telefonu
(fbcon=font:TER16x32), wiec klawisze wygladaja jak tekst, ktory wpisuja.

Po co generator zamiast wklejenia tablicy: plik w jadrze jest jednym
z dwoch zrodel prawdy i musi byc dokladnie tym, co widac na ekranie;
bramka check-font-klawiatury.py porownuje naglowek z wyjsciem tego skryptu,
wiec rozjazd nie przejdzie niezauwazony.

Uzycie: python3 scripts/gen-font-klawiatury.py > tools/klawiatura/czcionka.h
"""
import os
import re
import sys

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZRODLO = os.path.join(KATALOG, "sources", "linux", "lib", "fonts", "font_ter16x32.c")

SZEROKOSC = 16
WYSOKOSC = 32
NA_GLIF = WYSOKOSC * 2          # dwa bajty na wiersz
ZNAKOW = 256
RAZEM = ZNAKOW * NA_GLIF        # 16384

NAGLOWEK = """/* SPDX-License-Identifier: GPL-2.0 */
/* Czcionka Terminus %dx%d, wygenerowana z lib/fonts/font_ter16x32.c jadra
 * przez scripts/gen-font-klawiatury.py.  Nie edytowac recznie.
 *
 * Uklad: %d glifow po %d bajtow, dwa bajty na wiersz, bit starszy po lewej.
 */
#ifndef KLAWIATURA_CZCIONKA_H
#define KLAWIATURA_CZCIONKA_H

#define CZCIONKA_SZEROKOSC\t%d
#define CZCIONKA_WYSOKOSC\t%d
#define CZCIONKA_NA_GLIF\t%d

static const unsigned char CZCIONKA[%d] = {
"""

STOPKA = """};

#endif /* KLAWIATURA_CZCIONKA_H */
"""


def wczytaj_bajty(sciezka):
    """Wyciaga tablice bajtow z pliku czcionki jadra."""
    with open(sciezka, encoding="utf-8") as f:
        tekst = f.read()

    poczatek = tekst.find("fontdata_ter16x32")
    if poczatek < 0:
        sys.exit("w %s nie ma tablicy fontdata_ter16x32" % sciezka)

    bajty = [int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", tekst[poczatek:])]

    # Pierwsze cztery liczby to naglowek struktury (zera i rozmiar), zapisany
    # dziesietnie, wiec do tablicy nie trafiaja.  Zostaje sam obraz czcionki.
    if len(bajty) != RAZEM:
        sys.exit("oczekiwano %d bajtow czcionki, znaleziono %d" % (RAZEM, len(bajty)))
    return bajty


def main():
    if not os.path.exists(ZRODLO):
        sys.exit("brak %s (czy sources/linux jest pobrane?)" % ZRODLO)

    bajty = wczytaj_bajty(ZRODLO)
    out = [NAGLOWEK % (SZEROKOSC, WYSOKOSC, ZNAKOW, NA_GLIF,
                       SZEROKOSC, WYSOKOSC, NA_GLIF, RAZEM)]

    for i in range(0, RAZEM, 16):
        wiersz = ", ".join("0x%02x" % b for b in bajty[i:i + 16])
        out.append("\t" + wiersz + ",\n")

    out.append(STOPKA)
    sys.stdout.write("".join(out))


if __name__ == "__main__":
    main()
