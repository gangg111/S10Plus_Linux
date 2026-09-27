#!/usr/bin/env python3
"""Rasteryzuje Droid Sans do naglowka C dla klawiatury ekranowej.

Po co, skoro klawiatura ma juz czcionke.  Ma, ale konsolowa: Terminus 16x32,
bitmapa jednobitowa o stalej szerokosci, skalowana calkowicie.  Wyglada jak
terminal, bo nim jest.  Klawiatura ma wygladac jak klawiatura, a to znaczy
czcionke proporcjonalna, wygladzona i w dowolnym rozmiarze.

Zrodlo nie jest przypadkowe: telefon renderuje napisy przez fontconfig, ktory
na "Sans" odpowiada DOKLADNIE tym plikiem (sprawdzone na urzadzeniu:
`fc-match Sans` daje `DroidSans.ttf "Droid Sans" "Regular"`).  Klawiatura w C
uzywa wiec tej samej czcionki, co reszta systemu, zamiast swojej wlasnej.

Zapis: alfa po osiem bitow na piksel, glif przyciety do realnego zasiegu
tuszu.  Cztery bity wystarczaly do czytania, ale NIE do zgodnosci z Qt: przy
szesnastu poziomach obwodka litery skacze o 17 jednostek naraz i litera mierzy
sie o piksel wieksza z kazdej strony.  Przyciecie do tuszu oddaje z powrotem
wiecej, niz kosztuje pelna alfa, bo pudelko UKLADU jest szersze od litery
(dla "a" 38 pikseli wobec 30).

Rasteryzujemy w JEDNYM rozmiarze i skalujemy w locie w C, bo tablica dla
kazdego rozmiaru osobno kosztowalaby drugie tyle.

Uzycie:
  scripts/gen-font-sans-klawiatury.py            # statystyka
  scripts/gen-font-sans-klawiatury.py --wypisz   # na standardowe wyjscie
  scripts/gen-font-sans-klawiatury.py --zapisz   # wpisz do tools/klawiatura
"""
import io
import os
import sys

from PIL import Image, ImageDraw, ImageFont

NL = chr(10)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTF = os.path.join(ROOT, "sources", "fonts", "DroidSans.ttf")
CEL = os.path.join(ROOT, "tools", "klawiatura", "czcionka-sans.h")

# Rozmiar rasteryzacji.  Najwiekszy napis na klawiszu ma wysokosc 0,40 rzedu,
# a rzad ma okolo 180 pikseli, wiec 72 piksele to rozmiar uzywany wprost,
# bez pomniejszania, dla liter i cyfr.
ROZMIAR = 72
PIERWSZY = 32
OSTATNI = 126

# Polskie znaki diakrytyczne, dostepne na klawiaturze pod dlugim
# przytrzymaniem klawisza podstawowego.  Sa POZA zakresem ASCII, wiec ida
# osobna tablica, a nie przez indeks kodu: inaczej trzeba by wygenerowac
# wszystko od 32 do 380 i wiekszosc tablicy bylaby pusta.
DODATKOWE = [
    0x0105, 0x0107, 0x0119, 0x0142, 0x0144, 0x00f3, 0x015b, 0x017a, 0x017c,
    0x0104, 0x0106, 0x0118, 0x0141, 0x0143, 0x00d3, 0x015a, 0x0179, 0x017b,
]

NAGLOWEK = '''/* SPDX-License-Identifier: GPL-2.0 */
/* Czcionka klawiatury: Droid Sans, wygladzona, proporcjonalna.
 *
 * PLIK JEST GENEROWANY.  Zrodlem prawdy jest
 * scripts/gen-font-sans-klawiatury.py, a bramka scripts/check-font-sans.py
 * pilnuje, zeby oba byly zgodne.  Recznej zmiany tutaj nikt nie zauwazy,
 * a zobaczy ja dopiero na ekranie telefonu.
 *
 * Skad ta czcionka: telefon rozwiazuje "Sans" wlasnie na DroidSans.ttf
 * (fc-match na urzadzeniu), wiec klawiatura pisze tym samym krojem, co reszta
 * systemu, zamiast czcionka konsoli.
 *
 * Alfa siedzi po jednym bajcie na piksel, wierszami, a glif jest przyciety do
 * realnego zasiegu tuszu: pola lewo i gora mowia, o ile odsunac go od punktu
 * pisania.
 */
#ifndef KLAWIATURA_CZCIONKA_SANS_H
#define KLAWIATURA_CZCIONKA_SANS_H

'''


def wczytaj():
    if not os.path.exists(TTF):
        sys.exit("brak %s, uruchom scripts/fetch-sources.sh" % TTF)
    return ImageFont.truetype(TTF, ROZMIAR)


