savedcmd_lib/circ_buf_packet.o := aarch64-linux-gnu-gcc -Wp,-MMD,lib/.circ_buf_packet.o.d -nostdinc -I/root/k7/arch/arm64/include -I/root/k7/arch/arm64/include/generated -I/root/k7/include -I/root/k7/include -I/root/k7/arch/arm64/include/uapi -I/root/k7/arch/arm64/include/generated/uapi -I/root/k7/include/uapi -I/root/k7/include/generated/uapi -include /root/k7/include/linux/compiler-version.h -include /root/k7/include/linux/kconfig.h -include /root/k7/include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fshort-wchar -funsigned-char -fno-common -fno-PIE -fno-strict-aliasing -std=gnu11 -fms-extensions -mgeneral-regs-only -DCONFIG_CC_HAS_K_CONSTRAINT=1 -Wno-psabi -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -mbranch-protection=pac-ret -Wa,-march=armv8.5-a -DARM64_ASM_ARCH='"armv8.5-a"' -DKASAN_SHADOW_SCALE_SHIFT= -fno-delete-null-pointer-checks -O2 -fno-allow-store-data-races -fstack-protector-strong -fno-omit-frame-pointer -fno-optimize-sibling-calls -ftrivial-auto-var-init=zero -fno-stack-clash-protection -fpatchable-function-entry=4,2 -fmin-function-alignment=8 -fstrict-flex-arrays=3 -fno-strict-overflow -fno-stack-check -fconserve-stack -fno-builtin-wcslen -Wall -Wextra -Wundef -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Werror=strict-prototypes -Wno-format-security -Wno-trigraphs -Wno-frame-address -Wno-address-of-packed-member -Wmissing-declarations -Wmissing-prototypes -Wframe-larger-than=2048 -Wno-main -Wno-type-limits -Wno-dangling-pointer -Wvla-larger-than=1 -Wno-pointer-sign -Wcast-function-type -Wno-array-bounds -Wno-stringop-overflow -Wno-alloc-size-larger-than -Wimplicit-fallthrough=5 -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wenum-conversion -Wunused -Wno-unused-but-set-variable -Wno-unused-const-variable -Wno-packed-not-aligned -Wno-format-overflow -Wno-format-truncation -Wno-stringop-truncation -Wno-override-init -Wno-missing-field-initializers -Wno-shift-negative-value -Wno-maybe-uninitialized -Wno-sign-compare -Wno-unused-parameter -g -mstack-protector-guard=sysreg -mstack-protector-guard-reg=sp_el0 -mstack-protector-guard-offset=1600 -Wno-missing-prototypes -Wno-missing-declarations -I././include -I./. -DCONFIG_TZDEV=1 -DCONFIG_TZDEV_USE_ARM_CALLING_CONVENTION=1 -DCONFIG_TZDEV_IWI_EVENT=500 -DCONFIG_TZDEV_IWI_PANIC=501 -DCONFIG_TZDEV_SK_MULTICORE=1 -DCONFIG_TZDEV_KTHREADS_SMPBOOT=1 -DCONFIG_TZDEV_DEPLOY_TZAR=1 -DCONFIG_TZIRS=1 -DCONFIG_TZ_BOOT_LOG=1 -DCONFIG_TZ_BOOT_LOG_PG_CNT=1 -DCONFIG_TZDEV_MEMRESSZ=0x01000000 -D"_STR(s)=$(pound)s" -D"TZAR_PLIK=_STR(/mnt/c/Users/Artur/Documents/Serwis/Programowanie/S10Plus_Linux/tools/phone/tzdev/startup.tzar)"  -DMODULE  -DKBUILD_BASENAME='"circ_buf_packet"' -DKBUILD_MODNAME='"teegris"' -D__KBUILD_MODNAME=teegris -c -o lib/circ_buf_packet.o lib/circ_buf_packet.c  

source_lib/circ_buf_packet.o := lib/circ_buf_packet.c

