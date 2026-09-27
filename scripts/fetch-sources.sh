#!/bin/sh
# Pobiera przypięte źródła do sources/ (patrz SOURCES.md). Idempotentne.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
src="$root/sources"
mkdir -p "$src"

clone_pin() {   # $1 url  $2 dir  $3 commit  [$4 branch]
	if [ ! -d "$src/$2/.git" ]; then
		if [ $# -ge 4 ]; then
			git clone --depth=1 -b "$4" "$1" "$src/$2"
		else
			git clone --depth=1 "$1" "$src/$2"
		fi
	fi
	# Jesli przypiety commit juz jest w repo, NIE ruszamy HEAD. Skrypt bywa
	# uruchamiany ponownie na drzewie z nalozona seria i checkout skasowalby
	# ja bez slowa.
	if git -C "$src/$2" cat-file -e "$3^{commit}" 2>/dev/null; then
		echo "  $2: przypiety commit juz jest, HEAD bez zmian"
		return 0
	fi
	git -C "$src/$2" fetch --depth=1 origin "$3" 2>/dev/null || true
	git -C "$src/$2" checkout -q "$3" 2>/dev/null ||
		echo "WARN: $2 nie ma commitu $3 (plytki klon), sprawdz SOURCES.md" >&2
}

clone_pin https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git \
	linux 1200d84f4c0a929a0780180d25063d93773be79c
# Baza naszego wlasnego bootloadera (patrz patches-uboot/README.md).
clone_pin https://source.denx.de/u-boot/u-boot.git \
	u-boot 211de43d0f954a00a490220c1aac9db298287c40

clone_pin https://gitlab.postmarketos.org/postmarketOS/pmaports.git \
	pmaports 78958726e3f1a277bc3c568a7ba21b70ae642c9a
clone_pin https://github.com/ivoszbg/uniLoader.git \
	uniLoader 2fb7820aaf3b20db7b9d2e72ce45f42eb52f1d10

# Pojedyncze pliki dowodowe (całe drzewa downstreamu są niepotrzebne).
ds=$src/ds; mkdir -p "$ds"
DS=https://raw.githubusercontent.com/LineageOS/android_kernel_samsung_exynos9820/7d08ec364a0659edcf90a8dae4453b21e4542311
UB=https://raw.githubusercontent.com/chiffathefox/u-boot/c5afa30840d92471b5fea4421b10b0a8d83b449b/dts/upstream/src/arm64/exynos
CH=https://raw.githubusercontent.com/chiffathefox/exynos-9820-mainline-linux/0aeca03f7acddd3aacdf25b01fede0ee3c724d48

for f in arch/arm64/boot/dts/exynos/exynos9820.dts \
	 arch/arm64/configs/exynos9820-beyond2lte_defconfig \
	 drivers/soc/samsung/cal-if/pmucal_cpu.c \
	 drivers/soc/samsung/cal-if/pmucal_cpu.h \
	 drivers/soc/samsung/cal-if/pmucal_rae.c \
	 drivers/soc/samsung/cal-if/pmucal_powermode.c \
	 drivers/soc/samsung/cal-if/pmucal_powermode.h \
	 drivers/soc/samsung/cal-if/cal-if.c \
	 drivers/soc/samsung/cal-if/pmucal_common.h \
	 drivers/soc/samsung/exynos-cpupm.c \
	 drivers/pinctrl/samsung/pinctrl-exynos-arm64.c \
	 drivers/pinctrl/samsung/pinctrl-exynos.h \
	 drivers/video/fbdev/exynos/panel/panel_drv.c \
	 drivers/video/fbdev/exynos/panel/panel_drv.h \
	 drivers/video/fbdev/exynos/panel/panel.c \
	 drivers/video/fbdev/exynos/panel/panel.h \
	 drivers/muic/max77705-muic.c \
	 drivers/muic/max77705-muic-ccic.c \
	 drivers/ccic/max77705_pd.c \
	 drivers/ccic/max77705_usbc.c \
	 drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9.c \
	 drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9.h \
	 drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_beyond2_a3_s0_panel.h \
	 drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_davinci2_a3_s0_panel.h \
	 drivers/video/fbdev/exynos/panel/s6e3ha9/davinci2_df_tbl.h \
	 drivers/video/fbdev/exynos/dpu20/cal_9820/regs-decon.h \
	 drivers/video/fbdev/exynos/dpu20/cal_9820/regs-dsim.h \
	 drivers/video/fbdev/exynos/dpu20/panels/s6e3ha9_param.h \
	 drivers/video/fbdev/exynos/dpu20/panels/s6e3ha9_lcd_ctrl.c \
	 drivers/video/fbdev/exynos/dpu20/panels/decon_lcd.h \
	 drivers/video/fbdev/exynos/dpu20/dsim_drv.c \
	 drivers/video/fbdev/exynos/dpu20/dsim.h \
	 drivers/video/fbdev/exynos/dpu20/cal_9820/dsim_reg.c \
	 drivers/video/fbdev/exynos/dpu20/cal_9820/decon_reg.c \
	 drivers/video/fbdev/exynos/dpu20/cal_9820/decon_cal.h \
	 drivers/video/fbdev/exynos/dpu20/cal_9820/regs-dpp.h \
	 drivers/video/fbdev/exynos/dpu20/cal_9820/dpp_reg.c \
	 drivers/soc/samsung/cal-if/exynos9820/cmucal-sfr.c \
	 drivers/soc/samsung/cal-if/exynos9820/cmucal-sfr.h \
	 drivers/soc/samsung/cal-if/exynos9820/cmucal-node.c \
	 drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h \
	 drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_cpu_exynos9820.h \
	 drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_powermode_exynos9820.h \
	 drivers/pci/dwc/pcie-exynos-host-v0.c \
	 drivers/pci/dwc/pcie-exynos-host-v0.h \
	 drivers/pci/dwc/pci-exynos9820_cal.c \
	 arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_26.dts \
	 drivers/input/touchscreen/sec_ts/y771/sec_ts.c \
	 drivers/input/touchscreen/sec_ts/y771/sec_ts.h \
	 drivers/input/touchscreen/sec_ts/y771/sec_ts_fn.c \
	 sound/soc/samsung/abox/abox_soc.h \
	 sound/soc/samsung/abox/abox_rdma.c \
	 sound/soc/samsung/abox/abox_wdma.c \
	 sound/soc/samsung/abox/abox.c \
	 sound/soc/samsung/abox/abox.h \
	 sound/soc/samsung/abox/abox_soc.c \
	 sound/soc/samsung/abox/abox_if.c \
	 sound/soc/samsung/abox/abox_cmpnt_v20.c \
	 sound/soc/samsung/beyond_madera.c \
	 sound/soc/codecs/cs35l41.c \
	 drivers/extcon/extcon-madera.c \
	 drivers/mmc/host/dw_mmc-exynos.c \
	 drivers/mmc/host/dw_mmc-exynos.h; do
	curl -sSfL "$DS/$f" -o "$ds/$(basename "$f")"
done

mkdir -p "$src/ub"
for f in exynos9820.dtsi exynos9820-common.dtsi exynos9820-pinctrl.dtsi \
	 exynos9820-beyond1lte.dts exynos9820-beyond2lte.dts; do
	curl -sSfL "$UB/$f" -o "$src/ub/$f"
done

# Silnik dimmingu producenta (bramka scripts/check-dimming-engine.sh).
# Nazwy docelowe skrocone, bo tak odwoluje sie do nich harness.
PN=$DS/drivers/video/fbdev/exynos/panel
curl -sSfL "$PN/dimming.c"                                   -o "$ds/dimming.c"
curl -sSfL "$PN/dimming.h"                                   -o "$ds/dimming.h"
curl -sSfL "$PN/dimming_gamma.h"                             -o "$ds/dimming_gamma.h"
curl -sSfL "$PN/panel_dimming.h"                             -o "$ds/panel_dimming.h"
curl -sSfL "$PN/s6e3ha9/s6e3ha9_dimming.h"                   -o "$ds/s6e3ha9_dimming.h"
curl -sSfL "$PN/s6e3ha9/s6e3ha9_beyond2_a3_s0_panel_dimming.h"  -o "$ds/beyond2_dimming.h"
curl -sSfL "$PN/s6e3ha9/s6e3ha9_davinci2_a3_s0_panel_dimming.h" -o "$ds/davinci2_dimming.h"

# Warstwa cal-if producenta: stad pochodza offsety, szerokosci pol i rodzice
# bramek CMU_DPU i CMU_CMGP oraz specyfikacje typow PLL.
CI=$DS/drivers/soc/samsung/cal-if
curl -sSfL "$CI/pll_spec.c" -o "$ds/pll_spec.c"
curl -sSfL "$CI/cmucal.h"   -o "$ds/cmucal.h"

# Warstwa UFS producenta: stad pochodza tablice kalibracyjne PHY (blok PMA),
# sekwencje czekania na kalibracje i na zatrzask CDR oraz sterowanie izolacja PMU.
# Podstawa patcha PHY UFS w patches-uboot/.
UF=$DS/drivers/scsi/ufs
curl -sSfL "$UF/ufs-cal-9820.c" -o "$ds/ufs-cal-9820.c"
curl -sSfL "$UF/ufs-cal-9820.h" -o "$ds/ufs-cal-9820.h"
curl -sSfL "$UF/ufs-exynos.c"   -o "$ds/ufs-exynos.c"
curl -sSfL "$UF/ufs-exynos.h"   -o "$ds/ufs-exynos.h"

# Interfejs procesora komunikacyjnego (modem s5000ap). Stad pochodza: mapa
# rejestrow skrzynki pocztowej AP<->CP, sekwencje wlaczania domeny CP w PMU,
# uklad pamieci dzielonej z kolejkami SBD, stale protokolu ramkowania oraz
# wywolania do firmware bezpieczenstwa, ktore sprawdza podpis obrazu modemu.
# Bez tych plikow ani jedna liczba zebrana przy rozpoznaniu modemu nie daje
# sie zacytowac w serii, bo bramka cytatow wymaga pliku lezacego lokalnie.
MI=$DS/drivers/misc
curl -sSfL "$MI/mcu_ipc/regs-mcu_ipc.h"        -o "$ds/regs-mcu_ipc.h"
curl -sSfL "$MI/mcu_ipc/mcu_ipc.c"             -o "$ds/mcu_ipc.c"
curl -sSfL "$MI/mcu_ipc/shm_ipc.c"             -o "$ds/shm_ipc.c"
curl -sSfL "$MI/modem_v1/modem_ctrl_s5000ap.c" -o "$ds/modem_ctrl_s5000ap.c"
curl -sSfL "$MI/modem_v1/link_device_shmem.c"  -o "$ds/link_device_shmem.c"
curl -sSfL "$MI/modem_v1/link_device_memory.h" -o "$ds/link_device_memory.h"
curl -sSfL "$MI/modem_v1/modem_prj.h"          -o "$ds/modem_prj.h"
curl -sSfL "$MI/modem_v1/modem_v1.h"           -o "$ds/modem_v1.h"
curl -sSfL "$MI/modem_v1/include/sbd.h"        -o "$ds/sbd.h"
curl -sSfL "$MI/modem_v1/include/sipc5.h"      -o "$ds/sipc5.h"
curl -sSfL "$DS/drivers/soc/samsung/cal-if/exynos9820/pmucal_cp_exynos9820.h" \
	-o "$ds/pmucal_cp_exynos9820.h"

# Glowny uklad zasilania S2MPS19. Siedzi za firmware APM, nie na magistrali,
# wiec jego rejestry czyta sie wywolaniem do ACPM, a nie przez i2c. Stad
# pochodza: mapa rejestrow (adresy wlacznikow i pol napiecia), opisy wszystkich
# szyn wraz z krokiem i zakresem napiec oraz kanal ACPM, ktorym sterownik
# rozmawia z ukladem. Szyny dotyku (LDO19M, LDO27M) sa w tym samym pliku.
MF=$DS/drivers/mfd
curl -sSfL "$DS/include/linux/mfd/samsung/s2mps19.h"           -o "$ds/s2mps19.h"
curl -sSfL "$DS/include/linux/mfd/samsung/s2mps19-regulator.h" -o "$ds/s2mps19-regulator.h"
curl -sSfL "$MF/s2mps19_core.c"                                -o "$ds/s2mps19_core.c"
curl -sSfL "$DS/drivers/regulator/s2mps19_regulator.c"         -o "$ds/s2mps19_regulator.c"
curl -sSfL "$DS/drivers/soc/samsung/acpm/acpm_ipc.c"           -o "$ds/acpm_ipc.c"
curl -sSfL "$DS/drivers/soc/samsung/acpm/acpm_ipc.h"           -o "$ds/acpm_ipc.h"
curl -sSfL "$DS/drivers/soc/samsung/acpm/acpm.c"               -o "$ds/acpm.c"
# Kalibracja glosnikow: skad biora sie wartosci z /efs/cirrus i do ktorych
# pol firmware ochrony trafiaja po jego zaladowaniu.
curl -sSfL "$MF/cirrus-cal.c"                                  -o "$ds/cirrus-cal.c"

curl -sSfL "$CH/drivers/clk/samsung/clk-exynos9820.c" -o "$ds/clk-exynos9820.c"
curl -sSfL "$CH/include/dt-bindings/clock/exynos9820.h" -o "$ds/exynos9820-clk.h"

# Czcionka klawiatury ekranowej.  Telefon rozwiazuje "Sans" wlasnie na ten
# plik (`fc-match Sans` na urzadzeniu), wiec nasza klawiatura pisze tym samym
# krojem, co reszta systemu.  Bierzemy go z paczki postmarketOS, a nie
# z telefonu, zeby budowa byla powtarzalna bez podlaczonego urzadzenia.
mkdir -p "$src/fonts"
if [ ! -f "$src/fonts/DroidSans.ttf" ]; then
	tmp=$(mktemp -d)
	curl -sSfL "https://dl-cdn.alpinelinux.org/alpine/edge/community/aarch64/font-droid-20200215-r5.apk" 		-o "$tmp/font-droid.apk"
	tar xzf "$tmp/font-droid.apk" -C "$tmp" ./usr/share/fonts/droid/DroidSans.ttf
	cp "$tmp/usr/share/fonts/droid/DroidSans.ttf" "$src/fonts/DroidSans.ttf"
	rm -rf "$tmp"
fi

# Czcionka konsoli.  Terminus 16x32 jest wbudowany w jadro, ale tam ma 256
# glifow i ZADNEJ tablicy Unicode, wiec konsola zbija polskie litery do liter
# bazowych: klawiatura wysyla `ż`, a na ekranie stoi `z` (zmierzone,
# measurements/2026-09-22-ogonki-przytrzymanie).  Ta sama czcionka z paczki ma
# 512 glifow i tablice Unicode z kompletem ogonkow.  Wersja przypieta do tej,
# ktora siedzi w obrazie telefonu (`apk info -v` mowi font-terminus-4.49.1-r4).
if [ ! -f "$src/fonts/ter-v32n.psf" ]; then
	tmp=$(mktemp -d)
	curl -sSfL "https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/font-terminus-4.49.1-r4.apk" \
		-o "$tmp/font-terminus.apk"
	# Ta paczka trzyma sciezki BEZ przedrostka "./", inaczej niz font-droid
	# wyzej; podanie zlej formy konczy sie "Not found in archive".
	tar xzf "$tmp/font-terminus.apk" -C "$tmp" \
		usr/share/consolefonts/ter-v32n.psf.gz 2>/dev/null
	gzip -dc "$tmp/usr/share/consolefonts/ter-v32n.psf.gz" \
		> "$src/fonts/ter-v32n.psf"
	rm -rf "$tmp"
fi

echo "OK: źródła w $src"
