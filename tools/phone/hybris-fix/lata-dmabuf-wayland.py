#!/usr/bin/env python3
# Import dma-buf (EGL_LINUX_DMA_BUF_EXT) w platformie Wayland libhybris.
#
# Po co: okno GTK na libhybris (Mali) ma wyswietlac klatke narysowana przez
# Mese Panfrost w innym procesie, bez kopiowania przez CPU. Mesa (lata
# lata-gralloc-eksport.py w tools/phone/panfrost-kbase) podklada pod eksportowana
# teksture bufor z gralloc Androida i eksportuje go jako dma-buf z dodatkowymi
# plaszczyznami: fd-y uchwytu gralloc, a na koncu memfd z naglowkiem
# {-1, version, numFds, numInts} i intami uchwytu. To ta sama konwencja, co
# w platformie lindroid_drm Droidiana (lindroid_drmws_passthroughImageKHR):
# z plaszczyzn skladamy native_handle, hybris_gralloc_import_buffer, i obraz
# idzie do sterownika Mali jako EGL_NATIVE_BUFFER_ANDROID.
#
# GTK 4.22 importuje dma-buf tylko, gdy wyswietlacz EGL ma
# EGL_EXT_image_dma_buf_import_modifiers i eglQueryDmaBufFormatsEXT zwraca
# format (gdkdisplay.c, gdkdmabufegl.c), wiec dokladamy tez te dwie rzeczy.
# Bufor bez naglowka gralloc zostaje nietkniety (sterownik go odrzuci jak dotad).
# Uzycie: python3 lata-dmabuf-wayland.py <plik eglplatform_wayland.cpp>
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "waylandws_import_gralloc_dmabuf" in s:
    print("juz nalozona:", p)
    sys.exit(0)

