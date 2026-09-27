#!/usr/bin/env python3
"""Sprawdza, ze naglowek czcionki proporcjonalnej rowna sie wyjsciu generatora.

Po co osobna bramka.  tools/klawiatura/czcionka-sans.h ma 137 kB wartosci alfy
wyliczonych z pliku TTF.  Recznej zmiany w takim pliku nikt nie zauwazy, a
zobaczy ja dopiero na ekranie telefonu, w postaci krzywej litery.  Generator
jest zrodlem prawdy, wiec bramka pyta wprost, czy plik rowna sie jego wyjsciu.

Ta sama zasada, co przy czcionce konsoli (scripts/check-font-klawiatury.py);
roznica jest taka, ze tamta przepisuje bitmape z jadra, a ta rasteryzuje krzywe
Bezier z pliku DroidSans.ttf, wiec zalezy jeszcze od wersji biblioteki PIL.
Gdyby PIL zmienil rasteryzator, bramka to pokaze i wtedy trzeba przegenerowac
plik i obejrzec klawiature, a nie tlumic roznice.

Porownanie ignoruje koncowki linii, bo drzewo gita na Windowsie oddaje pliki
z CRLF, a generator pisze to, co dostanie od Pythona.

Exit 0, gdy plik zgadza sie z generatorem.  Exit 1 przy roznicy.
Exit 2, gdy bramki NIE DA SIE uruchomic (brak pliku TTF albo brak PIL): to nie
jest zielone swiatlo i verify.sh liczy to jako bramke nieuruchomiona.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR = os.path.join(ROOT, "scripts", "gen-font-sans-klawiatury.py")
PLIK = os.path.join(ROOT, "tools", "klawiatura", "czcionka-sans.h")
TTF = os.path.join(ROOT, "sources", "fonts", "DroidSans.ttf")
NL = chr(10)


def znormalizuj(tekst):
    return tekst.replace(chr(13) + chr(10), NL).replace(chr(13), NL)


def szukaj_interpretera():
    """Pierwszy python, ktory umie zaimportowac PIL."""
    kandydaci = [[sys.executable], ["py", "-3.12"], ["py", "-3"],
                 ["python"], ["python3"]]
    for k in kandydaci:
        try:
            r = subprocess.run([*k, "-c", "import PIL"],
                               capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0:
            return k
    return None


def main():
    if not os.path.exists(TTF):
        print("check-font-sans: brak %s, uruchom scripts/fetch-sources.sh"
              % os.path.relpath(TTF, ROOT))
        return 2
    if not os.path.exists(PLIK):
        print("check-font-sans: brak %s" % os.path.relpath(PLIK, ROOT))
        return 1
    # Interpreter, ktory ma PIL, nie musi byc tym, ktorym nas uruchomiono.
    # verify.sh dokłada do PATH katalog MSYS2 (dla clanga), a tamten python3
    # nie ma bibliotek CPythona.  Szukamy wiec pierwszego, ktory PIL ma,
    # zamiast uznawac bramke za nieuruchamialna.
    interpreter = szukaj_interpretera()
    if interpreter is None:
        print("check-font-sans: zaden dostepny python nie ma biblioteki PIL")
        return 2

    r = subprocess.run([*interpreter, GENERATOR, "--wypisz"],
                       capture_output=True, text=True)
    if r.returncode:
        print("check-font-sans: generator padl:%s%s" % (NL, r.stderr.strip()))
        return 2

    with open(PLIK, encoding="utf-8") as f:
        maja = znormalizuj(f.read())
    ma_byc = znormalizuj(r.stdout)

    if maja == ma_byc:
        print("check-font-sans: %s zgadza sie z generatorem (%d linii)"
              % (os.path.relpath(PLIK, ROOT), maja.count(NL)))
        return 0

    a = maja.split(NL)
    b = ma_byc.split(NL)
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            print("check-font-sans: roznica w wierszu %d" % (i + 1))
            print("  plik:      %s" % a[i][:90])
            print("  generator: %s" % b[i][:90])
            break
    else:
        print("check-font-sans: rozna liczba wierszy: plik %d, generator %d"
              % (len(a), len(b)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
