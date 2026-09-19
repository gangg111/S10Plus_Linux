#!/bin/sh
# minimalny "kernel cc" dla ARM64: te same include'y i definicje co Kbuild
RES=$(clang -print-resource-dir)
exec clang --target=aarch64-linux-gnu -nostdinc -isystem "$RES/include" \
 -I./arch/arm64/include -I./arch/arm64/include/generated -I./include \
 -I./arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi \
 -I./include/uapi -I./include/generated/uapi \
 -include ./include/linux/compiler-version.h -include ./include/linux/kconfig.h \
 -include ./include/linux/compiler_types.h -D__KERNEL__ \
 -O2 -std=gnu11 -fms-extensions -Wno-gnu -Wno-microsoft-anon-tag -fno-common -fshort-wchar -fno-PIE -mgeneral-regs-only \
 -fno-asynchronous-unwind-tables -fno-strict-aliasing "$@"
