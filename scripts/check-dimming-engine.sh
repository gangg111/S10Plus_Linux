#!/bin/sh
# Porownuje NASZ silnik dimmingu z silnikiem producenta: kompiluje oba
# w przestrzeni uzytkownika i sprawdza, czy dla tych samych (losowych) danych
# MTP daja identyczne ladunki komendy gammy dla wszystkich 74 poziomow.
#
# Wymaga wczesniejszego ./scripts/fetch-sources.sh (potrzebne pliki producenta
# w sources/ds) oraz kompilatora C hosta (domyslnie clang, nadpisywalny przez $CC).
set -eu
CC=${CC:-clang}
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ds="$root/sources/ds"
drv="$root/sources/linux/drivers/gpu/drm/panel"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# --- silnik producenta -------------------------------------------------------
mkdir -p "$work/vendor"
cp "$ds/dimming.c" "$ds/dimming.h" "$ds/dimming_gamma.h" "$work/vendor/"
cp "$root/scripts/dimming-harness/vendor_main.c" "$work/vendor/"

python3 - "$ds" "$work/vendor" <<'PY'
import re, sys
ds, out = sys.argv[1], sys.argv[2]
dim = open(ds + '/beyond2_dimming.h', encoding='utf8', errors='replace').read()
i = dim.index('static s32 beyond2_a3_s0_rtbl2nit')
j = dim.index('\n};', dim.index('static struct dimming_lut beyond2_a3_s0_dimming_lut[]')) + 3
d2 = open(ds + '/s6e3ha9_dimming.h', encoding='utf8', errors='replace').read()
k = d2.index('static struct tp s6e3ha9_beyond_tp[')
tp = d2[k:d2.index('\n};', k) + 3]
open(out + '/panel_data.h', 'w').write(
    '#ifndef PANEL_DATA_H\n#define PANEL_DATA_H\n#include "dimming.h"\n'
    '#define S6E3HA9_NR_TP (12)\n#define S6E3HA9_NR_LUMINANCE (74)\n'
    '#define S6E3HA9_BEYOND_TARGET_LUMINANCE (420)\n\n' + tp + '\n\n' + dim[i:j] + '\n#endif\n')
PY

(cd "$work/vendor" && "$CC" -w -std=gnu11 -O1 -DCONFIG_PANEL_AID_DIMMING -o vendor vendor_main.c dimming.c)

# --- nasz port ---------------------------------------------------------------
mkdir -p "$work/port"
cp "$drv/panel-samsung-s6e3ha9-dimming.c" "$drv/panel-samsung-s6e3ha9-dimming.h" \
   "$drv/panel-samsung-s6e3ha9-dimming-data.h" "$work/port/"
cp "$root/scripts/dimming-harness/port_main.c" "$work/port/"
sed -i 's|#include <linux/[a-z0-9]*\.h>||g; s|#include "panel-samsung-s6e3ha9-dimming.h"||' \
    "$work/port/panel-samsung-s6e3ha9-dimming.c"
# Naglowek portu tez ciagnie <linux/types.h>; harness ma wlasne typy, wiec tniemy.
sed -i 's|#include <linux/[a-z0-9_]*[.]h>||g' "$work/port/panel-samsung-s6e3ha9-dimming.h"
(cd "$work/port" && "$CC" -w -std=gnu11 -O1 -o port port_main.c)

# --- porownanie --------------------------------------------------------------
rc=0
for seed in 1 2 3 7 42 99 12345; do
	# Obie strony przez ten sam filtr grep: na hoscie Windows binarki MinGW pisza
	# CRLF, a grep z MSYS normalizuje koniec linii. Bez symetrii diff widzi 74/74 roznic.
	"$work/vendor/vendor" "$seed" 2>/dev/null | grep '^lum' > "$work/v.txt"
	"$work/port/port" "$seed" | grep '^lum' > "$work/p.txt"
	if diff -q "$work/v.txt" "$work/p.txt" >/dev/null; then
		echo "seed $seed: 74/74 poziomow zgodnych"
	else
		echo "seed $seed: ROZNICE"
		diff "$work/v.txt" "$work/p.txt" | head -4
		rc=1
	fi
done

[ $rc = 0 ] && echo "WSZYSTKO ZGODNE"
exit $rc
