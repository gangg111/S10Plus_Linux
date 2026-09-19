#!/bin/sh
# Kompiluje POJEDYNCZY plik .c drzewa jadra dla arm64, bez make.
#
# Uzycie:  scripts/cc-kernel.sh <sciezka/wzgledem/sources/linux/plik.c> [flagi]
#          MODE=-S OUT=plik.s scripts/cc-kernel.sh <plik.c>
#
# Wymaga wczesniejszego scripts/pc-prepare.sh (potrzebne .config i naglowki
# generowane). Flagi odtwarzaja to, co kbuild ustawia dla arm64 z LLVM=1:
# caly domyslny zestaw z scripts/Makefile.warn:9-26 (-Wall, -Wextra,
# -Werror=strict-prototypes, -Wmissing-declarations, -Wmissing-prototypes,
# -Wframe-larger-than z CONFIG_FRAME_WARN, -Wenum-conversion) razem z
# wyciszeniami, ktore kbuild dodaje poza W=2 i W=3 (:161-162, :195-196).
# -Werror=designated-init celowo nie ma: kbuild dodaje je przez cc-option,
# a clang tej opcji nie zna i zglasza -Wunknown-warning-option.
#
# Rozjazdy, ktore kosztowaly iteracje przy dochodzeniu do tego zestawu:
#   -fms-extensions       CC_FLAGS_DIALECT z Makefile:815 (CONFIG_CC_MS_EXTENSIONS),
#                         bez tego clang porzuca anonimowe pola z tagiem
#                         (struct ns_tree w ns_common) i sypie sie fs.h
#   -O2                   bez optymalizacji BUILD_BUG_ON nie znika i kvm_host.h
#                         wywala -Werror=return-type
#   token bez myslnikow   kbuild robi to samo (name-fix-token,
#                         scripts/Makefile.lib:19), inaczej makra rozwijaja sie
#                         do niepoprawnego identyfikatora i pada asembler
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
lin=$root/sources/linux
cd "$lin"

SRC=$1
shift

base=$(basename "$SRC" .c)
token=$(printf "%s" "$base" | tr -- "-," "__")

CC=${CC:-clang}

# W=1 odtwarza grupe ostrzezen z scripts/Makefile.warn:113-121: dokłada trzy
# ostrzezenia i zdejmuje wyciszenia, ktore kbuild trzyma tylko poza W=1.
if [ "${W:-0}" = "1" ]; then
	WARN_EXTRA="-Wmissing-format-attribute -Wmissing-include-dirs -Wunused-const-variable -DKBUILD_EXTRA_WARN1"
	WARN_QUIET=""
else
	WARN_EXTRA=""
	WARN_QUIET="-Wno-unused-but-set-variable -Wno-unused-const-variable -Wno-override-init"
fi
CROSS_TARGET=${CROSS_TARGET:---target=aarch64-linux-gnu}

LINUXINCLUDE="-nostdinc \
-I./arch/arm64/include \
-I./arch/arm64/include/generated \
-I./include \
-I./arch/arm64/include/uapi \
-I./arch/arm64/include/generated/uapi \
-I./include/uapi \
-I./include/generated/uapi \
-include ./include/linux/compiler-version.h \
-include ./include/linux/kconfig.h \
-include ./include/linux/compiler_types.h"

exec $CC $CROSS_TARGET -fintegrated-as \
	$LINUXINCLUDE \
	-D__KERNEL__ -DKBUILD_MODFILE=\"$base\" -DKBUILD_BASENAME=\"$base\" \
	-DKBUILD_MODNAME=\"$base\" -D__KBUILD_MODNAME=kmod_$token \
	-O2 -std=gnu11 -fms-extensions -Wno-gnu -Wno-microsoft-anon-tag \
	-fshort-wchar -funsigned-char -fno-common -fno-PIE \
	-fno-strict-aliasing -fno-stack-protector -fno-delete-null-pointer-checks \
	-fno-asynchronous-unwind-tables -fno-unwind-tables \
	-mlittle-endian -mgeneral-regs-only -mbranch-protection=pac-ret \
	-Wall -Wextra -Wundef -Werror=implicit-function-declaration \
	-Werror=implicit-int -Werror=return-type -Werror=strict-prototypes \
	-Wno-format-security -Wno-trigraphs -Wno-frame-address \
	-Wno-address-of-packed-member -Wmissing-declarations -Wmissing-prototypes \
	-Wframe-larger-than=2048 -Wno-format-overflow-non-kprintf \
	-Wno-format-truncation-non-kprintf -Wno-pointer-sign \
	-Werror=date-time -Werror=incompatible-pointer-types \
	-Wenum-conversion -Wunused -Wcast-function-type \
	-Wno-missing-field-initializers -Wno-shift-negative-value \
	-Wno-enum-enum-conversion -Wno-sign-compare -Wno-unused-parameter \
	$WARN_EXTRA $WARN_QUIET \
	"$@" ${MODE:--c} "$SRC" -o "${OUT:-/dev/null}"
