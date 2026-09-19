#!/usr/bin/env python3
"""Sprawdza, ze pliki drzewa urzadzen w serii sa DOKLADNIE tym, co wypisuja ich generatory.

Po co osobna bramka. Oba generatory pisza o sobie, ze sa zrodlem prawdy dla swojego pliku,
ale az do 11 wrzesnia 2026 nikt tego nie sprawdzal, i jeden z nich sie rozjechal: caly blok
reserved-memory (jedenascie rezerwacji dolozonych w rundzie R9) istnial tylko w serii, a
generator pliku plyty go nie znal. Jego wersja byla o 79 wierszy krotsza i cofnelaby prace,
gdyby ktos jej uzyl. Rozjazd nie dawal zadnego objawu, bo generatora nikt nie uruchamial.
(Drugi generator, ten od pliku SoC, byl wtedy zgodny na wszystkich czterech etapach.)

Co jest sprawdzane dla kazdego pliku: rosnie on w serii etapami, po jednym commicie na etap,
wiec bramka wymaga, zeby plik dotykalo DOKLADNIE tyle commitow, ile generator ma etapow,
i zeby tresc po k-tym commicie byla identyczna z wyjsciem `--etap k`. Trzeci commit tam, gdzie
generator zna dwa etapy, znaczy nowy etap, o ktorym generator nie wie, i tez zapala bramke.

Porownanie ignoruje koncowki linii, bo drzewo gita na Windowsie oddaje pliki z CRLF, a
generator pisze to, co dostanie od Pythona.

Exit 0, gdy wszystkie etapy wszystkich plikow sie zgadzaja. Exit 1 przy pierwszej roznicy.
Exit 2, gdy bramki NIE DA SIE uruchomic (brak repozytorium w sources/linux): to nie jest
zielone swiatlo i verify.sh liczy to jako bramke nieuruchomiona.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINUX = os.path.join(ROOT, "sources", "linux")
GALAZ = "series"
BAZA = "1200d84f4c0a929a0780180d25063d93773be79c"

# (generator, sciezka w drzewie jadra, liczba etapow)
PLIKI = (
    ("gen-dts-exynos9820.py", "arch/arm64/boot/dts/exynos/exynos9820.dtsi", 4),
    ("gen-dts-beyond2lte.py", "arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dts", 2),
)


def git(*args):
    r = subprocess.run(["git", "-C", LINUX, *args], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("blad gita: git %s%s%s" % (" ".join(args), chr(10), r.stderr.strip()))
    return r.stdout


def generuj(generator, etap):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", generator),
                        "--etap", str(etap)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("%s padl na etapie %d:%s%s" % (generator, etap, chr(10), r.stderr.strip()))
    return r.stdout


def znormalizuj(tekst):
    return tekst.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10))


def pierwsza_roznica(a, b):
    ax, bx = znormalizuj(a).split(chr(10)), znormalizuj(b).split(chr(10))
    for i in range(max(len(ax), len(bx))):
        wa = ax[i] if i < len(ax) else "(koniec pliku)"
        wb = bx[i] if i < len(bx) else "(koniec pliku)"
        if wa != wb:
            return i + 1, wa, wb
    return None


def sprawdz(generator, sciezka, etapy):
    """Zwraca liczbe bledow dla jednego pliku."""
    commity = [c for c in git("log", "--format=%H", "%s..%s" % (BAZA, GALAZ),
                              "--", sciezka).split() if c]
    commity.reverse()  # git log daje najnowszy pierwszy, chcemy od najstarszego
    nazwa = os.path.basename(sciezka)
    if len(commity) != etapy:
        print("BLAD: %s dotyka %d commitow serii, a %s zna %d etapow"
              % (nazwa, len(commity), generator, etapy))
        for c in commity:
            print("  %s %s" % (c[:11], git("log", "-1", "--format=%s", c).strip()))
        print("  Dopisz brakujacy etap w scripts/%s albo zloz zmiany w tych" % generator)
        print("  commitach, ktore generator odtwarza.")
        return 1
    bledy = 0
    for etap, rewizja in enumerate(commity, start=1):
        roznica = pierwsza_roznica(generuj(generator, etap),
                                   git("show", "%s:%s" % (rewizja, sciezka)))
        if roznica is None:
            print("OK: %s etap %d zgadza sie z %s" % (nazwa, etap, rewizja[:11]))
            continue
        bledy += 1
        wiersz, wg, ws = roznica
        print("BLAD: %s etap %d rozni sie od %s w wierszu %d"
              % (nazwa, etap, rewizja[:11], wiersz))
        print("  generator: %s" % wg)
        print("  seria    : %s" % ws)
    return bledy


def main():
    if not os.path.isdir(os.path.join(LINUX, ".git")):
        print("NIEURUCHOMIONA: brak repozytorium w sources/linux")
        return 2
    bledy = sum(sprawdz(*p) for p in PLIKI)
    if bledy:
        print("Napraw generator albo wszczep zmiane przez niego")
        print("(scripts/<generator> --etap N --zapisz), nie recznie w pliku.")
    return 1 if bledy else 0


if __name__ == "__main__":
    sys.exit(main())