def glify(font, kody):
    """Dla kazdego znaku: maska alfa przycieta do zasiegu tuszu."""
    wynik = []
    for kod in kody:
        znak = chr(kod)
        zaliczka = int(round(font.getlength(znak)))
        bbox = font.getbbox(znak)
        if bbox is None or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            wynik.append((kod, 0, 0, 0, 0, zaliczka, b""))
            continue
        szer = bbox[2] - bbox[0]
        wys = bbox[3] - bbox[1]
        # Rysujemy na plotnie pudelka UKLADU, a potem przycinamy do tego,
        # co naprawde ma tusz: getbbox() PIL-a zwraca pudelko ukladu, wiec
        # dla wiekszosci liter zostawia puste marginesy po bokach.
        obraz = Image.new("L", (szer, wys), 0)
        rysownik = ImageDraw.Draw(obraz)
        rysownik.text((-bbox[0], -bbox[1]), znak, font=font, fill=255)
        tusz = obraz.getbbox()
        if tusz is None:
            wynik.append((kod, 0, 0, 0, 0, zaliczka, b""))
            continue
        obraz = obraz.crop(tusz)
        wynik.append((kod, obraz.width, obraz.height,
                      bbox[0] + tusz[0], bbox[1] + tusz[1], zaliczka,
                      obraz.tobytes()))
    return wynik


def emituj():
    font = wczytaj()
    wzniesienie, opadanie = font.getmetrics()
    lista = glify(font, range(PIERWSZY, OSTATNI + 1))
    extra = glify(font, DODATKOWE)

    dane = bytearray()
    wpisy = []
    for kod, szer, wys, lewo, gora, zaliczka, alfa in lista:
        offset = len(dane)
        dane += alfa
        wpisy.append((kod, szer, wys, lewo, gora, zaliczka, offset))
    wpisy_extra = []
    for kod, szer, wys, lewo, gora, zaliczka, alfa in extra:
        offset = len(dane)
        dane += alfa
        wpisy_extra.append((kod, szer, wys, lewo, gora, zaliczka, offset))

    linie = [NAGLOWEK.rstrip(NL)]
    linie.append("")
    linie.append("#define SANS_ROZMIAR\t%d" % ROZMIAR)
    linie.append("#define SANS_BAZA\t%d" % wzniesienie)
    linie.append("#define SANS_WYSOKOSC\t%d" % (wzniesienie + opadanie))
    linie.append("#define SANS_PIERWSZY\t%d" % PIERWSZY)
    linie.append("#define SANS_OSTATNI\t%d" % OSTATNI)
    linie.append("")
    linie.append("struct glif_sans {")
    linie.append("\tunsigned short szer, wys;\t/* rozmiar maski alfa */")
    linie.append("\tshort lewo, gora;\t\t/* przesuniecie wzgledem punktu pisania */")
    linie.append("\tunsigned short zaliczka;\t/* o ile przesunac sie dalej */")
    linie.append("\tunsigned int offset;\t\t/* poczatek w SANS_ALFA */")
    linie.append("};")
    linie.append("")
    linie.append("static const struct glif_sans SANS_GLIFY[SANS_OSTATNI - SANS_PIERWSZY + 1] = {")
    for kod, szer, wys, lewo, gora, zaliczka, offset in wpisy:
        opis = chr(kod) if 33 <= kod <= 126 else "spacja"
        linie.append("\t{ %3d, %3d, %4d, %4d, %3d, %7d },\t/* %s */"
                     % (szer, wys, lewo, gora, zaliczka, offset, opis))
    linie.append("};")
    linie.append("")
    linie.append("/* Znaki poza ASCII, szukane po kodzie.  Kolejnosc jak w")
    linie.append(" * generatorze: najpierw male, potem wielkie. */")
    linie.append("struct glif_dodatkowy {")
    linie.append("	unsigned int kod;")
    linie.append("	struct glif_sans glif;")
    linie.append("};")
    linie.append("")
    linie.append("#define SANS_DODATKOWYCH	%d" % len(wpisy_extra))
    linie.append("static const struct glif_dodatkowy SANS_DODATKOWE[SANS_DODATKOWYCH] = {")
    for kod, szer, wys, lewo, gora, zaliczka, offset in wpisy_extra:
        linie.append("	{ 0x%04x, { %3d, %3d, %4d, %4d, %3d, %7d } },"
                     % (kod, szer, wys, lewo, gora, zaliczka, offset))
    linie.append("};")
    linie.append("")
    linie.append("static const unsigned char SANS_ALFA[%d] = {" % len(dane))
    for i in range(0, len(dane), 16):
        kawalek = dane[i:i + 16]
        linie.append("\t" + " ".join("0x%02x," % b for b in kawalek))
    linie.append("};")
    linie.append("")
    linie.append("#endif /* KLAWIATURA_CZCIONKA_SANS_H */")
    return NL.join(linie) + NL, len(dane), len(wpisy) + len(wpisy_extra)


def main():
    tresc, bajtow, znakow = emituj()
    if "--wypisz" in sys.argv:
        sys.stdout.write(tresc)
        return
    if "--zapisz" in sys.argv:
        io.open(CEL, "w", encoding="utf-8", newline=NL).write(tresc)
        print("zapisano %s (%d znakow, %d bajtow alfy, %d linii)"
              % (CEL, znakow, bajtow, tresc.count(NL)))
        return
    print("znakow %d, alfa %d bajtow, naglowek %d linii"
          % (znakow, bajtow, tresc.count(NL)))


if __name__ == "__main__":
    main()
