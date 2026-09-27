#!/usr/bin/env python3
"""Kazdy generowany plik drzewa musi byc DOKLADNIE tym, co wypisuje generator.

Po co osobna bramka obok check-gen-dts.  Tamta sprawdza dwa pliki drzewa
urzadzen etap po etapie, wiec wymaga repozytorium z galezia serii i milczy
o plikach, ktore etapow nie maja.  Ta sprawdza STAN KONCOWY kazdego
generowanego pliku i dziala na samych plikach, bez gita.

Rozjazd wychodzi tu natychmiast, a nie przy najblizszej regeneracji.  Tak
wlasnie zniknely kiedys trzy grupy wyprowadzen: dopisano je wprost do pliku
wyprowadzen z pominieciem generatora, nikt nie zauwazyl, i pierwsze
uruchomienie generatora skasowalo je razem z drzewem, ktore przestalo sie
skladac.

Kod 0 gdy wszystkie pliki sa zgodne, 1 przy pierwszym rozjezdzie.
"""
import io
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINUX = os.path.join(ROOT, "sources", "linux")
NL = chr(10)

# (generator, argumenty zapisu do pliku tymczasowego, plik w drzewie jadra)
#
# Generatory drzewa urzadzen pisza na standardowe wyjscie, generator zegarow
# do plikow podanych flagami, a generator wyprowadzen ma tylko --wypisz.
PLIKI = (
    ("gen-pinctrl-dts-exynos9820.py", ["--wypisz"], None,
     "arch/arm64/boot/dts/exynos/exynos9820-pinctrl.dtsi"),
    ("gen-clk-exynos9820.py", [], "--sterownik",
     "drivers/clk/samsung/clk-exynos9820.c"),
    ("gen-clk-exynos9820.py", [], "--naglowek",
     "include/dt-bindings/clock/samsung,exynos9820.h"),
)


def wypisz(generator, argumenty, flaga_pliku):
    sciezka = os.path.join(ROOT, "scripts", generator)
    if flaga_pliku is None:
        r = subprocess.run([sys.executable, sciezka] + argumenty,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode:
            sys.exit("%s padl:%s%s" % (generator, NL, r.stderr.strip()))
        return r.stdout
    kat = tempfile.mkdtemp()
    cel = os.path.join(kat, "wynik")
    r = subprocess.run([sys.executable, sciezka] + argumenty
                       + [flaga_pliku, cel],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit("%s padl:%s%s" % (generator, NL, r.stderr.strip()))
    tresc = io.open(cel, encoding="utf-8").read()
    os.remove(cel)
    os.rmdir(kat)
    return tresc


def znormalizuj(tekst):
    return tekst.replace(chr(13) + chr(10), NL).replace(chr(13), NL)


def main():
    zle = 0
    for generator, argumenty, flaga, plik in PLIKI:
        sciezka = os.path.join(LINUX, plik)
        if not os.path.isfile(sciezka):
            print("  FAIL brak %s" % plik)
            zle += 1
            continue
        nasz = znormalizuj(io.open(sciezka, encoding="utf-8").read())
        jego = znormalizuj(wypisz(generator, argumenty, flaga))
        if nasz == jego:
            print("  OK   %s" % plik)
            continue
        zle += 1
        a = nasz.split(NL)
        b = jego.split(NL)
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else "<koniec pliku>"
            y = b[i] if i < len(b) else "<koniec wyjscia>"
            if x != y:
                print("  FAIL %s, pierwsza roznica w linii %d" % (plik, i + 1))
                print("       w drzewie:    %s" % x[:70])
                print("       z generatora: %s" % y[:70])
                break

    print("check-generatory: plikow %d, rozjazdow %d" % (len(PLIKI), zle))
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main())
