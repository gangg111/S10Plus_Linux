#!/bin/sh
# Analiza statyczna kodu bootloadera: clang i sparse.
#
# Po co osobna bramka. Seria jadra ma swoj analizator (scripts/check-analyzer.sh),
# seria bootloadera nie miala ZADNEGO, a to jest kod, ktory NIGDY SIE NIE WYKONAL:
# dopoki telefon nie wystartuje, analiza statyczna jest jedynym narzedziem, ktore
# w ogole moze znalezc w nim blad. Kompilacja W=1 tego nie zastepuje, bo patrzy
# na skladnie, a nie na sciezki wykonania ani na adnotacje typow.
#
# Dwa narzedzia, bo lapia ROZLACZNE klasy bledow:
#   clang --analyze  sciezki: odczyt niezainicjowanej wartosci, wyluskanie NULL-a,
#                    martwa galaz;
#   sparse           typy: przestrzenie adresowe (__iomem), endian, typy bitowe,
#                    czyli dokladnie to, co sie psuje w sterowniku dotykajacym MMIO.
#
# Sparse idzie przez `make C=2`, a nie wolany wprost, bo U-Boot dokleja do niego
# wlasne CHECKFLAGS (--arch, -m64, endian). Wolany z golymi flagami gcc daje inne,
# szersze wyjscie, wiec bramka mierzylaby cos innego niz to, co drzewo uznaje za
# swoj wynik. clang dostaje flagi z pliku .cmd, czyli DOKLADNIE te, ktorymi build
# skompilowal dany plik: dzieki temu nie da sie analizy uruchomic na innej
# konfiguracji niz ta, ktora sie buduje.
#
# PROGI, a nie zero. Trzy klasy maja tlo, ktorego nie da sie usunac z poziomu
# naszych plikow, wiec kazda ma osobny licznik i osobny pulap:
#
#   przestrzen adresowa  readl/writel i dev_read_addr_ptr. Zmierzone tlo U-Boota:
#                        upstreamowy phy-exynos-usbdrd.c ma 55 takich uwag, a sam
#                        rdzen ufs-uclass.c ma 38. Upstream nie anotuje __iomem
#                        konsekwentnie, wiec wymaganie zera od naszych plikow
#                        byloby wymaganiem czegos, czego nie robi kod obok.
#   zasieg symbolu       symbole _u_boot_list_2_driver_2_*, ktore tworzy makro
#                        U_BOOT_DRIVER. Ma je KAZDY sterownik w tym drzewie.
#   ograniczenie sparse'a  sparse nie parsuje literalow UTF-16 (u"..."), a takiego
#                        uzywa tablica fw_images w exynos-mobile.c:31, czyli
#                        w kodzie plyty, ktorego NIE pisalismy. Stad trzy bledy,
#                        ktore nie sa bledami kodu.
#
# Wszystko POZA tymi trzema klasami ma byc zerem, i to jest wlasciwa tresc tej
# bramki. Podniesienie ktoregokolwiek pulapu wymaga uzasadnienia w opisie commita,
# tak samo jak przy pozostalych ratchetach projektu.
#
# Uzycie:  scripts/check-uboot-analyzer.sh
# Kod:     0 w normie, 1 regresja, 2 bramka NIE URUCHOMIONA (brak narzedzi albo
#          drzewa; to NIE jest zielone swiatlo)
set -u

UB=${UBOOT_TREE:-$HOME/u-boot-upstream}

# Drzewo bootloadera zyje w WSL. Gdy bramka startuje spod Windowsa, przechodzi
# do WSL i uruchamia sie tam ponownie, zamiast probowac budowac przez sieciowy
# system plikow.
if [ ! -d "$UB" ]; then
	if command -v wsl.exe >/dev/null 2>&1; then
		# Podwojny ukosnik jest tu konieczny: Git Bash przerabia argumenty
		# wygladajace na sciezki uniksowe i doklada do nich swoj wlasny
		# katalog glowny, przez co WSL dostaje sciezke, ktorej nie ma.
		exec wsl.exe -d Debian -u pm -- sh 			"//mnt/c/Users/Artur/Documents/Serwis/Programowanie/S10Plus_Linux/scripts/check-uboot-analyzer.sh"
	fi
	echo "check-uboot-analyzer: BRAMKA NIEURUCHOMIONA, brak drzewa U-Boota (UBOOT_TREE)"
	exit 2
fi

command -v clang >/dev/null 2>&1 || {
	echo "check-uboot-analyzer: BRAMKA NIEURUCHOMIONA, brak clang"
	exit 2
}
command -v sparse >/dev/null 2>&1 || {
	echo "check-uboot-analyzer: BRAMKA NIEURUCHOMIONA, brak sparse"
	exit 2
}

