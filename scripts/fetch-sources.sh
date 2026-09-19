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
	 arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_26.dts \
	 drivers/input/touchscreen/sec_ts/y771/sec_ts.c; do
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

curl -sSfL "$CH/drivers/clk/samsung/clk-exynos9820.c" -o "$ds/clk-exynos9820.c"
curl -sSfL "$CH/include/dt-bindings/clock/exynos9820.h" -o "$ds/exynos9820-clk.h"

echo "OK: źródła w $src"
