#!/usr/bin/env python3
"""Sprawdza, ze kazda latka w patches/ jest poprawnie zbudowana.

Po co osobna bramka.  Latki tej serii powstaja z dwoch zrodel: z gita, gdy
zmiana jest pisana recznie, i ze skryptu, gdy plik ma generator.  Drugie
zrodlo potrafi sie pomylic w liczbach nagłowka fragmentu, a taki blad NIE
daje o sobie znac: `checkpatch` czyta tresc, nie arytmetyke, bramki bindingow
czytaja pliki drzewa, a nie latki, i wszystko swieci na zielono do chwili,
gdy ktos sprobuje serie nalozyc.  Wtedy `git am` mowi tylko "corrupt patch at
line N" i nie wskazuje, co jest nie tak.  Zdarzylo sie to latce 0064, ktora
przez cala runde lezala zepsuta.

Co jest sprawdzane dla kazdej latki:
  1. naglowek listu: From, Date, Subject, przynajmniej jeden Signed-off-by,
     oraz linia "---" oddzielajaca opis od diffa,
  2. kazdy fragment "@@ -a,b +c,d @@" ma tyle linii, ile deklaruje:
     b = kontekst + usuniete, d = kontekst + dodane,
  3. wewnatrz fragmentu nie ma linii CALKIEM pustej: kontekst pustej linii
     zrodla musi miec wiodaca spacje.  Bez niej `git apply` liczy inaczej niz
     czlowiek czytajacy latke i odrzuca ja,
  4. latka naprawde cos zmienia (ma co najmniej jeden fragment).

Uzycie:
  scripts/check-latki.py            # wszystkie latki
  scripts/check-latki.py --napraw   # popraw liczby w nagłowkach fragmentow

Kod 0 gdy wszystkie latki sa spojne, 1 przy pierwszym bledzie, 2 gdy nie ma
czego sprawdzac.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KATALOG = os.path.join(ROOT, "patches")
NL = chr(10)

FRAGMENT = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def sprawdz_latke(sciezka, napraw):
    """Zwraca (lista bledow, nowa tresc albo None)."""
    tekst = io.open(sciezka, encoding="utf-8", errors="replace").read()
    linie = tekst.split(NL)
    bledy = []
    nazwa = os.path.basename(sciezka)

    for pole in ("From: ", "Date: ", "Subject: "):
        if not any(l.startswith(pole) for l in linie[:12]):
            bledy.append("brak naglowka %s" % pole.strip())
    if not any(l.startswith("Signed-off-by: ") for l in linie):
        bledy.append("brak Signed-off-by")
    if "---" not in linie:
        bledy.append("brak linii --- miedzy opisem a diffem")

    # Fragmenty.  Idziemy liniowo: naglowek fragmentu otwiera zliczanie,
    # a konczy je nastepny naglowek, nastepny plik albo koniec latki.
    fragmenty = 0
    poprawki = {}
    puste = []
    i = 0
    while i < len(linie):
        m = FRAGMENT.match(linie[i])
        if not m:
            i += 1
            continue
        fragmenty += 1
        nr_naglowka = i
        deklarowane_stare = int(m.group(2) if m.group(2) is not None else 1)
        deklarowane_nowe = int(m.group(4) if m.group(4) is not None else 1)
        kontekst = usuniete = dodane = 0
        i += 1
        while i < len(linie):
            l = linie[i]
            if l.startswith("@@ ") or l.startswith("diff --git ") or \
                    l.startswith("-- "):
                break
            if l.startswith("+++") or l.startswith("---"):
                break
            if l.startswith("+"):
                dodane += 1
            elif l.startswith("-"):
                usuniete += 1
            elif l.startswith(" "):
                kontekst += 1
            elif l.startswith(chr(92)):      # "\ No newline at end of file"
                pass
            elif l == "":
                # Pusta linia w srodku fragmentu: albo zjedzony kontekst,
                # albo koniec latki.  Rozstrzyga to, co jest dalej.
                reszta = [x for x in linie[i + 1:] if x.strip()]
                if not reszta:
                    break
                bledy.append("fragment w linii %d: pusta linia %d bez"
                             " wiodacej spacji" % (nr_naglowka + 1, i + 1))
                puste.append(i)
                kontekst += 1
            else:
                break
            i += 1
        stare = kontekst + usuniete
        nowe = kontekst + dodane
        if stare != deklarowane_stare or nowe != deklarowane_nowe:
            bledy.append("fragment w linii %d deklaruje %d i %d, a ma %d i %d"
                         % (nr_naglowka + 1, deklarowane_stare,
                            deklarowane_nowe, stare, nowe))
            poprawki[nr_naglowka] = (int(m.group(1)), stare,
                                     int(m.group(3)), nowe)

    if not fragmenty:
        bledy.append("latka nie ma ani jednego fragmentu")

    nowa = None
    if napraw and (poprawki or puste):
        # Najpierw spacje, bo od nich zaleza liczby, potem liczby.
        for nr in puste:
            linie[nr] = " "
        for nr, (a, b, c, d) in poprawki.items():
            ogon = linie[nr].split("@@", 2)[2] if linie[nr].count("@@") > 1 \
                else ""
            linie[nr] = "@@ -%d,%d +%d,%d @@%s" % (a, b, c, d, ogon)
        nowa = NL.join(linie)

    return nazwa, bledy, nowa


def main():
    if not os.path.isdir(KATALOG):
        print("check-latki: brak katalogu patches, nie mam czego sprawdzac")
        return 2
    latki = sorted(f for f in os.listdir(KATALOG) if f.endswith(".patch"))
    if not latki:
        print("check-latki: katalog patches jest pusty")
        return 2

    napraw = "--napraw" in sys.argv
    zle = 0
    naprawione = 0
    for f in latki:
        sciezka = os.path.join(KATALOG, f)
        nazwa, bledy, nowa = sprawdz_latke(sciezka, napraw)
        if bledy:
            zle += 1
            print("  FAIL %s" % nazwa)
            for b in bledy[:5]:
                print("       %s" % b)
        if nowa is not None:
            io.open(sciezka, "w", encoding="utf-8", newline=NL).write(nowa)
            naprawione += 1
            print("       naprawiono liczby w naglowkach fragmentow")

    print("check-latki: latek %d, niespojnych %d%s"
          % (len(latki), zle,
             ", naprawionych %d" % naprawione if naprawione else ""))
    return 1 if zle and not naprawione else 0


if __name__ == "__main__":
    sys.exit(main())