log=/mnt/c/Users/Artur/Documents/Serwis/Programowanie/S10Plus_Linux/build-logs
[ -d "$log" ] || log=/tmp
# Nazwa MUSI byc inna niz plik, do ktorego verify.sh przechwytuje stdout tej
# bramki, inaczej bramka kasuje log, ktory tamten wlasnie zapisal, i przy
# awarii nie ma czego czytac.
out="$log/63-uboot-analyzer-detail.log"

# Pliki, ktore wnosi NASZA seria, plus plyta, ktora nasza seria zmienia.
PLIKI="drivers/pinctrl/exynos/pinctrl-exynos9820
drivers/clk/exynos/clk-exynos9820
drivers/phy/phy-samsung-ufs
drivers/phy/phy-exynos9820-ufs
drivers/ufs/ufs-exynos
board/samsung/exynos-mobile/exynos-mobile"

# Pulapy zmierzone 19.09.2026 na naszym defconfigu.
MAX_ADDRSPACE=32
MAX_STATIC=6
MAX_SPARSE_BUG=3

cd "$UB" || exit 2
CROSS_COMPILE=${CROSS_COMPILE:-aarch64-linux-gnu-}
export CROSS_COMPILE

: > "$out"
clang_total=0
addr_total=0
static_total=0
bug_total=0
inne_total=0
plikow=0

licz() {	# $1 = tekst, $2 = wzorzec; pusty tekst to zero, nie jeden
	[ -n "$1" ] || { echo 0; return; }
	printf '%s\n' "$1" | grep -c "$2"
}

for base in $PLIKI; do
	src="$UB/$base.c"
	cmdfile="$UB/$(dirname "$base")/.$(basename "$base").o.cmd"
	[ -f "$src" ] || {
		echo "check-uboot-analyzer: BRAMKA NIEURUCHOMIONA, brak $base.c"
		exit 2
	}
	[ -f "$cmdfile" ] || {
		echo "check-uboot-analyzer: BRAMKA NIEURUCHOMIONA, brak $cmdfile;" \
		     "zbuduj drzewo naszym defconfigiem"
		exit 2
	}
	plikow=$((plikow + 1))

	# clang: flagi prosto z polecenia, ktorym build skompilowal ten plik.
	flags=$(sed -n 's/^cmd_[^ ]* := //p' "$cmdfile" |
		sed -e 's/^[^ ]*gcc //' -e 's/-c -o [^ ]*\.o //' -e 's#[^ ]*\.c$##')
	c=$(clang --target=aarch64-linux-gnu --analyze \
		-Xclang -analyzer-output=text \
		-Xclang -analyzer-disable-checker -Xclang deadcode.DeadStores \
		$flags "$base.c" 2>&1)
	printf '=== clang %s ===\n%s\n' "$base.c" "$c" >> "$out"
	clang_total=$((clang_total + $(licz "$c" 'warning:')))

	# sparse: przez system budowania, zeby dostal CHECKFLAGS U-Boota.
	rm -f "$base.o"
	s=$(make C=2 "$base.o" 2>&1 | grep -E 'warning:|error:')
	printf '=== sparse %s ===\n%s\n' "$base.c" "$s" >> "$out"

	a=$(licz "$s" 'address space')
	st=$(licz "$s" 'Should it be static')
	# Znane ograniczenie parsera sparse'a na literalach UTF-16.
	bug=$(licz "$s" "undefined identifier 'u'\|Expected } at end of initializer\|got \"UBOOT_BOOT_PARTITION\"")
	inne=$(( $(licz "$s" '.') - a - st - bug ))

	addr_total=$((addr_total + a))
	static_total=$((static_total + st))
	bug_total=$((bug_total + bug))
	inne_total=$((inne_total + inne))
done

rc=0
sprawdz() {	# $1 = nazwa, $2 = wynik, $3 = pulap
	if [ "$2" -gt "$3" ]; then
		echo "check-uboot-analyzer: $1: $2, pulap $3"
		rc=1
	fi
}

sprawdz "clang, znalezisk sciezkowych" "$clang_total" 0
sprawdz "sparse, uwagi poza znanymi klasami" "$inne_total" 0
sprawdz "sparse, przestrzen adresowa" "$addr_total" "$MAX_ADDRSPACE"
sprawdz "sparse, zasieg symbolu" "$static_total" "$MAX_STATIC"
sprawdz "sparse, ograniczenie parsera" "$bug_total" "$MAX_SPARSE_BUG"

if [ "$rc" != 0 ]; then
	echo "check-uboot-analyzer: patrz build-logs/$(basename "$out")"
	exit 1
fi

rm -f "$out"
echo "check-uboot-analyzer: plikow $plikow, clang 0, sparse poza tlem 0" \
     "(tlo: przestrzen adresowa $addr_total/$MAX_ADDRSPACE," \
     "zasieg symbolu $static_total/$MAX_STATIC," \
     "ograniczenie parsera $bug_total/$MAX_SPARSE_BUG)"
exit 0
