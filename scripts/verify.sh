#!/bin/sh
# Bramki weryfikacyjne projektu. ZASADA RATCHET: kazda bramka, ktora raz
# przeszla, musi przechodzic zawsze. Skrypt konczy sie kodem:
#   0  wszystkie bramki przeszly
#   1  ktoras bramka PADLA (regresja)
#   2  wszystkie uruchomione bramki przeszly, ale czesci NIE DALO SIE
#      uruchomic (brak narzedzia); to NIE jest zielone swiatlo
#
# Zielony wynik nie znaczy "dziala". Znaczy tylko "nie pogorszylo sie
# i stale zgadzaja sie ze zrodlem". Nic w tym projekcie nie jest udowodnione
# jako dzialajace, dopoki nie potwierdzi tego sprzet przez UART.
#
# Uzycie:
#   scripts/verify.sh                 pelny przebieg
#   scripts/verify.sh --update-golden odswieza pliki wzorcowe (patrz nizej)
#
# --update-golden wolno uzyc TYLKO wtedy, gdy zmiana wyniku jest zamierzona
# i uzasadniona w opisie commita. Nie jest to sposob na "naprawienie" bramki.
set -u

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
lin="$root/sources/linux"
log="$root/build-logs"
gold="$root/scripts/golden"
ds="$root/sources/ds"
BASE=1200d84f4c0a929a0780180d25063d93773be79c

UPDATE=0
[ "${1:-}" = "--update-golden" ] && UPDATE=1

mkdir -p "$log" "$gold"

PASS=0; FAIL=0; SKIP=0
FAILED_LIST=""
SKIPPED_LIST=""

