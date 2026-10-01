#!/usr/bin/env python3
# Eksport tekstury Panfrosta jako bufora gralloc Androida (zero kopii do okna na libhybris).
#
# Zmierzone 30.09.2026: WebKit na Panfroscie przekazuje klatke do okna GTK przez
# pamiec wspolna (glReadPixels + kopia w oknie), co zjada ponad rdzen CPU. Okno GTK
# rysuje przez sterownik Mali Androida (libhybris), a ten przyjmuje tylko bufory
# gralloc. Test tools/phone/panfrost-kbase/test-gralloc.c pokazal, ze Panfrost
# rysuje poprawnie do bufora z hybris_gralloc_allocate zaimportowanego jako dma-buf.
#
# Lata (wlaczana zmienna PAN_GRALLOC_EXPORT=1, domyslnie nic sie nie zmienia):
# przy pierwszym zapytaniu o eksport (eglExportDMABUFImageQueryMESA ->
# resource_get_param/resource_get_handle) pusta tekstura 2D RGBA8/RGBX8 dostaje
# nowe zaplecze: bufor z gralloc (libgralloc.so.1 przez dlopen), zaimportowany
# jak dma-buf (LINEAR, pitch z gralloc). Eksport ma wtedy numFds+1 plaszczyzn:
# fd-y uchwytu gralloc i memfd z naglowkiem {-1, version, numFds, numInts}
# oraz intami uchwytu (konwencja lindroid_drm z libhybris; strona odbiorcza:
# tools/phone/hybris-fix/lata-dmabuf-wayland.py).
# Uzycie: python3 lata-gralloc-eksport.py <katalog mali-panfrost>
import os
import sys

src = os.path.join(sys.argv[1], "src/gallium/drivers/panfrost")


