#!/usr/bin/env python3
"""Sprawdza czcionke konsoli: 512 glifow, tablica Unicode i polskie litery.

Po co osobna bramka.  `ter32x64.psf` nie jest trzymana w drzewie, tylko
generowana przy wszywaniu do obrazu, wiec nie ma z czym porownywac tresci.
Ale wlasnie dlatego nikt nie zauwazy, ze generator zaczal wypluwac czcionke
BEZ tablicy Unicode: klawiatura bedzie wysylac poprawne bajty, a konsola
narysuje `z` zamiast `ż` (zmierzone, measurements/2026-09-22-ogonki-
przytrzymanie).  Bramka sprawdza wiec WLASNOSCI wyniku, a nie jego sume.

Sprawdzane:
  1. Generator konczy sie bez bledu.
  2. Naglowek PSF2: 512 glifow, 32 na 64 piksele, znacznik tablicy Unicode.
  3. Tablica Unicode zna wszystkie osiemnascie polskich liter.
  4. Glif przypisany literze `ą` ma zapalone piksele, czyli nie jest pusty.

Exit 0, gdy wszystko sie zgadza.  Exit 1, gdy czcionka jest zla.
Exit 2, gdy bramki NIE DA SIE uruchomic (brak pliku zrodlowego).
"""
import os
import struct
import subprocess
import sys
import tempfile

NL = chr(10)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR = os.path.join(ROOT, "scripts", "gen-psf-konsoli.py")
ZRODLO = os.path.join(ROOT, "sources", "fonts", "ter-v32n.psf")

POLSKIE = [0x0105, 0x0107, 0x0119, 0x0142, 0x0144, 0x00f3, 0x015b, 0x017a,
           0x017c, 0x0104, 0x0106, 0x0118, 0x0141, 0x0143, 0x00d3, 0x015a,
           0x0179, 0x017b]

PSF2_MAGIC = 0x864AB572
PSF2_MA_UNICODE = 0x01


def czytaj_tablice(dane, naglowek, ile, na_glif):
    """Kod znaku na numer glifu, z tablicy Unicode formatu PSF2."""
    tab = dane[naglowek + ile * na_glif:]
    mapa = {}
    biezacy = bytearray()
    glif = 0
    for bajt in tab:
        if bajt in (0xFF, 0xFE):
            if biezacy:
                for znak in biezacy.decode("utf-8", "replace"):
                    mapa.setdefault(ord(znak), glif)
                biezacy = bytearray()
            if bajt == 0xFF:
                glif += 1
            continue
        biezacy.append(bajt)
    return mapa


def main():
    if not os.path.exists(ZRODLO):
        print("check-psf: brak %s, uruchom scripts/fetch-sources.sh"
              % os.path.relpath(ZRODLO, ROOT))
        return 2

    kat = tempfile.mkdtemp()
    cel = os.path.join(kat, "ter32x64.psf")
    r = subprocess.run([sys.executable, GENERATOR, cel],
                       capture_output=True, text=True)
    if r.returncode:
        print("check-psf: generator padl:%s%s" % (NL, r.stderr.strip()))
        os.rmdir(kat)
        return 2

    with open(cel, "rb") as f:
        dane = f.read()
    os.remove(cel)
    os.rmdir(kat)

    magia, wersja, naglowek, flagi, ile, na_glif, wys, szer = \
        struct.unpack("<8I", dane[:32])
    if magia != PSF2_MAGIC:
        print("check-psf: wynik nie jest plikiem PSF2")
        return 1
    if (szer, wys) != (32, 64):
        print("check-psf: czcionka ma %dx%d, a ma miec 32x64" % (szer, wys))
        return 1
    if ile != 512:
        print("check-psf: %d glifow, a ma byc 512" % ile)
        return 1
    if not flagi & PSF2_MA_UNICODE:
        print("check-psf: brak tablicy Unicode; konsola zbije polskie litery"
              " do liter bazowych")
        return 1

    mapa = czytaj_tablice(dane, naglowek, ile, na_glif)
    brak = ["U+%04x" % k for k in POLSKIE if k not in mapa]
    if brak:
        print("check-psf: tablica Unicode nie zna: %s" % " ".join(brak))
        return 1

    # Glif litery `ą` musi miec zapalone piksele: pusty znaczy, ze tablica
    # wskazuje w niezapisane miejsce.
    nr = mapa[0x0105]
    glif = dane[naglowek + nr * na_glif:naglowek + (nr + 1) * na_glif]
    if not any(glif):
        print("check-psf: glif litery a z ogonkiem jest pusty")
        return 1

    print("check-psf: %d glifow %dx%d, tablica Unicode zna %d znakow,"
          " komplet polskich liter" % (ile, szer, wys, len(mapa)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