ok()   { PASS=$((PASS+1)); printf "  OK      %s\n" "$1"; }
bad()  { FAIL=$((FAIL+1)); FAILED_LIST="$FAILED_LIST$1
"; printf "  PADLA   %s\n" "$1"; [ $# -gt 1 ] && printf "          %s\n" "$2"; }
skip() { SKIP=$((SKIP+1)); SKIPPED_LIST="$SKIPPED_LIST$1 ($2)
"; printf "  BRAK    %s: %s\n" "$1" "$2"; }

have() { command -v "$1" >/dev/null 2>&1; }

# Porownanie z plikiem wzorcowym; przy --update-golden zapisuje nowy wzorzec.
golden() {   # $1 nazwa bramki  $2 plik z wynikiem  $3 nazwa wzorca
	g="$gold/$3"
	if [ "$UPDATE" = 1 ]; then
		cp "$2" "$g"
		printf "  ZAPIS   %s -> scripts/golden/%s\n" "$1" "$3"
		return 0
	fi
	if [ ! -f "$g" ]; then
		bad "$1" "brak wzorca scripts/golden/$3, uruchom --update-golden"
		return 1
	fi
	if diff -u "$g" "$2" > "$log/diff-$3.txt" 2>&1; then
		rm -f "$log/diff-$3.txt"
		ok "$1"
	else
		bad "$1" "rozjazd z wzorcem, patrz build-logs/diff-$3.txt"
	fi
}

echo "=========================================================="
echo " bramki projektu s10-mainline"
echo " data: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=========================================================="

[ -d "$lin" ] || { echo "Brak $lin, uruchom najpierw scripts/fetch-sources.sh" >&2; exit 1; }

# ---------------------------------------------------------------- 1. seria
echo
echo "[1] seria patchy"

npatches=$(ls "$root"/patches/*.patch 2>/dev/null | wc -l)
echo "  patchy w serii: $npatches"

# 1a. zadnych smieci po narzedziach
junk=$(ls "$root"/patches/*.orig "$root"/patches/*.rej "$root"/patches/*~ 2>/dev/null | wc -l)
if [ "$junk" = 0 ]; then
	ok "brak plikow .orig/.rej/~ w patches/"
else
	bad "brak plikow .orig/.rej/~ w patches/" "znaleziono $junk"
fi

# 1b. seria stosuje sie sekwencyjnie na czysta baze (bez dotykania worktree)
idx=$(mktemp)
rm -f "$idx"
# indeks tymczasowy trzeba zasiac drzewem bazowym, inaczej
# apply --cached nie ma na czym pracowac
GIT_INDEX_FILE="$idx" git -C "$lin" read-tree "$BASE" 2>/dev/null
applied=0
apply_fail=""
for p in "$root"/patches/*.patch; do
	if GIT_INDEX_FILE="$idx" git -C "$lin" apply --cached --whitespace=nowarn "$p" 2>"$log/apply-err.txt"; then
		applied=$((applied+1))
	else
		apply_fail=$(basename "$p")
		break
	fi
done
rm -f "$idx"
if [ -z "$apply_fail" ] && [ "$applied" = "$npatches" ]; then
	ok "seria stosuje sie na $BASE ($applied/$npatches)"
	rm -f "$log/apply-err.txt"
else
	bad "seria stosuje sie na $BASE" "padlo na $apply_fail ($applied/$npatches)"
fi

# 1d. Drzewo po nalozeniu serii MUSI byc tym samym drzewem, ktore sprawdzaja
# pozostale bramki. Bez tego regresja wprowadzona tylko w pliku .patch, czyli
# dokladnie w tym, co jedzie na liste, przechodzi niezauwazona: bramki liczbowe
# i kompilacja czytaja wylacznie drzewo robocze.
idx2=$(mktemp); rm -f "$idx2"
tree_patches=""
tree_worktree=""
if [ -z "$apply_fail" ]; then
	idx3=$(mktemp); rm -f "$idx3"
	GIT_INDEX_FILE="$idx3" git -C "$lin" read-tree "$BASE" 2>/dev/null
	for p in "$root"/patches/*.patch; do
		GIT_INDEX_FILE="$idx3" git -C "$lin" apply --cached --whitespace=nowarn "$p" 2>/dev/null || break
	done
	tree_patches=$(GIT_INDEX_FILE="$idx3" git -C "$lin" write-tree 2>/dev/null)
	rm -f "$idx3"
	GIT_INDEX_FILE="$idx2" git -C "$lin" add -A 2>/dev/null
	tree_worktree=$(GIT_INDEX_FILE="$idx2" git -C "$lin" write-tree 2>/dev/null)
fi
rm -f "$idx2"
# Porownujemy TRESC plikow, ktore rusza seria, a nie cale drzewa: na Windows
# core.filemode jest wylaczony, wiec tryb wykonywalny rozjezdza sie dla setek
# plikow, ktorych seria w ogole nie dotyka, i samo porownanie hashy drzew
# zawsze by padalo. Identyfikator bloba zalezy tylko od tresci.
drift=""
if [ -n "$tree_patches" ] && [ -n "$tree_worktree" ]; then
	for f in $(git -C "$lin" diff --name-only "$BASE" "$tree_patches"); do
		a=$(git -C "$lin" rev-parse "$tree_patches:$f" 2>/dev/null)
		b=$(git -C "$lin" rev-parse "$tree_worktree:$f" 2>/dev/null)
		[ "$a" = "$b" ] || drift="$drift $f"
	done
	if [ -z "$drift" ]; then
		ok "seria daje dokladnie te pliki, ktore sprawdzaja pozostale bramki"
	else
		bad "seria zgadza sie z drzewem roboczym" "rozjazd:$drift"
	fi
else
	bad "seria zgadza sie z drzewem roboczym" "nie udalo sie zbudowac drzew do porownania"
fi

# 1b2. Porownanie wyzej patrzy tylko na pliki, ktore rusza seria, wiec plik
# lezacy w drzewie roboczym, a nieobjety zadnym patchem, jest dla niego
# niewidzialny. To jest dokladnie ta awaria, ktorej reszta projektu sie boi:
# u autora sie kompiluje, bo naglowek lezy na dysku, a u odbiorcy go nie ma.
#
# Falszywy alarm, ktory ta bramka potrafi zglosic: drzewo jadra ma 99 dowiazan
# symbolicznych (Documentation/Changes, komplet scripts/dtc/include-prefixes/*,
# katalogi w tools/), a narzedzie bez prawa do ich zakladania zostawia w ich
# miejscu zwykla tresc. Wtedy status pokazuje 87 zmian typu i 12 "usuniec",
# ktore nie maja nic wspolnego z seria. NIE odsiewac ich w bramce, tylko
# odtworzyc dowiazania; dotyczy ich dokladnie tyle, ile zwraca pierwsza linia:
#   git -C sources/linux ls-files -s | awk '$1=="120000"{sub(/^[^\t]*\t/,"");print}' > /tmp/lnk
#   while read -r p; do rm -rf "$p"; done < /tmp/lnk
#   git -C sources/linux checkout -- $(tr '\n' ' ' < /tmp/lnk)
brud=$(git -C "$lin" status --porcelain 2>/dev/null)
if [ -z "$brud" ]; then
	ok "drzewo robocze nie ma nic poza seria"
else
	bad "drzewo robocze nie ma nic poza seria" 		"$(printf '%s' "$brud" | tr '
' ' ')"
fi


# 1c. patche nie wnosza plikow .orig/.rej
if grep -lE "^\+\+\+ b/.*\.(orig|rej)$" "$root"/patches/*.patch >/dev/null 2>&1; then
	bad "patche nie wnosza plikow .orig/.rej" "$(grep -lE '^\+\+\+ b/.*\.(orig|rej)$' "$root"/patches/*.patch | tr '\n' ' ')"
else
	ok "patche nie wnosza plikow .orig/.rej"
fi

# 1e. patches-oot/ tez jest artefaktem, ktory sie wysyla, tylko do INNEGO drzewa.
# Bez tej bramki jego defekty nie mialy sie gdzie zapalic: jeden z nich (patch
# ruszal sterownik, ale nie naglowek z identyfikatorami zegarow, wiec u odbiorcy
# sie nie budowal) przezyl caly poprzedni przebieg.
if [ -d "$root/patches-oot" ] && [ -d "$ds" ]; then
	oot=$(mktemp -d)
	mkdir -p "$oot/drivers/clk/samsung" "$oot/include/dt-bindings/clock"
	cp "$ds/clk-exynos9820.c" "$oot/drivers/clk/samsung/" 2>/dev/null
	cp "$ds/exynos9820-clk.h" "$oot/include/dt-bindings/clock/exynos9820.h" 2>/dev/null
	oot_fail=""
	for p in "$root"/patches-oot/*.patch; do
		git -C "$oot" init -q . 2>/dev/null
		git -C "$oot" apply --check "$p" 2>/dev/null || oot_fail="$oot_fail $(basename "$p")"
	done
	if [ -z "$oot_fail" ]; then
		ok "patche out-of-tree stosuja sie na przypiete drzewo obce"
	else
		bad "patche out-of-tree stosuja sie na przypiete drzewo obce" "padlo:$oot_fail"
	fi
	# kazdy identyfikator uzyty przez dodany kod musi byc zdefiniowany po patchu
	for p in "$root"/patches-oot/*.patch; do
		git -C "$oot" apply "$p" 2>/dev/null
	done
	brak=""
	for id in $(grep -ohE "CLK_(MOUT|DOUT|GOUT|NR)_[A-Z0-9_]*(DPU|CMGP)[A-Z0-9_]*" 		    "$oot/drivers/clk/samsung/clk-exynos9820.c" 2>/dev/null | sort -u); do
		grep -q "define $id[^A-Z0-9_]" "$oot/include/dt-bindings/clock/exynos9820.h" 2>/dev/null 			|| brak="$brak $id"
	done
	if [ -z "$brak" ]; then
		ok "patche out-of-tree wnosza komplet identyfikatorow zegarow"
	else
		bad "patche out-of-tree wnosza komplet identyfikatorow" "brakuje:$brak"
	fi
	rm -rf "$oot"
else
	skip "patche out-of-tree" "brak katalogu patches-oot albo sources/ds"
fi


# ---------------------------------------------------------- 2. checkpatch
echo
echo "[2] checkpatch --strict"
if have perl && [ -f "$lin/scripts/checkpatch.pl" ]; then
	: > "$log/05-checkpatch.log"
	cp_err=0; cp_chk=0; cp_warn=0
	for p in "$root"/patches/*.patch; do
		echo "########## $(basename "$p")" >> "$log/05-checkpatch.log"
		( cd "$lin" && perl scripts/checkpatch.pl --strict --no-signoff "$p" ) \
			>> "$log/05-checkpatch.log" 2>&1
	done
	cp_tot=$(grep -c "^total: " "$log/05-checkpatch.log" 2>/dev/null)
	cp_tot=${cp_tot:-0}
	# sam grep po logu nie odroznia "czysto" od "narzedzie padlo": bez tego
	# porownania martwy checkpatch zaliczal trzy bramki naraz
	if [ "$cp_tot" = "$npatches" ]; then
		ok "checkpatch przeliczyl kazdy patch ($cp_tot/$npatches)"
	else
		bad "checkpatch przeliczyl kazdy patch" "podsumowan $cp_tot, patchy $npatches"
	fi
	cp_err=$(grep -c "^ERROR:" "$log/05-checkpatch.log" 2>/dev/null)
	cp_err=${cp_err:-0}
	# nMUX() to nazwa makra z drivers/clk/samsung/clk.h:164, a nie nasz
	# identyfikator.  checkpatch widzi w niej CamelCase i ten sam CHECK
	# dostaje kazdy plik w drzewie, ktory tego makra uzywa; sprawdzone
	# na clk-exynos990.c.  Odsiewamy to jedno trafienie, reszta checkow
	# nadal musi byc zerem.
	# Tak samo nazwy rejestrow MAX17042_* z include/linux/power/
	# max17042_battery.h: niezmieniony max17042_battery.c dostaje od
	# checkpatcha -f 47 takich CHECK-ow, bo enum w naglowku nosi nazwy
	# z noty katalogowej (RepSOC, MiscCFG).  Latka 0105 tylko ich uzywa.
	cp_chk=$(grep "^CHECK:" "$log/05-checkpatch.log" 2>/dev/null \
		| grep -v "Avoid CamelCase: <nMUX" \
		| grep -v "Avoid CamelCase: <MAX17042_" | wc -l | tr -d " ")
	cp_chk=${cp_chk:-0}
	# Warningi ida do DWOCH kubelkow, kazdy z wlasnym limitem.  Sterownik
	# zegarow trzyma nazwy rejestrow producenta w jednej linii i przez to
	# ma ich setki dluzszych niz 100 kolumn, tak samo jak sterowniki
	# Samsunga w drzewie (clk-gs101.c 146 takich linii, clk-exynos2200.c
	# 195).  Przy jednym wspolnym limicie skrocenie takiej linii robiloby
	# miejsce na prawdziwy nowy warning; osobne kubelki na to nie pozwalaja.
	cp_long=$(grep -c "^WARNING: line length of" \
		"$log/05-checkpatch.log" 2>/dev/null)
	cp_long=${cp_long:-0}
	cp_warn=$(grep "^WARNING:" "$log/05-checkpatch.log" 2>/dev/null \
		| grep -v "^WARNING: line length of" | wc -l | tr -d " ")
	cp_warn=${cp_warn:-0}
	echo "  errors=$cp_err checks=$cp_chk warnings=$cp_warn dlugie=$cp_long"
	[ "$cp_err" = 0 ] && ok "checkpatch: 0 errors" \
		|| bad "checkpatch: 0 errors" "jest $cp_err"
	[ "$cp_chk" = 0 ] && ok "checkpatch: 0 checks" \
		|| bad "checkpatch: 0 checks" "jest $cp_chk"
	# warningi maja limit, ktory wolno tylko obnizac
	if [ "$UPDATE" = 1 ]; then
		echo "$cp_warn" > "$gold/checkpatch-warnings.max"
		echo "$cp_long" > "$gold/checkpatch-longlines.max"
		printf "  ZAPIS   limit warningow -> %s, dlugich linii -> %s\n" \
			"$cp_warn" "$cp_long"
	elif [ -f "$gold/checkpatch-warnings.max" ]; then
		max=$(cat "$gold/checkpatch-warnings.max")
		if [ "$cp_warn" -le "$max" ]; then
			ok "checkpatch: warningow $cp_warn (limit $max)"
		else
			bad "checkpatch: warningow $cp_warn (limit $max)" "seria przybrala warningow"
		fi
		if [ -f "$gold/checkpatch-longlines.max" ]; then
			maxl=$(cat "$gold/checkpatch-longlines.max")
			if [ "$cp_long" -le "$maxl" ]; then
				ok "checkpatch: dlugich linii $cp_long (limit $maxl)"
			else
				bad "checkpatch: dlugich linii $cp_long (limit $maxl)" \
					"seria przybrala dlugich linii"
			fi
		else
			bad "limit dlugich linii" \
				"brak scripts/golden/checkpatch-longlines.max"
		fi
	else
		bad "limit warningow checkpatcha" "brak scripts/golden/checkpatch-warnings.max"
	fi
else
	skip "checkpatch" "brak perla albo scripts/checkpatch.pl"
fi

# ------------------------------------------------------------------ 3. dtb
echo
echo "[3] device tree"
# Artefakt z poprzedniego przebiegu kasujemy ZANIM sprawdzimy, czy jest czym
# budowac: inaczej przy braku dtc bramka dt-validate bierze stary plik.
rm -f "$root/.pc-tools/b2.dtb" "$root/.pc-tools/b2.dts.tmp"
DTC=""
for c in "$root/.pc-tools/dtc" "$root/.pc-tools/dtc.exe" "$lin/scripts/dtc/dtc"; do
	[ -x "$c" ] && { DTC=$c; break; }
done
have dtc && [ -z "$DTC" ] && DTC=$(command -v dtc)

if [ -n "$DTC" ] && have cpp; then
	dts=arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dts
	if [ -f "$lin/$dts" ]; then
		tmp="$root/.pc-tools"
		mkdir -p "$tmp"
		# bez tego padniety dtc zostawia plik z POPRZEDNIEGO przebiegu,
		# a bramka zalicza sie na starym artefakcie
		rm -f "$tmp/b2.dtb" "$tmp/b2.dts.tmp"
		dtb_ok=1
		( cd "$lin" && cpp -E -nostdinc -I scripts/dtc/include-prefixes \
			-undef -D__DTS__ -x assembler-with-cpp -o "$tmp/b2.dts.tmp" "$dts" ) \
			2>"$log/02-dtb.log"
		( cd "$lin" && "$DTC" -o "$tmp/b2.dtb" -b 0 \
			-iarch/arm64/boot/dts/exynos/ -iscripts/dtc/include-prefixes \
			-Wno-unique_unit_address -Wno-unit_address_vs_reg \
			-Wno-avoid_unnecessary_addr_size -Wno-alias_paths \
			-Wno-interrupt_map -Wno-simple_bus_reg "$tmp/b2.dts.tmp" ) \
			>>"$log/02-dtb.log" 2>&1 || dtb_ok=0
		if [ "$dtb_ok" = 1 ] && [ -s "$tmp/b2.dtb" ]; then
			sha=$(sha256sum "$tmp/b2.dtb" | cut -d' ' -f1)
			echo "$sha  exynos9820-beyond2lte.dtb" > "$tmp/dtb.sha256"
			golden "dtb bajt w bajt" "$tmp/dtb.sha256" "dtb.sha256"
		else
			bad "dtb sie buduje" "patrz build-logs/02-dtb.log"
		fi
	else
		bad "dts jest w drzewie" "brak $dts, czy seria jest nalozona"
	fi
else
	skip "dtb" "brak dtc albo cpp, uruchom scripts/pc-prepare.sh"
fi

# Bramki schematow DT bez make: dtschema ma wlasne narzedzia i nie potrzebuje
# kbuilda. dt-validate na DTB odpowiada CHECK_DTBS, dt-doc-validate na plikach
# yaml odpowiada dt_binding_check.
DTV=""; DTD=""
for c in "$root/.pc-tools/venv/Scripts/dt-validate.exe" "$root/.pc-tools/venv/bin/dt-validate"; do
	[ -x "$c" ] && { DTV=$c; DTD=$(dirname "$c")/dt-doc-validate; [ -x "$DTD" ] || DTD=$(dirname "$c")/dt-doc-validate.exe; break; }
done
if [ -z "$DTV" ] && have dt-validate; then
	DTV=$(command -v dt-validate); DTD=$(command -v dt-doc-validate)
fi

if [ -n "$DTV" ] && [ -f "$root/.pc-tools/b2.dtb" ]; then
	# -m doklada wezly, ktorych zaden schemat nie wybral. Bez tego wezel
	# z compatible spoza wszystkich bindingow przechodzi bez slowa, a
	# `make dtbs_check` u opiekuna go pokaze.
	if "$DTV" -m -s "$lin/Documentation/devicetree/bindings" "$root/.pc-tools/b2.dtb" 	   > "$log/03-check-dtbs.log" 2>&1 && [ ! -s "$log/03-check-dtbs.log" ]; then
		ok "dt-validate na dtb (odpowiednik CHECK_DTBS): 0 naruszen"
	else
		bad "dt-validate na dtb" "patrz build-logs/03-check-dtbs.log"
	fi
else
	skip "dt-validate na dtb" "brak dtschema albo .pc-tools/b2.dtb"
fi

if [ -n "$DTD" ] && [ -x "$DTD" ]; then
	yamls=$(grep -hoE "^[+]{3} b/(Documentation/devicetree/bindings/.*[.]yaml)" 		"$root"/patches/*.patch | sed "s|^+++ b/||" | sort -u)
	if [ -n "$yamls" ]; then
		: > "$log/04-dt-binding-check.log"
		for y in $yamls; do
			[ -f "$lin/$y" ] || continue
			"$DTD" -u "$lin/Documentation/devicetree/bindings" "$lin/$y" 				>> "$log/04-dt-binding-check.log" 2>&1
		done
		# Na Windows dtschema zglasza dla KAZDEGO pliku, takze nietknietego pliku
		# mainline, "Cannot determine base path from $id": porownuje sciezke z $id
		# ze sciezka systemowa, a ta ma odwrotne ukosniki. To artefakt srodowiska,
		# nie blad bindingu, wiec ten komunikat i dwie linie po nim sa odsiewane.
		real=$(awk "/Cannot determine base path from/ {skip=2; next} skip>0 {skip--; next} {print}" 			"$log/04-dt-binding-check.log" | grep -c .)
		if [ "$real" = 0 ]; then
			ok "dt-doc-validate na bindingach serii (odpowiednik dt_binding_check)"
		else
			bad "dt-doc-validate na bindingach serii" "patrz build-logs/04-dt-binding-check.log"
		fi
	else
		skip "dt-doc-validate" "seria nie wnosi plikow yaml"
	fi
else
	skip "dt-doc-validate" "brak dtschema"
fi

# Przyklady z bindingow: dt-validate sprawdza zbudowane DTB, dt-doc-validate
# sam schemat, a przyklad nie przechodzi przez zadne z nich. Audyt cytowan
# znalazl tak trzy bledne makra zegarow w dwoch przykladach.
bex=$(sh "$root/scripts/check-binding-examples.sh" 2>&1); rc=$?
if [ "$rc" = 0 ]; then
	ok "przyklady bindingow (odpowiednik dt_binding_check): $(printf "%s" "$bex" | head -1)"
elif [ "$rc" = 2 ]; then
	skip "przyklady bindingow" "brak dtschema albo dtc"
else
	bad "przyklady bindingow" "patrz build-logs/48-binding-examples.log"
fi

# ------------------------------------------------------- 4. kompilacja arm64
echo
echo "[4] kompilacja arm64 (bez make)"
if [ -f "$lin/include/generated/autoconf.h" ] && have clang; then
	for f in drivers/clk/samsung/clk-exynos9820.c \
		 drivers/clk/samsung/clk-pll.c \
		 drivers/pinctrl/samsung/pinctrl-exynos-arm64.c \
		 drivers/pinctrl/samsung/pinctrl-samsung.c \
		 drivers/pmdomain/samsung/exynos-pm-domains.c \
		 drivers/gpu/drm/panel/panel-samsung-s6e3ha9-main.c \
		 drivers/gpu/drm/panel/panel-samsung-s6e3ha9-dimming.c \
		 drivers/gpu/drm/exynos/exynos9820_drm_decon.c \
		 drivers/phy/samsung/phy-exynos9820-dsim.c \
		 drivers/gpu/drm/bridge/samsung-dsim.c \
		 drivers/video/backlight/exynos9820-dsim-lcd.c \
		 drivers/thermal/samsung/exynos9820-tmu.c \
		 drivers/clk/samsung/clk-acpm.c ; do
		if [ ! -f "$lin/$f" ]; then
			bad "kompilacja $f" "pliku nie ma w drzewie"
			continue
		fi
		out=$(sh "$root/scripts/cc-kernel.sh" "$f" 2>&1)
		if [ -z "$out" ]; then
			ok "kompilacja $(basename "$f") (0 uwag)"
		else
			echo "$out" > "$log/cc-$(basename "$f").log"
			bad "kompilacja $(basename "$f")" "uwagi w build-logs/cc-$(basename "$f").log"
		fi
		w1=$(W=1 sh "$root/scripts/cc-kernel.sh" "$f" 2>&1)
		if [ -z "$w1" ]; then
			ok "kompilacja W=1 $(basename "$f") (0 uwag)"
		else
			echo "$w1" > "$log/cc-w1-$(basename "$f").log"
			bad "kompilacja W=1 $(basename "$f")" "uwagi w build-logs/cc-w1-$(basename "$f").log"
		fi
	done
else
	skip "kompilacja arm64" "brak clang albo include/generated/autoconf.h (scripts/pc-prepare.sh)"
fi

# Analiza sciezkowa clanga: lapie odczyt niezainicjowanej wartosci albo
# wyluskanie NULL-a, czyli to, czego kompilacja W=1 nie widzi, bo nie chodzi
# o skladnie tylko o sciezke wykonania. Wzorzec pilnuje, ze lista znalezisk
# sie nie powieksza.
if [ "$UPDATE" = 1 ]; then
	ana=$(sh "$root/scripts/check-analyzer.sh" --update-golden 2>&1); rc=$?
else
	ana=$(sh "$root/scripts/check-analyzer.sh" 2>&1); rc=$?
fi
if [ "$rc" = 0 ]; then
	ok "analizator statyczny clang: $(printf "%s" "$ana" | tail -1 | sed "s/^check-analyzer: //")"
elif [ "$rc" = 2 ]; then
	skip "analizator statyczny clang" "brak clang albo drzewo nieprzygotowane"
else
	bad "analizator statyczny clang" "patrz build-logs/diff-analyzer.txt"
fi

# -------------------------------------------------------- 5. bramki liczbowe
echo
echo "[5] stale i tablice wobec zrodel producenta"
PY=python3
if have $PY && [ -d "$ds" ]; then
	export PYTHONIOENCODING=utf-8
	tmp=$(mktemp -d)

	if $PY "$root/scripts/decode-pps.py" "$ds/s6e3ha9_beyond2_a3_s0_panel.h" > "$tmp/pps-beyond2.txt" 2>&1; then
		golden "PPS panelu beyond2 (128 B)" "$tmp/pps-beyond2.txt" "pps-beyond2.txt"
	else
		bad "PPS panelu beyond2 (128 B)" "skrypt zwrocil blad"
	fi

	if $PY "$root/scripts/decode-pps.py" "$ds/s6e3ha9_param.h" > "$tmp/pps-dpu20.txt" 2>&1; then
		golden "PPS dpu20 (kontrola krzyzowa)" "$tmp/pps-dpu20.txt" "pps-dpu20.txt"
	else
		bad "PPS dpu20 (kontrola krzyzowa)" "skrypt zwrocil blad"
	fi

	if $PY "$root/scripts/ffc-calc.py" > "$tmp/ffc.txt" 2>&1; then
		golden "model FFC (0xC5)" "$tmp/ffc.txt" "ffc.txt"
	else
		bad "model FFC (0xC5)" "skrypt zwrocil blad"
	fi

	if $PY "$root/scripts/dump-init-seq.py" "$ds/s6e3ha9_beyond2_a3_s0_panel.h" \
		beyond2_a3_s0_init_cmdtbl > "$tmp/init-seq.txt" 2>&1; then
		golden "sekwencja init rozwinieta" "$tmp/init-seq.txt" "init-seq.txt"
	else
		bad "sekwencja init rozwinieta" "skrypt zwrocil blad"
	fi

	if $PY "$root/scripts/dump-init-seq.py" "$ds/s6e3ha9_beyond2_a3_s0_panel.h" \
		beyond2_a3_s0_display_on_cmdtbl > "$tmp/display-on.txt" 2>&1; then
		golden "sekwencja display-on" "$tmp/display-on.txt" "display-on.txt"
	else
		bad "sekwencja display-on" "skrypt zwrocil blad"
	fi

	if $PY "$root/scripts/check-dsc-config.py" > "$tmp/dsc.txt" 2>&1; then
		ok "DSC panelu: 30/30 pol zgodnych z firmowym PPS"
	else
		cp "$tmp/dsc.txt" "$log/23-dsc-config-check.log"
		bad "DSC panelu" "patrz build-logs/23-dsc-config-check.log"
	fi

	if CC=${CC:-clang} $PY "$root/scripts/check-decon-dsc.py" > "$tmp/decon.txt" 2>&1; then
		ok "DSC enkoderow DECON: 18/18 pol"
	else
		cp "$tmp/decon.txt" "$log/33-decon-dsc-check.log"
		bad "DSC enkoderow DECON" "patrz build-logs/33-decon-dsc-check.log"
	fi

	if $PY "$root/scripts/check-aid-tables.py" > "$tmp/aid.txt" 2>&1; then
		ok "tablice AID: $(grep -o 'wierszy w sterowniku: [0-9]*' "$tmp/aid.txt" | head -1)"
	else
		cp "$tmp/aid.txt" "$log/40-aid-tables-check.log"
		bad "tablice AID" "patrz build-logs/40-aid-tables-check.log"
	fi
	rm -rf "$tmp"
else
	skip "bramki liczbowe" "brak python3 albo sources/ds"
fi

# silnik dimmingu wymaga kompilatora hosta
if have "${CC:-clang}" || have gcc; then
	if CC=$(have clang && echo clang || echo gcc) sh "$root/scripts/check-dimming-engine.sh" \
		> "$log/42-dimming-engine-check.log" 2>&1; then
		ok "silnik dimmingu: 74/74 poziomy dla 7 zestawow MTP"
	else
		bad "silnik dimmingu" "patrz build-logs/42-dimming-engine-check.log"
	fi
else
	skip "silnik dimmingu" "brak kompilatora hosta"
fi

# Bramka bisectowalnosci jest droga (przestawia drzewo po kazdym commicie
# dotykajacym kodu), wiec jest opcjonalna: VERIFY_BISECT=1 scripts/verify.sh
if [ "${VERIFY_BISECT:-0}" = "1" ]; then
	echo
	echo "[5b] bisectowalnosc serii"
	if sh "$root/scripts/check-bisect.sh" > "$log/46-bisect.log" 2>&1; then
		ok "kazdy punkt serii kompiluje sie w swoim miejscu"
	else
		bad "bisectowalnosc serii" "patrz build-logs/46-bisect.log"
	fi
fi


# Odsylacze do patchy w dokumentach: numery zmieniaja sie przy kazdym
# przestawieniu serii, wiec migawka pilnuje, ze wskazuja to samo co wczesniej.
if have python3; then
	if [ "$UPDATE" = 1 ]; then
		python3 "$root/scripts/check-doc-refs.py" --update > /dev/null 2>&1
		printf "  ZAPIS   migawka odsylaczy do patchy
"
	elif python3 "$root/scripts/check-doc-refs.py" > "$log/47-doc-refs.log" 2>&1; then
		ok "odsylacze do patchy w dokumentach"
		rm -f "$log/47-doc-refs.log"
	else
		bad "odsylacze do patchy w dokumentach" "patrz build-logs/47-doc-refs.log"
	fi
fi


# Kazdy cytat musi dac sie otworzyc. Seria wskazywala na decon_reg.c:1073,
# regs-dpp.h i cmucal-sfr.c, ktorych nie bylo w sources/, wiec dziesiatki stalych
# byly formalnie nie do sprawdzenia mimo poprawnego cytatu.
if have python3 && [ -d "$ds" ]; then
	if python3 "$root/scripts/check-citations.py" > "$log/48-citations.log" 2>&1; then
		ok "cytaty do zrodel: $(grep -o 'cytatow z linia [0-9]*' "$log/48-citations.log")"
		rm -f "$log/48-citations.log"
	else
		bad "cytaty do zrodel" "patrz build-logs/48-citations.log"
	fi

	# Piec blednych stalych rejestrow przeszlo checkpatch, W=1 i dt-validate.
	# Zadna nie psuje builda, kazda psuje obraz bez sladu w logu.
	if python3 "$root/scripts/check-regs.py" > "$log/49-regs.log" 2>&1; then
		ok "rejestry wobec producenta: $(grep -o 'rozwiazane wobec producenta [0-9]*' "$log/49-regs.log")"
		rm -f "$log/49-regs.log"
	else
		bad "rejestry wobec producenta" "patrz build-logs/49-regs.log"
	fi

	# Tablica kalibracyjna PHY UFS w serii bootloadera wobec warstwy CAL
	# producenta. Bramka idzie w obie strony: zla wartosc i POMINIETY wpis.
	# Ta druga polowa jest wazniejsza, bo fork, ktory sluzy za punkt
	# odniesienia, mial wszystkie przepisane wartosci dobre, a gubil cale
	# tablice i czekania.
	python3 "$root/scripts/check-ufs-phy-cal.py" > "$log/60-ufs-phy-cal.log" 2>&1
	case $? in
	0)
		ok "PHY UFS wobec producenta: $(grep -o 'wpisow zgodnych z producentem [0-9]*' "$log/60-ufs-phy-cal.log")"
		rm -f "$log/60-ufs-phy-cal.log"
		;;
	2)
		skip "PHY UFS wobec producenta" "$(tail -1 "$log/60-ufs-phy-cal.log")"
		rm -f "$log/60-ufs-phy-cal.log"
		;;
	*)
		bad "PHY UFS wobec producenta" "patrz build-logs/60-ufs-phy-cal.log"
		;;
	esac

	# Blizniacza bramka dla sterownika HOSTA: warstwy, ktore ida przez DME
	# i przez okno UniPro. Poza poprawnoscia i kompletnoscia sprawdza jeszcze
	# KOLEJNOSC: przekazanie sterowania do PHY ma stac dokladnie tam, gdzie
	# u producenta lezy blok PMA. Bez tego wpisy, ktore u producenta ten blok
	# OTACZAJA (para zapisow atrybutu 0xA006 w tablicy po-linkowej), moglyby
	# wyladowac po zlej jego stronie, czego zadne porownanie wartosci nie widzi.
	python3 "$root/scripts/check-ufs-host-cal.py" > "$log/61-ufs-host-cal.log" 2>&1
	case $? in
	0)
		ok "host UFS wobec producenta: $(grep -o 'wpisow zgodnych z producentem [0-9]*' "$log/61-ufs-host-cal.log")"
		rm -f "$log/61-ufs-host-cal.log"
		;;
	2)
		skip "host UFS wobec producenta" "$(tail -1 "$log/61-ufs-host-cal.log")"
		rm -f "$log/61-ufs-host-cal.log"
		;;
	*)
		bad "host UFS wobec producenta" "patrz build-logs/61-ufs-host-cal.log"
		;;
	esac

	# Te same tablice producenta przepisane po raz drugi, tym razem do jadra.
	# Osobna bramka, bo przy przepisaniu zmienil sie dialekt makr i ksztalt
	# sekwencji (dwa oczekiwania wyszly z tablic do hakow), wiec porownanie
	# jednego sterownika z drugim niczego nie dowodzi: obie wersje musza
	# zgadzac sie z producentem osobno.
	python3 "$root/scripts/check-ufs-phy-kernel.py" > "$log/65-ufs-phy-kernel.log" 2>&1
	case $? in
	0)
		ok "PHY UFS jadra wobec producenta: $(grep -o 'wpisow zgodnych z producentem [0-9]*' "$log/65-ufs-phy-kernel.log")"
		rm -f "$log/65-ufs-phy-kernel.log"
		;;
	2)
		skip "PHY UFS jadra wobec producenta" "$(tail -1 "$log/65-ufs-phy-kernel.log")"
		rm -f "$log/65-ufs-phy-kernel.log"
		;;
	*)
		bad "PHY UFS jadra wobec producenta" "patrz build-logs/65-ufs-phy-kernel.log"
		;;
	esac

	# Warstwy hosta w jadrze. Mainline nie zna zadnej struktury tablicowej,
	# wiec te same zapisy sa tam jawnymi wywolaniami w hakach i bramka
	# porownuje ZBIORY par (atrybut, wartosc, rodzaj), a nie wpis po wpisie.
	python3 "$root/scripts/check-ufs-host-kernel.py" > "$log/66-ufs-host-kernel.log" 2>&1
	case $? in
	0)
		ok "host UFS jadra wobec producenta: $(grep -o 'wpisow zgodnych z producentem [0-9]*' "$log/66-ufs-host-kernel.log")"
		rm -f "$log/66-ufs-host-kernel.log"
		;;
	2)
		skip "host UFS jadra wobec producenta" "$(tail -1 "$log/66-ufs-host-kernel.log")"
		rm -f "$log/66-ufs-host-kernel.log"
		;;
	*)
		bad "host UFS jadra wobec producenta" "patrz build-logs/66-ufs-host-kernel.log"
		;;
	esac

	# Wezel UFS w drzewie urzadzen. dt-validate sprawdza KSZTALT, nie TRESC:
	# adres przepisany o cyfre obok, przerwanie sasiedniego bloku albo nazwy
	# zegarow z bootloadera przechodza walidacje bez slowa, a ta ostatnia
	# pozycja konczy probe sterownika bledem.
	python3 "$root/scripts/check-ufs-dts.py" > "$log/67-ufs-dts.log" 2>&1
	case $? in
	0)
		ok "wezel UFS wobec producenta: $(grep -o 'sprawdzonych zgodnosci z producentem [0-9]*' "$log/67-ufs-dts.log")"
		rm -f "$log/67-ufs-dts.log"
		;;
	2)
		skip "wezel UFS wobec producenta" "$(tail -1 "$log/67-ufs-dts.log")"
		rm -f "$log/67-ufs-dts.log"
		;;
	*)
		bad "wezel UFS wobec producenta" "patrz build-logs/67-ufs-dts.log"
		;;
	esac

	# Drzewo urzadzen bootloadera. Trzy pliki w dts/upstream to KOPIE plikow
	# serii jadra, a kopia rozjezdza sie po cichu. Do tego numer aliasu
	# pinctrl wybiera tablice bankow w sterowniku, wiec rozjazd tych dwoch
	# kolejnosci daje piny ustawiane w zlym bloku bez slowa w logu.
	python3 "$root/scripts/check-uboot-dts.py" > "$log/62-uboot-dts.log" 2>&1
	case $? in
	0)
		ok "DT bootloadera: $(grep -o 'kopii bajt w bajt z seria jadra [0-9]*' "$log/62-uboot-dts.log")"
		rm -f "$log/62-uboot-dts.log"
		;;
	2)
		skip "DT bootloadera" "$(tail -1 "$log/62-uboot-dts.log")"
		rm -f "$log/62-uboot-dts.log"
		;;
	*)
		bad "DT bootloadera" "patrz build-logs/62-uboot-dts.log"
		;;
	esac

	# Seria bootloadera kontra jego drzewo robocze. Odpowiednik punktu 1 dla
	# serii jadra, ktorego strona bootloadera nie miala wcale: 21.09.2026
	# poza seria lezalo 2391 linii plus commit opisany jako WIP, a README
	# katalogu twierdzil, ze port jest kompletny w osmiu patchach. Zadna
	# z pozostalych bramek tego nie widziala, bo wszystkie czytaja drzewo.
	sh "$root/scripts/check-uboot-seria.sh" > "$log/79-uboot-seria.log" 2>&1
	case $? in
	0)
		ok "seria bootloadera: $(grep -o 'latek [0-9]*, wszystko w normie' "$log/79-uboot-seria.log")"
		rm -f "$log/79-uboot-seria.log"
		;;
	2)
		skip "seria bootloadera" "$(tail -1 "$log/79-uboot-seria.log")"
		rm -f "$log/79-uboot-seria.log"
		;;
	*)
		bad "seria bootloadera" "patrz build-logs/79-uboot-seria.log"
		;;
	esac

	# Kolejnosc rejestracji zegarow bootloadera. clk_register wiaze zegar
	# z rodzicem PO NAZWIE w chwili rejestracji, a gdy rodzica jeszcze nie
	# ma, NIE PRZERYWA: wiaze z NULL-em i od tej chwili czestotliwosc jest
	# liczona z kodu bledu, bez ani jednego komunikatu. Tak padlo lacze UFS:
	# dzielnik zwracal DIV_ROUND_UP(-ENODEV, 2), sterownik wzial to za zegar
	# UniPro, a objawil sie "link startup failed -110", czyli zupelnie gdzie
	# indziej niz przyczyna.
	python3 "$root/scripts/check-uboot-clk-order.py" > "$log/64-uboot-clk-order.log" 2>&1
	case $? in
	0)
		ok "kolejnosc zegarow bootloadera: $(grep -o 'zegarow [0-9]* w [0-9]* CMU' "$log/64-uboot-clk-order.log")"
		rm -f "$log/64-uboot-clk-order.log"
		;;
	2)
		skip "kolejnosc zegarow bootloadera" "$(tail -1 "$log/64-uboot-clk-order.log")"
		rm -f "$log/64-uboot-clk-order.log"
		;;
	*)
		bad "kolejnosc zegarow bootloadera" "patrz build-logs/64-uboot-clk-order.log"
		;;
	esac

	# Analiza statyczna kodu bootloadera. Seria jadra ma swoj analizator,
	# seria bootloadera nie miala zadnego, a to jest kod, ktory NIGDY SIE NIE
	# WYKONAL: dopoki telefon nie wystartuje, to jedyne narzedzie, ktore moze
	# w nim cokolwiek znalezc. Bramka wola clanga (sciezki) i sparse'a (typy,
	# w tym przestrzenie adresowe przy MMIO). Trzy klasy tla maja osobne
	# pulapy, wszystko poza nimi ma byc zerem.
	sh "$root/scripts/check-uboot-analyzer.sh" > "$log/63-uboot-analyzer.log" 2>&1
	case $? in
	0)
		ok "analiza statyczna bootloadera: $(grep -o 'plikow [0-9]*, clang [0-9]*' "$log/63-uboot-analyzer.log")"
		rm -f "$log/63-uboot-analyzer.log"
		;;
	2)
		skip "analiza statyczna bootloadera" "$(tail -1 "$log/63-uboot-analyzer.log")"
		rm -f "$log/63-uboot-analyzer.log"
		;;
	*)
		bad "analiza statyczna bootloadera" "patrz build-logs/63-uboot-analyzer-detail.log"
		;;
	esac

	# Predkosc lacza, ktora wyliczy host, musi istniec w tablicy timingow PHY.
	# Bez tej bramki host prosil o 1592 Mbps, bo liczyl z nieskompresowanych
	# 24 bpp, a PHY ma wiersz tylko dla 898: kompilacja, checkpatch, dt-validate
	# i hash DTB byly przy tym zielone.
	if python3 "$root/scripts/check-link-rate.py" > "$log/51-link-rate.log" 2>&1; then
		ok "predkosc lacza wobec tablicy D-PHY"
		rm -f "$log/51-link-rate.log"
	else
		bad "predkosc lacza wobec tablicy D-PHY" "patrz build-logs/51-link-rate.log"
	fi

	# Sterownik zegarow wobec tablic CAL producenta, nie wobec innego portu.
	if python3 "$root/scripts/check-cmu.py" > "$log/50-cmu.log" 2>&1; then
		ok "zegary wobec cmucal: $(grep -o 'offsetow [0-9]*/[0-9]*' "$log/50-cmu.log") offsetow"
		rm -f "$log/50-cmu.log"
	else
		bad "zegary wobec cmucal" "patrz build-logs/50-cmu.log"
	fi

	# Spojnosc samego drzewa zegarow: zly rodzic nie wywala kompilacji
	# ani porownania z producentem, tylko zostawia zegar bez rodzica.
	if python3 "$root/scripts/check-clk-parents.py" \
		> "$log/52-clk-parents.log" 2>&1; then
		ok "drzewo zegarow bez sierot: $(grep -o 'zegarow [0-9]*' "$log/52-clk-parents.log")"
		rm -f "$log/52-clk-parents.log"
	else
		bad "drzewo zegarow bez sierot" "patrz build-logs/52-clk-parents.log"
	fi

	# Sierota to jedno, zly rodzic to drugie: bramka wyzej wymaga tylko, zeby
	# nazwa rodzica gdziekolwiek istniala, wiec zamiana rodzicow miedzy dwoma
	# zegarami przez nia przechodzi. Ta porownuje rodzica z tablica producenta.
	if python3 "$root/scripts/check-clk-vendor-parents.py" \
		> "$log/53-clk-vendor-parents.log" 2>&1; then
		ok "rodzice zegarow wobec producenta: $(grep -o 'zgodnych z producentem [0-9]*, udokumentowanych wyjatkow [0-9]*' "$log/53-clk-vendor-parents.log")"
		rm -f "$log/53-clk-vendor-parents.log"
	else
		bad "rodzice zegarow wobec producenta" "patrz build-logs/53-clk-vendor-parents.log"
	fi

	# Wezel z compatible, ktorego zaden sterownik nie obsluguje, nie probuje
	# sie i nie mowi o tym ani slowa: nie widzi tego ani kompilacja, ani
	# dtbs_check.  Tak przez cala serie brakowalo tablic pinow Exynos9820.
	if python3 "$root/scripts/check-compatibles.py" \
		> "$log/53-compatibles.log" 2>&1; then
		ok "kazdy wezel DT ma sterownik: $(grep -o 'wezlow [0-9]*' "$log/53-compatibles.log")"
		rm -f "$log/53-compatibles.log"
	else
		bad "kazdy wezel DT ma sterownik" "patrz build-logs/53-compatibles.log"
	fi

	# Makro zegara, ktorego nie ma w naglowku, zatrzymuje kompilacje
	# drzewa urzadzen, ale w PRZYKLADZIE w pliku bindingu przechodzi
	# niezauwazone: przyklady kompiluje dopiero make dt_binding_check.
	if python3 "$root/scripts/check-clk-macros.py" \
		> "$log/54-clk-macros.log" 2>&1; then
		ok "makra zegarow istnieja: $(grep -o 'uzyc [0-9]*' "$log/54-clk-macros.log")"
		rm -f "$log/54-clk-macros.log"
	else
		bad "makra zegarow istnieja" "patrz build-logs/54-clk-macros.log"
	fi
else
	skip "bramki cytatow i stalych" "brak python3 albo sources/ds"
fi


# Zrodla producenta w sources/ds sa poza gitem, wiec nic nie pilnowalo ich
# tresci: rownoczesna zmiana w sterowniku i w pliku zrodlowym dawala pelna
# zielonosc. Suma kontrolna przypina je tak samo jak commity w SOURCES.md.
if [ -d "$ds" ] && have sha256sum; then
	dsum=$(mktemp)
	( cd "$ds" && LC_ALL=C sha256sum $(LC_ALL=C ls | LC_ALL=C sort) ) > "$dsum" 2>/dev/null
	golden "zrodla producenta w sources/ds" "$dsum" "sources-ds.sha256"
	rm -f "$dsum"
else
	skip "sumy kontrolne sources/ds" "brak katalogu albo sha256sum"
fi

# Suma kontrolna wyzej przypina TRESC plikow producenta, ale nie mowi, skad
# one sa. Siedem plikow doszlo do sources/ds bez wiersza w SOURCES.md, wiec
# czytelnik odtwarzajacy prace dostawal plik bez sciezki w drzewie producenta.
if [ -d "$ds" ] && have python3; then
	if python3 "$root/scripts/check-sources-doc.py" 		> "$log/55-sources-doc.log" 2>&1; then
		ok "kazde zrodlo producenta opisane w SOURCES.md: $(grep -o 'plikow [0-9]*' "$log/55-sources-doc.log")"
		rm -f "$log/55-sources-doc.log"
	else
		bad "kazde zrodlo producenta opisane w SOURCES.md" "patrz build-logs/55-sources-doc.log"
	fi
else
	skip "opis zrodel w SOURCES.md" "brak python3 albo sources/ds"
fi

# Generator pliku plyty sam o sobie pisze, ze jest zrodlem prawdy, ale nikt tego
# nie sprawdzal i rozjechal sie z seria: caly blok reserved-memory z rundy R9
# istnial tylko w serii, a wersja z generatora byla o 79 wierszy krotsza.
if have python3; then
	python3 "$root/scripts/check-gen-dts.py" > "$log/57-gen-dts.log" 2>&1
	case $? in
	0)
		ok "oba pliki DT zgodne ze swoimi generatorami (10 + 6 etapow)"
		rm -f "$log/57-gen-dts.log"
		;;
	2)
		skip "oba pliki DT zgodne ze swoimi generatorami" "$(tail -1 "$log/57-gen-dts.log")"
		rm -f "$log/57-gen-dts.log"
		;;
	*)
		bad "oba pliki DT zgodne ze swoimi generatorami" "patrz build-logs/57-gen-dts.log"
		;;
	esac

	# Stan koncowy KAZDEGO generowanego pliku, takze tych bez etapow.
	if python3 "$root/scripts/check-generatory.py" > "$log/58-generatory.log" 2>&1; then
		ok "pliki generowane zgodne z generatorami: $(tail -1 "$log/58-generatory.log")"
		rm -f "$log/58-generatory.log"
	else
		bad "pliki generowane zgodne z generatorami" "patrz build-logs/58-generatory.log"
	fi

	# Latki serii: arytmetyka naglowkow fragmentow i brak zjedzonych spacji.
	if python3 "$root/scripts/check-latki.py" > "$log/59-latki.log" 2>&1; then
		ok "latki serii poprawnie zbudowane: $(tail -1 "$log/59-latki.log")"
		rm -f "$log/59-latki.log"
	else
		bad "latki serii poprawnie zbudowane" "patrz build-logs/59-latki.log"
	fi

	# Czy latki niosa to, co dzis wypisuja generatory.
	if python3 "$root/scripts/odswiez-latki.py" > "$log/60-latki-generatory.log" 2>&1; then
		ok "latki plikow generowanych zgodne z generatorami"
		rm -f "$log/60-latki-generatory.log"
	else
		bad "latki plikow generowanych zgodne z generatorami" "uruchom scripts/odswiez-latki.py --zapisz"
	fi
