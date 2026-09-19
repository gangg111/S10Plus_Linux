#!/usr/bin/env python3
"""Sprawdza, ze panel TEGO egzemplarza wybiera wariant, z ktorego przepisano tablice.

Po co. Bootloader podaje jadru `lcdtype=10555411`, czyli 0xA11013, a naglowek producenta,
z ktorego wzieto sekwencje inicjalizacyjna i tablice dimmingu, zna dla tej plyty warianty
0x900100, 0xA01010 i 0xA01011. Ostatni bajt sie nie zgadza (0x13 zamiast 0x11) i przez chwile
wygladalo to na powazne ryzyko: obraz bylby, ale barwy albo jasnosc moglyby byc nie te, i nic
by tego nie zglosilo.

Rozstrzygniecie nie jest domyslem. Producent NIE dopasowuje wariantu po polu `.id` struktury,
tylko po tablicy `panel-lut` z drzewa urzadzen, wpis po wpisie, z maska:
`(lut[i].id & lut[i].mask) == (id & lut[i].mask)`, pierwsze trafienie wygrywa
(`sources/ds/panel.c:187-207`, format wpisu w `sources/ds/panel.h:866-871`). W drzewie zdjetym
z tego telefonu ostatni wpis ma maske zero, wiec lapie wszystko i wskazuje wariant `_default`.
Ostatni bajt identyfikatora nie ma wiec znaczenia dla wyboru tablic.

Bramka odtwarza ten rachunek na zapisanym pomiarze i pilnuje trzech rzeczy:
  * `lcdtype` z linii polecen tego egzemplarza nadal wybiera wariant `_default`,
  * lista `panel-name` z drzewa nadal ma ten wariant pod indeksem, ktory wskazuje tablica,
  * naglowek producenta nadal opisuje `_default` jako `0xA01011`, czyli ten, z ktorego
    przepisano tablice do serii.

Uzycie: scripts/check-panel-variant.py [--id 0xA11013] [--dts <plik>]
Exit 0, gdy wszystko sie zgadza. Exit 1 przy niezgodnosci. Exit 2, gdy brak materialu
pomiarowego (bramka nieuruchomiona, nie zielona).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POMIAR = os.path.join(ROOT, "measurements", "2026-09-11-etap0a")
DTS = os.path.join(POMIAR, "stock-fdt.dts")
CMDLINE = os.path.join(POMIAR, "cmdline.txt")
NAGLOWEK = os.path.join(ROOT, "sources", "ds", "s6e3ha9_beyond2_a3_s0_panel.h")

OCZEKIWANY = "s6e3ha9_beyond2_a3_s0_default"
OCZEKIWANE_ID = 0xA01011


def czytaj_lut(tekst):
    """panel-name jako lista nazw i panel-lut jako lista krotek (id, mask, index, ddi)."""
    m = re.search(r'panel-name = ([^;]+);', tekst)
    if not m:
        return None, None
    nazwy = re.findall(r'"([^"]+)"', m.group(1))
    m = re.search(r'panel-lut = <([^>]+)>;', tekst)
    if not m:
        return nazwy, None
    liczby = [int(x, 16) if x.startswith("0x") else int(x) for x in m.group(1).split()]
    if len(liczby) % 4:
        return nazwy, None
    return nazwy, [tuple(liczby[i:i + 4]) for i in range(0, len(liczby), 4)]


def dopasuj(lut, pid):
    """Regula producenta: pierwszy wpis, ktory zgadza sie pod swoja maska."""
    for i, (idv, maska, index, _ddi) in enumerate(lut):
        if (idv & maska) == (pid & maska):
            return i, index
    return None, None


def main():
    args = sys.argv[1:]
    dts = DTS
    if "--dts" in args:
        dts = args[args.index("--dts") + 1]
    pid = None
    if "--id" in args:
        pid = int(args[args.index("--id") + 1], 0)

    for p in (dts, CMDLINE, NAGLOWEK):
        if not os.path.exists(p):
            print("NIEURUCHOMIONA: brak %s" % p)
            return 2

    if pid is None:
        cmdline = open(CMDLINE, encoding="utf-8", errors="replace").read()
        m = re.search(r"lcdtype=(\d+)", cmdline)
        if not m:
            print("BLAD: w zapisanym cmdline nie ma lcdtype=")
            return 1
        pid = int(m.group(1))

    tekst = open(dts, encoding="utf-8", errors="replace").read()
    nazwy, lut = czytaj_lut(tekst)
    if not nazwy or not lut:
        print("BLAD: w drzewie nie ma czytelnych panel-name / panel-lut")
        return 1

    wpis, index = dopasuj(lut, pid)
    if index is None:
        print("BLAD: id 0x%06X nie pasuje do zadnego wpisu panel-lut" % pid)
        print("      producent zglosilby wtedy 'panel not found'")
        return 1
    if index >= len(nazwy):
        print("BLAD: wpis %d wskazuje indeks %d, a nazw jest %d" % (wpis, index, len(nazwy)))
        return 1

    wybrany = nazwy[index]
    if wybrany != OCZEKIWANY:
        print("BLAD: id 0x%06X wybiera wariant %s, a tablice w serii sa z %s"
              % (pid, wybrany, OCZEKIWANY))
        print("      trafil wpis %d: id=0x%08X maska=0x%08X" % (wpis, lut[wpis][0], lut[wpis][1]))
        return 1

    naglowek = open(NAGLOWEK, encoding="utf-8", errors="replace").read()
    blok = re.search(r'\.name = "' + OCZEKIWANY + r'".*?\.id = (0x[0-9A-Fa-f]+)',
                     naglowek, re.S)
    if not blok:
        print("BLAD: w naglowku producenta nie ma wariantu %s z polem .id" % OCZEKIWANY)
        return 1
    if int(blok.group(1), 16) != OCZEKIWANE_ID:
        print("BLAD: wariant %s ma w naglowku .id = %s, oczekiwano 0x%06X"
              % (OCZEKIWANY, blok.group(1), OCZEKIWANE_ID))
        return 1

    print("OK: lcdtype 0x%06X wybiera %s (wpis %d, maska 0x%08X), naglowek .id = 0x%06X"
          % (pid, wybrany, wpis, lut[wpis][1], OCZEKIWANE_ID))
    return 0


if __name__ == "__main__":
    sys.exit(main())
