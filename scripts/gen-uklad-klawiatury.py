#!/usr/bin/env python3
"""Uklad klawiszy z klawiatury Qt na naglowek C.

Po co: uklad ma byc przeniesiony JEDEN DO JEDNEGO z klawiatury Qt, ktora
napisal uzytkownik (`tools/klawiatura/wzorzec/Layouts.qml`).  Przepisywanie go
recznie znaczy, ze przy kazdej zmianie wzorca ktos musi pamietac o drugim
pliku, a zapomnienie widac dopiero na telefonie.  Dlatego zrodlem prawdy jest
plik QML, a `tools/klawiatura/uklad.h` jest z niego generowany, a bramka
`scripts/check-uklad-klawiatury.py` pilnuje, ze oba sa zgodne.

Co przenosimy: cztery warstwy, kolejnosc rzedow, kolejnosc klawiszy, szerokosci
(pole `w`), odstepy (`sp`), wysokosc rzedu (`rh`), etykiety (`label`), znaki
(`t`), klawisze systemowe (`k`), akcje (`act`, `to`, `mod`), warianty pod
przytrzymaniem (`alt`) i autopowtarzanie (`rep`).

Szerokosci QML sa w jednostkach klawisza i nie musza sumowac sie do dziesieciu
(rzad z Enterem ma 10,5).  Qml dzieli szerokosc rzedu przez SUME wag, wiec
przenosimy wagi wprost, w setnych jednostki, a suma liczona jest osobno dla
kazdego rzedu.

Uzycie:
  scripts/gen-uklad-klawiatury.py            # statystyka
  scripts/gen-uklad-klawiatury.py --wypisz   # na standardowe wyjscie
  scripts/gen-uklad-klawiatury.py --zapisz   # wpisz do tools/klawiatura
"""
import io
import os
import re
import sys

NL = chr(10)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZRODLO = os.path.join(ROOT, "tools", "klawiatura", "wzorzec", "Layouts.qml")
CEL = os.path.join(ROOT, "tools", "klawiatura", "uklad.h")

# Kolejnosc warstw jest kolejnoscia z QML; numer warstwy trafia do pola docel
# klawiszy act:"layer", wiec nie wolno jej zmieniac bez zmiany obu plikow.
WARSTWY = ["letters", "symbols", "symbols2", "nav"]

# Klawisze systemowe: nazwa w QML na kod jadra.  Tabela przepisana
# z wzorzec/../src/keymap.cpp, zeby oba programy rozumialy te same nazwy.
NAZWANE = {
    "Backspace": "KEY_BACKSPACE", "Enter": "KEY_ENTER", "Tab": "KEY_TAB",
    "Esc": "KEY_ESC", "Space": "KEY_SPACE", "Delete": "KEY_DELETE",
    "Left": "KEY_LEFT", "Right": "KEY_RIGHT", "Up": "KEY_UP",
    "Down": "KEY_DOWN", "Home": "KEY_HOME", "End": "KEY_END",
    "PageUp": "KEY_PAGEUP", "PageDown": "KEY_PAGEDOWN",
    "F1": "KEY_F1", "F2": "KEY_F2", "F3": "KEY_F3", "F4": "KEY_F4",
    "F5": "KEY_F5", "F6": "KEY_F6", "F7": "KEY_F7", "F8": "KEY_F8",
    "F9": "KEY_F9", "F10": "KEY_F10", "F11": "KEY_F11", "F12": "KEY_F12",
}

MODYFIKATORY = {"ctrl": "KEY_LEFTCTRL", "alt": "KEY_LEFTALT"}

# Etykiety, ktore w QML sa znakami Unicode, a u nas rysowanymi ikonami.
IKONY = {
    "⇧": "IKONA_SHIFT",	# strzalka w gore z podstawka
    "⌫": "IKONA_BACKSPACE",
    "⏎": "IKONA_ENTER",
    "↑": "IKONA_GORA",
    "↓": "IKONA_DOL",
    "←": "IKONA_LEWO",
    "→": "IKONA_PRAWO",
}

