savedcmd_modem_sonda2.mod.o := aarch64-linux-gnu-gcc -Wp,-MMD,./.modem_sonda2.mod.o.d -nostdinc -I/root/k7/arch/arm64/include -I/root/k7/arch/arm64/include/generated -I/root/k7/include -I/root/k7/include -I/root/k7/arch/arm64/include/uapi -I/root/k7/arch/arm64/include/generated/uapi -I/root/k7/include/uapi -I/root/k7/include/generated/uapi -include /root/k7/include/linux/compiler-version.h -include /root/k7/include/linux/kconfig.h -include /root/k7/include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fshort-wchar -funsigned-char -fno-common -fno-PIE -fno-strict-aliasing -std=gnu11 -fms-extensions -mgeneral-regs-only -DCONFIG_CC_HAS_K_CONSTRAINT=1 -Wno-psabi -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -mbranch-protection=pac-ret -Wa,-march=armv8.5-a -DARM64_ASM_ARCH='"armv8.5-a"' -DKASAN_SHADOW_SCALE_SHIFT= -fno-delete-null-pointer-checks -O2 -fno-allow-store-data-races -fstack-protector-strong -fno-omit-frame-pointer -fno-optimize-sibling-calls -ftrivial-auto-var-init=zero -fno-stack-clash-protection -fpatchable-function-entry=4,2 -fmin-function-alignment=8 -fstrict-flex-arrays=3 -fno-strict-overflow -fno-stack-check -fconserve-stack -fno-builtin-wcslen -Wall -Wextra -Wundef -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Werror=strict-prototypes -Wno-format-security -Wno-trigraphs -Wno-frame-address -Wno-address-of-packed-member -Wmissing-declarations -Wmissing-prototypes -Wframe-larger-than=2048 -Wno-main -Wno-type-limits -Wno-dangling-pointer -Wvla-larger-than=1 -Wno-pointer-sign -Wcast-function-type -Wno-array-bounds -Wno-stringop-overflow -Wno-alloc-size-larger-than -Wimplicit-fallthrough=5 -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wenum-conversion -Wunused -Wno-unused-but-set-variable -Wno-unused-const-variable -Wno-packed-not-aligned -Wno-format-overflow -Wno-format-truncation -Wno-stringop-truncation -Wno-override-init -Wno-missing-field-initializers -Wno-shift-negative-value -Wno-maybe-uninitialized -Wno-sign-compare -Wno-unused-parameter -g -mstack-protector-guard=sysreg -mstack-protector-guard-reg=sp_el0 -mstack-protector-guard-offset=1600  -DMODULE  -DKBUILD_BASENAME='"modem_sonda2.mod"' -DKBUILD_MODNAME='"modem_sonda2"' -D__KBUILD_MODNAME=modem_sonda2 -c -o modem_sonda2.mod.o modem_sonda2.mod.c  

source_modem_sonda2.mod.o := modem_sonda2.mod.c