else
	skip "oba pliki DT zgodne ze swoimi generatorami" "brak python3"
fi

# Naglowek czcionki klawiatury ma 16384 bajty przepisane z jadra; recznej zmiany
# w takim pliku nie widac ani w kodzie, ani w kompilacji, a psuje obraz na ekranie.
if have python3; then
	python3 "$root/scripts/check-font-klawiatury.py" > "$log/58-font-klawiatury.log" 2>&1
	case $? in
	0)
		ok "czcionka klawiatury zgodna z generatorem"
		rm -f "$log/58-font-klawiatury.log"
		;;
	2)
		skip "czcionka klawiatury zgodna z generatorem" "$(tail -1 "$log/58-font-klawiatury.log")"
		rm -f "$log/58-font-klawiatury.log"
		;;
	*)
		bad "czcionka klawiatury zgodna z generatorem" "patrz build-logs/58-font-klawiatury.log"
		;;
	esac
else
	skip "czcionka klawiatury zgodna z generatorem" "brak python3"
fi

# Druga czcionka klawiatury: Droid Sans wrasteryzowany z pliku TTF.  Ta sama
# zasada, co wyzej, tylko wartosci nie sa przepisane z jadra, lecz wyliczone
# z krzywych, wiec zaleza takze od wersji biblioteki rasteryzujacej.
if have python3; then
	python3 "$root/scripts/check-font-sans.py" > "$log/63-font-sans.log" 2>&1
	case $? in
	0)
		ok "czcionka proporcjonalna zgodna z generatorem"
		rm -f "$log/63-font-sans.log"
		;;
	2)
		skip "czcionka proporcjonalna zgodna z generatorem" "$(tail -1 "$log/63-font-sans.log")"
		rm -f "$log/63-font-sans.log"
		;;
	*)
		bad "czcionka proporcjonalna zgodna z generatorem" "patrz build-logs/63-font-sans.log"
		;;
	esac