NAGLOWEK = '''/* SPDX-License-Identifier: GPL-2.0 */
/* Uklad klawiszy klawiatury ekranowej.
 *
 * PLIK JEST GENEROWANY.  Zrodlem prawdy jest tools/klawiatura/wzorzec/
 * Layouts.qml, czyli uklad klawiatury Qt, a przepisuje go
 * scripts/gen-uklad-klawiatury.py.  Bramka scripts/check-uklad-klawiatury.py
 * pilnuje, ze oba sa zgodne, bo inaczej rozjazd widac dopiero na telefonie.
 *
 * Szerokosc klawisza jest w SETNYCH jednostki klawisza, tak jak pole w w QML,
 * i suma wag w rzedzie NIE musi byc rowna dziesieciu: rzad dzieli swoja
 * szerokosc przez wlasna sume wag.  Wysokosc rzedu jest w setnych wysokosci
 * rzedu wzorcowej (pole rh), bo rzad cyfr jest nizszy.
 */
#ifndef KLAWIATURA_UKLAD_H
#define KLAWIATURA_UKLAD_H

#include <linux/input-event-codes.h>

#include "ekran.h"

enum rola {
	ROLA_ZNAK = 0,		/* wstawia swoj znak */
	ROLA_NAZWANY,		/* klawisz systemowy: kod wprost */
	ROLA_SHIFT,		/* jedno dotkniecie shift, drugie blokada */
	ROLA_WARSTWA,		/* przechodzi do warstwy docel */
	ROLA_MOD,		/* Ctrl albo Alt: zapala sie do nastepnego znaku */
	ROLA_ODSTEP,		/* puste miejsce, nie rysowane i nieklikalne */
};

'''

STOPKA = '''
#endif /* KLAWIATURA_UKLAD_H */
'''


def czytaj_qml():
    if not os.path.exists(ZRODLO):
        sys.exit("brak %s" % ZRODLO)
    return io.open(ZRODLO, encoding="utf-8").read()


def wytnij_warstwe(tekst, nazwa):
    """Zawartosc tablicy readonly property var <nazwa>: [ ... ]."""
    wzor = r"readonly\s+property\s+var\s+" + nazwa + r"\s*:\s*\["
    m = re.search(wzor, tekst)
    if not m:
        sys.exit("w %s nie ma warstwy %s" % (ZRODLO, nazwa))
    i = m.end() - 1
    glebokosc = 0
    for j in range(i, len(tekst)):
        if tekst[j] == "[":
            glebokosc += 1
        elif tekst[j] == "]":
            glebokosc -= 1
            if glebokosc == 0:
                return tekst[i + 1:j]
    sys.exit("niedomknieta tablica warstwy %s" % nazwa)


def bez_komentarzy(tekst):
    return re.sub(r"//[^" + NL + r"]*", "", tekst)


def czytaj_napis(tekst, i):
    """Napis w cudzyslowach od pozycji i; zwraca (wartosc, nastepna pozycja)."""
    wynik = []
    i += 1
    while i < len(tekst):
        z = tekst[i]
        if z == "\\":
            wynik.append(tekst[i + 1])
            i += 2
            continue
        if z == '"':
            return "".join(wynik), i + 1
        wynik.append(z)
        i += 1
    sys.exit("niedomkniety napis w %s" % ZRODLO)


def czytaj_wartosc(tekst, i):
    while tekst[i] in " \t" + NL:
        i += 1
    if tekst[i] == '"':
        return czytaj_napis(tekst, i)
    if tekst[i] == "[":
        lista = []
        i += 1
        while True:
            while tekst[i] in " \t," + NL:
                i += 1
            if tekst[i] == "]":
                return lista, i + 1
            wartosc, i = czytaj_wartosc(tekst, i)
            lista.append(wartosc)
    m = re.match(r"(true|false|-?[0-9]+(?:\.[0-9]+)?)", tekst[i:])
    if not m:
        sys.exit("nieznana wartosc w %s przy %r" % (ZRODLO, tekst[i:i + 20]))
    slowo = m.group(1)
    if slowo == "true":
        return True, i + len(slowo)
    if slowo == "false":
        return False, i + len(slowo)
    return float(slowo), i + len(slowo)


