#!/bin/sh
# Przygotowuje drzewo sources/linux do bramek, ktore nie potrzebuja make:
#   1. buduje dtc z drzewa jadra (natywna binarka hosta),
#   2. buduje kconfigowy conf i generuje .config z arm64 defconfig,
#   3. generuje naglowki, ktore normalnie robi faza archprepare
#      (wrappery asm, syscalle, bounds.h, timeconst.h, asm-offsets.h,
#       rq-offsets.h, cpucap-defs.h, kernel-hwcap.h, sysreg-defs.h).
#
# Po tym scripts/verify.sh potrafi na tym samym drzewie zbudowac dtb
# i skompilowac kazdy plik .c serii na arm64, bez make i bez Linuksa.
#
# Wymagania: git, python3, bison, flex, bc, awk, sed oraz DWA kompilatory:
#   HOSTCC  - kompilator hosta z POSIX-em (na Windows: gcc z MSYS2, /usr/bin/gcc,
#             NIE mingw, bo brakuje sys/mman.h)
#   CC      - clang, ktory potrafi --target=aarch64-linux-gnu
#
# Na Windows uruchamiac z powloki MSYS2:
#   /c/msys64/usr/bin/bash.exe -lc "sh scripts/pc-prepare.sh"
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
lin="$root/sources/linux"
out="$root/.pc-tools"

HOSTCC=${HOSTCC:-gcc}
CC=${CC:-clang}
CROSS_TARGET=${CROSS_TARGET:---target=aarch64-linux-gnu}

[ -d "$lin" ] || { echo "Brak $lin, uruchom najpierw scripts/fetch-sources.sh" >&2; exit 1; }

for t in "$HOSTCC" "$CC" bison flex bc python3 awk sed; do
	command -v "$t" >/dev/null 2>&1 || { echo "brak narzedzia: $t" >&2; exit 1; }
done

mkdir -p "$out"

