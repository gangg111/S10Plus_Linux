#!/usr/bin/env python3
# Szybki odczyt klatki (glReadPixels) w Panfroscie na kbase.
#
# Zmierzone 30.09.2026 (perf, WebKit na Panfroscie): 96,5% czasu watku
# kompozytora w convert_ubyte_rgba_to_bgra, bo backend kbase mapuje CALA
# pamiec dla CPU bez pamieci podrecznej (autor portu pominal BASE_MEM_CACHED_CPU,
# bo nie synchronizowal pamieci podrecznej CPU). Kazdy odczytany piksel szedl
# prosto z RAM: ~70 ms na klatke 1440x2838.
#
# Lata:
# 1. kbase_kmod.c: PAN_KMOD_BO_FLAG_WB_MMAP -> BASE_MEM_CACHED_CPU (bit 12,
#    include/uapi/gpu/arm/bv_r32p1/jm/mali_base_jm_kernel.h) i synchronizacja
#    przez KBASE_IOCTL_MEM_SYNC (nr 15; typ 0 = clean, 1 = invalidate) jako
#    zapas; na aarch64 Mesa i tak robi to z przestrzeni uzytkownika (DC CIVAC).
# 2. gallium panfrost: bufor posredni do CZYSTEGO odczytu (mapa bez
#    PIPE_MAP_WRITE) z pamiecia podreczna; po czekaniu na GPU unieswaznienie
#    pamieci podrecznej przed zwroceniem wskaznika. Bufory do zapisu bez zmian.
# Uzycie: python3 lata-odczyt-cached.py <katalog mali-panfrost>
import os
import sys

src = os.path.join(sys.argv[1], "src")


def lataj(sciezka, zmiany):
    p = os.path.join(src, sciezka)
    s = open(p, encoding="utf-8").read()
    if "PAN_BO_CACHED_CPU" in s or "BASE_MEM_CACHED_CPU (1ull" in s or "kbase_kmod_flush_bo_map_syncs" in s:
        print("juz nalozona:", sciezka)
        return
    for a, b in zmiany:
        assert s.count(a) == 1, (sciezka, a[:70])
        s = s.replace(a, b, 1)
    open(p, "w", encoding="utf-8").write(s)
    print("lata nalozona:", sciezka)


lataj("panfrost/lib/kmod/kbase_kmod.c", [
    ("#define BASE_MEM_COHERENT_LOCAL (1ull << 11)\n",
     "#define BASE_MEM_COHERENT_LOCAL (1ull << 11)\n"
     "\n"
     "/* CPU-cached mapping, for PAN_KMOD_BO_FLAG_WB_MMAP only (readback staging): the caller keeps\n"
     " * it coherent with pan_kmod_queue_bo_map_sync(). Bit 12 in the r32p1 base headers. */\n"
     "#define BASE_MEM_CACHED_CPU (1ull << 12)\n"
     "\n"
     "/* nr 15, cache maintenance on a region: type 0 cleans (CPU to memory), 1 invalidates. */\n"
     "struct kbase_ioctl_mem_sync {\n"
     "   uint64_t handle;\n"
     "   uint64_t user_addr;\n"
     "   uint64_t size;\n"
     "   uint8_t type;\n"
     "   uint8_t padding[7];\n"
     "};\n"
     "#define KBASE_IOCTL_MEM_SYNC _IOW(KBASE_IOCTL_TYPE, 15, struct kbase_ioctl_mem_sync)\n"),
    ("                       : KBASE_MEM_FLAGS_RW | (grow ? BASE_MEM_GROW_ON_GPF : 0),\n",
     "                       : KBASE_MEM_FLAGS_RW | (grow ? BASE_MEM_GROW_ON_GPF : 0) |\n"
     "                            ((flags & PAN_KMOD_BO_FLAG_WB_MMAP) ? BASE_MEM_CACHED_CPU : 0),\n"),
    ("static struct pan_kmod_bo *\nkbase_kmod_bo_alloc(",
     "/* Kernel fallback of pan_kmod_queue_bo_map_sync(), used when userspace cache ops are not\n"
     " * available. SAME_VA: the anchor mapping sits at gpu_va, so that is also the CPU address. */\n"
     "static int\n"
     "kbase_kmod_flush_bo_map_syncs(struct pan_kmod_dev *dev)\n"
     "{\n"
     "   int ret = 0;\n"
     "\n"
     "   util_dynarray_foreach(&dev->pending_bo_syncs.array, struct pan_kmod_deferred_bo_sync, sync) {\n"
     "      struct kbase_kmod_bo *bo = container_of(sync->bo, struct kbase_kmod_bo, base);\n"
     "      struct kbase_ioctl_mem_sync req = {\n"
     "         .handle = bo->gpu_va,\n"
     "         .user_addr = bo->gpu_va + sync->start,\n"
     "         .size = sync->size,\n"
     "         .type = 0,\n"
     "      };\n"
     "      if (pan_kmod_ioctl(dev->fd, KBASE_IOCTL_MEM_SYNC, &req))\n"
     "         ret = -1;\n"
     "      if (sync->type == PAN_KMOD_BO_SYNC_CPU_CACHE_FLUSH_AND_INVALIDATE) {\n"
     "         req.type = 1;\n"
     "         if (pan_kmod_ioctl(dev->fd, KBASE_IOCTL_MEM_SYNC, &req))\n"
     "            ret = -1;\n"
     "      }\n"
     "   }\n"
     "   if (ret)\n"
     "      mesa_loge(\"kbase: MEM_SYNC failed (err=%d)\", errno);\n"
     "   return ret;\n"
     "}\n"
     "\n"
     "static struct pan_kmod_bo *\nkbase_kmod_bo_alloc("),
    ("   .bo_alloc = kbase_kmod_bo_alloc,\n",
     "   .bo_alloc = kbase_kmod_bo_alloc,\n"
     "   .flush_bo_map_syncs = kbase_kmod_flush_bo_map_syncs,\n"),
    ("   if (!kbase_kmod_query_props(fd, &kbase_dev->base.props)) {",
     "   kbase_dev->base.props.supported_bo_flags |= PAN_KMOD_BO_FLAG_WB_MMAP;\n"
     "   if (!kbase_kmod_query_props(fd, &kbase_dev->base.props)) {"),
])

