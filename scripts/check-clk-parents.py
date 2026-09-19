#!/usr/bin/env python3
"""Sprawdza spojnosc drzewa zegarow w clk-exynos9820.c.

Zly rodzic jest bledem CICHYM.  Common clock framework nie odmawia rejestracji
zegara, ktorego rodzica nie ma: zapamietuje nazwe i czeka, az sie pojawi.
Zegar zostaje wiec bez rodzica, `clk_get_rate()` zwraca zero, a `probe`
odbiorcy konczy sie sukcesem.  Literowka w nazwie rodzica przechodzi przez
kompilacje, przez checkpatch i przez porownanie z tablicami producenta, bo
zaden z nich nie patrzy na powiazania miedzy wpisami.

Skrypt sprawdza trzy rzeczy naraz:

  1. kazda nazwa rodzica wskazuje zegar rejestrowany przez ten sterownik albo
     zegar wejsciowy z drzewa urzadzen (oscclk),
  2. zadna nazwa zegara nie powtarza sie w calym pliku,
  3. identyfikatory kazdego bloku CMU tworza ciag 1..N bez dziur i bez
     powtorzen, a CLKS_NR_<BLOK> rowna sie N+1.

Punkt 3 chroni `nr_clk_ids`: gdyby identyfikator wystawal poza zadeklarowana
liczbe, samsung_clk_init przydzieliloby za krotka tablice i zegar wypadlby
z providera, znowu bez zadnego komunikatu.

Wyjscie 0, gdy wszystko trzyma sie kupy.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEROWNIK = os.path.join(ROOT, "sources", "linux", "drivers", "clk", "samsung",
                         "clk-exynos9820.c")
NAGLOWEK = os.path.join(ROOT, "sources", "linux", "include", "dt-bindings",
                        "clock", "samsung,exynos9820.h")

# Zegary, ktore przychodza z drzewa urzadzen, a nie z tego sterownika.
# `oscclk` jest w bindingu jako pierwszy wpis clock-names kazdego CMU.
ZEWNETRZNE = {"oscclk"}

# makro -> (pozycja identyfikatora, pozycja nazwy, pozycja rodzica albo None)
MAKRA = {
    "PLL": (1, 2, 3),
    "FRATE": (0, 1, 2),
    "MUX": (0, 1, None),
    "MUX_F": (0, 1, None),
    "nMUX": (0, 1, None),
    "nMUX_F": (0, 1, None),
    "DIV": (0, 1, 2),
    "DIV_F": (0, 1, 2),
    "DIV_T": (0, 1, 2),
    "GATE": (0, 1, 2),
    "FFACTOR": (0, 1, 2),
}


def argumenty(tekst, poz):
    """Rozbija liste argumentow makra zaczynajaca sie na '(' pod poz."""
    glebokosc, biezacy, args = 0, [], []
    for znak in tekst[poz:]:
        if znak == "(":
            glebokosc += 1
            if glebokosc == 1:
                continue
        elif znak == ")":
            glebokosc -= 1
            if glebokosc == 0:
                args.append("".join(biezacy).strip())
                return args
        if glebokosc == 1 and znak == ",":
            args.append("".join(biezacy).strip())
            biezacy = []
        else:
            biezacy.append(znak)
    return args


def bez_cudzyslowu(t):
    t = t.strip()
    if t.startswith('"') and t.endswith('"'):
        return t[1:-1]
    return None


def wczytaj(tekst):
    """Zwraca (zegary, rodzice_wpisane, tablice_pname)."""
    zegary = []          # (identyfikator, nazwa, linia)
    rodzice = []         # (nazwa_rodzica, kontekst, linia)
    wzor = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(
        sorted(MAKRA, key=len, reverse=True)) + r")\(")
    for m in wzor.finditer(tekst):
        makro = m.group(1)
        args = argumenty(tekst, m.end() - 1)
        ii, ni, ri = MAKRA[makro]
        if len(args) <= max(x for x in (ii, ni, ri or 0)):
            continue
        nazwa = bez_cudzyslowu(args[ni])
        if nazwa is None:
            continue
        linia = tekst.count("\n", 0, m.start()) + 1
        zegary.append((args[ii], nazwa, linia))
        if ri is not None:
            rodzic = bez_cudzyslowu(args[ri])
            if rodzic is not None:
                rodzice.append((rodzic, nazwa, linia))

    for m in re.finditer(r"PNAME\(([a-z0-9_]+)\)\s*=\s*\{(.*?)\}\s*;", tekst,
                         re.S):
        linia = tekst.count("\n", 0, m.start()) + 1
        for r in re.findall(r'"([^"]+)"', m.group(2)):
            rodzice.append((r, m.group(1), linia))
    return zegary, rodzice


def main():
    for p in (STEROWNIK, NAGLOWEK):
        if not os.path.exists(p):
            print("check-clk-parents: brak %s" % p)
            return 2

    tekst = io.open(STEROWNIK, encoding="utf-8", errors="replace").read()
    zegary, rodzice = wczytaj(tekst)
    nazwy = {}
    zle = []

    for ident, nazwa, linia in zegary:
        if nazwa in nazwy:
            zle.append("nazwa %s uzyta dwa razy: linie %d i %d"
                       % (nazwa, nazwy[nazwa], linia))
        nazwy[nazwa] = linia

    for rodzic, kontekst, linia in rodzice:
        if rodzic in nazwy or rodzic in ZEWNETRZNE:
            continue
        zle.append("rodzic %s (w %s, linia %d) nie jest nigdzie rejestrowany"
                   % (rodzic, kontekst, linia))

    # identyfikatory blokami, z naglowka bindingu
    naglowek = io.open(NAGLOWEK, encoding="utf-8", errors="replace").read()
    wartosci = dict((m.group(1), int(m.group(2))) for m in
                    re.finditer(r"#define\s+(CLK_[A-Z0-9_]+)\s+\(?(\d+)",
                                naglowek))
    bloki = {}
    for m in re.finditer(r"/\* ---- (CMU_[A-Z0-9]+) ", tekst):
        bloki[m.start()] = m.group(1)
    granice = sorted(bloki)
    uzyte = {}
    for ident, nazwa, linia in zegary:
        poz = tekst.find(ident)
        blok = None
        for g in granice:
            if g <= poz:
                blok = bloki[g]
        if blok is None or ident not in wartosci:
            continue
        uzyte.setdefault(blok, []).append((wartosci[ident], ident))

    for blok in sorted(uzyte):
        pary = sorted(uzyte[blok])
        numery = [n for n, _ in pary]
        if len(set(numery)) != len(numery):
            zle.append("%s: identyfikator uzyty dwa razy" % blok)
        if numery != list(range(1, len(numery) + 1)):
            zle.append("%s: identyfikatory nie tworza ciagu 1..%d (max %d)"
                       % (blok, len(numery), max(numery)))
        krotki = blok[len("CMU_"):]
        m = re.search(r"#define CLKS_NR_" + krotki + r"\s+\((CLK_[A-Z0-9_]+)"
                      r" \+ 1\)", tekst)
        if not m:
            zle.append("%s: brak CLKS_NR_%s" % (blok, krotki))
        elif wartosci.get(m.group(1)) != len(numery):
            zle.append("%s: CLKS_NR_%s liczy od %s (%s), a zegarow jest %d"
                       % (blok, krotki, m.group(1),
                          wartosci.get(m.group(1)), len(numery)))

    for b in zle:
        print("  FAIL %s" % b)
    print("check-clk-parents: zegarow %d, odwolan do rodzicow %d, blokow %d"
          % (len(zegary), len(rodzice), len(uzyte)))
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main())