else
	skip "czcionka proporcjonalna zgodna z generatorem" "brak python3"
fi

# Czcionka konsoli nie jest trzymana w drzewie, tylko generowana przy wszywaniu
# do obrazu, wiec nie ma z czym porownac jej tresci.  Bramka sprawdza wiec
# WLASNOSCI wyniku: 512 glifow i tablice Unicode.  Bez tablicy klawiatura
# wysyla poprawne bajty, a konsola rysuje "z" zamiast "ż" (zmierzone).
if have python3; then
	python3 "$root/scripts/check-psf-konsoli.py" > "$log/64-psf-konsoli.log" 2>&1
	case $? in
	0)
		ok "czcionka konsoli ma tablice Unicode i polskie litery"
		rm -f "$log/64-psf-konsoli.log"
		;;
	2)
		skip "czcionka konsoli ma tablice Unicode" "$(tail -1 "$log/64-psf-konsoli.log")"
		rm -f "$log/64-psf-konsoli.log"
		;;
	*)
		bad "czcionka konsoli ma tablice Unicode" "patrz build-logs/64-psf-konsoli.log"
		;;
	esac
else
	skip "czcionka konsoli ma tablice Unicode" "brak python3"
fi

# Szerokosci klawiszy sa wagami rzedu, a caly uklad jest przeniesiony
# z klawiatury Qt uzytkownika.  Rozjazd ze wzorcem kompiluje sie bez slowa,
# a widac go dopiero na telefonie: klawisz w innym miejscu albo taki, ktorego
# we wzorcu nie ma.
if have python3; then
	python3 "$root/scripts/check-uklad-klawiatury.py" > "$log/59-uklad-klawiatury.log" 2>&1
	case $? in
	0)
		ok "uklad klawiatury zgodny ze wzorcem QML"
		rm -f "$log/59-uklad-klawiatury.log"
		;;
	2)
		skip "uklad klawiatury zgodny ze wzorcem QML" "$(tail -1 "$log/59-uklad-klawiatury.log")"
		rm -f "$log/59-uklad-klawiatury.log"
		;;
	*)
		bad "uklad klawiatury zgodny ze wzorcem QML" "patrz build-logs/59-uklad-klawiatury.log"
		;;
	esac
