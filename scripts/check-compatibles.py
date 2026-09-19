#!/usr/bin/env python3
"""Sprawdza, czy kazdy wezel naszego drzewa urzadzen ma sterownik.

To jest bramka na blad, ktory nie daje o sobie znac ani przy kompilacji, ani
przy `dtbs_check`: drzewo deklaruje `compatible`, ktorego ZADEN sterownik
w drzewie jadra nie obsluguje. Wezel wtedy po prostu nie probuje sie, bez
komunikatu, a wszystko, co od niego zalezy, wisi w probe deferral albo cicho
nie dziala.

Tak wlasnie bylo z `samsung,exynos9820-pinctrl`: seria dodawala binding i osiem
wezlow w drzewie, ale nigdy tablic bankow do `pinctrl-exynos-arm64.c`. Kazdy
inny compatible tego SoC ma zapasowy ("samsung,exynos9820-mct",
"samsung,exynos4210-mct"), ten jeden nie mial i nie mial czym byc obsluzony,
wiec padalby kazdy pin i kazde GPIO. Kompilacja byla czysta, dtbs_check tez.

Zasada: wezel przechodzi, jesli CHOC JEDEN z jego ciagow `compatible` wystepuje
w tablicy dopasowan jakiegos sterownika w drzewie jadra. Zapasowy compatible
liczy sie tak samo jak wlasny, bo to wlasnie po to istnieje.

Wyjscie 0, gdy kazdy wezel ma czym byc obsluzony.
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINUX = os.path.join(ROOT, "sources", "linux")
DTS = os.path.join(LINUX, "arch", "arm64", "boot", "dts", "exynos")

# Wezly, ktore SWIADOMIE nie maja sterownika i nie powinny go miec.
# Kazdy z powodem, bo inaczej ta lista bylaby workiem na wymowki.
BEZ_STEROWNIKA = {
    # Opisuja wylacznie topologie dla innych sterownikow, nikt ich nie probuje.
    "samsung,exynos9820": "korzen drzewa, identyfikuje plyte",
    "operating-points-v2": "tablica punktow pracy, czyta ja cpufreq",
    # Rdzenie procesora jadro rozpoznaje po MIDR, a nie po compatible: te ciagi
    # sluza wylacznie schematowi drzewa (Documentation/.../arm/cpus.yaml)
    # i zadna tablica dopasowan w kodzie ich nie zawiera.
    "arm,cortex-a55": "rdzen procesora, rozpoznawany po MIDR",
    "arm,cortex-a75": "rdzen procesora, rozpoznawany po MIDR",
    "samsung,mongoose-m4": "rdzen procesora, rozpoznawany po MIDR",
}

# Katalogi, w ktorych szukamy tablic dopasowan.
GALEZIE = ["drivers", "arch/arm64", "sound", "kernel", "fs"]


def nasze_compatible():
    """(plik, linia, [ciagi]) dla kazdego wezla naszych plikow DT."""
    out = []
    for nazwa in sorted(os.listdir(DTS)):
        if "exynos9820" not in nazwa:
            continue
        p = os.path.join(DTS, nazwa)
        tekst = io.open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"compatible\s*=\s*([^;]+);", tekst):
            ciagi = re.findall(r'"([^"]+)"', m.group(1))
            if ciagi:
                linia = tekst.count(chr(10), 0, m.start()) + 1
                out.append((nazwa, linia, ciagi))
    return out


def znane_sterownikom(ciagi):
    """Zbior ciagow, ktore wystepuja w zrodlach jadra poza drzewem urzadzen."""
    znane = set()
    if not ciagi:
        return znane
    # Jedno wywolanie grepa na komplet, inaczej to trwa minuty.  Wzorce ida
    # BEZ wlasnych cudzyslowow: na Windows argumenty przechodza przez
    # list2cmdline i wzorzec z cudzyslowem dociera do grepa zniekształcony,
    # po czym nie znajduje niczego, a bramka swieci na zielono z pustej listy.
    args = ["grep", "-rlF", "--include=*.c", "--include=*.h"]
    for c in sorted(ciagi):
        args += ["-e", c]
    args += GALEZIE
    w = subprocess.run(args, cwd=LINUX, capture_output=True, text=True)
    pliki = [x.strip() for x in w.stdout.split(chr(10)) if x.strip()]
    if not pliki:
        return znane

    # Warunek "ciag stoi w cudzyslowie", czyli jest wpisem tablicy dopasowan,
    # a nie wzmianka w komentarzu, sprawdzamy juz w Pythonie.
    szukane = dict(('"%s"' % c, c) for c in ciagi)
    for f in pliki:
        try:
            tekst = io.open(os.path.join(LINUX, f), encoding="utf-8",
                            errors="replace").read()
        except OSError:
            continue
        for wzor, c in szukane.items():
            if c not in znane and wzor in tekst:
                znane.add(c)
    return znane


def main():
    if not os.path.isdir(DTS):
        print("check-compatibles: brak %s" % DTS)
        return 2

    wezly = nasze_compatible()
    wszystkie = set()
    for _, _, ciagi in wezly:
        wszystkie |= set(ciagi)
    znane = znane_sterownikom(wszystkie - set(BEZ_STEROWNIKA))

    zle = []
    for nazwa, linia, ciagi in wezly:
        if any(c in BEZ_STEROWNIKA for c in ciagi):
            continue
        if not any(c in znane for c in ciagi):
            zle.append((nazwa, linia, ciagi))

    for nazwa, linia, ciagi in zle:
        print("  FAIL %s:%d zaden sterownik nie obsluguje %s"
              % (nazwa, linia, ", ".join(ciagi)))
    print("check-compatibles: wezlow %d, roznych ciagow %d, bez sterownika %d"
          % (len(wezly), len(wszystkie), len(zle)))
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main())
