#!/bin/sh
# Sprawdza, ze fragment konfiguracji scala sie z arm64 defconfigiem i ze KAZDY
# symbol, ktory fragment zamawia, ma po scaleniu zadana wartosc.
#
# Po co: seria dokladala trzy nowe symbole (DECON, panel, D-PHY), wszystkie
# domyslnie n, a defconfig arm64 nie ma tez REGULATOR_S2DOS05, PINCTRL_EXYNOS
# ani EXYNOS_PM_DOMAINS.  Zbudowane z samego defconfiga jadro kompiluje sie
# bez jednej uwagi i nie zapala ekranu.  Bramka kompilacji tego nie widzi, bo
# ona kompiluje pojedyncze pliki, a nie sprawdza, czy sa w ogole wciagniete.
#
# Czego bramka NIE dowodzi: ze jadro sie zlinkuje ani ze wystartuje.  Dowodzi
# jednego: ze zaleznosci Kconfiga sa spelnione, a wiec ze kazdy sterownik serii
# trafia do obrazu.  Symbol z niespelniona zaleznoscia zostaje przez
# olddefconfig wylaczony po cichu i wtedy ta bramka pada.
#
# Konfiguracja liczona jest w katalogu tymczasowym: KCONFIG_CONFIG i oba
# KCONFIG_AUTO* wskazuja poza drzewo, wiec .config i include/generated
# przygotowane przez scripts/pc-prepare.sh zostaja nietkniete.  Bez tego bramka
# psulaby wejscie bramki kompilacji.
#
# Z argumentem sprawdza tez nakladke, z ktorej naprawde budowany jest obraz
# na telefon (scripts/bringup.config: simpledrm zamiast stosu DECON i DSI).
# Oba pliki ida wtedy tak jak w merge_config.sh przy budowaniu: w kolejnosci,
# z wierszami "is not set", a o symbolu decyduje jego ostatnie przypisanie.
# Bez tego sterownik zalezny od wylaczonego DSI mogl wypasc z obrazu po cichu.
#
# Uzycie: scripts/check-kconfig.sh [nakladka]
# Kod:    0 wszystkie symbole zgodne, 1 rozjazd, 2 brak narzedzi
set -u

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
lin="$root/sources/linux"
frag="$root/scripts/exynos9820.config"
nakl=${1:-}
WZOR='^CONFIG_[A-Z0-9_]+=|^# CONFIG_[A-Z0-9_]+ is not set$'

CONF=""
for c in "$root/.pc-tools/conf" "$root/.pc-tools/conf.exe"; do
	[ -x "$c" ] && { CONF=$c; break; }
done
[ -n "$CONF" ] || {
	echo "check-kconfig: brak .pc-tools/conf, uruchom scripts/pc-prepare.sh"
	exit 2
}
[ -f "$frag" ] || { echo "check-kconfig: brak $frag"; exit 2; }
[ -z "$nakl" ] || [ -f "$nakl" ] || { echo "check-kconfig: brak $nakl"; exit 2; }
# Sciezka bezwzgledna, bo dalej skrypt pracuje w sources/linux.
[ -z "$nakl" ] || nakl=$(CDPATH= cd -- "$(dirname -- "$nakl")" && pwd)/$(basename -- "$nakl")
[ -f "$lin/arch/arm64/configs/defconfig" ] || {
	echo "check-kconfig: brak defconfiga arm64"
	exit 2
}

tmp=$(mktemp -d) || exit 2
trap 'rm -rf "$tmp"' EXIT

cd "$lin" || exit 2
ARCH=arm64; SRCARCH=arm64; srctree=.; objtree=.
export ARCH SRCARCH srctree objtree
export KERNELVERSION=${KERNELVERSION:-7.2.0}
export CC=${CC:-clang}
export CLANG_FLAGS="${CROSS_TARGET:---target=aarch64-linux-gnu} -fintegrated-as"
export LLVM=1 LLVM_IAS=1
export LD=${LD:-ld.lld} AR=${AR:-llvm-ar} NM=${NM:-llvm-nm}
export OBJCOPY=${OBJCOPY:-llvm-objcopy}
export HOSTCC=${HOSTCC:-gcc} HOSTCXX=${HOSTCXX:-g++}
# BTF zalezy od wersji pahole; na Windowsie pahole jest tylko w WSL.
if [ -z "${PAHOLE:-}" ] && ! command -v pahole >/dev/null 2>&1 &&
   command -v wsl.exe >/dev/null 2>&1; then
	PAHOLE="$root/scripts/pahole-wsl.sh"