else
	skip "uklad klawiatury zgodny ze wzorcem QML" "brak python3"
fi

# Mapa RAM-u, trzy obszary EL2/KASLR i adres framebuffera przestaly byc zgadywane
# 11 wrzesnia 2026: sa odczytane z telefonu (measurements/2026-09-11-etap0a).
# Regula 3 z docs/HW-BLOCKED.md kaze zamknieta pozycje przypiac bramka, a sama suma
# kontrolna DTB tego nie robi: zmienia sie przy kazdej zmianie drzewa, wiec kusi, zeby
# ja nadpisac. Ta bramka porownuje wartosci, nie hasze.
if have python3; then
	python3 "$root/scripts/check-memory-map.py" > "$log/58-memory-map.log" 2>&1
	case $? in
	0)
		ok "mapa pamieci zgodna z odczytem z telefonu: $(grep -o '[0-9]* bankow[^,]*' "$log/58-memory-map.log")"
		rm -f "$log/58-memory-map.log"
		;;
	# 2 = brak materialu albo brak zbudowanego DTB. Bramka NIE zostala uruchomiona
	# i nie wolno jej policzyc jako zielonej: to ten sam blad, ktory ta bramka lapie
	# w drzewie, tylko po stronie samej bramki.
	2)
		skip "mapa pamieci zgodna z odczytem z telefonu" "$(tail -1 "$log/58-memory-map.log")"
		rm -f "$log/58-memory-map.log"
		;;
	*)
		bad "mapa pamieci zgodna z odczytem z telefonu" "patrz build-logs/58-memory-map.log"
		;;
	esac
