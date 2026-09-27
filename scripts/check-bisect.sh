#!/bin/sh
# Sprawdza, ze KAZDY patch serii kompiluje sie w miejscu, w ktorym stoi, czyli
# ze seria jest bisectowalna. Dla kazdego commita, ktory dotyka plikow .c
# objetych bramka kompilacji, przestawia drzewo na ten commit i kompiluje
# wszystkie takie pliki istniejace w tym momencie.
#
# To lapie klase bledu, ktorej nie widac po nalozeniu calej serii: patch, ktory
# uzywa czegos, co wnosi dopiero patch pozniejszy (np. sterownik zegarow przed
# bindingiem z identyfikatorami).
#
# Wymaga przygotowanego drzewa (scripts/pc-prepare.sh) i galezi "series".
# Uzycie: scripts/check-bisect.sh
set -u

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
lin="$root/sources/linux"
BASE=1200d84f4c0a929a0780180d25063d93773be79c

[ -d "$lin/.git" ] || { echo "brak repo w $lin" >&2; exit 1; }
[ -f "$lin/include/generated/autoconf.h" ] || {
	echo "brak include/generated/autoconf.h, uruchom scripts/pc-prepare.sh" >&2
	exit 1
}

start=$(git -C "$lin" rev-parse --abbrev-ref HEAD)
[ "$start" = "HEAD" ] && start=$(git -C "$lin" rev-parse HEAD)

restore() {
	git -C "$lin" checkout -q "$start" 2>/dev/null
	[ -n "${tmpdtb:-}" ] && rm -rf "$tmpdtb"
	return 0
}
trap restore EXIT INT TERM

if [ -n "$(git -C "$lin" status --porcelain)" ]; then
	echo "drzewo nie jest czyste, przerywam" >&2
	exit 1
fi

# Wszystkie pliki .c, ktore seria dotyka. Lista musi byc pelna, inaczej bramka
# obiecuje bisectowalnosc calej serii, a sprawdza jej czesc: przed poprawka
# brakowalo tu czterech plikow (obu pinctrl oraz exynos_drm_drv.c
# i exynos_drm_dsi.c), czyli patchy 0007, 0035 i 0037.
# panel-samsung-s6e3ha9.c nie istnieje na koncu serii, bo zostaje podzielony
# na -main i -dimming, ale istnieje w commitach posrednich i wlasnie o nie tu
# chodzi.
WATCH="drivers/clk/samsung/clk-exynos9820.c
drivers/clk/samsung/clk-pll.c
drivers/pmdomain/samsung/exynos-pm-domains.c
drivers/pinctrl/samsung/pinctrl-samsung.c
drivers/pinctrl/samsung/pinctrl-exynos-arm64.c
drivers/gpu/drm/panel/panel-samsung-s6e3ha9.c
drivers/gpu/drm/panel/panel-samsung-s6e3ha9-main.c
drivers/gpu/drm/panel/panel-samsung-s6e3ha9-dimming.c
drivers/gpu/drm/exynos/exynos9820_drm_decon.c
drivers/gpu/drm/exynos/exynos_drm_drv.c
drivers/gpu/drm/exynos/exynos_drm_dsi.c
drivers/phy/samsung/phy-exynos9820-dsim.c
drivers/gpu/drm/bridge/samsung-dsim.c
drivers/video/backlight/exynos9820-dsim-lcd.c
drivers/thermal/samsung/exynos9820-tmu.c
drivers/clk/samsung/clk-acpm.c"

# Drzewo urzadzen ma wlasna kolejnosc zaleznosci i wlasna klase bledu: wezel,
# ktory odwoluje sie do makra z naglowka wnoszonego przez patch pozniejszy,
# albo do etykiety, ktora jeszcze nie istnieje. Kompilacja plikow .c tego nie
# widzi, bo DTS nie przechodzi przez kompilator C.
DTS_DIR=arch/arm64/boot/dts/exynos
DTS_TOP=$DTS_DIR/exynos9820-beyond2lte.dts

DTC=""
for c in "$root/.pc-tools/dtc" "$root/.pc-tools/dtc.exe" "$lin/scripts/dtc/dtc"; do
	[ -x "$c" ] && { DTC=$c; break; }
done
command -v dtc >/dev/null 2>&1 && [ -z "$DTC" ] && DTC=$(command -v dtc)
command -v cpp >/dev/null 2>&1 || DTC=""
[ -n "$DTC" ] || echo "check-bisect: brak dtc albo cpp, punkty DT beda pominiete" >&2

# Buduje drzewo urzadzen w biezacym stanie drzewa. Zwraca 0, gdy sie zbudowalo.
zbuduj_dtb() {
	tmpd=$1
	rm -f "$tmpd/bisect.dts.tmp" "$tmpd/bisect.dtb"
	( cd "$lin" && cpp -E -nostdinc -I scripts/dtc/include-prefixes 		-undef -D__DTS__ -x assembler-with-cpp 		-o "$tmpd/bisect.dts.tmp" "$DTS_TOP" ) >/dev/null 2>&1 || return 1
	( cd "$lin" && "$DTC" -o "$tmpd/bisect.dtb" -b 0 		-i"$DTS_DIR/" -iscripts/dtc/include-prefixes 		-Wno-unique_unit_address -Wno-unit_address_vs_reg 		-Wno-avoid_unnecessary_addr_size -Wno-alias_paths 		-Wno-interrupt_map -Wno-simple_bus_reg 		"$tmpd/bisect.dts.tmp" ) >/dev/null 2>&1 || return 1
	[ -s "$tmpd/bisect.dtb" ]
}

tmpdtb=$(mktemp -d) || exit 1

rc=0
checked=0
dtb_punktow=0
for sha in $(git -C "$lin" rev-list --reverse "$BASE..series"); do
	pliki=$(git -C "$lin" show --stat --name-only --format= "$sha")
	touched=0
	for f in $WATCH; do
		if printf '%s
' "$pliki" | grep -qx "$f"; then
			touched=1
			break
		fi
	done
	dt_touched=0
	printf '%s
' "$pliki" | grep -q "^$DTS_DIR/" && dt_touched=1
	[ "$touched" = 0 ] && [ "$dt_touched" = 0 ] && continue

	git -C "$lin" checkout -q --detach "$sha"
	subject=$(git -C "$lin" log --format='%s' -1 | cut -c1-52)
	bad=""
	for f in $WATCH; do
		[ -f "$lin/$f" ] || continue
		out=$(sh "$root/scripts/cc-kernel.sh" "$f" 2>&1)
		[ -n "$out" ] && bad="$bad $(basename "$f")"
	done
	# Drzewo urzadzen budujemy tylko od commita, ktory wnosi plik plyty:
	# wczesniej nie ma czego budowac i brak pliku nie jest bledem.
	if [ "$dt_touched" = 1 ] && [ -n "$DTC" ] && [ -f "$lin/$DTS_TOP" ]; then
		dtb_punktow=$((dtb_punktow + 1))
		zbuduj_dtb "$tmpdtb" || bad="$bad dtb"
	fi
	checked=$((checked + 1))
	if [ -z "$bad" ]; then
		printf "OK    %-54s\n" "$subject"
	else
		printf "PADLO %-54s :%s\n" "$subject" "$bad"
		rc=1
	fi
done

echo
echo "sprawdzonych punktow serii: $checked, w tym z budowaniem DT: $dtb_punktow"
[ "$rc" = 0 ] && echo "SERIA BISECTOWALNA: kazdy sprawdzony punkt kompiluje sie" \
	|| echo "SERIA NIE JEST BISECTOWALNA"
exit $rc
