#!/bin/sh
# Programy testowe libcamx (strona Linuksa) NA TELEFONIE. libcamx.so sam jest czescia
# aplikacji aparatu (src/camx/ w patches/) i instaluje go paczka do
# /usr/lib/droidian-camera/libcamx.so. Zrodla aplikacji (naglowki cam2.h, dng-writer)
# bierze z ~/src/droidian-camera (po ../buduj.sh).
# Uruchomienie (aplikacja aparatu musi byc zamknieta):
#   LD_PRELOAD=libtls-padding.so ./camx-test [kamera] [sciezka libcamx.so]
#   LD_PRELOAD=libtls-padding.so ./cam2-test [kamera] [sciezka libcamx.so] [katalog]
# Dowod dzialania camx-test: camx_check 1, z obcym listenerem 0, exposure-compensation
# 20/-20 przyjete (kod 0), 99 odrzucone (-22), tryby ostrosci z warstwy zgodnosci zgodne.
# Dowod dzialania cam2-test: ISO 50-3200, czas 85-100000 us, raw 1 (4032x3024); zdjecie
# z recznym ISO 800 i 20 ms daje JPEG (ffd8..ffd9) i linie RAW z ISO 800 20000 us,
# a seria 5 klatek "wynik 5". Pliki testowe usun po sprawdzeniu.
set -e
cd "$(dirname "$0")"
A=$HOME/src/droidian-camera/src
cc -O2 -o camx-test camx-test.c -I/usr/include/hybris -lcamera -lhybris-common
g++ -O2 -I $A -o cam2-test cam2-test.cpp $A/dng-writer.cpp -lhybris-common
ls -la camx-test cam2-test