else
	skip "mapa pamieci zgodna z odczytem z telefonu" "brak python3"
fi

# Ten egzemplarz zglasza panel 0xA11013, a naglowek, z ktorego przepisano tablice, zna
# 0xA01010 i 0xA01011. Rozjazd okazal sie pozorny, bo producent dopasowuje wariant przez
# tablice z maska, a nie przez pole .id. Bramka pilnuje tego rachunku, zeby nikt pozniej
# nie podmienil tablic na inny wariant "dla zgodnosci z identyfikatorem".
if have python3; then
	python3 "$root/scripts/check-panel-variant.py" > "$log/59-panel-variant.log" 2>&1
	case $? in
	0)
		ok "panel tego egzemplarza wybiera wariant, z ktorego sa tablice"
		rm -f "$log/59-panel-variant.log"
		;;
	2)
		skip "panel tego egzemplarza wybiera wariant, z ktorego sa tablice" "$(tail -1 "$log/59-panel-variant.log")"
		rm -f "$log/59-panel-variant.log"
		;;
	*)
		bad "panel tego egzemplarza wybiera wariant, z ktorego sa tablice" "patrz build-logs/59-panel-variant.log"
		;;
	esac
else
	skip "panel tego egzemplarza wybiera wariant, z ktorego sa tablice" "brak python3"