lataj("gallium/drivers/panfrost/pan_bo.h", [
    ("#define PAN_BO_SHAREABLE (1 << 5)\n",
     "#define PAN_BO_SHAREABLE (1 << 5)\n"
     "\n"
     "/* CPU-cached mapping (PAN_KMOD_BO_FLAG_WB_MMAP), for readback staging: the reader\n"
     " * invalidates the CPU cache after the GPU wrote. */\n"
     "#define PAN_BO_CACHED_CPU (1 << 6)\n"),
])

lataj("gallium/drivers/panfrost/pan_bo.c", [
    ("   if (flags & PAN_BO_INVISIBLE)\n      kmod_bo_flags |= PAN_KMOD_BO_FLAG_NO_MMAP;\n",
     "   if (flags & PAN_BO_INVISIBLE)\n      kmod_bo_flags |= PAN_KMOD_BO_FLAG_NO_MMAP;\n"
     "   if (flags & PAN_BO_CACHED_CPU)\n      kmod_bo_flags |= PAN_KMOD_BO_FLAG_WB_MMAP;\n"),
])

lataj("gallium/drivers/panfrost/pan_resource.c", [
    ("      uint32_t flags = PAN_BO_DELAY_MMAP;\n",
     "      uint32_t flags = PAN_BO_DELAY_MMAP;\n"
     "\n"
     "      /* Read-only staging (pan_alloc_staging): CPU-cached, if the kernel backend can. */\n"
     "      if ((template->flags & PIPE_RESOURCE_FLAG_DRV_PRIV) &&\n"
     "          (dev->kmod.dev->props.supported_bo_flags & PAN_KMOD_BO_FLAG_WB_MMAP))\n"
     "         flags |= PAN_BO_CACHED_CPU;\n"),
    ("pan_alloc_staging(struct panfrost_context *ctx, struct panfrost_resource *rsc,\n"
     "                  unsigned level, const struct pipe_box *box)\n",
     "pan_alloc_staging(struct panfrost_context *ctx, struct panfrost_resource *rsc,\n"
     "                  unsigned level, const struct pipe_box *box, bool cpu_read_only)\n"),
    ("   tmpl.compression_rate = PIPE_COMPRESSION_FIXED_RATE_NONE;\n",
     "   tmpl.compression_rate = PIPE_COMPRESSION_FIXED_RATE_NONE;\n"
     "   /* private marker: CPU-cached staging, only when the CPU never writes it */\n"
     "   tmpl.flags &= ~PIPE_RESOURCE_FLAG_DRV_PRIV;\n"
     "   if (cpu_read_only)\n"
     "      tmpl.flags |= PIPE_RESOURCE_FLAG_DRV_PRIV;\n"),
    ("         pan_alloc_staging(ctx, rsrc, level, box);\n",
     "         pan_alloc_staging(ctx, rsrc, level, box, !(usage & PIPE_MAP_WRITE));\n"),
    ("      if (panfrost_bo_mmap(staging->bo))\n         return NULL;\n\n      return staging->bo->ptr.cpu;\n",
     "      if (panfrost_bo_mmap(staging->bo))\n         return NULL;\n"
     "\n"
     "      /* Cached staging: drop stale CPU cache lines before the CPU reads what the GPU wrote. */\n"
     "      if (staging->bo->kmod_bo->flags & PAN_KMOD_BO_FLAG_WB_MMAP) {\n"
     "         pan_kmod_queue_bo_map_sync(staging->bo->kmod_bo, 0, staging->bo->ptr.cpu,\n"
     "                                    panfrost_bo_size(staging->bo),\n"
     "                                    PAN_KMOD_BO_SYNC_CPU_CACHE_FLUSH_AND_INVALIDATE);\n"
     "         pan_kmod_flush_bo_map_syncs(dev->kmod.dev);\n"
     "      }\n"
     "\n"
     "      return staging->bo->ptr.cpu;\n"),
])