fi
export RUSTC=${RUSTC:-rustc} PAHOLE=${PAHOLE:-pahole}
# Makefile jadra liczy PAHOLE_VERSION sam i podaje ja Kconfigowi przez
# srodowisko (init/Kconfig: default "$(PAHOLE_VERSION)"); conf wolany wprost
# tego nie zrobi, a bez niej BTF wypada po cichu.
export PAHOLE_VERSION=${PAHOLE_VERSION:-$(sh scripts/pahole-version.sh "$PAHOLE")}
export KCONFIG_CONFIG="$tmp/.config"
export KCONFIG_AUTOCONFIG="$tmp/auto.conf"
export KCONFIG_AUTOHEADER="$tmp/autoconf.h"
export KCONFIG_RUSTCCFG="$tmp/rustc_cfg"

if ! "$CONF" --defconfig=arch/arm64/configs/defconfig Kconfig >"$tmp/log" 2>&1; then
	echo "check-kconfig: defconfig sie nie policzyl"
	tail -5 "$tmp/log"
	exit 2
fi

# Wiersze "CONFIG_X=..." i "# CONFIG_X is not set" z fragmentu dopisujemy na
# koniec, bo olddefconfig bierze ostatnie wystapienie symbolu.  Tak samo robi
# merge_config.sh przy budowaniu: "is not set" wylacza symbol, ktory defconfig
# wlacza (np. DEBUG_INFO_REDUCED blokujacy BTF), a nie tylko go opisuje.
if [ -z "$nakl" ]; then
	grep -E "$WZOR" "$frag" >> "$tmp/.config"
	grep -E "$WZOR" "$frag" > "$tmp/chcemy"
else
	grep -hE "$WZOR" "$frag" "$nakl" >> "$tmp/.config"
	grep -hE "$WZOR" "$frag" "$nakl" | awk '
		{ s = ($1 == "#") ? $2 : substr($0, 1, index($0, "=") - 1)
		  if (!(s in ost)) kol[++n] = s
		  ost[s] = $0 }
		END { for (i = 1; i <= n; i++) print ost[kol[i]] }' > "$tmp/chcemy"
fi

if ! "$CONF" --olddefconfig Kconfig >>"$tmp/log" 2>&1; then
	echo "check-kconfig: olddefconfig sie nie policzyl"
	tail -5 "$tmp/log"
	exit 2
fi

zle=0
zamowione=0
while IFS= read -r wiersz; do
	zamowione=$((zamowione + 1))
	if ! grep -qxF "$wiersz" "$tmp/.config"; then
		nazwa=${wiersz%%=*}
		mamy=$(grep -E "^$nazwa=" "$tmp/.config" || echo "$nazwa nie jest ustawione")
		echo "  FAIL zamowiono $wiersz, wyszlo: $mamy"
		zle=$((zle + 1))
	fi
done <<EOF
$(grep -E '^CONFIG_[A-Z0-9_]+=' "$tmp/chcemy")
EOF

# Druga strona: symbole, ktore fragment celowo ZOSTAWIA wylaczone, opisane
# w nim jako zakomentowane "# CONFIG_X is not set".  Jesli ktorys wejdzie sam,
# przez select z czegos innego, decyzja z fragmentu przestaje obowiazywac po
# cichu i trzeba ja przemyslec na nowo, a nie dowiedziec sie o tym na telefonie.
wylaczone=0
for nazwa in $(sed -n 's/^# \(CONFIG_[A-Z0-9_]*\) is not set$/\1/p' "$tmp/chcemy"); do
	wylaczone=$((wylaczone + 1))
	if grep -qE "^$nazwa=" "$tmp/.config"; then
		echo "  FAIL $nazwa mial zostac wylaczony, a wszedl: $(grep -E "^$nazwa=" "$tmp/.config")"
		zle=$((zle + 1))
	fi
done

echo "check-kconfig: zamowionych symboli $zamowione, swiadomie wylaczonych $wylaczone, rozjazdow $zle"
[ "$zle" = 0 ] || exit 1
exit 0
