#!/bin/sh
# Buduje paczki adaptacji natywnie na telefonie (Droidian, arm64).
# Uruchamiac na telefonie z katalogu, do ktorego skopiowano tools/phone/adaptacja.
# Wynik: ../adaptation-samsung-beyond2lte{,-configs,-tools}_<wersja>_*.deb
# Dowod: dpkg-deb -c pokazuje komplet plikow, a sumy binarek w -tools zgadzaja sie z README.md.
set -e
cd "$(dirname "$0")"
chmod +x debian/rules debian/*.preinst debian/*.postinst debian/*.postrm usr/lib/s10plus/*.py
rm -rf debian/.debhelper debian/adaptation-samsung-beyond2lte debian/adaptation-samsung-beyond2lte-configs \
	debian/adaptation-samsung-beyond2lte-tools debian/files debian/*.substvars debian/debhelper-build-stamp
dpkg-buildpackage -b -uc -us > ../adaptacja-deb.log 2>&1 || { tail -30 ../adaptacja-deb.log; exit 1; }
ls -la ../adaptation-samsung-beyond2lte*_$(dpkg-parsechangelog -S Version)_*.deb
