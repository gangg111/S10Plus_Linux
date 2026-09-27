#!/bin/sh
# Buduje w WSL wszystkie moduly, ktore telefon laduje z /lib/modules/<wersja>/extra:
# gpu-sched, panfrost, drm_dma_helper, rfcomm (rozmowy przez Bluetooth) i kfifo_buf
# z drzewa jadra oraz decon9820, s6e3ha9_jas i brcm_sensorhub (hub czujnikow) spoza
# drzewa.
#
# Po co: zmiana konfiguracji jadra (np. sekcja diagnostyczna) zmienia uklad
# struktur, a vermagic zostaje ten sam, wiec stary modul zaladowalby sie do
# nowego jadra i mogl je wywrocic. Po KAZDEJ przebudowie jadra budowac tym
# skryptem i wgrywac tools/pc/wgraj-moduly-extra.sh PRZED wgraniem jadra.
#
# Uzycie (w WSL): sh tools/pc/buduj-moduly-extra.sh
# Wynik: /home/pm/ko-extra/*.ko (bez debug info, z sekcja .BTF)
exec </dev/null
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$HOME/linux"
K="make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8"
$K drivers/gpu/drm/scheduler/gpu-sched.ko drivers/gpu/drm/panfrost/panfrost.ko \
	drivers/gpu/drm/drm_dma_helper.ko net/bluetooth/rfcomm/rfcomm.ko \
	drivers/iio/buffer/kfifo_buf.ko >> /home/pm/kb.log 2>&1
D=/home/pm/decon9820
mkdir -p $D
cat "$repo/tools/phone/decon9820/decon9820.c" > $D/decon9820.c
cat "$repo/tools/phone/decon9820/decon9820-edid.h" > $D/decon9820-edid.h
cat "$repo/tools/phone/decon9820/Makefile" > $D/Makefile
$K M=$D modules 2>&1 | grep -E "error|warning" || true
# Jasnosc panelu: silnik dimmingu z serii plus modul spoza drzewa.
J=/home/pm/jasnosc
mkdir -p $J
for f in s6e3ha9_jasnosc.c s6e3ha9-tabele.h Makefile; do
	cat "$repo/tools/phone/s6e3ha9-jasnosc/$f" > $J/$f
done
for f in panel-samsung-s6e3ha9-dimming.c panel-samsung-s6e3ha9-dimming.h panel-samsung-s6e3ha9-dimming-data.h; do
	cat drivers/gpu/drm/panel/$f > $J/$f
done
$K M=$J modules 2>&1 | grep -E "error|warning" || true
# Hub czujnikow BCM47752 (port brcm_sensorhub, uruchamia go tools/phone/hubd).
H=/home/pm/hub-modul
rm -rf $H; mkdir -p $H
(cd "$repo/tools/phone/hub-modul" && tar cf - .) | tar xf - -C $H
(cd $H && make KDIR=$HOME/linux 2>&1 | grep -E "error|warning" | grep -v Reliable) || true
O=/home/pm/ko-extra
rm -rf $O; mkdir -p $O
for m in drivers/gpu/drm/scheduler/gpu-sched.ko drivers/gpu/drm/panfrost/panfrost.ko \
	 drivers/gpu/drm/drm_dma_helper.ko net/bluetooth/rfcomm/rfcomm.ko \
	 drivers/iio/buffer/kfifo_buf.ko $D/decon9820.ko $J/s6e3ha9_jas.ko \
	 $H/brcm_sensorhub.ko; do
	aarch64-linux-gnu-strip --strip-debug -o "$O/$(basename $m)" "$m"
done
# Listy sterownikow wbudowanych. Bez nich depmod robi pusty modules.builtin.bin
# i `modprobe <wbudowany>` konczy sie "Module not found", co zmierzone
# 26.09.2026 wywracalo zramstart pmOS (set -e po modprobe zram).
cp modules.builtin modules.builtin.modinfo $O/
for m in $O/*.ko; do
	printf '%-18s %8s B  %s\n' "$(basename $m)" "$(stat -c %s $m)" "$(modinfo -F vermagic $m)"
done
cat include/config/kernel.release