def czytaj_obiekt(tekst, i):
    """Obiekt {klucz: wartosc, ...} od pozycji i."""
    pola = {}
    i += 1
    while True:
        while tekst[i] in " \t," + NL:
            i += 1
        if tekst[i] == "}":
            return pola, i + 1
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", tekst[i:])
        if not m:
            sys.exit("nieznane pole w %s przy %r" % (ZRODLO, tekst[i:i + 20]))
        klucz = m.group(1)
        i += m.end()
        pola[klucz], i = czytaj_wartosc(tekst, i)


def czytaj_rzedy(tresc):
    """Lista rzedow, kazdy lista slownikow opisujacych klawisze."""
    tresc = bez_komentarzy(tresc)
    rzedy = []
    i = 0
    while i < len(tresc):
        if tresc[i] == "[":
            rzad = []
            i += 1
            while True:
                while i < len(tresc) and tresc[i] in " \t," + NL:
                    i += 1
                if tresc[i] == "]":
                    i += 1
                    break
                if tresc[i] != "{":
                    sys.exit("w rzedzie spodziewam sie obiektu, jest %r"
                             % tresc[i:i + 20])
                pola, i = czytaj_obiekt(tresc, i)
                rzad.append(pola)
            rzedy.append(rzad)
            continue
        i += 1
    return rzedy


def c_napis(tekst):
    """Napis w C, zawsze w ASCII.

    Znaki spoza ASCII ida jako bajty w hex, a napis jest ROZBIJANY, gdy po
    sekwencji \\xNN idzie cyfra szesnastkowa: kompilator wciagnalby ja do tej
    samej sekwencji i zamiast dwoch bajtow wyszedlby jeden, inny.
    """
    if tekst is None:
        return "NULL"
    czesci = []
    biezaca = []
    poprzedni_hex = False
    for bajt in tekst.encode("utf-8"):
        znak_hex = False
        if bajt == 0x22:
            kawalek = '\\"'
        elif bajt == 0x5c:
            kawalek = "\\\\"
        elif 0x20 <= bajt < 0x7f:
            kawalek = chr(bajt)
        else:
            kawalek = "\\x%02x" % bajt
            znak_hex = True
        if poprzedni_hex and kawalek[0] in "0123456789abcdefABCDEF":
            czesci.append("".join(biezaca))
            biezaca = []
        biezaca.append(kawalek)
        poprzedni_hex = znak_hex
    czesci.append("".join(biezaca))
    return " ".join('"%s"' % c for c in czesci)


def opisz_klawisz(k):
    """Jeden inicjalizator struct klawisz."""
    etykieta = k.get("label")
    znak = k.get("t")
    rola = "ROLA_ZNAK"
    kod = "0"
    docel = "0"
    ikona = "IKONA_BRAK"

    if "sp" in k:
        rola = "ROLA_ODSTEP"
        waga = int(round(k["sp"] * 100))
    else:
        waga = int(round(k.get("w", 1.0) * 100))

    if "k" in k:
        nazwa = k["k"]
        if nazwa not in NAZWANE:
            sys.exit("nieznany klawisz systemowy %r" % nazwa)
        rola = "ROLA_NAZWANY"
        kod = NAZWANE[nazwa]
    elif k.get("act") == "shift":
        rola = "ROLA_SHIFT"
    elif k.get("act") == "layer":
        rola = "ROLA_WARSTWA"
        if k["to"] not in WARSTWY:
            sys.exit("nieznana warstwa docelowa %r" % k["to"])
        docel = str(WARSTWY.index(k["to"]))
    elif k.get("act") == "mod":
        rola = "ROLA_MOD"
        if k["mod"] not in MODYFIKATORY:
            sys.exit("nieznany modyfikator %r" % k["mod"])
        kod = MODYFIKATORY[k["mod"]]

    if etykieta in IKONY:
        ikona = IKONY[etykieta]
        etykieta = None

    warianty = k.get("alt", [])
    if len(warianty) > 3:
        sys.exit("wiecej niz trzy warianty przy %r" % k)
    lista = ", ".join([c_napis(w) for w in warianty] +
                      ["NULL"] * (3 - len(warianty)))

    return ("\t\t{ %s, %s, { %s }, %s, %d, %s, %s, %s, %d }"
            % (c_napis(etykieta), c_napis(znak), lista,
               ikona, waga, rola, docel, kod,
               1 if k.get("rep") else 0))


