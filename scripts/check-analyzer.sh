#!/bin/sh
# Analizator statyczny clang na plikach serii.
#
# Po co: dokument sterujacy wymienia sparse, smatch i coccicheck jako bramki
# dostepne na PC, a niedostepne w Termuxie.  Zadnego z tych trzech nie ma na tej
# maszynie (sprawdzone: brak w PATH, brak pakietu w msys2), za to jest
# analizator sciezkowy clanga, ktory lapie te sama klase bledow: odczyt
# niezainicjowanej wartosci, wyluskanie NULL-a, wyciek, martwa galaz.
# Kompilacja W=1 tego nie widzi, bo to analiza sciezek, a nie ostrzezenia
# skladniowe.
#
# deadcode.DeadStores jest WYLACZONY i to nie jest wygoda.  Makra debugowe
# jadra znikaja przy wylaczonym CONFIG_DYNAMIC_DEBUG, wiec kazda zmienna
# uzywana tylko w dev_dbg() wyglada dla analizatora na martwy zapis.  Dowod, ze
# to szum, a nie znalezisko: przy wlaczonym checkerze zglasza sie tak samo
# byte_clk w samsung-dsim.c:1093, ktory stoi w mainline od 2023 roku
# (commit e7447128ca4a).
#
# Uzycie:  scripts/check-analyzer.sh [--update-golden]
# Kod:     0 zgodnie z wzorcem, 1 rozjazd, 2 brak narzedzi
set -u

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
lin="$root/sources/linux"
log="$root/build-logs"
gold="$root/scripts/golden/analyzer.txt"
mkdir -p "$log"

UPDATE=0
[ "${1:-}" = "--update-golden" ] && UPDATE=1

command -v clang >/dev/null 2>&1 || {
	echo "check-analyzer: brak clang"
	exit 2
}
[ -f "$lin/include/generated/autoconf.h" ] || {
	echo "check-analyzer: drzewo nieprzygotowane, uruchom scripts/pc-prepare.sh"
	exit 2
}

PLIKI="drivers/clk/samsung/clk-exynos9820.c
drivers/clk/samsung/clk-pll.c
drivers/pinctrl/samsung/pinctrl-exynos-arm64.c
drivers/pinctrl/samsung/pinctrl-samsung.c
drivers/pmdomain/samsung/exynos-pm-domains.c
drivers/gpu/drm/panel/panel-samsung-s6e3ha9-main.c
drivers/gpu/drm/panel/panel-samsung-s6e3ha9-dimming.c
drivers/gpu/drm/exynos/exynos9820_drm_decon.c
drivers/phy/samsung/phy-exynos9820-dsim.c
drivers/gpu/drm/bridge/samsung-dsim.c
drivers/video/backlight/exynos9820-dsim-lcd.c
drivers/thermal/samsung/exynos9820-tmu.c
drivers/clk/samsung/clk-acpm.c"

ANALIZA="--analyze -Xclang -analyzer-output=text \
-Xclang -analyzer-disable-checker -Xclang deadcode.DeadStores"

wynik=$(mktemp)
pelny="$log/51-analyzer.log"
: > "$pelny"

for f in $PLIKI; do
	[ -f "$lin/$f" ] || { echo "check-analyzer: brak $f"; rm -f "$wynik"; exit 2; }
	out=$(MODE="$ANALIZA" OUT=/dev/null sh "$root/scripts/cc-kernel.sh" "$f" 2>&1)
	printf "%s\n" "$out" >> "$pelny"
	# Wzorzec trzyma NAZWE pliku i checker, a nie numer linii: numer zmienia sie
	# przy kazdej edycji wyzej w pliku i wzorzec staly by sie szumem.
	printf "%s\n" "$out" |
		sed -n 's/^\([^ ]*\):[0-9]*:[0-9]*: warning: .*\[\([a-zA-Z.]*\)\]$/\1 \2/p' |
		LC_ALL=C sort >> "$wynik"
done

if [ "$UPDATE" = 1 ]; then
	cp "$wynik" "$gold"
	echo "check-analyzer: zapisany wzorzec scripts/golden/analyzer.txt"
	rm -f "$wynik"
	exit 0
fi

if [ ! -f "$gold" ]; then
	echo "check-analyzer: brak wzorca, uruchom z --update-golden"
	rm -f "$wynik"
	exit 1
fi

if diff -u "$gold" "$wynik" > "$log/diff-analyzer.txt" 2>&1; then
	rm -f "$log/diff-analyzer.txt"
	n=$(grep -c . "$wynik" 2>/dev/null || echo 0)
	echo "check-analyzer: $n znalezisk, zgodnie z wzorcem"
	rm -f "$wynik"
	exit 0
fi

echo "check-analyzer: rozjazd z wzorcem, patrz build-logs/diff-analyzer.txt"
cat "$log/diff-analyzer.txt"
rm -f "$wynik"
exit 1
