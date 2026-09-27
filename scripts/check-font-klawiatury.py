#!/usr/bin/env python3
"""Sprawdza, ze naglowek czcionki klawiatury jest DOKLADNIE tym, co wypisuje generator.

Po co osobna bramka: tools/klawiatura/czcionka.h ma 16384 bajty przepisane z jadra.
Recznie wprowadzona zmiana w takim pliku nie rzuca sie w oczy i nie psuje kompilacji,
a psuje obraz na ekranie, co widac dopiero na telefonie. Generator jest zrodlem prawdy,
wiec bramka pyta wprost, czy plik rowna sie jego wyjsciu.

Porownanie ignoruje koncowki linii, bo drzewo gita na Windowsie oddaje pliki z CRLF,
a generator pisze to, co dostanie od Pythona.

Exit 0, gdy plik zgadza sie z generatorem. Exit 1 przy roznicy.
Exit 2, gdy bramki NIE DA SIE uruchomic (brak zrodel jadra w sources/linux): to nie jest
zielone swiatlo i verify.sh liczy to jako bramke nieuruchomiona.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR = os.path.join(ROOT, "scripts", "gen-font-klawiatury.py")
PLIK = os.path.join(ROOT, "tools", "klawiatura", "czcionka.h")
ZRODLO = os.path.join(ROOT, "sources", "linux", "lib", "fonts", "font_ter16x32.c")


def znormalizuj(tekst):
    return tekst.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10))


def main():
    if not os.path.exists(ZRODLO):
        print("BRAMKA NIEURUCHOMIONA: brak %s" % ZRODLO)
        return 2
    if not os.path.exists(PLIK):
        print("brak %s, a generator go wypisuje" % PLIK)
        return 1

    r = subprocess.run([sys.executable, GENERATOR], capture_output=True, text=True)
    if r.returncode != 0:
        print("generator padl:%s%s" % (chr(10), r.stderr.strip()))
        return 1

    z_pliku = znormalizuj(open(PLIK, encoding="utf-8").read())
    z_generatora = znormalizuj(r.stdout)

    if z_pliku == z_generatora:
        print("czcionka klawiatury zgodna z generatorem (%d bajtow danych)"
              % (16384,))
        return 0

    a, b = z_pliku.split(chr(10)), z_generatora.split(chr(10))
    for i in range(max(len(a), len(b))):
        wa = a[i] if i < len(a) else "<koniec pliku>"
        wb = b[i] if i < len(b) else "<koniec wyjscia generatora>"
        if wa != wb:
            print("roznica w wierszu %d" % (i + 1))
            print("  plik:      %s" % wa[:100])
            print("  generator: %s" % wb[:100])
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())