def emituj():
    tekst = czytaj_qml()
    warstwy = []
    for nazwa in WARSTWY:
        warstwy.append((nazwa, czytaj_rzedy(wytnij_warstwe(tekst, nazwa))))

    rzedow_max = max(len(r) for _, r in warstwy)
    w_rzedzie = max(len(k) for _, r in warstwy for k in r)

    linie = [NAGLOWEK.rstrip(NL)]
    linie.append("")
    linie.append("#define WARSTW\t\t%d" % len(warstwy))
    linie.append("#define RZEDOW_MAX\t%d" % rzedow_max)
    linie.append("#define W_RZEDZIE\t%d" % w_rzedzie)
    linie.append("#define WARIANTOW_MAX\t3")
    linie.append("")
    linie.append("struct klawisz {")
    linie.append("\tconst char *etykieta;\t/* NULL: rysuj znak */")
    linie.append("\tconst char *znak;\t/* tekst wstawiany, NULL dla akcji */")
    linie.append("\tconst char *warianty[WARIANTOW_MAX];")
    linie.append("\tenum ikona ikona;\t/* rysowana zamiast etykiety */")
    linie.append("\tunsigned short waga;\t/* szerokosc w setnych jednostki */")
    linie.append("\tunsigned char rola;")
    linie.append("\tunsigned char docel;\t/* warstwa dla ROLA_WARSTWA */")
    linie.append("\tunsigned short kod;\t/* KEY_* dla ROLA_NAZWANY i MOD */")
    linie.append("\tunsigned char powtarza;\t/* autopowtarzanie */")
    linie.append("};")
    linie.append("")
    linie.append("struct rzad {")
    linie.append("\tunsigned short wysokosc;\t/* w setnych wysokosci rzedu */")
    linie.append("\tunsigned char ile;")
    linie.append("\tstruct klawisz klawisze[W_RZEDZIE];")
    linie.append("};")
    linie.append("")
    linie.append("struct warstwa {")
    linie.append("\tconst char *nazwa;")
    linie.append("\tunsigned char rzedow;")
    linie.append("\tstruct rzad rzedy[RZEDOW_MAX];")
    linie.append("};")
    linie.append("")
    linie.append("static const struct warstwa UKLAD[WARSTW] = {")
    klawiszy = 0
    for nazwa, rzedy in warstwy:
        linie.append("\t{ %s, %d, {" % (c_napis(nazwa), len(rzedy)))
        for rzad in rzedy:
            wysokosc = int(round(rzad[0].get("rh", 1.0) * 100))
            linie.append("\t{ %d, %d, {" % (wysokosc, len(rzad)))
            for k in rzad:
                linie.append(opisz_klawisz(k) + ",")
                klawiszy += 1
            linie.append("\t} },")
        linie.append("\t} },")
    linie.append("};")
    return NL.join(linie) + STOPKA, len(warstwy), klawiszy


def main():
    tresc, warstw, klawiszy = emituj()
    if "--wypisz" in sys.argv:
        sys.stdout.write(tresc)
        return
    if "--zapisz" in sys.argv:
        io.open(CEL, "w", encoding="utf-8", newline=NL).write(tresc)
        print("zapisano %s (%d warstw, %d klawiszy, %d linii)"
              % (CEL, warstw, klawiszy, tresc.count(NL)))
        return
    print("warstw %d, klawiszy %d, naglowek %d linii"
          % (warstw, klawiszy, tresc.count(NL)))


if __name__ == "__main__":
    main()