deps_modem_sonda2.mod.o := \
    $(wildcard include/config/MODULE_UNLOAD) \
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
  /root/k7/include/linux/module.h \
    $(wildcard include/config/MODULES) \
    $(wildcard include/config/SYSFS) \
    $(wildcard include/config/MODULES_TREE_LOOKUP) \
    $(wildcard include/config/LIVEPATCH) \
    $(wildcard include/config/STACKTRACE_BUILD_ID) \
    $(wildcard include/config/ARCH_USES_CFI_TRAPS) \
    $(wildcard include/config/MODULE_SIG) \
    $(wildcard include/config/GENERIC_BUG) \
    $(wildcard include/config/KALLSYMS) \
    $(wildcard include/config/SMP) \
    $(wildcard include/config/TRACEPOINTS) \
    $(wildcard include/config/TREE_SRCU) \
    $(wildcard include/config/BPF_EVENTS) \
    $(wildcard include/config/DEBUG_INFO_BTF_MODULES) \
    $(wildcard include/config/JUMP_LABEL) \
    $(wildcard include/config/TRACING) \
    $(wildcard include/config/EVENT_TRACING) \
    $(wildcard include/config/DYNAMIC_FTRACE) \
    $(wildcard include/config/KPROBES) \
    $(wildcard include/config/HAVE_STATIC_CALL_INLINE) \
    $(wildcard include/config/KUNIT) \
    $(wildcard include/config/PRINTK_INDEX) \
    $(wildcard include/config/CONSTRUCTORS) \
    $(wildcard include/config/FUNCTION_ERROR_INJECTION) \
    $(wildcard include/config/DYNAMIC_DEBUG_CORE) \
    $(wildcard include/config/MITIGATION_RETPOLINE) \
  /root/k7/include/linux/list.h \
    $(wildcard include/config/LIST_HARDENED) \
    $(wildcard include/config/DEBUG_LIST) \
  /root/k7/include/linux/container_of.h \
  /root/k7/include/linux/build_bug.h \
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
  /root/k7/include/linux/poison.h \
    $(wildcard include/config/ILLEGAL_POINTER_VALUE) \
  /root/k7/include/linux/const.h \
  /root/k7/include/vdso/const.h \
  /root/k7/include/uapi/linux/const.h \
  /root/k7/arch/arm64/include/asm/barrier.h \
    $(wildcard include/config/ARM64_PSEUDO_NMI) \
  /root/k7/arch/arm64/include/asm/alternative-macros.h \
  /root/k7/include/vdso/bits.h \
  /root/k7/arch/arm64/include/asm/cpucaps.h \
    $(wildcard include/config/ARM64_EPAN) \
    $(wildcard include/config/ARM64_SVE) \
    $(wildcard include/config/ARM64_SME) \
    $(wildcard include/config/ARM64_CNP) \
    $(wildcard include/config/ARM64_MTE) \
    $(wildcard include/config/ARM64_BTI) \
    $(wildcard include/config/ARM64_TLB_RANGE) \
    $(wildcard include/config/ARM64_POE) \
    $(wildcard include/config/ARM64_GCS) \
    $(wildcard include/config/ARM64_HAFT) \
    $(wildcard include/config/UNMAP_KERNEL_AT_EL0) \
    $(wildcard include/config/ARM64_ERRATUM_843419) \
    $(wildcard include/config/ARM64_ERRATUM_1742098) \
    $(wildcard include/config/ARM64_ERRATUM_2645198) \
    $(wildcard include/config/ARM64_ERRATUM_2658417) \
    $(wildcard include/config/CAVIUM_ERRATUM_23154) \
    $(wildcard include/config/ARM64_WORKAROUND_DISABLE_CNP) \
    $(wildcard include/config/ARM64_WORKAROUND_REPEAT_TLBI_SYNC) \
    $(wildcard include/config/ARM64_ERRATUM_3194386) \
    $(wildcard include/config/ARM64_ERRATUM_4193714) \
    $(wildcard include/config/HW_PERF_EVENTS) \
    $(wildcard include/config/ARM64_LSUI) \
  /root/k7/arch/arm64/include/generated/asm/cpucap-defs.h \
  /root/k7/arch/arm64/include/asm/insn-def.h \
  /root/k7/arch/arm64/include/asm/brk-imm.h \
  /root/k7/include/linux/stringify.h \
  /root/k7/include/asm-generic/barrier.h \
  /root/k7/include/linux/stat.h \
  /root/k7/arch/arm64/include/asm/stat.h \
    $(wildcard include/config/COMPAT) \
  /root/k7/arch/arm64/include/generated/uapi/asm/stat.h \
  /root/k7/include/uapi/asm-generic/stat.h \
  /root/k7/include/linux/time.h \
    $(wildcard include/config/POSIX_TIMERS) \
  /root/k7/include/linux/cache.h \
    $(wildcard include/config/ARCH_HAS_CACHE_LINE_SIZE) \
  /root/k7/include/uapi/linux/kernel.h \
  /root/k7/include/uapi/linux/sysinfo.h \
  /root/k7/include/vdso/cache.h \
  /root/k7/arch/arm64/include/asm/cache.h \
    $(wildcard include/config/KASAN_HW_TAGS) \
  /root/k7/include/linux/bitops.h \
  /root/k7/include/linux/bits.h \
  /root/k7/include/uapi/linux/bits.h \
  /root/k7/include/linux/overflow.h \
  /root/k7/include/linux/limits.h \
  /root/k7/include/uapi/linux/limits.h \
  /root/k7/include/vdso/limits.h \
  /root/k7/include/linux/typecheck.h \
  /root/k7/include/asm-generic/bitops/generic-non-atomic.h \
  /root/k7/arch/arm64/include/asm/bitops.h \
  /root/k7/include/asm-generic/bitops/builtin-__ffs.h \
  /root/k7/include/asm-generic/bitops/builtin-ffs.h \
  /root/k7/include/asm-generic/bitops/builtin-__fls.h \
  /root/k7/include/asm-generic/bitops/builtin-fls.h \
  /root/k7/include/asm-generic/bitops/ffz.h \
  /root/k7/include/asm-generic/bitops/fls64.h \
  /root/k7/include/asm-generic/bitops/sched.h \
  /root/k7/include/asm-generic/bitops/hweight.h \
  /root/k7/include/asm-generic/bitops/arch_hweight.h \
  /root/k7/include/asm-generic/bitops/const_hweight.h \
  /root/k7/include/asm-generic/bitops/atomic.h \
  /root/k7/include/linux/atomic.h \
  /root/k7/arch/arm64/include/asm/atomic.h \
  /root/k7/arch/arm64/include/asm/cmpxchg.h \
  /root/k7/arch/arm64/include/asm/lse.h \
  /root/k7/arch/arm64/include/asm/atomic_ll_sc.h \
    $(wildcard include/config/CC_HAS_K_CONSTRAINT) \
  /root/k7/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/GENDWARFKSYMS) \
  /root/k7/include/linux/linkage.h \
    $(wildcard include/config/ARCH_USE_SYM_ANNOTATIONS) \
  /root/k7/arch/arm64/include/asm/linkage.h \
  /root/k7/arch/arm64/include/asm/alternative.h \
  /root/k7/include/linux/init.h \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
  /root/k7/arch/arm64/include/asm/atomic_lse.h \
  /root/k7/include/linux/atomic/atomic-arch-fallback.h \
    $(wildcard include/config/GENERIC_ATOMIC64) \
  /root/k7/include/linux/atomic/atomic-long.h \
  /root/k7/include/linux/atomic/atomic-instrumented.h \
  /root/k7/include/linux/instrumented.h \
    $(wildcard include/config/DEBUG_ATOMIC) \
    $(wildcard include/config/DEBUG_ATOMIC_LARGEST_ALIGN) \
  /root/k7/include/linux/bug.h \
    $(wildcard include/config/PRINTK) \
    $(wildcard include/config/BUG_ON_DATA_CORRUPTION) \
  /root/k7/arch/arm64/include/asm/bug.h \
  /root/k7/arch/arm64/include/asm/asm-bug.h \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
  /root/k7/include/asm-generic/bug.h \
    $(wildcard include/config/DEBUG_BUGVERBOSE_DETAILED) \
    $(wildcard include/config/BUG) \
    $(wildcard include/config/GENERIC_BUG_RELATIVE_POINTERS) \
  /root/k7/include/linux/instrumentation.h \
    $(wildcard include/config/NOINSTR_VALIDATION) \
  /root/k7/include/linux/once_lite.h \
  /root/k7/include/linux/panic.h \
    $(wildcard include/config/PANIC_TIMEOUT) \
  /root/k7/include/linux/stdarg.h \
  /root/k7/include/linux/printk.h \
    $(wildcard include/config/MESSAGE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_QUIET) \
    $(wildcard include/config/EARLY_PRINTK) \
    $(wildcard include/config/DYNAMIC_DEBUG) \
  /root/k7/include/linux/kern_levels.h \
  /root/k7/include/linux/ratelimit_types.h \
  /root/k7/include/uapi/linux/param.h \
  /root/k7/arch/arm64/include/uapi/asm/param.h \
  /root/k7/include/asm-generic/param.h \
    $(wildcard include/config/HZ) \
  /root/k7/include/uapi/asm-generic/param.h \
  /root/k7/include/linux/spinlock_types_raw.h \
    $(wildcard include/config/DEBUG_SPINLOCK) \
    $(wildcard include/config/DEBUG_LOCK_ALLOC) \
  /root/k7/arch/arm64/include/asm/spinlock_types.h \
  /root/k7/include/asm-generic/qspinlock_types.h \
    $(wildcard include/config/NR_CPUS) \
  /root/k7/include/asm-generic/qrwlock_types.h \
  /root/k7/arch/arm64/include/uapi/asm/byteorder.h \
  /root/k7/include/linux/byteorder/little_endian.h \
  /root/k7/include/uapi/linux/byteorder/little_endian.h \
  /root/k7/include/linux/swab.h \
  /root/k7/include/uapi/linux/swab.h \
  /root/k7/arch/arm64/include/generated/uapi/asm/swab.h \
  /root/k7/include/uapi/asm-generic/swab.h \
  /root/k7/include/linux/byteorder/generic.h \
  /root/k7/include/linux/lockdep_types.h \
    $(wildcard include/config/PROVE_RAW_LOCK_NESTING) \
    $(wildcard include/config/LOCKDEP) \
    $(wildcard include/config/LOCK_STAT) \
  /root/k7/include/linux/kmsan-checks.h \
    $(wildcard include/config/KMSAN) \
  /root/k7/include/asm-generic/bitops/instrumented-atomic.h \
  /root/k7/include/asm-generic/bitops/lock.h \
  /root/k7/include/asm-generic/bitops/instrumented-lock.h \
  /root/k7/include/asm-generic/bitops/non-atomic.h \
  /root/k7/include/asm-generic/bitops/non-instrumented-non-atomic.h \
  /root/k7/include/asm-generic/bitops/le.h \
  /root/k7/include/asm-generic/bitops/ext2-atomic-setbit.h \
  /root/k7/include/linux/kasan-enabled.h \
    $(wildcard include/config/ARCH_DEFER_KASAN) \
    $(wildcard include/config/KASAN) \
  /root/k7/include/linux/static_key.h \
  /root/k7/include/linux/jump_label.h \
    $(wildcard include/config/HAVE_ARCH_JUMP_LABEL_RELATIVE) \
  /root/k7/include/linux/cleanup.h \
  /root/k7/include/linux/err.h \
  /root/k7/arch/arm64/include/generated/uapi/asm/errno.h \
  /root/k7/include/uapi/asm-generic/errno.h \
  /root/k7/include/uapi/asm-generic/errno-base.h \
  /root/k7/include/linux/args.h \
  /root/k7/arch/arm64/include/asm/jump_label.h \
  /root/k7/arch/arm64/include/asm/insn.h \
  /root/k7/arch/arm64/include/asm/cputype.h \
  /root/k7/arch/arm64/include/asm/sysreg.h \
    $(wildcard include/config/BROKEN_GAS_INST) \
    $(wildcard include/config/ARM64_PA_BITS_52) \
    $(wildcard include/config/ARM64_4K_PAGES) \
    $(wildcard include/config/ARM64_16K_PAGES) \
    $(wildcard include/config/ARM64_64K_PAGES) \
    $(wildcard include/config/AMPERE_ERRATUM_AC04_CPU_23) \
  /root/k7/include/linux/kasan-tags.h \
  /root/k7/arch/arm64/include/asm/gpr-num.h \
  /root/k7/arch/arm64/include/generated/asm/sysreg-defs.h \
  /root/k7/include/linux/bitfield.h \
  /root/k7/arch/arm64/include/asm/mte-def.h \
  /root/k7/include/linux/math64.h \
    $(wildcard include/config/ARCH_SUPPORTS_INT128) \
  /root/k7/include/linux/math.h \
  /root/k7/arch/arm64/include/generated/asm/div64.h \
  /root/k7/include/asm-generic/div64.h \
    $(wildcard include/config/CC_OPTIMIZE_FOR_PERFORMANCE) \
  /root/k7/include/vdso/math64.h \
  /root/k7/include/linux/time64.h \
  /root/k7/include/vdso/time64.h \
  /root/k7/include/uapi/linux/time.h \
  /root/k7/include/uapi/linux/time_types.h \
  /root/k7/include/linux/time32.h \
  /root/k7/include/linux/timex.h \
  /root/k7/include/uapi/linux/timex.h \
  /root/k7/arch/arm64/include/asm/timex.h \
  /root/k7/arch/arm64/include/asm/arch_timer.h \
    $(wildcard include/config/ARM_ARCH_TIMER_OOL_WORKAROUND) \
  /root/k7/arch/arm64/include/asm/hwcap.h \
  /root/k7/arch/arm64/include/uapi/asm/hwcap.h \
  /root/k7/arch/arm64/include/asm/cpufeature.h \
    $(wildcard include/config/ARM64_SW_TTBR0_PAN) \
    $(wildcard include/config/ARM64_DEBUG_PRIORITY_MASKING) \
    $(wildcard include/config/ARM64_BTI_KERNEL) \
    $(wildcard include/config/ARM64_PA_BITS) \
    $(wildcard include/config/ARM64_HW_AFDBM) \
    $(wildcard include/config/ARM64_AMU_EXTN) \
    $(wildcard include/config/ARM64_LPA2) \
  /root/k7/include/linux/kernel.h \
    $(wildcard include/config/PREEMPT_VOLUNTARY_BUILD) \
    $(wildcard include/config/PREEMPT_DYNAMIC) \
    $(wildcard include/config/HAVE_PREEMPT_DYNAMIC_CALL) \
    $(wildcard include/config/HAVE_PREEMPT_DYNAMIC_KEY) \
    $(wildcard include/config/PREEMPT_) \
    $(wildcard include/config/DEBUG_ATOMIC_SLEEP) \
    $(wildcard include/config/MMU) \
    $(wildcard include/config/PROVE_LOCKING) \
  /root/k7/include/linux/align.h \
  /root/k7/include/vdso/align.h \
  /root/k7/include/linux/array_size.h \
  /root/k7/include/linux/kstrtox.h \
  /root/k7/include/linux/log2.h \
    $(wildcard include/config/ARCH_HAS_ILOG2_U32) \
    $(wildcard include/config/ARCH_HAS_ILOG2_U64) \
  /root/k7/include/linux/minmax.h \
  /root/k7/include/linux/sprintf.h \
  /root/k7/include/linux/static_call_types.h \
    $(wildcard include/config/HAVE_STATIC_CALL) \
  /root/k7/include/linux/trace_printk.h \
  /root/k7/include/linux/instruction_pointer.h \
  /root/k7/include/linux/util_macros.h \
    $(wildcard include/config/FOO_SUSPEND) \
  /root/k7/include/linux/wordpart.h \
  /root/k7/include/linux/cpumask.h \
    $(wildcard include/config/FORCE_NR_CPUS) \
    $(wildcard include/config/HOTPLUG_CPU) \
    $(wildcard include/config/DEBUG_PER_CPU_MAPS) \
    $(wildcard include/config/CPUMASK_OFFSTACK) \
  /root/k7/include/linux/bitmap.h \
  /root/k7/include/linux/errno.h \
  /root/k7/include/uapi/linux/errno.h \
  /root/k7/include/linux/find.h \
  /root/k7/include/linux/string.h \
    $(wildcard include/config/BINARY_PRINTF) \
  /root/k7/include/uapi/linux/string.h \
  /root/k7/arch/arm64/include/asm/string.h \
    $(wildcard include/config/ARCH_HAS_UACCESS_FLUSHCACHE) \
  /root/k7/include/linux/bitmap-str.h \
  /root/k7/include/linux/cpumask_types.h \
  /root/k7/include/linux/threads.h \
    $(wildcard include/config/BASE_SMALL) \
  /root/k7/include/linux/gfp_types.h \
  /root/k7/include/linux/numa.h \
    $(wildcard include/config/NUMA_KEEP_MEMINFO) \
    $(wildcard include/config/NUMA) \
    $(wildcard include/config/HAVE_ARCH_NODE_DEV_GROUP) \
  /root/k7/include/linux/nodemask.h \
    $(wildcard include/config/HIGHMEM) \
  /root/k7/include/linux/nodemask_types.h \
    $(wildcard include/config/NODES_SHIFT) \
  /root/k7/include/linux/random.h \
    $(wildcard include/config/VMGENID) \
  /root/k7/include/uapi/linux/random.h \
  /root/k7/include/uapi/linux/ioctl.h \
  /root/k7/arch/arm64/include/generated/uapi/asm/ioctl.h \
  /root/k7/include/asm-generic/ioctl.h \
  /root/k7/include/uapi/asm-generic/ioctl.h \
  /root/k7/include/linux/irqnr.h \
  /root/k7/include/uapi/linux/irqnr.h \
  /root/k7/arch/arm64/include/asm/sparsemem.h \
  /root/k7/arch/arm64/include/asm/pgtable-prot.h \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_WP) \
  /root/k7/arch/arm64/include/asm/memory.h \
    $(wildcard include/config/ARM64_VA_BITS) \
    $(wildcard include/config/KASAN_SHADOW_OFFSET) \
    $(wildcard include/config/RANDOMIZE_BASE) \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/EFI) \
    $(wildcard include/config/ARM_GIC_V3_ITS) \
  /root/k7/include/linux/sizes.h \
  /root/k7/arch/arm64/include/asm/page-def.h \
  /root/k7/include/vdso/page.h \
    $(wildcard include/config/PAGE_SHIFT) \
  /root/k7/include/linux/mmdebug.h \
    $(wildcard include/config/DEBUG_VM) \
    $(wildcard include/config/DEBUG_VM_IRQSOFF) \
    $(wildcard include/config/DEBUG_VM_PGFLAGS) \
  /root/k7/arch/arm64/include/asm/boot.h \
  /root/k7/arch/arm64/include/asm/sections.h \
  /root/k7/include/asm-generic/sections.h \
    $(wildcard include/config/HAVE_FUNCTION_DESCRIPTORS) \
  /root/k7/include/asm-generic/memory_model.h \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/SPARSEMEM) \
  /root/k7/include/linux/pfn.h \
  /root/k7/arch/arm64/include/asm/pgtable-hwdef.h \
    $(wildcard include/config/PGTABLE_LEVELS) \
    $(wildcard include/config/ARM64_CONT_PTE_SHIFT) \
    $(wildcard include/config/ARM64_CONT_PMD_SHIFT) \
    $(wildcard include/config/ARM64_VA_BITS_52) \
  /root/k7/arch/arm64/include/asm/pgtable-types.h \
  /root/k7/arch/arm64/include/asm/rsi.h \
  /root/k7/arch/arm64/include/asm/rsi_cmds.h \
  /root/k7/include/linux/arm-smccc.h \
    $(wildcard include/config/HAVE_ARM_SMCCC) \
    $(wildcard include/config/ARM) \
  /root/k7/include/linux/uuid.h \
  /root/k7/arch/arm64/include/asm/rsi_smc.h \
  /root/k7/arch/arm64/include/generated/asm/kernel-hwcap.h \
  /root/k7/include/linux/percpu.h \
    $(wildcard include/config/KMALLOC_PARTITION_CACHES) \
    $(wildcard include/config/PAGE_SIZE_4KB) \
    $(wildcard include/config/NEED_PER_CPU_PAGE_FIRST_CHUNK) \
    $(wildcard include/config/HAVE_SETUP_PER_CPU_AREA) \
  /root/k7/include/linux/alloc_tag.h \
    $(wildcard include/config/MEM_ALLOC_PROFILING_DEBUG) \
    $(wildcard include/config/MEM_ALLOC_PROFILING) \
    $(wildcard include/config/ARCH_MODULE_NEEDS_WEAK_PER_CPU) \
    $(wildcard include/config/MEM_ALLOC_PROFILING_ENABLED_BY_DEFAULT) \
  /root/k7/include/linux/codetag.h \
    $(wildcard include/config/CODE_TAGGING) \
  /root/k7/include/linux/preempt.h \
    $(wildcard include/config/PREEMPT_RT) \
    $(wildcard include/config/PREEMPT_COUNT) \
    $(wildcard include/config/DEBUG_PREEMPT) \
    $(wildcard include/config/TRACE_PREEMPT_TOGGLE) \
    $(wildcard include/config/PREEMPTION) \
    $(wildcard include/config/PREEMPT_NOTIFIERS) \
    $(wildcard include/config/PREEMPT_NONE) \
    $(wildcard include/config/PREEMPT_VOLUNTARY) \
    $(wildcard include/config/PREEMPT) \
    $(wildcard include/config/PREEMPT_LAZY) \
  /root/k7/arch/arm64/include/asm/preempt.h \
  /root/k7/include/linux/thread_info.h \
    $(wildcard include/config/THREAD_INFO_IN_TASK) \
    $(wildcard include/config/GENERIC_ENTRY) \
    $(wildcard include/config/ARCH_HAS_PREEMPT_LAZY) \
    $(wildcard include/config/HAVE_ARCH_WITHIN_STACK_FRAMES) \
    $(wildcard include/config/SH) \
  /root/k7/include/linux/restart_block.h \
  /root/k7/arch/arm64/include/asm/current.h \
  /root/k7/arch/arm64/include/asm/thread_info.h \
    $(wildcard include/config/ARM64_MPAM) \
  /root/k7/arch/arm64/include/asm/stack_pointer.h \
  /root/k7/arch/arm64/include/asm/percpu.h \
  /root/k7/include/asm-generic/percpu.h \
  /root/k7/include/linux/percpu-defs.h \
    $(wildcard include/config/DEBUG_FORCE_WEAK_PER_CPU) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /root/k7/include/linux/smp.h \
    $(wildcard include/config/UP_LATE_INIT) \
    $(wildcard include/config/CSD_LOCK_WAIT_DEBUG) \
  /root/k7/include/linux/smp_types.h \
  /root/k7/include/linux/llist.h \
    $(wildcard include/config/ARCH_HAVE_NMI_SAFE_CMPXCHG) \
  /root/k7/arch/arm64/include/asm/smp.h \
    $(wildcard include/config/ARM64_ACPI_PARKING_PROTOCOL) \
  /root/k7/include/linux/irqflags.h \
    $(wildcard include/config/TRACE_IRQFLAGS) \
    $(wildcard include/config/IRQSOFF_TRACER) \
    $(wildcard include/config/PREEMPT_TRACER) \
    $(wildcard include/config/DEBUG_IRQFLAGS) \
    $(wildcard include/config/TRACE_IRQFLAGS_SUPPORT) \
  /root/k7/include/linux/irqflags_types.h \
  /root/k7/arch/arm64/include/asm/irqflags.h \
  /root/k7/arch/arm64/include/asm/ptrace.h \
  /root/k7/arch/arm64/include/uapi/asm/ptrace.h \
  /root/k7/arch/arm64/include/uapi/asm/sve_context.h \
  /root/k7/include/linux/irqchip/arm-gic-v3-prio.h \
  /root/k7/arch/arm64/include/asm/stacktrace/frame.h \
  /root/k7/include/linux/sched.h \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_NATIVE) \
    $(wildcard include/config/SCHED_INFO) \
    $(wildcard include/config/SCHEDSTATS) \
    $(wildcard include/config/SCHED_CORE) \
    $(wildcard include/config/FAIR_GROUP_SCHED) \
    $(wildcard include/config/RT_GROUP_SCHED) \
    $(wildcard include/config/RT_MUTEXES) \
    $(wildcard include/config/UCLAMP_TASK) \
    $(wildcard include/config/UCLAMP_BUCKETS_COUNT) \
    $(wildcard include/config/KMAP_LOCAL) \
    $(wildcard include/config/SCHED_CLASS_EXT) \
    $(wildcard include/config/CGROUP_SCHED) \
    $(wildcard include/config/CFS_BANDWIDTH) \
    $(wildcard include/config/BLK_DEV_IO_TRACE) \
    $(wildcard include/config/PREEMPT_RCU) \
    $(wildcard include/config/TASKS_RCU) \
    $(wildcard include/config/TASKS_TRACE_RCU) \
    $(wildcard include/config/TRIVIAL_PREEMPT_RCU) \
    $(wildcard include/config/MEMCG_V1) \
    $(wildcard include/config/LRU_GEN) \
    $(wildcard include/config/COMPAT_BRK) \
    $(wildcard include/config/CGROUPS) \
    $(wildcard include/config/BLK_CGROUP) \
    $(wildcard include/config/PSI) \
    $(wildcard include/config/PAGE_OWNER) \
    $(wildcard include/config/EVENTFD) \
    $(wildcard include/config/ARCH_HAS_CPU_PASID) \
    $(wildcard include/config/X86_BUS_LOCK_DETECT) \
    $(wildcard include/config/TASK_DELAY_ACCT) \
    $(wildcard include/config/STACKPROTECTOR) \
    $(wildcard include/config/ARCH_HAS_SCALED_CPUTIME) \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_GEN) \
    $(wildcard include/config/NO_HZ_FULL) \
    $(wildcard include/config/POSIX_CPUTIMERS) \
    $(wildcard include/config/POSIX_CPU_TIMERS_TASK_WORK) \
    $(wildcard include/config/KEYS) \
    $(wildcard include/config/SYSVIPC) \
    $(wildcard include/config/DETECT_HUNG_TASK) \
    $(wildcard include/config/IO_URING) \
    $(wildcard include/config/AUDIT) \
    $(wildcard include/config/AUDITSYSCALL) \
    $(wildcard include/config/DETECT_HUNG_TASK_BLOCKER) \
    $(wildcard include/config/UBSAN) \
    $(wildcard include/config/UBSAN_TRAP) \
    $(wildcard include/config/COMPACTION) \
    $(wildcard include/config/TASK_XACCT) \
    $(wildcard include/config/CPUSETS) \
    $(wildcard include/config/X86_CPU_RESCTRL) \
    $(wildcard include/config/PERF_EVENTS) \
    $(wildcard include/config/NUMA_BALANCING) \
    $(wildcard include/config/SCHED_CACHE) \
    $(wildcard include/config/ARCH_HAS_LAZY_MMU_MODE) \
    $(wildcard include/config/FAULT_INJECTION) \
    $(wildcard include/config/LATENCYTOP) \
    $(wildcard include/config/FUNCTION_GRAPH_TRACER) \
    $(wildcard include/config/MEMCG) \
    $(wildcard include/config/UPROBES) \
    $(wildcard include/config/BCACHE) \
    $(wildcard include/config/VMAP_STACK) \
    $(wildcard include/config/SECURITY) \
    $(wildcard include/config/BPF_SYSCALL) \
    $(wildcard include/config/KSTACK_ERASE) \
    $(wildcard include/config/KSTACK_ERASE_METRICS) \
    $(wildcard include/config/X86_MCE) \
    $(wildcard include/config/KRETPROBES) \
    $(wildcard include/config/RETHOOK) \
    $(wildcard include/config/ARCH_HAS_PARANOID_L1D_FLUSH) \
    $(wildcard include/config/RV) \
    $(wildcard include/config/RV_PER_TASK_MONITORS) \
    $(wildcard include/config/USER_EVENTS) \
    $(wildcard include/config/UNWIND_USER) \
    $(wildcard include/config/SCHED_PROXY_EXEC) \
    $(wildcard include/config/SCHED_MM_CID) \
  /root/k7/include/uapi/linux/sched.h \
  /root/k7/arch/arm64/include/asm/processor.h \
    $(wildcard include/config/KUSER_HELPERS) \
    $(wildcard include/config/ARM64_FORCE_52BIT) \
    $(wildcard include/config/HAVE_HW_BREAKPOINT) \
    $(wildcard include/config/ARM64_TAGGED_ADDR_ABI) \
  /root/k7/include/vdso/processor.h \
  /root/k7/arch/arm64/include/asm/vdso/processor.h \
  /root/k7/arch/arm64/include/asm/hw_breakpoint.h \
    $(wildcard include/config/CPU_PM) \
  /root/k7/arch/arm64/include/asm/virt.h \
    $(wildcard include/config/KVM) \
  /root/k7/arch/arm64/include/asm/kasan.h \
  /root/k7/arch/arm64/include/asm/mte-kasan.h \
  /root/k7/arch/arm64/include/asm/pointer_auth.h \
  /root/k7/include/uapi/linux/prctl.h \
  /root/k7/arch/arm64/include/asm/spectre.h \
  /root/k7/arch/arm64/include/asm/fpsimd.h \
  /root/k7/arch/arm64/include/uapi/asm/sigcontext.h \
  /root/k7/include/linux/futex_types.h \
    $(wildcard include/config/FUTEX) \
    $(wildcard include/config/FUTEX_PRIVATE_HASH) \
    $(wildcard include/config/FUTEX_ROBUST_UNLOCK) \
  /root/k7/include/linux/mutex_types.h \
    $(wildcard include/config/MUTEX_SPIN_ON_OWNER) \
    $(wildcard include/config/DEBUG_MUTEXES) \
  /root/k7/include/linux/osq_lock.h \
  /root/k7/include/linux/spinlock_types.h \
  /root/k7/include/linux/rwlock_types.h \
  /root/k7/include/linux/pid_types.h \
  /root/k7/include/linux/sem_types.h \
  /root/k7/include/linux/shm.h \
  /root/k7/arch/arm64/include/asm/page.h \
  /root/k7/include/linux/personality.h \
  /root/k7/include/uapi/linux/personality.h \
  /root/k7/include/asm-generic/getorder.h \
  /root/k7/arch/arm64/include/asm/shmparam.h \
  /root/k7/include/asm-generic/shmparam.h \
  /root/k7/include/linux/kmsan_types.h \
  /root/k7/include/linux/plist_types.h \
  /root/k7/include/linux/hrtimer_types.h \
  /root/k7/include/linux/timerqueue_types.h \
  /root/k7/include/linux/rbtree_types.h \
  /root/k7/include/linux/timer_types.h \
  /root/k7/include/linux/seccomp_types.h \
    $(wildcard include/config/SECCOMP) \
  /root/k7/include/linux/refcount_types.h \
  /root/k7/include/linux/resource.h \
  /root/k7/include/uapi/linux/resource.h \
  /root/k7/arch/arm64/include/generated/uapi/asm/resource.h \
  /root/k7/include/asm-generic/resource.h \
  /root/k7/include/uapi/asm-generic/resource.h \
  /root/k7/include/linux/latencytop.h \
  /root/k7/include/linux/sched/prio.h \
  /root/k7/include/linux/sched/types.h \
  /root/k7/include/linux/signal_types.h \
    $(wildcard include/config/OLD_SIGACTION) \
  /root/k7/include/uapi/linux/signal.h \
  /root/k7/arch/arm64/include/asm/signal.h \
  /root/k7/arch/arm64/include/uapi/asm/signal.h \
  /root/k7/include/asm-generic/signal.h \
  /root/k7/include/uapi/asm-generic/signal.h \
  /root/k7/include/uapi/asm-generic/signal-defs.h \
  /root/k7/arch/arm64/include/generated/uapi/asm/siginfo.h \
  /root/k7/include/uapi/asm-generic/siginfo.h \
  /root/k7/include/linux/spinlock.h \
  /root/k7/include/linux/bottom_half.h \
  /root/k7/include/linux/lockdep.h \
    $(wildcard include/config/DEBUG_LOCKING_API_SELFTESTS) \
  /root/k7/arch/arm64/include/generated/asm/mmiowb.h \
  /root/k7/include/asm-generic/mmiowb.h \
    $(wildcard include/config/MMIOWB) \
  /root/k7/arch/arm64/include/asm/spinlock.h \
  /root/k7/arch/arm64/include/generated/asm/qspinlock.h \
  /root/k7/include/asm-generic/qspinlock.h \
  /root/k7/arch/arm64/include/generated/asm/qrwlock.h \
  /root/k7/include/asm-generic/qrwlock.h \
  /root/k7/include/linux/rwlock.h \
  /root/k7/include/linux/spinlock_api_smp.h \
    $(wildcard include/config/INLINE_SPIN_LOCK) \
    $(wildcard include/config/INLINE_SPIN_LOCK_BH) \
    $(wildcard include/config/INLINE_SPIN_LOCK_IRQ) \
    $(wildcard include/config/INLINE_SPIN_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_SPIN_TRYLOCK) \
    $(wildcard include/config/INLINE_SPIN_TRYLOCK_BH) \
    $(wildcard include/config/UNINLINE_SPIN_UNLOCK) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_BH) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_IRQRESTORE) \
    $(wildcard include/config/GENERIC_LOCKBREAK) \
  /root/k7/include/linux/rwlock_api_smp.h \
    $(wildcard include/config/INLINE_READ_LOCK) \
    $(wildcard include/config/INLINE_WRITE_LOCK) \
    $(wildcard include/config/INLINE_READ_LOCK_BH) \
    $(wildcard include/config/INLINE_WRITE_LOCK_BH) \
    $(wildcard include/config/INLINE_READ_LOCK_IRQ) \
    $(wildcard include/config/INLINE_WRITE_LOCK_IRQ) \
    $(wildcard include/config/INLINE_READ_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_WRITE_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_READ_TRYLOCK) \
    $(wildcard include/config/INLINE_WRITE_TRYLOCK) \
    $(wildcard include/config/INLINE_READ_UNLOCK) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK) \
    $(wildcard include/config/INLINE_READ_UNLOCK_BH) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_BH) \
    $(wildcard include/config/INLINE_READ_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_READ_UNLOCK_IRQRESTORE) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_IRQRESTORE) \
  /root/k7/include/linux/syscall_user_dispatch_types.h \
  /root/k7/include/linux/mm_types_task.h \
    $(wildcard include/config/ARCH_WANT_BATCHED_UNMAP_TLB_FLUSH) \
  /root/k7/arch/arm64/include/asm/tlbbatch.h \
  /root/k7/include/linux/netdevice_xmit.h \
    $(wildcard include/config/NET_ACT_MIRRED) \
    $(wildcard include/config/NET_EGRESS) \
    $(wildcard include/config/NF_DUP_NETDEV) \
  /root/k7/include/linux/task_io_accounting.h \
    $(wildcard include/config/TASK_IO_ACCOUNTING) \
  /root/k7/include/linux/posix-timers_types.h \
  /root/k7/include/linux/rseq_types.h \
    $(wildcard include/config/RSEQ) \
    $(wildcard include/config/RSEQ_SLICE_EXTENSION) \
  /root/k7/include/linux/irq_work_types.h \
  /root/k7/include/linux/workqueue_types.h \
  /root/k7/include/linux/seqlock_types.h \
  /root/k7/include/linux/kcsan.h \
  /root/k7/include/linux/rv.h \
    $(wildcard include/config/RV_LTL_MONITOR) \
    $(wildcard include/config/RV_HA_MONITOR) \
    $(wildcard include/config/RV_REACTORS) \
  /root/k7/include/linux/uidgid_types.h \
  /root/k7/include/linux/tracepoint-defs.h \
  /root/k7/include/linux/unwind_deferred_types.h \
  /root/k7/arch/arm64/include/generated/asm/kmap_size.h \
  /root/k7/include/asm-generic/kmap_size.h \
    $(wildcard include/config/DEBUG_KMAP_LOCAL) \
  /root/k7/include/generated/rq-offsets.h \
  /root/k7/include/linux/sched/ext.h \
    $(wildcard include/config/EXT_GROUP_SCHED) \
  /root/k7/include/clocksource/arm_arch_timer.h \
    $(wildcard include/config/ARM_ARCH_TIMER) \
  /root/k7/include/linux/timecounter.h \
  /root/k7/include/asm-generic/timex.h \
  /root/k7/include/vdso/time32.h \
  /root/k7/include/vdso/time.h \
  /root/k7/arch/arm64/include/asm/compat.h \
  /root/k7/include/asm-generic/compat.h \
    $(wildcard include/config/COMPAT_FOR_U64_ALIGNMENT) \
  /root/k7/include/linux/sched/task_stack.h \
    $(wildcard include/config/STACK_GROWSUP) \
    $(wildcard include/config/DEBUG_STACK_USAGE) \
  /root/k7/include/uapi/linux/magic.h \
  /root/k7/include/linux/refcount.h \
  /root/k7/include/linux/kasan.h \
    $(wildcard include/config/KASAN_STACK) \
    $(wildcard include/config/KASAN_VMALLOC) \
  /root/k7/include/uapi/linux/stat.h \
  /root/k7/include/linux/uidgid.h \
    $(wildcard include/config/MULTIUSER) \
    $(wildcard include/config/USER_NS) \
  /root/k7/include/linux/highuid.h \
  /root/k7/include/linux/buildid.h \
    $(wildcard include/config/VMCORE_INFO) \
  /root/k7/include/linux/kmod.h \
  /root/k7/include/linux/umh.h \
  /root/k7/include/linux/gfp.h \
    $(wildcard include/config/ZONE_DMA) \
    $(wildcard include/config/ZONE_DMA32) \
    $(wildcard include/config/ZONE_DEVICE) \
    $(wildcard include/config/CONTIG_ALLOC) \
  /root/k7/include/linux/mmzone.h \
    $(wildcard include/config/ARCH_FORCE_MAX_ORDER) \
    $(wildcard include/config/PAGE_BLOCK_MAX_ORDER) \
    $(wildcard include/config/HAVE_GIGANTIC_FOLIOS) \
    $(wildcard include/config/HUGETLB_PAGE) \
    $(wildcard include/config/HUGETLB_PAGE_OPTIMIZE_VMEMMAP) \
    $(wildcard include/config/CMA) \
    $(wildcard include/config/MEMORY_ISOLATION) \
    $(wildcard include/config/ZSMALLOC) \
    $(wildcard include/config/UNACCEPTED_MEMORY) \
    $(wildcard include/config/IOMMU_SUPPORT) \
    $(wildcard include/config/SWAP) \
    $(wildcard include/config/TRANSPARENT_HUGEPAGE) \
    $(wildcard include/config/LRU_GEN_STATS) \
    $(wildcard include/config/LRU_GEN_WALKS_MMU) \
    $(wildcard include/config/MEMORY_FAILURE) \
    $(wildcard include/config/PAGE_EXTENSION) \
    $(wildcard include/config/DEFERRED_STRUCT_PAGE_INIT) \
    $(wildcard include/config/HAVE_MEMORYLESS_NODES) \
    $(wildcard include/config/SPARSEMEM_EXTREME) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP_PREINIT) \
    $(wildcard include/config/HAVE_ARCH_PFN_VALID) \
  /root/k7/include/linux/list_nulls.h \
  /root/k7/include/linux/wait.h \
  /root/k7/include/linux/seqlock.h \
    $(wildcard include/config/CC_IS_GCC) \
    $(wildcard include/config/GCC_VERSION) \
    $(wildcard include/config/UBSAN_ALIGNMENT) \
  /root/k7/include/linux/mutex.h \
  /root/k7/include/linux/debug_locks.h \
  /root/k7/include/linux/pageblock-flags.h \
    $(wildcard include/config/HUGETLB_PAGE_SIZE_VARIABLE) \
  /root/k7/include/linux/page-flags-layout.h \
  /root/k7/include/generated/bounds.h \
  /root/k7/include/linux/mm_types.h \
    $(wildcard include/config/HAVE_ALIGNED_STRUCT_PAGE) \
    $(wildcard include/config/SLAB_OBJ_EXT) \
    $(wildcard include/config/HUGETLB_PMD_PAGE_TABLE_SHARING) \
    $(wildcard include/config/SLAB_FREELIST_HARDENED) \
    $(wildcard include/config/USERFAULTFD) \
    $(wildcard include/config/ANON_VMA_NAME) \
    $(wildcard include/config/PER_VMA_LOCK) \
    $(wildcard include/config/HAVE_ARCH_COMPAT_MMAP_BASES) \
    $(wildcard include/config/MEMBARRIER) \
    $(wildcard include/config/ARCH_HAS_ELF_CORE_EFLAGS) \
    $(wildcard include/config/AIO) \
    $(wildcard include/config/MMU_NOTIFIER) \
    $(wildcard include/config/SPLIT_PMD_PTLOCKS) \
    $(wildcard include/config/IOMMU_MM_DATA) \
    $(wildcard include/config/KSM) \
    $(wildcard include/config/MM_ID) \
    $(wildcard include/config/CORE_DUMP_DEFAULT_ELF_HEADERS) \
  /root/k7/include/linux/auxvec.h \
  /root/k7/include/uapi/linux/auxvec.h \
  /root/k7/arch/arm64/include/uapi/asm/auxvec.h \
  /root/k7/include/linux/kref.h \
  /root/k7/include/linux/rbtree.h \
  /root/k7/include/linux/rcupdate.h \
    $(wildcard include/config/TINY_RCU) \
    $(wildcard include/config/RCU_STRICT_GRACE_PERIOD) \
    $(wildcard include/config/RCU_LAZY) \
    $(wildcard include/config/RCU_STALL_COMMON) \
    $(wildcard include/config/VIRT_XFER_TO_GUEST_WORK) \
    $(wildcard include/config/RCU_NOCB_CPU) \
    $(wildcard include/config/TASKS_RCU_GENERIC) \
    $(wildcard include/config/TASKS_RUDE_RCU) \
    $(wildcard include/config/TREE_RCU) \
    $(wildcard include/config/DEBUG_OBJECTS_RCU_HEAD) \
    $(wildcard include/config/PROVE_RCU) \
    $(wildcard include/config/ARCH_WEAK_RELEASE_ACQUIRE) \
  /root/k7/include/linux/context_tracking_irq.h \
    $(wildcard include/config/CONTEXT_TRACKING_IDLE) \
  /root/k7/include/linux/rcutree.h \
  /root/k7/include/linux/maple_tree.h \
    $(wildcard include/config/MAPLE_RCU_DISABLED) \
    $(wildcard include/config/DEBUG_MAPLE_TREE) \
  /root/k7/include/linux/rwsem.h \
    $(wildcard include/config/RWSEM_SPIN_ON_OWNER) \
    $(wildcard include/config/DEBUG_RWSEMS) \
  /root/k7/include/linux/completion.h \
  /root/k7/include/linux/swait.h \
  /root/k7/include/linux/uprobes.h \
  /root/k7/include/linux/timer.h \
    $(wildcard include/config/DEBUG_OBJECTS_TIMERS) \
    $(wildcard include/config/NO_HZ_COMMON) \
  /root/k7/include/linux/ktime.h \
  /root/k7/include/linux/jiffies.h \
  /root/k7/include/vdso/jiffies.h \
  /root/k7/include/generated/timeconst.h \
  /root/k7/include/vdso/ktime.h \
  /root/k7/include/linux/timekeeping.h \
    $(wildcard include/config/POSIX_AUX_CLOCKS) \
    $(wildcard include/config/GENERIC_CMOS_UPDATE) \
  /root/k7/include/linux/clocksource_ids.h \
  /root/k7/include/linux/debugobjects.h \
    $(wildcard include/config/DEBUG_OBJECTS) \
    $(wildcard include/config/DEBUG_OBJECTS_FREE) \
  /root/k7/arch/arm64/include/asm/uprobes.h \
  /root/k7/arch/arm64/include/asm/debug-monitors.h \
  /root/k7/arch/arm64/include/asm/esr.h \
  /root/k7/arch/arm64/include/asm/probes.h \
  /root/k7/include/linux/workqueue.h \
    $(wildcard include/config/DEBUG_OBJECTS_WORK) \
    $(wildcard include/config/FREEZER) \
    $(wildcard include/config/WQ_WATCHDOG) \
  /root/k7/include/linux/percpu_counter.h \
  /root/k7/arch/arm64/include/asm/mmu.h \
    $(wildcard include/config/ARM64_E0PD) \
  /root/k7/include/linux/page-flags.h \
    $(wildcard include/config/PAGE_IDLE_FLAG) \
    $(wildcard include/config/ARCH_USES_PG_ARCH_2) \
    $(wildcard include/config/ARCH_USES_PG_ARCH_3) \
    $(wildcard include/config/MIGRATION) \
    $(wildcard include/config/DEBUG_KMAP_LOCAL_FORCE_MAP) \
  /root/k7/include/linux/local_lock.h \
  /root/k7/include/linux/local_lock_internal.h \
  /root/k7/include/linux/zswap.h \
    $(wildcard include/config/ZSWAP) \
  /root/k7/include/linux/memory_hotplug.h \
    $(wildcard include/config/ARCH_HAS_ADD_PAGES) \
    $(wildcard include/config/MEMORY_HOTREMOVE) \
  /root/k7/include/linux/notifier.h \
  /root/k7/include/linux/srcu.h \
    $(wildcard include/config/TINY_SRCU) \
    $(wildcard include/config/NEED_SRCU_NMI_SAFE) \
  /root/k7/include/linux/rcu_segcblist.h \
  /root/k7/include/linux/srcutree.h \
  /root/k7/include/linux/rcu_node_tree.h \
    $(wildcard include/config/RCU_FANOUT) \
    $(wildcard include/config/RCU_FANOUT_LEAF) \
  /root/k7/arch/arm64/include/generated/asm/mmzone.h \
  /root/k7/include/asm-generic/mmzone.h \
  /root/k7/include/linux/topology.h \
    $(wildcard include/config/USE_PERCPU_NUMA_NODE_ID) \
    $(wildcard include/config/SCHED_SMT) \
    $(wildcard include/config/GENERIC_ARCH_TOPOLOGY) \
  /root/k7/include/linux/arch_topology.h \
  /root/k7/arch/arm64/include/asm/topology.h \
  /root/k7/arch/arm64/include/asm/numa.h \
  /root/k7/include/asm-generic/numa.h \
    $(wildcard include/config/NUMA_EMU) \
  /root/k7/include/asm-generic/topology.h \
  /root/k7/include/linux/sysctl.h \
    $(wildcard include/config/SYSCTL) \
  /root/k7/include/uapi/linux/sysctl.h \
  /root/k7/include/linux/elf.h \
    $(wildcard include/config/ARCH_HAVE_EXTRA_ELF_NOTES) \
    $(wildcard include/config/ARCH_USE_GNU_PROPERTY) \
    $(wildcard include/config/ARCH_HAVE_ELF_PROT) \
  /root/k7/arch/arm64/include/asm/elf.h \
    $(wildcard include/config/COMPAT_VDSO) \
  /root/k7/arch/arm64/include/generated/asm/user.h \
  /root/k7/include/asm-generic/user.h \
  /root/k7/include/uapi/linux/elf.h \
  /root/k7/include/uapi/linux/elf-em.h \
  /root/k7/include/linux/fs.h \
    $(wildcard include/config/FANOTIFY_ACCESS_PERMISSIONS) \
    $(wildcard include/config/FS_POSIX_ACL) \
    $(wildcard include/config/CGROUP_WRITEBACK) \
    $(wildcard include/config/IMA) \
    $(wildcard include/config/FILE_LOCKING) \
    $(wildcard include/config/FSNOTIFY) \
    $(wildcard include/config/EPOLL) \
    $(wildcard include/config/FS_DAX) \
    $(wildcard include/config/BLOCK) \
    $(wildcard include/config/UNICODE) \
  /root/k7/include/linux/fs/super.h \
  /root/k7/include/linux/fs/super_types.h \
    $(wildcard include/config/QUOTA) \
    $(wildcard include/config/FS_ENCRYPTION) \
    $(wildcard include/config/FS_VERITY) \
  /root/k7/include/linux/fs_dirent.h \
  /root/k7/include/linux/errseq.h \
  /root/k7/include/linux/list_lru.h \
  /root/k7/include/linux/shrinker.h \
    $(wildcard include/config/SHRINKER_DEBUG) \
  /root/k7/include/linux/xarray.h \
    $(wildcard include/config/XARRAY_MULTI) \
  /root/k7/include/linux/sched/mm.h \
    $(wildcard include/config/MMU_LAZY_TLB_REFCOUNT) \
    $(wildcard include/config/ARCH_HAS_MEMBARRIER_CALLBACKS) \
    $(wildcard include/config/ARCH_HAS_SYNC_CORE_BEFORE_USERMODE) \
  /root/k7/include/linux/sync_core.h \
    $(wildcard include/config/ARCH_HAS_PREPARE_SYNC_CORE_CMD) \
  /root/k7/include/linux/sched/coredump.h \
  /root/k7/include/linux/list_bl.h \
  /root/k7/include/linux/bit_spinlock.h \
  /root/k7/include/linux/percpu-rwsem.h \
  /root/k7/include/linux/rcuwait.h \
  /root/k7/include/linux/sched/signal.h \
    $(wildcard include/config/SCHED_AUTOGROUP) \
    $(wildcard include/config/BSD_PROCESS_ACCT) \
    $(wildcard include/config/TASKSTATS) \
  /root/k7/include/linux/rculist.h \
    $(wildcard include/config/PROVE_RCU_LIST) \
  /root/k7/include/linux/signal.h \
    $(wildcard include/config/DYNAMIC_SIGFRAME) \
    $(wildcard include/config/PROC_FS) \
  /root/k7/include/linux/sched/jobctl.h \
  /root/k7/include/linux/sched/task.h \
    $(wildcard include/config/HAVE_EXIT_THREAD) \
    $(wildcard include/config/ARCH_WANTS_DYNAMIC_TASK_STRUCT) \
    $(wildcard include/config/HAVE_ARCH_THREAD_STRUCT_WHITELIST) \
  /root/k7/include/linux/uaccess.h \
    $(wildcard include/config/ARCH_HAS_SUBPAGE_FAULTS) \
    $(wildcard include/config/ARCH_MEMORY_ORDER_TSO) \
    $(wildcard include/config/HARDENED_USERCOPY) \
  /root/k7/include/linux/fault-inject-usercopy.h \
    $(wildcard include/config/FAULT_INJECTION_USERCOPY) \
  /root/k7/include/linux/nospec.h \
  /root/k7/include/linux/ucopysize.h \
    $(wildcard include/config/HARDENED_USERCOPY_DEFAULT_ON) \
  /root/k7/arch/arm64/include/asm/uaccess.h \
    $(wildcard include/config/CC_HAS_ASM_GOTO_OUTPUT) \
  /root/k7/arch/arm64/include/asm/kernel-pgtable.h \
    $(wildcard include/config/RELOCATABLE) \
  /root/k7/arch/arm64/include/asm/asm-extable.h \
  /root/k7/arch/arm64/include/asm/mte.h \
  /root/k7/arch/arm64/include/asm/extable.h \
    $(wildcard include/config/BPF_JIT) \
  /root/k7/include/asm-generic/access_ok.h \
    $(wildcard include/config/ALTERNATE_USER_ADDRESS_SPACE) \
  /root/k7/include/linux/cred.h \
  /root/k7/include/linux/capability.h \
  /root/k7/include/uapi/linux/capability.h \
  /root/k7/include/linux/key.h \
    $(wildcard include/config/KEY_NOTIFICATIONS) \
    $(wildcard include/config/NET) \
  /root/k7/include/linux/assoc_array.h \
    $(wildcard include/config/ASSOCIATIVE_ARRAY) \
  /root/k7/include/linux/sched/user.h \
    $(wildcard include/config/VFIO_PCI_ZDEV_KVM) \
    $(wildcard include/config/IOMMUFD) \
    $(wildcard include/config/WATCH_QUEUE) \
  /root/k7/include/linux/ratelimit.h \
  /root/k7/include/linux/pid.h \
  /root/k7/include/linux/rhashtable-types.h \
  /root/k7/include/linux/posix-timers.h \
  /root/k7/include/linux/alarmtimer.h \
    $(wildcard include/config/RTC_CLASS) \
  /root/k7/include/linux/hrtimer.h \
    $(wildcard include/config/HIGH_RES_TIMERS) \
    $(wildcard include/config/TIME_LOW_RES) \
    $(wildcard include/config/TIMERFD) \
  /root/k7/include/linux/hrtimer_defs.h \
  /root/k7/include/linux/timerqueue.h \
  /root/k7/include/linux/hrtimer_rearm.h \
    $(wildcard include/config/HRTIMER_REARM_DEFERRED) \
  /root/k7/include/linux/rcuref.h \
  /root/k7/include/linux/rcu_sync.h \
  /root/k7/include/linux/quota.h \
    $(wildcard include/config/QUOTA_NETLINK_INTERFACE) \
  /root/k7/include/uapi/linux/dqblk_xfs.h \
  /root/k7/include/linux/dqblk_v1.h \
  /root/k7/include/linux/dqblk_v2.h \
  /root/k7/include/linux/dqblk_qtree.h \
  /root/k7/include/linux/projid.h \
  /root/k7/include/uapi/linux/quota.h \
  /root/k7/include/linux/unicode.h \
  /root/k7/include/linux/dcache.h \
  /root/k7/include/linux/rculist_bl.h \
  /root/k7/include/linux/lockref.h \
    $(wildcard include/config/ARCH_USE_CMPXCHG_LOCKREF) \
  /root/k7/include/linux/stringhash.h \
    $(wildcard include/config/DCACHE_WORD_ACCESS) \
  /root/k7/include/linux/hash.h \
    $(wildcard include/config/HAVE_ARCH_HASH) \
  /root/k7/include/linux/vfsdebug.h \
    $(wildcard include/config/DEBUG_VFS) \
  /root/k7/include/linux/wait_bit.h \
  /root/k7/include/linux/kdev_t.h \
  /root/k7/include/uapi/linux/kdev_t.h \
  /root/k7/include/linux/path.h \
  /root/k7/include/linux/radix-tree.h \
  /root/k7/include/linux/semaphore.h \
  /root/k7/include/linux/fcntl.h \
    $(wildcard include/config/ARCH_32BIT_OFF_T) \
  /root/k7/include/uapi/linux/fcntl.h \
  /root/k7/arch/arm64/include/uapi/asm/fcntl.h \
  /root/k7/include/uapi/asm-generic/fcntl.h \
  /root/k7/include/uapi/linux/openat2.h \
  /root/k7/include/linux/migrate_mode.h \
  /root/k7/include/linux/delayed_call.h \
  /root/k7/include/linux/ioprio.h \
  /root/k7/include/linux/sched/rt.h \
  /root/k7/include/linux/iocontext.h \
    $(wildcard include/config/BLK_ICQ) \
  /root/k7/include/uapi/linux/ioprio.h \
  /root/k7/include/linux/mount.h \
  /root/k7/include/linux/mnt_idmapping.h \
  /root/k7/include/linux/slab.h \
    $(wildcard include/config/FAILSLAB) \
    $(wildcard include/config/KFENCE) \
    $(wildcard include/config/SLUB_TINY) \
    $(wildcard include/config/SLUB_DEBUG) \
    $(wildcard include/config/KMALLOC_PARTITION_RANDOM) \
    $(wildcard include/config/KMALLOC_PARTITION_TYPED) \
    $(wildcard include/config/SLAB_BUCKETS) \
    $(wildcard include/config/KVFREE_RCU_BATCHED) \
  /root/k7/include/linux/percpu-refcount.h \
  /root/k7/include/linux/rw_hint.h \
  /root/k7/include/linux/file_ref.h \
  /root/k7/include/uapi/linux/fs.h \
  /root/k7/include/linux/kobject.h \
    $(wildcard include/config/UEVENT_HELPER) \
    $(wildcard include/config/DEBUG_KOBJECT_RELEASE) \
  /root/k7/include/linux/sysfs.h \
  /root/k7/include/linux/kernfs.h \
    $(wildcard include/config/KERNFS) \
  /root/k7/include/linux/idr.h \
  /root/k7/include/linux/kobject_ns.h \
  /root/k7/include/linux/moduleparam.h \
    $(wildcard include/config/ALPHA) \
    $(wildcard include/config/PPC64) \
  /root/k7/include/linux/rbtree_latch.h \
  /root/k7/include/linux/error-injection.h \
  /root/k7/include/asm-generic/error-injection.h \
  /root/k7/include/linux/dynamic_debug.h \
  /root/k7/arch/arm64/include/asm/module.h \
  /root/k7/include/asm-generic/module.h \
    $(wildcard include/config/HAVE_MOD_ARCH_SPECIFIC) \
  /root/k7/include/linux/export-internal.h \
    $(wildcard include/config/PARISC) \

modem_sonda2.mod.o: $(deps_modem_sonda2.mod.o)

$(deps_modem_sonda2.mod.o):