fi

# Blok wyswietlacza serii jest przepisany z tablic producenta bez udokumentowanej
# jednostki (HW-01), bez zmierzonego zegara lacza (HW-02) i ze sporem 18 kontra 20
# MHz na zegarze escape (HW-03). Log S-Boota tego egzemplarza pokazuje, co bootloader
# NAPRAWDE programuje, gdy panel zaswieca: te wartosci przypina bramka do serii, plus
# rewizje krzemu EVT1 (HW-11 zamkniete). Nikt nie ruszy naszych licznikow w bok od sprzetu.
if have python3; then
	python3 "$root/scripts/check-dphy-timing.py" > "$log/60-dphy-timing.log" 2>&1
	case $? in
	0)
		ok "D-PHY, PLL, escape i rewizja krzemu zgodne z logiem S-Boota: $(grep -o 'rewizja EVT[0-9.]*' "$log/60-dphy-timing.log")"
		rm -f "$log/60-dphy-timing.log"
		;;
	2)
		skip "D-PHY i rewizja krzemu wobec logu S-Boota" "$(tail -1 "$log/60-dphy-timing.log")"
		rm -f "$log/60-dphy-timing.log"
		;;
	*)
		bad "D-PHY, PLL, escape i rewizja krzemu zgodne z logiem S-Boota" "patrz build-logs/60-dphy-timing.log"
		;;
	esac