deps_lib/circ_buf_packet.o := \
  /root/k7/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /root/k7/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /root/k7/include/linux/compiler_types.h \
    $(wildcard include/config/DEBUG_INFO_BTF) \
    $(wildcard include/config/PAHOLE_HAS_BTF_TAG) \
    $(wildcard include/config/FUNCTION_ALIGNMENT) \
    $(wildcard include/config/CC_HAS_SANE_FUNCTION_ALIGNMENT) \
    $(wildcard include/config/X86_64) \
    $(wildcard include/config/ARM64) \
    $(wildcard include/config/LD_DEAD_CODE_DATA_ELIMINATION) \
    $(wildcard include/config/LTO_CLANG) \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/CC_HAS_ASSUME) \
    $(wildcard include/config/CC_HAS_COUNTED_BY) \
    $(wildcard include/config/FORTIFY_SOURCE) \
    $(wildcard include/config/UBSAN_BOUNDS) \
    $(wildcard include/config/CC_HAS_COUNTED_BY_PTR) \
    $(wildcard include/config/CC_HAS_MULTIDIMENSIONAL_NONSTRING) \
    $(wildcard include/config/CFI) \
    $(wildcard include/config/ARCH_USES_CFI_GENERIC_LLVM_PASS) \
    $(wildcard include/config/CC_HAS_BROKEN_COUNTED_BY_REF) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /root/k7/include/linux/compiler-context-analysis.h \
  /root/k7/include/linux/compiler_attributes.h \
  /root/k7/include/linux/compiler-gcc.h \
    $(wildcard include/config/ARCH_USE_BUILTIN_BSWAP) \
    $(wildcard include/config/SHADOW_CALL_STACK) \
    $(wildcard include/config/KCOV) \
    $(wildcard include/config/CC_HAS_TYPEOF_UNQUAL) \
  /root/k7/arch/arm64/include/asm/compiler.h \
    $(wildcard include/config/ARM64_PTR_AUTH_KERNEL) \
    $(wildcard include/config/ARM64_PTR_AUTH) \
    $(wildcard include/config/BUILTIN_RETURN_ADDRESS_STRIPS_PAC) \
  /root/k7/arch/arm64/include/generated/asm/percpu_types.h \
  /root/k7/include/asm-generic/percpu_types.h \
  /root/k7/include/linux/err.h \
  /root/k7/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/OBJTOOL) \
  /root/k7/arch/arm64/include/asm/rwonce.h \
    $(wildcard include/config/LTO) \
  /root/k7/include/asm-generic/rwonce.h \
  /root/k7/include/linux/kasan-checks.h \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KASAN_SW_TAGS) \
  /root/k7/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /root/k7/include/uapi/linux/types.h \
  /root/k7/arch/arm64/include/generated/uapi/asm/types.h \
  /root/k7/include/uapi/asm-generic/types.h \
  /root/k7/include/asm-generic/int-ll64.h \
  /root/k7/include/uapi/asm-generic/int-ll64.h \
  /root/k7/arch/arm64/include/uapi/asm/bitsperlong.h \
  /root/k7/include/asm-generic/bitsperlong.h \
  /root/k7/include/uapi/asm-generic/bitsperlong.h \
  /root/k7/include/uapi/linux/posix_types.h \
  /root/k7/include/linux/stddef.h \
  /root/k7/include/uapi/linux/stddef.h \
  /root/k7/arch/arm64/include/uapi/asm/posix_types.h \
  /root/k7/include/uapi/asm-generic/posix_types.h \
  /root/k7/include/linux/kcsan-checks.h \
    $(wildcard include/config/KCSAN_WEAK_MEMORY) \
    $(wildcard include/config/KCSAN_IGNORE_ATOMICS) \
  /root/k7/arch/arm64/include/generated/uapi/asm/errno.h \
  /root/k7/include/uapi/asm-generic/errno.h \
  /root/k7/include/uapi/asm-generic/errno-base.h \
  lib/circ_buf.h \
  lib/circ_buf_packet.h \

lib/circ_buf_packet.o: $(deps_lib/circ_buf_packet.o)

$(deps_lib/circ_buf_packet.o):
