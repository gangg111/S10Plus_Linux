#!/usr/bin/env python3
"""Sprawdza, ze KAZDY plik w sources/ds jest opisany w SOURCES.md.

Po co osobna bramka. Bramka sumy kontrolnej przypina TRESC plikow producenta,
ale nie mowi nic o tym, czy ktokolwiek wie, skad one sa. Pliki dochodzily
pojedynczo, w miare jak kolejna bramka ich potrzebowala, i siedem z nich
weszlo do sources/ds bez wiersza w SOURCES.md. Skutek nie jest kosmetyczny:
czytelnik odtwarzajacy prace dostaje plik bez sciezki w drzewie producenta,
wiec nie umie sprawdzic ani cytatu, ani tego, czy plik pochodzi z wlasciwego
commita. Dokladnie ta klasa bledu, ktora zamknal audyt cytowan po stronie
patchy, tylko przesunieta o poziom wyzej, do samej paczki zrodel.

Dopasowanie po nazwie pliku, nie po sciezce, bo SOURCES.md opisuje pliki ich
sciezkami w drzewie producenta, a sources/ds trzyma je plasko. Dwa pliki sa
w sources/ds pod nazwa skrocona i dla nich jest jawna tablica aliasow: kazdy
alias musi byc uzasadniony, zeby nie stal sie furtka na wszystko.

Exit 0, gdy kazdy plik ma opis. Exit 1, gdy ktorys go nie ma.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = os.path.join(ROOT, "sources", "ds")
DOC = os.path.join(ROOT, "SOURCES.md")

# Plik w sources/ds -> fragment, ktory MUSI wystapic w SOURCES.md.
# Wpis tutaj jest potrzebny tylko wtedy, gdy nazwa lokalna rozni sie od tej,
# ktora dokument wymienia.
ALIASY = {
    # pobierany z include/dt-bindings/clock/exynos9820.h portu chiffathefoxa,
    # przemianowany lokalnie, zeby nie zderzal sie z naglowkiem mainline
    "exynos9820-clk.h": "include/dt-bindings/clock/exynos9820.h",
    # SOURCES.md opisuje caly katalog sterownika dotyku jednym wzorcem
    "sec_ts.c": "drivers/input/touchscreen/sec_ts/y771/*",
}


def main():
    if not os.path.isdir(DS):
        print("check-sources-doc: brak sources/ds")
        return 2
    if not os.path.exists(DOC):
        print("check-sources-doc: brak SOURCES.md")
        return 2

    doc = open(DOC, encoding="utf-8", errors="replace").read()
    pliki = sorted(os.listdir(DS))
    brak, przez_alias = [], []
    for f in pliki:
        if not os.path.isfile(os.path.join(DS, f)):
            continue
        if f in doc:
            continue
        alias = ALIASY.get(f)
        if alias and alias in doc:
            przez_alias.append(f)
            continue
        brak.append(f)

    # Druga strona: alias, ktory przestal byc potrzebny, bo plik wystepuje juz
    # pod wlasna nazwa, jest martwym kodem w bramce i ma o sobie powiedziec.
    martwe = [f for f in ALIASY if f in doc]

    for f in brak:
        print("  FAIL %s lezy w sources/ds, a SOURCES.md go nie opisuje" % f)
    for f in martwe:
        print("  FAIL alias dla %s jest zbedny, plik wystepuje w SOURCES.md "
              "pod wlasna nazwa" % f)

    print("check-sources-doc: plikow %d, opisanych wprost %d, przez alias %d, "
          "bez opisu %d"
          % (len(pliki), len(pliki) - len(przez_alias) - len(brak),
             len(przez_alias), len(brak)))
    return 1 if (brak or martwe) else 0


if __name__ == "__main__":
    sys.exit(main())