def lataj(sciezka, zmiany):
    p = os.path.join(src, sciezka)
    s = open(p, encoding="utf-8").read()
    if "pan_gralloc_backing" in s:
        print("juz nalozona:", sciezka)
        return
    for a, b in zmiany:
        assert s.count(a) == 1, (sciezka, a[:70])
        s = s.replace(a, b, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("lata nalozona:", sciezka)


# Bez tego EGL nie ogłasza EGL_MESA_image_dma_buf_export i WebKit wybiera pamiec
# wspolna (SwapChain Surfaceless w AcceleratedSurface.cpp).
lataj("pan_screen.c", [
    ("   if (pan_kmod_dev_is_kbase(dev->kmod.dev))\n      caps->dmabuf = DRM_PRIME_CAP_IMPORT;\n",
     "   if (pan_kmod_dev_is_kbase(dev->kmod.dev))\n      caps->dmabuf = DRM_PRIME_CAP_IMPORT;\n"
     "\n"
     "   /* ...except through a gralloc backing (pan_gralloc_backing in pan_resource.c) */\n"
     "   if (pan_kmod_dev_is_kbase(dev->kmod.dev) && debug_get_bool_option(\"PAN_GRALLOC_EXPORT\", false))\n"
     "      caps->dmabuf |= DRM_PRIME_CAP_EXPORT;\n"),
])

# WebKit (AcceleratedSurface.cpp, RenderTargetTexture::create) podaje do
# eglExportDMABUFImageQueryMESA wskaznik na JEDEN uint64_t modifier, a Mesa pisze
# modyfikator dla kazdej plaszczyzny. Przy 3 plaszczyznach gralloc nadpisywalo to
# stos WebKita (liczba plaszczyzn w oknie wychodzila smieciowa, GTK:
# gdk_dmabuf_texture_builder_set_n_planes assertion). Wszystkie plaszczyzny maja ten
# sam modyfikator, wiec w trybie gralloc piszemy tylko pierwszy.
src_egl = os.path.join(sys.argv[1], "src/egl/drivers/dri2")
p = os.path.join(src_egl, "egl_dri2.c")
s = open(p, encoding="utf-8").read()
a = "      for (int i = 0; i < num_planes; i++)\n         modifiers[i] = modifier;\n"
if "PAN_GRALLOC_EXPORT" in s:
    print("juz nalozona: egl_dri2.c")
else:
    assert s.count(a) == 1
    s = s.replace(a,
                  "      /* PAN_GRALLOC_EXPORT: extra planes carry the gralloc handle; callers like WebKit\n"
                  "       * pass room for a single modifier, which is the same for every plane anyway */\n"
                  "      int modifier_count = getenv(\"PAN_GRALLOC_EXPORT\") ? 1 : num_planes;\n"
                  "      for (int i = 0; i < modifier_count; i++)\n         modifiers[i] = modifier;\n", 1)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("lata nalozona: egl_dri2.c")

lataj("pan_resource.h", [
    ("   struct pan_afbcp *afbcp;\n};\n",
     "   struct pan_afbcp *afbcp;\n"
     "\n"
     "   /* Android gralloc buffer backing the resource (PAN_GRALLOC_EXPORT) */\n"
     "   struct pan_gralloc_backing *gralloc;\n"
     "};\n"),
])

lataj("pan_resource.c", [
    ("#include <fcntl.h>\n",
     "#include <dlfcn.h>\n"
     "#include <fcntl.h>\n"
     "#include <sys/mman.h>\n"
     "#include \"util/os_file.h\"\n"),
    ("   util_range_destroy(&rsrc->valid_buffer_range);\n",
     "   if (rsrc->gralloc)\n"
     "      pan_gralloc_backing_free(rsrc->gralloc);\n"
     "\n"
     "   util_range_destroy(&rsrc->valid_buffer_range);\n"),
    ("static void\npanfrost_resource_destroy(struct pipe_screen *screen, struct pipe_resource *pt)\n",
     "/* Android gralloc backing, see pan_gralloc_attach(). */\n"
     "struct pan_gralloc_native_handle {\n"
     "   int version;\n"
     "   int numFds;\n"
     "   int numInts;\n"
     "   int data[];\n"
     "};\n"
     "\n"
     "struct pan_gralloc_backing {\n"
     "   const struct pan_gralloc_native_handle *handle;\n"
     "   int meta_fd;\n"
     "};\n"
     "\n"
     "static struct {\n"
     "   bool loaded;\n"
     "   int (*allocate)(int w, int h, int format, int usage,\n"
     "                   const struct pan_gralloc_native_handle **handle, uint32_t *stride);\n"
     "   int (*release)(const struct pan_gralloc_native_handle *handle, int was_allocated);\n"
     "} pan_gralloc;\n"
     "\n"
     "static void\n"
     "pan_gralloc_backing_free(struct pan_gralloc_backing *g)\n"
     "{\n"
     "   if (g->meta_fd >= 0)\n"
     "      close(g->meta_fd);\n"
     "   if (g->handle && pan_gralloc.release)\n"
     "      pan_gralloc.release(g->handle, 1);\n"
     "   free(g);\n"
     "}\n"
     "\n"
     "static void\npanfrost_resource_destroy(struct pipe_screen *screen, struct pipe_resource *pt)\n"),
    ("static bool\npanfrost_resource_get_handle(struct pipe_screen *pscreen,\n",
     "static bool\n"
     "pan_gralloc_load(void)\n"
     "{\n"
     "   if (pan_gralloc.loaded)\n"
     "      return pan_gralloc.allocate != NULL;\n"
     "   pan_gralloc.loaded = true;\n"
     "\n"
     "   void *lib = dlopen(\"libgralloc.so.1\", RTLD_NOW | RTLD_GLOBAL);\n"
     "   if (!lib) {\n"
     "      mesa_loge(\"panfrost: PAN_GRALLOC_EXPORT: %s\", dlerror());\n"
     "      return false;\n"
     "   }\n"
     "   void (*initialize)(int) = (void (*)(int))dlsym(lib, \"hybris_gralloc_initialize\");\n"
     "   pan_gralloc.allocate = dlsym(lib, \"hybris_gralloc_allocate\");\n"
     "   pan_gralloc.release = dlsym(lib, \"hybris_gralloc_release\");\n"
     "   if (!initialize || !pan_gralloc.allocate || !pan_gralloc.release) {\n"
     "      pan_gralloc.allocate = NULL;\n"
     "      return false;\n"
     "   }\n"
     "   initialize(0);\n"
     "   return true;\n"
     "}\n"
     "\n"
     "/* Give a fresh 2D RGBA8/RGBX8 resource a gralloc buffer as backing, so that its dma-buf\n"
     " * export carries the gralloc handle and libhybris can hand it to the Android driver.\n"
     " * Only when PAN_GRALLOC_EXPORT is set and nothing was written yet (no copy needed). */\n"
     "static bool\n"
     "pan_gralloc_attach(struct pipe_screen *pscreen, struct panfrost_resource *rsrc)\n"
     "{\n"
     "   static int enabled = -1;\n"
     "\n"
     "   if (rsrc->gralloc)\n"
     "      return true;\n"
     "   if (enabled < 0)\n"
     "      enabled = debug_get_bool_option(\"PAN_GRALLOC_EXPORT\", false);\n"
     "   if (!enabled)\n"
     "      return false;\n"
     "\n"
     "   const struct pipe_resource *b = &rsrc->base;\n"
     "   int hal_format;\n"
     "   if (b->format == PIPE_FORMAT_R8G8B8A8_UNORM)\n"
     "      hal_format = 1; /* HAL_PIXEL_FORMAT_RGBA_8888 */\n"
     "   else if (b->format == PIPE_FORMAT_R8G8B8X8_UNORM)\n"
     "      hal_format = 2; /* HAL_PIXEL_FORMAT_RGBX_8888 */\n"
     "   else\n"
     "      return false;\n"
     "   if ((b->target != PIPE_TEXTURE_2D && b->target != PIPE_TEXTURE_RECT) ||\n"
     "       b->last_level || b->array_size > 1 || b->nr_samples > 1 || b->next ||\n"
     "       BITSET_TEST(rsrc->valid.data, 0) || !pan_gralloc_load())\n"
     "      return false;\n"
     "\n"
     "   /* HW_TEXTURE | HW_RENDER | SW_READ_RARELY, linear on Mali gralloc */\n"
     "   const struct pan_gralloc_native_handle *h = NULL;\n"
     "   uint32_t stride_px = 0;\n"
     "   if (pan_gralloc.allocate(b->width0, b->height0, hal_format, 0x302, &h, &stride_px) || !h ||\n"
     "       h->numFds < 1) {\n"
     "      mesa_loge(\"panfrost: gralloc allocation %ux%u failed\", b->width0, b->height0);\n"
     "      return false;\n"
     "   }\n"
     "\n"
     "   struct pipe_resource tmpl = *b;\n"
     "   tmpl.next = NULL;\n"
     "   tmpl.bind |= PIPE_BIND_SHARED;\n"
     "   struct winsys_handle whandle = {\n"
     "      .type = WINSYS_HANDLE_TYPE_FD,\n"
     "      .handle = h->data[0],\n"
     "      .stride = stride_px * 4,\n"
     "      .offset = 0,\n"
     "      .modifier = DRM_FORMAT_MOD_LINEAR,\n"
     "   };\n"
     "   struct pipe_resource *tmp_prsrc =\n"
     "      panfrost_resource_from_handle(pscreen, &tmpl, &whandle, 0);\n"
     "   int meta_fd = memfd_create(\"pan-gralloc-meta\", MFD_CLOEXEC);\n"
     "   struct pan_gralloc_backing *g = calloc(1, sizeof(*g));\n"
     "   int header[4] = {-1, h->version, h->numFds, h->numInts};\n"
     "   size_t ints_size = h->numInts * sizeof(int);\n"
     "   if (!tmp_prsrc || meta_fd < 0 || !g ||\n"
     "       write(meta_fd, header, sizeof(header)) != sizeof(header) ||\n"
     "       write(meta_fd, &h->data[h->numFds], ints_size) != (ssize_t)ints_size) {\n"
     "      mesa_loge(\"panfrost: gralloc buffer import failed\");\n"
     "      if (tmp_prsrc)\n"
     "         pipe_resource_reference(&tmp_prsrc, NULL);\n"
     "      if (meta_fd >= 0)\n"
     "         close(meta_fd);\n"
     "      free(g);\n"
     "      pan_gralloc.release(h, 1);\n"
     "      return false;\n"
     "   }\n"
     "   struct panfrost_resource *tmp = pan_resource(tmp_prsrc);\n"
     "\n"
     "   /* Same swap as pan_resource_modifier_convert(), with the imported gralloc BO. */\n"
     "   pan_resource_afbcp_stop(rsrc);\n"
     "   if (rsrc->owns_label) {\n"
     "      char *old_label = (char *)panfrost_bo_replace_label(rsrc->bo, \"Disposed for gralloc BO\", false);\n"
     "      free(old_label);\n"
     "   }\n"
     "   panfrost_bo_unreference(rsrc->bo);\n"
     "   rsrc->bo = tmp->bo;\n"
     "   panfrost_bo_reference(rsrc->bo);\n"
     "   rsrc->owns_label = false;\n"
     "   rsrc->image = tmp->image;\n"
     "   rsrc->plane = tmp->plane;\n"
     "   rsrc->image.planes[0] = &rsrc->plane;\n"
     "   rsrc->plane.base = rsrc->bo->ptr.gpu;\n"
     "   pan_crc_state_set_ptr(&rsrc->crc_state, &rsrc->bo->ptr);\n"
     "   rsrc->modifier = DRM_FORMAT_MOD_LINEAR;\n"
     "   rsrc->modifier_constant = true;\n"
     "   pipe_resource_reference(&tmp_prsrc, NULL);\n"
     "\n"
     "   g->handle = h;\n"
     "   g->meta_fd = meta_fd;\n"
     "   rsrc->gralloc = g;\n"
     "   return true;\n"
     "}\n"
     "\n"
     "/* Planes of a gralloc-backed export: 0..numFds-1 the handle fds, numFds the meta memfd. */\n"
     "static int\n"
     "pan_gralloc_plane_fd(const struct pan_gralloc_backing *g, unsigned plane)\n"
     "{\n"
     "   if (plane < (unsigned)g->handle->numFds)\n"
     "      return g->handle->data[plane];\n"
     "   return plane == (unsigned)g->handle->numFds ? g->meta_fd : -1;\n"
     "}\n"
     "\n"
     "static bool\npanfrost_resource_get_handle(struct pipe_screen *pscreen,\n"),
    ("   struct renderonly_scanout *scanout;\n\n   if (handle->plane >= ARRAY_SIZE(rsrc->image.planes) ||",
     "   struct renderonly_scanout *scanout;\n"
     "\n"
     "   if (handle->type == WINSYS_HANDLE_TYPE_FD && pan_gralloc_attach(pscreen, rsrc)) {\n"
     "      int fd = pan_gralloc_plane_fd(rsrc->gralloc, handle->plane);\n"
     "      if (fd < 0 || (fd = os_dupfd_cloexec(fd)) < 0)\n"
     "         return false;\n"
     "      handle->handle = fd;\n"
     "      handle->modifier = DRM_FORMAT_MOD_LINEAR;\n"
     "      handle->stride = handle->plane ? 0 : pan_image_get_wsi_row_pitch(&rsrc->image, 0, 0);\n"
     "      handle->offset = handle->plane ? 0 : pan_image_get_wsi_offset(&rsrc->image, 0, 0);\n"
     "      return true;\n"
     "   }\n"
     "\n"
     "   if (handle->plane >= ARRAY_SIZE(rsrc->image.planes) ||"),
    ("   struct panfrost_resource *rsrc =\n      pan_resource(util_resource_at_index(prsc, plane));\n",
     "   if (pan_gralloc_attach(pscreen, pan_resource(prsc))) {\n"
     "      const struct pan_gralloc_backing *g = pan_resource(prsc)->gralloc;\n"
     "      switch (param) {\n"
     "      case PIPE_RESOURCE_PARAM_NPLANES:\n"
     "         *value = g->handle->numFds + 1;\n"
     "         return true;\n"
     "      case PIPE_RESOURCE_PARAM_DISJOINT_PLANES:\n"
     "         *value = 1;\n"
     "         return true;\n"
     "      case PIPE_RESOURCE_PARAM_MODIFIER:\n"
     "         *value = DRM_FORMAT_MOD_LINEAR;\n"
     "         return true;\n"
     "      case PIPE_RESOURCE_PARAM_STRIDE:\n"
     "      case PIPE_RESOURCE_PARAM_OFFSET:\n"
     "         if (plane > 0) {\n"
     "            *value = 0;\n"
     "            return true;\n"
     "         }\n"
     "         break;\n"
     "      default:\n"
     "         if (plane > 0)\n"
     "            return false;\n"
     "         break;\n"
     "      }\n"
     "   }\n"
     "\n"
     "   struct panfrost_resource *rsrc =\n      pan_resource(util_resource_at_index(prsc, plane));\n"),
])