else
	skip "D-PHY i rewizja krzemu wobec logu S-Boota" "brak python3"
fi

# Sterownik PLL czyta M, P i S wprost spod con_offset, a te wspolczynniki leza
# w CON3, nie w CON0. Pierwsza wersja sterownika zegarow przekazywala CON0 dla
# wszystkich dziewieciu PLL-i, wiec kazda odczytana czestotliwosc byla liczona
# z rejestru sterujacego. Blad nie przeszkadza w starcie (zegary ustawia
# bootloader, bledny jest tylko odczyt) i dlatego przezyl do teraz.
if have python3; then
	python3 "$root/scripts/check-pll-con3.py" > "$log/61-pll-con3.log" 2>&1
	case $? in
	0)
		ok "zaden PLL nie jest rejestrowany jako PLL: $(grep -o 'stalych czestotliwosci [0-9]* zgodnych' "$log/61-pll-con3.log")"
		rm -f "$log/61-pll-con3.log"
		;;
	2)
		skip "offsety CON3 w wywolaniach PLL()" "$(tail -1 "$log/61-pll-con3.log")"
		rm -f "$log/61-pll-con3.log"
		;;
	*)
		bad "zaden PLL nie jest rejestrowany jako PLL" "patrz build-logs/61-pll-con3.log"
		;;
	esac
else
	skip "offsety CON3 w wywolaniach PLL()" "brak python3"
fi

# Warstwa konfiguracji. Bramka kompilacji podaje pliki kompilatorowi wprost,
# wiec nie pyta Kconfiga, czy te pliki w ogole trafilyby do obrazu. Jadro
# zbudowane z samego arm64 defconfiga nie ma ani DECON-a, ani panelu, ani
# D-PHY, ani regulatorow panelu, i nie zapali ekranu mimo zielonych bramek.
if [ -x "$root/.pc-tools/conf" ] || [ -x "$root/.pc-tools/conf.exe" ]; then
	if sh "$root/scripts/check-kconfig.sh" 		> "$log/56-kconfig.log" 2>&1; then
		ok "fragment konfiguracji scala sie z defconfigiem: $(grep -o 'zamowionych symboli [0-9]*, swiadomie wylaczonych [0-9]*' "$log/56-kconfig.log")"
		rm -f "$log/56-kconfig.log"
	else
		bad "fragment konfiguracji scala sie z defconfigiem" "patrz build-logs/56-kconfig.log"
	fi
	# To samo dla nakladki, z ktorej naprawde budowany jest obraz na telefon.
	# Sterownik zalezny od wylaczonego tam DSI (latka 0100) wypadalby z obrazu
	# po cichu, a pierwsza bramka tego nie widzi, bo liczy sam fragment serii.
	if sh "$root/scripts/check-kconfig.sh" "$root/scripts/bringup.config" \
		> "$log/56-kconfig-bringup.log" 2>&1; then
		ok "nakladka uruchomieniowa scala sie z fragmentem: $(grep -o 'zamowionych symboli [0-9]*, swiadomie wylaczonych [0-9]*' "$log/56-kconfig-bringup.log")"
		rm -f "$log/56-kconfig-bringup.log"
	else
		bad "nakladka uruchomieniowa scala sie z fragmentem" "patrz build-logs/56-kconfig-bringup.log"
	fi
else
	skip "fragment konfiguracji" "brak .pc-tools/conf, uruchom scripts/pc-prepare.sh"
fi


# ------------------------------------------------ 6. spojnosc HW-BLOCKED
echo
echo "[6] spojnosc z docs/HW-BLOCKED.md"
hw="$root/docs/HW-BLOCKED.md"
mapa="$gold/unverified-sites.txt"
# Kod idacy na liste NIE nosi numerow pozycji: docs/HW-BLOCKED.md nie trafia
# do jadra, wiec "HW-26" nic by czytelnikowi upstream nie mowilo, a dwie z tych
# adnotacji siedza we wspolnym samsung-dsim.c. Zwiazek adnotacja <-> pozycja
# trzyma mapa, a te trzy bramki pilnuja jej w obie strony.
if [ ! -f "$hw" ]; then
	bad "docs/HW-BLOCKED.md istnieje" "pliku nie ma"
elif [ ! -f "$mapa" ]; then
	bad "mapa scripts/golden/unverified-sites.txt istnieje" "pliku nie ma"
else
	brak_frazy=""; brak_pozycji=""; zle_miejsce=""; nwierszy=0
	while IFS='|' read -r plik ids fraza; do
		case "$plik" in ''|'#'*) continue ;; esac
		nwierszy=$((nwierszy+1))
		grep -qF "UNVERIFIED: $fraza" "$lin/$plik" 2>/dev/null ||
			brak_frazy="$brak_frazy $plik($ids)"
		for id in $(printf '%s' "$ids" | tr ',' ' '); do
			grep -q "^#### $id " "$hw" || brak_pozycji="$brak_pozycji $id"
			# Wiersz mapy i pozycja w HW-BLOCKED musza mowic o tym samym
			# pliku, inaczej fraza i identyfikator zyja obok siebie bez
			# zadnego zwiazku i wiersz przypisany do zlej pozycji przechodzi.
			awk -v id="$id" 'BEGIN {p=0}
				$0 ~ "^#### " id " " {p=1; next}
				p && /^#### / {p=0}
				p {print}' "$hw" |
				grep -qF "$plik" ||
				zle_miejsce="$zle_miejsce $id"
		done
	done < "$mapa"

	if [ -z "$brak_frazy" ]; then
		ok "kazdy wiersz mapy wskazuje na adnotacje w serii"
	else
		bad "kazdy wiersz mapy wskazuje na adnotacje w serii" 			"nie znalazlem:$brak_frazy"
	fi
	if [ -z "$brak_pozycji" ]; then
		ok "kazda pozycja z mapy jest opisana w HW-BLOCKED"
	else
		bad "kazda pozycja z mapy jest opisana w HW-BLOCKED" 			"brakuje:$brak_pozycji"
	fi

	if [ -z "$zle_miejsce" ]; then
		ok "pozycja i wiersz mapy wskazuja ten sam plik"
	else
		bad "pozycja i wiersz mapy wskazuja ten sam plik" 			"rozjazd:$zle_miejsce"
	fi

	# Druga strona: adnotacji w serii ma byc dokladnie tyle, ile wierszy mapy.
	# Bez tego nowa adnotacja przeszlaby niezauwazona, bo w kodzie nie ma juz
	# numeru, po ktorym dalo sie ja znalezc.
	nadnotacji=$(cat "$root"/patches/*.patch 2>/dev/null |
		grep -c "^+.*UNVERIFIED:")
	if [ "$nadnotacji" = "$nwierszy" ]; then
		ok "liczba adnotacji UNVERIFIED zgadza sie z mapa ($nwierszy)"
	else
		bad "liczba adnotacji UNVERIFIED zgadza sie z mapa" 			"seria ma $nadnotacji, mapa $nwierszy"
	fi
fi

# --------------------------------------------------------------- podsumowanie
echo
echo "=========================================================="
printf " przeszlo: %-3s padlo: %-3s nieuruchomione: %s\n" "$PASS" "$FAIL" "$SKIP"
if [ "$FAIL" != 0 ]; then
	echo " REGRESJA, padly bramki:"
	printf "%s" "$FAILED_LIST" | sed 's/^/   - /'
fi
if [ "$SKIP" != 0 ]; then
	echo " NIE URUCHOMIONO (to nie jest zaliczenie):"
	printf "%s" "$SKIPPED_LIST" | sed 's/^/   - /'
fi
echo "=========================================================="

[ "$FAIL" != 0 ] && exit 1
[ "$SKIP" != 0 ] && exit 2
exit 0
