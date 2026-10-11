#!/bin/sh
# Buduje paczki adaptacji natywnie na telefonie (Droidian, arm64).
# Uruchamiac na telefonie z katalogu, do ktorego skopiowano tools/phone/adaptacja.
# Wynik: ../adaptation-samsung-beyond2lte{,-configs,-tools}_<wersja>_*.deb
# Dowod: dpkg-deb -c pokazuje komplet plikow, a sumy binarek w -tools zgadzaja sie z README.md.
set -e
cd "$(dirname "$0")"
# Tryby zawsze od zera, niezaleznie od zrodla: z dysku Windowsa (/mnt/c) wszystko ma
# 777, a debhelper URUCHAMIA wykonywalny plik .install jako skrypt dh-exec (tak
# wystartowal plasma_session w trakcie budowy). Z gita z kolei bit x bywa zgubiony
# (core.filemode=false), a dh_fixperms nadaje go tylko w */bin.
find . -type f -exec chmod 0644 {} +
chmod +x debian/rules debian/*.preinst debian/*.postinst debian/*.postrm usr/lib/s10plus/* tools/maliit/maliit-keyboard buduj.sh
rm -rf debian/.debhelper debian/adaptation-samsung-beyond2lte debian/adaptation-samsung-beyond2lte-configs \
	debian/adaptation-samsung-beyond2lte-tools debian/files debian/*.substvars debian/debhelper-build-stamp
dpkg-buildpackage -b -uc -us > ../adaptacja-deb.log 2>&1 || { tail -30 ../adaptacja-deb.log; exit 1; }
ls -la ../adaptation-samsung-beyond2lte*_$(dpkg-parsechangelog -S Version)_*.deb
