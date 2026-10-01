#!/usr/bin/env python3
# Diagnostyka: MESA_EGL_NO_NATIVE_FENCE=1 ukrywa EGL_ANDROID_native_fence_sync.
# WebKit (RenderTargetShareableBuffer::sync) eksportuje plotek renderowania jako
# sync_file i okno czeka na jego sygnal; bez rozszerzenia robi glFinish-owy
# clientWait po stronie procesu tresci i wysyla klatke bez plotka.
# Uzycie: python3 lata-bez-plotka.py <mali-panfrost>/src/egl/drivers/dri2/egl_dri2.c
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
a = """   if (dri_fence_get_caps(dri2_dpy->dri_screen_render_gpu)
      & __DRI_FENCE_CAP_NATIVE_FD)
      disp->Extensions.ANDROID_native_fence_sync = EGL_TRUE;"""
b = """   if ((dri_fence_get_caps(dri2_dpy->dri_screen_render_gpu)
      & __DRI_FENCE_CAP_NATIVE_FD) && !getenv("MESA_EGL_NO_NATIVE_FENCE"))
      disp->Extensions.ANDROID_native_fence_sync = EGL_TRUE;"""
if b in s:
    print("juz nalozona")
    sys.exit(0)
assert s.count(a) == 1
s = s.replace(a, b, 1)
if "#include <stdlib.h>" not in s:
    s = "#include <stdlib.h>\n" + s
open(p, "w", encoding="utf-8").write(s)
print("lata nalozona:", p)
