#!/bin/sh
# Kompiluje i waliduje PRZYKLADY z bindingow serii, czyli to, co w drzewie
# jadra robi `make dt_binding_check`.
#
# Po co osobna bramka: dt-validate sprawdza zbudowane DTB, a dt-doc-validate
# sprawdza sam schemat.  Przyklad w bindingu nie przechodzi przez zadne z nich,
# wiec moze zawierac makro, ktorego nie ma, wezel niezgodny z wlasnym schematem
# albo wlasciwosc, ktorej schemat zabrania, i nikt tego nie zauwazy.  Audyt
# cytowan (R6) znalazl tak trzy bledne makra zegarow w dwoch przykladach.
#
# Uzycie:  scripts/check-binding-examples.sh
# Kod:     0 wszystko czyste, 1 naruszenie, 2 brak narzedzi
set -u

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
lin="$root/sources/linux"
log="$root/build-logs"
mkdir -p "$log"

V=""
for c in "$root/.pc-tools/venv/Scripts" "$root/.pc-tools/venv/bin"; do
	[ -d "$c" ] && { V=$c; break; }
done
DTE="$V/dt-extract-example"; [ -x "$DTE" ] || DTE="$DTE.exe"
DTV="$V/dt-validate"; [ -x "$DTV" ] || DTV="$DTV.exe"
DTC="$root/.pc-tools/dtc"; [ -x "$DTC" ] || DTC="$DTC.exe"

if [ ! -x "$DTE" ] || [ ! -x "$DTV" ] || [ ! -x "$DTC" ]; then
	echo "check-binding-examples: brak dtschema albo dtc, uruchom scripts/pc-prepare.sh"
	exit 2
fi
command -v cpp >/dev/null 2>&1 || {
	echo "check-binding-examples: brak cpp"
	exit 2
}

yamls=$(grep -hoE "^[+]{3} b/(Documentation/devicetree/bindings/.*[.]yaml)" \
	"$root"/patches/*.patch 2>/dev/null | sed "s|^+++ b/||" | sort -u)
[ -n "$yamls" ] || { echo "check-binding-examples: seria nie rusza zadnego bindingu"; exit 1; }

out="$log/48-binding-examples.log"
: > "$out"
tmp=$(mktemp -d)
zle=0
ile=0

for y in $yamls; do
	[ -f "$lin/$y" ] || continue
	grep -q "^examples:" "$lin/$y" || continue
	ile=$((ile + 1))
	base=$(basename "$y" .yaml)
	if ! "$DTE" "$lin/$y" > "$tmp/$base.dts" 2>>"$out"; then
		echo "$y: nie dalo sie wyciagnac przykladu" >> "$out"
		zle=$((zle + 1))
		continue
	fi
	if ! ( cd "$lin" && cpp -E -nostdinc -I include \
			-I scripts/dtc/include-prefixes -undef -D__DTS__ \
			-x assembler-with-cpp -o "$tmp/$base.pp.dts" \
			"$tmp/$base.dts" ) 2>>"$out"; then
		echo "$y: preprocesor odrzucil przyklad" >> "$out"
		zle=$((zle + 1))
		continue
	fi
	# Ostrzezenia ksztaltu (adres jednostki, #address-cells) sa w przykladach
	# normalne i mainline je przy dt_binding_check wycisza; liczy sie tylko
	# to, czy dtc w ogole zbudowal plik.
	if ! "$DTC" -I dts -O dtb -o "$tmp/$base.dtb" "$tmp/$base.pp.dts" \
			2>"$tmp/$base.dtcerr"; then
		echo "$y: dtc odrzucil przyklad" >> "$out"
		cat "$tmp/$base.dtcerr" >> "$out"
		zle=$((zle + 1))
		continue
	fi
done

# Walidacja idzie JEDNYM wywolaniem na caly katalog: dt-validate wczytuje przy
# starcie wszystkie schematy z drzewa, wiec wolanie go osobno dla kazdego
# przykladu kosztuje kilkanascie razy tyle, co jedno wolanie na komplecie.
#
# -m doklada wezly, ktorych zaden schemat nie wybral: przyklad opisujacy
# compatible spoza wszystkich bindingow tez jest bledem.
if ls "$tmp"/*.dtb >/dev/null 2>&1; then
	res=$("$DTV" -m -s "$lin/Documentation/devicetree/bindings" "$tmp" 2>&1 |
		grep -v "Cannot determine base path\|^	\$id:\|^	file:")
	if [ -n "$res" ]; then
		printf "%s\n" "$res" >> "$out"
		# liczymy wiersze z naruszeniem, a nie doklejane do nich
		# wiersze "from schema $id:"
		zle=$((zle + $(printf "%s\n" "$res" | grep -c "[.]dtb:")))
	fi
fi

rm -rf "$tmp"

# Zero zbudowanych przykladow to nie sukces: tak konczy sie przebieg, w ktorym
# seria nie jest nalozona albo kazdy binding zostal po cichu pominiety.
if [ "$ile" = 0 ]; then
	echo "check-binding-examples: zaden binding serii nie ma przykladu do zbudowania"
	cat "$out"
	exit 1
fi

if [ "$zle" != 0 ]; then
	echo "check-binding-examples: $zle naruszen w $ile przykladach"
	cat "$out"
	exit 1
fi
echo "check-binding-examples: $ile przykladow zbudowanych i zwalidowanych"
exit 0
