#!/usr/bin/env python3
"""Robi logo rozruchowe jadra ze znaku postmarketOS.

Po co osobny generator.  Plik, ktory jadro kompiluje w siebie, to PPM w
postaci tekstowej: sto siedemdziesiat tysiecy liczb, ktorych nikt nie
przeczyta i nikt recznie nie poprawi.  Zrodlem jest obrazek, a nie ten plik,
wiec zrodlo lezy w repozytorium (scripts/zrodla/logo-pmos.png), a plik dla
jadra powstaje z niego tutaj.  Bez tego zmiana rozmiaru albo barwy konczy sie
recznym grzebaniem w liczbach i nikt po tygodniu nie wie, skad sie wzielo to,
co jest w serii.

Co robi: skaluje znak do kwadratu ROZMIAR na ROZMIAR, klada go na czerni (bo
konsola ramki nie ma przezroczystosci) i sprowadza do ILE_BARW kolorow, bo
tyle najwyzej miesci paleta CLUT224 jadra; reszte indeksow zajmuje paleta
konsoli.  Zapis jest tekstowy (P3), tak jak logo, ktore jadro niesie samo.

Uzycie:
  scripts/gen-logo-pmos.py             # zapisz plik dla jadra
  scripts/gen-logo-pmos.py --sprawdz   # tylko porownaj, niczego nie zapisuj

Kod 0 gdy plik zgadza sie z generatorem, 1 przy rozjezdzie, 2 gdy nie ma
czego sprawdzac (brak zrodla albo brak biblioteki obrazkow).

Uwaga o powtarzalnosci: redukcja kolorow idzie przez Pillow.  Inna wersja
biblioteki moze wybrac inna palete i wtedy bramka pokaze rozjazd, ktory nie
jest bledem tresci.  Naprawa jest jedna: uruchomic generator i obejrzec, co
sie zmienilo.
"""
import io
import os
import sys

ROZMIAR = 240
ILE_BARW = 223
PIKSELE_W_WIERSZU = 8

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZRODLO = os.path.join(ROOT, "scripts", "zrodla", "logo-pmos.png")
CEL = os.path.join(ROOT, "sources", "linux", "drivers", "video", "logo",
                   "logo_pmos_clut224.ppm")
NL = chr(10)


def zbuduj():
    """Zwraca tresc pliku PPM jako tekst."""
    from PIL import Image

    znak = Image.open(ZRODLO).convert("RGBA")
    znak = znak.resize((ROZMIAR, ROZMIAR), Image.LANCZOS)

    plaski = Image.new("RGB", (ROZMIAR, ROZMIAR), (0, 0, 0))
    plaski.paste(znak, (0, 0), znak)

    malo = plaski.quantize(colors=ILE_BARW, method=Image.MEDIANCUT,
                           dither=Image.Dither.NONE).convert("RGB")

    dane = list(malo.getdata())
    wiersze = [
        "P3",
        "# postmarketOS logo for the Linux boot console",
        "%d %d" % (ROZMIAR, ROZMIAR),
        "255",
    ]
    for i in range(0, len(dane), PIKSELE_W_WIERSZU):
        kawalek = dane[i:i + PIKSELE_W_WIERSZU]
        wiersze.append(" ".join("%d %d %d" % p for p in kawalek))

    return NL.join(wiersze) + NL


def main():
    sprawdz = "--sprawdz" in sys.argv[1:]

    if not os.path.exists(ZRODLO):
        print("gen-logo-pmos: BRAK ZRODLA %s" % ZRODLO)
        return 2
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("gen-logo-pmos: BRAK Pillow, nie ma czym zbudowac")
        return 2

    tresc = zbuduj()
    barw = len(set(tresc.split(NL)[4:]))

    if sprawdz:
        if not os.path.exists(CEL):
            print("gen-logo-pmos: brak %s" % CEL)
            return 1
        mial = io.open(CEL, encoding="utf-8", newline="").read()
        if mial == tresc:
            print("gen-logo-pmos: logo zgodne z generatorem (%d na %d)"
                  % (ROZMIAR, ROZMIAR))
            return 0
        print("gen-logo-pmos: ROZJAZD, %s nie jest tym, co daje generator"
              % os.path.relpath(CEL, ROOT))
        return 1

    io.open(CEL, "w", encoding="utf-8", newline=NL).write(tresc)
    print("gen-logo-pmos: zapisane %s, %d na %d, wierszy %d"
          % (os.path.relpath(CEL, ROOT), ROZMIAR, ROZMIAR, barw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
