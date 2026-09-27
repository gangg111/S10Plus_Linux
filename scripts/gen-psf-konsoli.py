#!/usr/bin/env python3
"""Czcionka konsoli 32x64 dla telefonu, w formacie PSF2.

Po co: panel ma 1440 na 3040 pikseli przy ponad 500 pikselach na cal, wiec
najwieksza czcionka wbudowana w jadro (Terminus 16x32) daje znak szerokosci
okolo 0,8 mm. Na ekranie trzymanym w rece jest to na granicy czytelnosci.
Konsola tekstowa nie umie skalowac czcionki, ale umie zaladowac wieksza.

Jak: kazdy piksel zrodlowej czcionki staje sie kwadratem dwa na dwa. Ksztalt
liter bez zmian, rozmiar podwojny. Ta sama metoda, co w gen-font-32x64.py,
ktory robi to dla konsoli bootloadera.

Skad zrodlo i czemu NIE z jadra.  Wersja pierwsza brala tablice
`fontdata_ter16x32` z `sources/linux/lib/fonts`: 256 glifow, BEZ tablicy
Unicode.  Zmierzone, do czego to prowadzi: klawiatura po dodaniu polskich
znakow wysylala poprawne bajty (`c5 bc` dla `ż`), ale konsola rysowala `z`,
bo dla znaku bez glifu jadro siega po litere bazowa.  Uzytkownik pisal wiec
`zażółć`, a widzial `zazolc`.  Terminus z paczki ma 512 glifow ORAZ tablice
Unicode z kompletem polskich liter, wiec bierzemy jego i tablice przepisujemy
bez zmian: numery glifow sie nie zmieniaja, tylko kazdy glif jest wiekszy.

Uzycie: gen-psf-konsoli.py <plik wyjsciowy.psf>
"""
import os
import struct
import sys

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZRODLO = os.path.join(KATALOG, "sources", "fonts", "ter-v32n.psf")

SZER_ZR, WYS_ZR = 16, 32
SZER, WYS = SZER_ZR * 2, WYS_ZR * 2
BAJTOW_WIERSZ = (SZER + 7) // 8		# 4
NA_GLIF = BAJTOW_WIERSZ * WYS		# 256

PSF2_MAGIC = 0x864AB572
PSF2_MA_UNICODE = 0x01


def wczytaj_zrodlo():
    """Glify 16x32 i tablica Unicode z pliku PSF2."""
    dane = open(ZRODLO, "rb").read()
    if len(dane) < 32:
        sys.exit("%s jest za krotki na naglowek PSF2" % ZRODLO)
    magia, wersja, naglowek, flagi, ile, na_glif, wys, szer = \
        struct.unpack("<8I", dane[:32])
    if magia != PSF2_MAGIC:
        sys.exit("%s nie jest plikiem PSF2" % ZRODLO)
    if (szer, wys) != (SZER_ZR, WYS_ZR):
        sys.exit("oczekiwano czcionki %dx%d, a jest %dx%d"
                 % (SZER_ZR, WYS_ZR, szer, wys))
    if na_glif != WYS_ZR * 2:
        sys.exit("nieoczekiwany rozmiar glifu: %d bajtow" % na_glif)
    if not flagi & PSF2_MA_UNICODE:
        sys.exit("%s nie ma tablicy Unicode, a bez niej konsola zbija polskie"
                 " litery do liter bazowych" % ZRODLO)

    koniec = naglowek + ile * na_glif
    if len(dane) < koniec:
        sys.exit("%s jest krotszy, niz mowi naglowek" % ZRODLO)
    glify = [dane[naglowek + i * na_glif:naglowek + (i + 1) * na_glif]
             for i in range(ile)]
    return glify, dane[koniec:], wersja


def powieksz(glif):
    """Zamienia glif 16x32 na 32x64, podwajajac kazdy piksel w obu osiach."""
    wynik = bytearray()
    for w in range(WYS_ZR):
        bity = (glif[w * 2] << 8) | glif[w * 2 + 1]

        # Kazdy bit zrodla daje dwa bity obok siebie.
        szerokie = 0
        for k in range(SZER_ZR):
            if bity & (1 << (SZER_ZR - 1 - k)):
                szerokie |= 0b11 << (SZER - 2 - k * 2)

        wiersz = struct.pack(">I", szerokie)
        wynik += wiersz		# ten sam wiersz dwa razy: podwojenie w pionie
        wynik += wiersz
    return bytes(wynik)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if not os.path.exists(ZRODLO):
        sys.exit("brak %s (uruchom scripts/fetch-sources.sh)" % ZRODLO)

    male, unikod, wersja = wczytaj_zrodlo()
    duze = b"".join(powieksz(g) for g in male)

    naglowek = struct.pack("<8I", PSF2_MAGIC, wersja, 32, PSF2_MA_UNICODE,
                           len(male), NA_GLIF, WYS, SZER)

    with open(sys.argv[1], "wb") as f:
        f.write(naglowek)
        f.write(duze)
        f.write(unikod)

    print("zapisane %s: %d znakow %dx%d, tablica Unicode %d bajtow,"
          " razem %d bajtow"
          % (sys.argv[1], len(male), SZER, WYS, len(unikod),
             len(naglowek) + len(duze) + len(unikod)))


if __name__ == "__main__":
    main()