echo "== 1/4 dtc =="
if [ ! -x "$out/dtc" ] && [ ! -x "$out/dtc.exe" ]; then
	d=$out/dtc-build
	rm -rf "$d"; mkdir -p "$d/libfdt"
	cp "$lin"/scripts/dtc/*.c "$lin"/scripts/dtc/*.h "$lin"/scripts/dtc/*.l \
	   "$lin"/scripts/dtc/*.y "$d/"
	cp "$lin"/scripts/dtc/libfdt/* "$d/libfdt/"
	( cd "$d" &&
	  flex -o dtc-lexer.lex.c dtc-lexer.l &&
	  bison -o dtc-parser.tab.c -d dtc-parser.y &&
	  "$HOSTCC" -w -I. -Ilibfdt -DNO_YAML -o "$out/dtc" \
		dtc.c flattree.c fstree.c data.c livetree.c treesource.c \
		srcpos.c checks.c util.c dtc-lexer.lex.c dtc-parser.tab.c \
		libfdt/fdt.c libfdt/fdt_ro.c libfdt/fdt_wip.c libfdt/fdt_sw.c \
		libfdt/fdt_rw.c libfdt/fdt_strerror.c libfdt/fdt_empty_tree.c \
		libfdt/fdt_addresses.c libfdt/fdt_overlay.c )
	rm -rf "$d"
fi
DTC=$out/dtc; [ -x "$DTC" ] || DTC=$out/dtc.exe
"$DTC" --version

echo "== 2/4 conf i .config =="
if [ ! -x "$out/conf" ] && [ ! -x "$out/conf.exe" ]; then
	d=$out/conf-build
	rm -rf "$d"; mkdir -p "$d"
	( cd "$lin/scripts/kconfig" &&
	  bison -o "$d/parser.tab.c" --defines="$d/parser.tab.h" -t -l parser.y &&
	  flex -o "$d/lexer.lex.c" -L lexer.l &&
	  "$HOSTCC" -w -I. -I"$lin/scripts/include" -I"$d" -o "$out/conf" \
		conf.c confdata.c expr.c menu.c preprocess.c symbol.c util.c \
		"$d/parser.tab.c" "$d/lexer.lex.c" )
	rm -rf "$d"
fi
CONF=$out/conf; [ -x "$CONF" ] || CONF=$out/conf.exe

cd "$lin"
ARCH=arm64; SRCARCH=arm64; srctree=.; objtree=.
export ARCH SRCARCH srctree objtree
export KERNELVERSION=7.2.0
export CC CLANG_FLAGS="$CROSS_TARGET -fintegrated-as" LLVM=1 LLVM_IAS=1
export LD=ld.lld AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy
export HOSTCC HOSTCXX=g++ RUSTC=rustc PAHOLE=pahole
export KCONFIG_AUTOCONFIG=include/config/auto.conf
export KCONFIG_AUTOHEADER=include/generated/autoconf.h
export KCONFIG_RUSTCCFG=include/generated/rustc_cfg
mkdir -p include/config include/generated
"$CONF" --defconfig=arch/arm64/configs/defconfig Kconfig >/dev/null
"$CONF" --syncconfig Kconfig >/dev/null
echo "   .config: $(grep -c '^CONFIG_' .config) opcji"

echo "== 3/4 naglowki arch =="
G=arch/arm64/include/generated/asm
U=arch/arm64/include/generated/uapi/asm
mkdir -p "$G" "$U"
awk -f arch/arm64/tools/gen-cpucaps.awk arch/arm64/tools/cpucaps > "$G/cpucap-defs.h"
sh -e arch/arm64/tools/gen-kernel-hwcaps.sh arch/arm64/include/uapi/asm/hwcap.h > "$G/kernel-hwcap.h"
awk -f arch/arm64/tools/gen-sysreg.awk arch/arm64/tools/sysreg > "$G/sysreg-defs.h"
T32=arch/arm64/tools/syscall_32.tbl
T64=arch/arm64/tools/syscall_64.tbl
sh scripts/syscallhdr.sh --emit-nr --abis common,32 "$T32" "$G/unistd_32.h"
sh scripts/syscallhdr.sh --emit-nr --prefix compat32_ --abis common,32 "$T32" "$G/unistd_compat_32.h"
sh scripts/syscallhdr.sh --emit-nr --abis common,64,renameat,rlimit,memfd_secret "$T64" "$U/unistd_64.h"
sh scripts/syscalltbl.sh --abis common,32 "$T32" "$G/syscall_table_32.h"
sh scripts/syscalltbl.sh --abis common,64,renameat,rlimit,memfd_secret "$T64" "$G/syscall_table_64.h"
python3 "$root/scripts/pc-gen-headers.py" "$lin"

echo "== 4/4 offsety =="
CCK="$root/scripts/cc-kernel.sh"
HZ=$(sed -n 's/^CONFIG_HZ=\([0-9]*\)$/\1/p' .config | head -1)
echo "$HZ" | bc -q kernel/time/timeconst.bc > include/generated/timeconst.h
MODE=-S OUT="$out/bounds.s" sh "$CCK" kernel/bounds.c
python3 "$root/scripts/pc-mkoffsets.py" "$out/bounds.s" include/generated/bounds.h __LINUX_BOUNDS_H__
MODE=-S OUT="$out/asm-offsets.s" sh "$CCK" arch/arm64/kernel/asm-offsets.c
python3 "$root/scripts/pc-mkoffsets.py" "$out/asm-offsets.s" include/generated/asm-offsets.h __ASM_OFFSETS_H__
MODE=-S OUT="$out/rq-offsets.s" sh "$CCK" kernel/sched/rq-offsets.c -I kernel/sched
python3 "$root/scripts/pc-mkoffsets.py" "$out/rq-offsets.s" include/generated/rq-offsets.h __RQ_OFFSETS_H__

echo "GOTOWE: drzewo przygotowane, dtc w $out"