zmiany = [
    ('#include "wayland_window.h"\n',
     '#include "wayland_window.h"\n'
     '#include "windowbuffer.h"\n'
     '#include <cutils/native_handle.h>\n'),
    ("extern \"C\" void waylandws_passthroughImageKHR(EGLContext *ctx, EGLenum *target, EGLClientBuffer *buffer, const EGLint **attrib_list)\n"
     "{\n"
     "\teglplatformcommon_passthroughImageKHR(ctx, target, buffer, attrib_list);\n"
     "}\n",
     "#define WS_FOURCC(a, b, c, d) ((EGLint)(a) | ((EGLint)(b) << 8) | ((EGLint)(c) << 16) | ((EGLint)(d) << 24))\n"
     "static const EGLint waylandws_dmabuf_formats[] = {\n"
     "\tWS_FOURCC('A', 'B', '2', '4'), /* ABGR8888: bajty R,G,B,A = HAL RGBA_8888 */\n"
     "\tWS_FOURCC('X', 'B', '2', '4'), /* XBGR8888 = HAL RGBX_8888 */\n"
     "};\n"
     "\n"
     "/* dma-buf with the gralloc handle appended as extra planes (last plane: memfd with\n"
     " * {-1, version, numFds, numInts} and the ints), as exported by Mesa panfrost with\n"
     " * PAN_GRALLOC_EXPORT. Returns true when the image was converted to a native buffer. */\n"
     "static bool waylandws_import_gralloc_dmabuf(EGLContext *ctx, EGLenum *target, EGLClientBuffer *buffer, const EGLint **attrib_list)\n"
     "{\n"
     "\tint width = 0, height = 0, format = 0, pitch = 0;\n"
     "\tint plane_fds[4] = { -1, -1, -1, -1 };\n"
     "\n"
     "\tfor (const EGLint *attr = *attrib_list; attr && *attr != EGL_NONE; attr += 2) {\n"
     "\t\tswitch (attr[0]) {\n"
     "\t\tcase EGL_DMA_BUF_PLANE0_FD_EXT: plane_fds[0] = attr[1]; break;\n"
     "\t\tcase EGL_DMA_BUF_PLANE1_FD_EXT: plane_fds[1] = attr[1]; break;\n"
     "\t\tcase EGL_DMA_BUF_PLANE2_FD_EXT: plane_fds[2] = attr[1]; break;\n"
     "\t\tcase EGL_DMA_BUF_PLANE3_FD_EXT: plane_fds[3] = attr[1]; break;\n"
     "\t\tcase EGL_WIDTH: width = attr[1]; break;\n"
     "\t\tcase EGL_HEIGHT: height = attr[1]; break;\n"
     "\t\tcase EGL_LINUX_DRM_FOURCC_EXT: format = attr[1]; break;\n"
     "\t\tcase EGL_DMA_BUF_PLANE0_PITCH_EXT: pitch = attr[1]; break;\n"
     "\t\tdefault: break;\n"
     "\t\t}\n"
     "\t}\n"
     "\n"
     "\tint num_planes = 0;\n"
     "\twhile (num_planes < 4 && plane_fds[num_planes] >= 0)\n"
     "\t\tnum_planes++;\n"
     "\tif (num_planes < 2 || !width || !height || !format || !pitch)\n"
     "\t\treturn false;\n"
     "\n"
     "\tint meta_fd = plane_fds[num_planes - 1];\n"
     "\tint header[4];\n"
     "\tif (pread(meta_fd, header, sizeof(header), 0) != (ssize_t)sizeof(header))\n"
     "\t\treturn false;\n"
     "\tint version = header[1], numFds = header[2], numInts = header[3];\n"
     "\tif (header[0] != -1 || numFds != num_planes - 1 || numInts <= 0 || numInts > 1024)\n"
     "\t\treturn false;\n"
     "\n"
     "\tint *ints = (int *)malloc(numInts * sizeof(int));\n"
     "\tif (!ints)\n"
     "\t\treturn false;\n"
     "\tif (pread(meta_fd, ints, numInts * sizeof(int), sizeof(header)) != (ssize_t)(numInts * sizeof(int))) {\n"
     "\t\tfree(ints);\n"
     "\t\treturn false;\n"
     "\t}\n"
     "\n"
     "\tnative_handle_t *nh = native_handle_create(numFds, numInts);\n"
     "\tnh->version = version;\n"
     "\tfor (int i = 0; i < numFds; i++)\n"
     "\t\tnh->data[i] = plane_fds[i];\n"
     "\tfor (int i = 0; i < numInts; i++)\n"
     "\t\tnh->data[numFds + i] = ints[i];\n"
     "\tfree(ints);\n"
     "\n"
     "\t/* import dups the fds, the caller keeps its own */\n"
     "\tbuffer_handle_t out_handle = NULL;\n"
     "\tint ret = hybris_gralloc_import_buffer(nh, &out_handle);\n"
     "\tnative_handle_delete(nh);\n"
     "\tif (ret != 0 || !out_handle) {\n"
     "\t\tHYBRIS_ERROR(\"gralloc import of a dma-buf image failed: %d\", ret);\n"
     "\t\treturn false;\n"
     "\t}\n"
     "\n"
     "\tint hal_format = format == waylandws_dmabuf_formats[1] ? HAL_PIXEL_FORMAT_RGBX_8888 : HAL_PIXEL_FORMAT_RGBA_8888;\n"
     "\tRemoteWindowBuffer *buf = new RemoteWindowBuffer(width, height, pitch / 4, hal_format,\n"
     "\t\tGRALLOC_USAGE_HW_TEXTURE | GRALLOC_USAGE_HW_RENDER, out_handle);\n"
     "\tbuf->common.incRef(&buf->common);\n"
     "\n"
     "\t*buffer = (EGLClientBuffer) static_cast<ANativeWindowBuffer *>(buf);\n"
     "\t*attrib_list = NULL;\n"
     "\t*ctx = EGL_NO_CONTEXT;\n"
     "\t*target = EGL_NATIVE_BUFFER_ANDROID;\n"
     "\treturn true;\n"
     "}\n"
     "\n"
     "extern \"C\" void waylandws_passthroughImageKHR(EGLContext *ctx, EGLenum *target, EGLClientBuffer *buffer, const EGLint **attrib_list)\n"
     "{\n"
     "\tif (*target == EGL_LINUX_DMA_BUF_EXT && waylandws_import_gralloc_dmabuf(ctx, target, buffer, attrib_list))\n"
     "\t\treturn;\n"
     "\teglplatformcommon_passthroughImageKHR(ctx, target, buffer, attrib_list);\n"
     "}\n"
     "\n"
     "extern \"C\" void waylandws_destroyImageKHR(EGLImageKHR image)\n"
     "{\n"
     "\tstruct egl_image *img = (struct egl_image *)image;\n"
     "\t/* only the dma-buf imports own their buffer; wayland buffers belong to the server */\n"
     "\tif (!img || img->target != EGL_LINUX_DMA_BUF_EXT || !img->ws_buffer)\n"
     "\t\treturn;\n"
     "\tANativeWindowBuffer *buf = (ANativeWindowBuffer *)img->ws_buffer;\n"
     "\timg->ws_buffer = NULL;\n"
     "\tbuf->common.decRef(&buf->common);\n"
     "}\n"
     "\n"
     "extern \"C\" EGLBoolean waylandws_queryDmaBufFormatsEXT(EGLDisplay dpy, EGLint max_formats, EGLint *formats, EGLint *num_formats)\n"
     "{\n"
     "\tconst EGLint n = sizeof(waylandws_dmabuf_formats) / sizeof(waylandws_dmabuf_formats[0]);\n"
     "\tif (max_formats < 0 || !num_formats)\n"
     "\t\treturn EGL_FALSE;\n"
     "\t*num_formats = n;\n"
     "\tif (max_formats == 0)\n"
     "\t\treturn EGL_TRUE;\n"
     "\tif (!formats)\n"
     "\t\treturn EGL_FALSE;\n"
     "\t*num_formats = max_formats < n ? max_formats : n;\n"
     "\tfor (EGLint i = 0; i < *num_formats; i++)\n"
     "\t\tformats[i] = waylandws_dmabuf_formats[i];\n"
     "\treturn EGL_TRUE;\n"
     "}\n"
     "\n"
     "extern \"C\" EGLBoolean waylandws_queryDmaBufModifiersEXT(EGLDisplay dpy, EGLint format, EGLint max_modifiers, EGLuint64KHR *modifiers, EGLBoolean *external_only, EGLint *num_modifiers)\n"
     "{\n"
     "\tif (max_modifiers < 0 || !num_modifiers)\n"
     "\t\treturn EGL_FALSE;\n"
     "\t*num_modifiers = 1;\n"
     "\tif (max_modifiers == 0)\n"
     "\t\treturn EGL_TRUE;\n"
     "\tif (!modifiers)\n"
     "\t\treturn EGL_FALSE;\n"
     "\tmodifiers[0] = 0; /* DRM_FORMAT_MOD_LINEAR */\n"
     "\tif (external_only)\n"
     "\t\texternal_only[0] = EGL_FALSE;\n"
     "\treturn EGL_TRUE;\n"
     "}\n"),
    ('\t\t\t"EGL_EXT_swap_buffers_with_damage EGL_WL_create_wayland_buffer_from_image"\n',
     '\t\t\t"EGL_EXT_swap_buffers_with_damage EGL_WL_create_wayland_buffer_from_image"\n'
     '\t\t\t" EGL_EXT_image_dma_buf_import EGL_EXT_image_dma_buf_import_modifiers"\n'),
    ("\twaylandws_eglInitialized,\n};",
     "\twaylandws_eglInitialized,\n"
     "\twaylandws_destroyImageKHR,\n"
     "\tNULL,\n"
     "\twaylandws_queryDmaBufFormatsEXT,\n"
     "\twaylandws_queryDmaBufModifiersEXT,\n"
     "};"),
]
for a, b in zmiany:
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b, 1)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("lata nalozona:", p)
