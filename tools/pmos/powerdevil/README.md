# PowerDevil z Alpine 6.7.5-r1 + latka ukrywajaca uspienie

Latka `hide-suspend-when-unsupported.patch`: modul ustawien zasilania Plasma Mobile
(kcm_mobile_power) dostaje wlasciwosc `canSuspend`, a pole "Suspend device after" i
separator nad nim pokazuja sie tylko, gdy uspienie jest mozliwe.  Na tym telefonie
uspienie jest wylaczone (tools/phone/bez-usypiania), wiec pole znika.

pkgrel=100, zeby apk wolal ten pakiet przed Alpine 6.7.5-r1.  Po aktualizacji
Plasmy w Alpine przeniesc latke na nowa wersje.

Budowa (WSL, pmbootstrap):

    cp APKBUILD *.patch ~/.local/var/pmbootstrap/cache_git/pmaports/temp/powerdevil/
    pmbootstrap -y --no-ccache build --arch aarch64 powerdevil

Dwie pulapki: download.kde.org potrafi zerwac polaczenie (archiwum wlozyc recznie do
cache_distfiles, sha512 z APKBUILD), a ccache w buildroot_aarch64 konczy sie
"Permission denied" (stad --no-ccache).
