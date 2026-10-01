#!/usr/bin/env python3
# Laty libhybris (Droidian, galaz feature/next/lindroid-drm, commit 91f805b),
# hybris/egl/egl.c. W trybie Wayland aplikacja dostaje OPAKOWANY EGLDisplay
# (struct _EGLDisplay), a libhybris odpakowuje go tylko w funkcjach z tabeli
# _eglHybrisOverrideFunctions. Dwa bledy (zmierzone 30.09.2026 testem eglattr.c):
# 1. eglGetConfigAttrib podaje Androidowi opakowanie -> zawsze EGL_BAD_DISPLAY,
#    wiec Firefox nie wybiera konfiguracji ("Failed to create EGLConfig for
#    WebRender!") i rysuje programowo, a Qt widzi format 0/0/0/0.
# 2. Funkcje synchronizacji (EGL_KHR_fence_sync, EGL_ANDROID_native_fence_sync,
#    rdzen EGL 1.5) nie sa w tabeli, wiec ida do Androida z opakowaniem ->
#    EGL_BAD_DISPLAY ("eglCreateSync failed with 0x3008" w Chromium/ANGLE).
# Uzycie: python3 lata-egl.py <sciezka do hybris/egl/egl.c>
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, a[:80]
    s = s.replace(a, b, 1)


rep("\tret = (*_eglGetConfigAttrib)(dpy, config, attribute, value);",
    "\tret = (*_eglGetConfigAttrib)(hybris_egl_get_real_display(dpy), config, attribute, value);")

SYNC = r'''
/* Fence sync: unwrap the display before calling Android EGL. */
static EGLSyncKHR (*_eglCreateSyncKHR)(EGLDisplay, EGLenum, const EGLint *) = NULL;
static EGLBoolean (*_eglDestroySyncKHR)(EGLDisplay, EGLSyncKHR) = NULL;
static EGLint (*_eglClientWaitSyncKHR)(EGLDisplay, EGLSyncKHR, EGLint, EGLTimeKHR) = NULL;
static EGLBoolean (*_eglGetSyncAttribKHR)(EGLDisplay, EGLSyncKHR, EGLint, EGLint *) = NULL;
static EGLint (*_eglWaitSyncKHR)(EGLDisplay, EGLSyncKHR, EGLint) = NULL;
static EGLBoolean (*_eglSignalSyncKHR)(EGLDisplay, EGLSyncKHR, EGLenum) = NULL;
static EGLint (*_eglDupNativeFenceFDANDROID)(EGLDisplay, EGLSyncKHR) = NULL;

static EGLSyncKHR _my_eglCreateSyncKHR(EGLDisplay dpy, EGLenum type, const EGLint *attrib_list)
{
	HYBRIS_DLSYSM(egl, &_eglCreateSyncKHR, "eglCreateSyncKHR");
	if (!_eglCreateSyncKHR) return EGL_NO_SYNC_KHR;
	return (*_eglCreateSyncKHR)(hybris_egl_get_real_display(dpy), type, attrib_list);
}

static EGLBoolean _my_eglDestroySyncKHR(EGLDisplay dpy, EGLSyncKHR sync)
{
	HYBRIS_DLSYSM(egl, &_eglDestroySyncKHR, "eglDestroySyncKHR");
	if (!_eglDestroySyncKHR) return EGL_FALSE;
	return (*_eglDestroySyncKHR)(hybris_egl_get_real_display(dpy), sync);
}

static EGLint _my_eglClientWaitSyncKHR(EGLDisplay dpy, EGLSyncKHR sync, EGLint flags, EGLTimeKHR timeout)
{
	HYBRIS_DLSYSM(egl, &_eglClientWaitSyncKHR, "eglClientWaitSyncKHR");
	if (!_eglClientWaitSyncKHR) return EGL_FALSE;
	return (*_eglClientWaitSyncKHR)(hybris_egl_get_real_display(dpy), sync, flags, timeout);
}

static EGLBoolean _my_eglGetSyncAttribKHR(EGLDisplay dpy, EGLSyncKHR sync, EGLint attribute, EGLint *value)
{
	HYBRIS_DLSYSM(egl, &_eglGetSyncAttribKHR, "eglGetSyncAttribKHR");
	if (!_eglGetSyncAttribKHR) return EGL_FALSE;
	return (*_eglGetSyncAttribKHR)(hybris_egl_get_real_display(dpy), sync, attribute, value);
}

static EGLint _my_eglWaitSyncKHR(EGLDisplay dpy, EGLSyncKHR sync, EGLint flags)
{
	HYBRIS_DLSYSM(egl, &_eglWaitSyncKHR, "eglWaitSyncKHR");
	if (!_eglWaitSyncKHR) return EGL_FALSE;
	return (*_eglWaitSyncKHR)(hybris_egl_get_real_display(dpy), sync, flags);
}

static EGLBoolean _my_eglSignalSyncKHR(EGLDisplay dpy, EGLSyncKHR sync, EGLenum mode)
{
	HYBRIS_DLSYSM(egl, &_eglSignalSyncKHR, "eglSignalSyncKHR");
	if (!_eglSignalSyncKHR) return EGL_FALSE;
	return (*_eglSignalSyncKHR)(hybris_egl_get_real_display(dpy), sync, mode);
}

static EGLint _my_eglDupNativeFenceFDANDROID(EGLDisplay dpy, EGLSyncKHR sync)
{
	HYBRIS_DLSYSM(egl, &_eglDupNativeFenceFDANDROID, "eglDupNativeFenceFDANDROID");
	if (!_eglDupNativeFenceFDANDROID) return EGL_NO_NATIVE_FENCE_FD_ANDROID;
	return (*_eglDupNativeFenceFDANDROID)(hybris_egl_get_real_display(dpy), sync);
}

/* EGL 1.5 core sync on top of the KHR entry points (attribute lists are
 * EGLAttrib there, EGLint in KHR). */
static EGLSyncKHR _my_eglCreateSync(EGLDisplay dpy, EGLenum type, const EGLAttrib *attrib_list)
{
	EGLint attrs[64];
	int n = 0;
	if (attrib_list) {
		while (attrib_list[n] != EGL_NONE && n < 62) {
			attrs[n] = (EGLint)attrib_list[n];
			attrs[n + 1] = (EGLint)attrib_list[n + 1];
			n += 2;
		}
	}
	attrs[n] = EGL_NONE;
	return _my_eglCreateSyncKHR(dpy, type, attrs);
}

static EGLBoolean _my_eglGetSyncAttrib(EGLDisplay dpy, EGLSyncKHR sync, EGLint attribute, EGLAttrib *value)
{
	EGLint v = 0;
	EGLBoolean ret = _my_eglGetSyncAttribKHR(dpy, sync, attribute, &v);
	if (ret && value) *value = v;
	return ret;
}

static EGLBoolean _my_eglWaitSync(EGLDisplay dpy, EGLSyncKHR sync, EGLint flags)
{
	return _my_eglWaitSyncKHR(dpy, sync, flags) == EGL_TRUE;
}

struct FuncNamePair {'''
rep("\nstruct FuncNamePair {", SYNC)

rep("\tOVERRIDE_MY(eglDestroyImageKHR),\n",
    "\tOVERRIDE_MY(eglDestroyImageKHR),\n"
    "\tOVERRIDE_MY(eglCreateSyncKHR),\n"
    "\tOVERRIDE_MY(eglDestroySyncKHR),\n"
    "\tOVERRIDE_MY(eglClientWaitSyncKHR),\n"
    "\tOVERRIDE_MY(eglGetSyncAttribKHR),\n"
    "\tOVERRIDE_MY(eglWaitSyncKHR),\n"
    "\tOVERRIDE_MY(eglSignalSyncKHR),\n"
    "\tOVERRIDE_MY(eglDupNativeFenceFDANDROID),\n"
    "\tOVERRIDE_MY(eglCreateSync),\n"
    "\tOVERRIDE_TO(eglDestroySync, _my_eglDestroySyncKHR),\n"
    "\tOVERRIDE_TO(eglClientWaitSync, _my_eglClientWaitSyncKHR),\n"
    "\tOVERRIDE_MY(eglGetSyncAttrib),\n"
    "\tOVERRIDE_MY(eglWaitSync),\n")

# 3. Platforma EGL_MESA_platform_surfaceless (0x31DD): WebKitGTK otwiera nia EGL
#    w procesie tresci (renderer z pamiecia wspoldzielona). Bez obslugi glvnd
#    oddaje ja Mesie i strona rysuje sie programowo (libgallium, brak /dev/mali0).
#    Na Androidzie to zwykly wyswietlacz natywny bez okna: modul "null".
# 4. Platforma GBM tylko przy urzadzeniu lindroid (evdi). Bez niego modul
#    lindroid-drm nie ma czego otworzyc, a pierwsze wywolanie przypina caly proces
#    do tego modulu (ws_init laduje jeden modul na proces). WebKit w oknie probuje
#    GBM, gdy zna urzadzenie DRM (okno.c podaje atrape dla klatek bez kopii), i bez
#    tego proces okna padal na asercji w ws_init.
rep("""		case EGL_PLATFORM_GBM_KHR:
			hybris_ws = "lindroid-drm";
			break;
""", """		case EGL_PLATFORM_GBM_KHR:
			if (access("/dev/dri/by-path/platform-evdi-lindroid.0-card", F_OK) != 0) {
				__eglHybrisSetError(EGL_BAD_PARAMETER);
				return EGL_NO_DISPLAY;
			}
			hybris_ws = "lindroid-drm";
			break;

		case 0x31DD: /* EGL_PLATFORM_SURFACELESS_MESA */
			/* opt-in: by default surfaceless is left to the next glvnd
			 * vendor (Mesa Panfrost on kbase draws it correctly, the
			 * Android blob gave a grey WebKit view) */
			if (!getenv("HYBRIS_EGL_SURFACELESS")) {
				__eglHybrisSetError(EGL_BAD_PARAMETER);
				return EGL_NO_DISPLAY;
			}
			hybris_ws = "null";
			break;
""")

open(p, "w", encoding="utf-8").write(s)
print("lata nalozona:", p)

# Modul glvnd musi zglosic platforme, inaczej glvnd nie zapyta o nia libhybris.
g = p.replace("egl.c", "glvnd/eglglvnd.cpp")
t = open(g, encoding="utf-8").read()
a = """    if (name == __EGL_VENDOR_STRING_PLATFORM_EXTENSIONS) {
        return
"""
assert t.count(a) == 1
t = t.replace(a, """    if (name == __EGL_VENDOR_STRING_PLATFORM_EXTENSIONS && getenv("HYBRIS_EGL_SURFACELESS")) {
        return
            "EGL_KHR_platform_android EGL_MESA_platform_surfaceless"
#ifdef WANT_WAYLAND
            " EGL_EXT_platform_wayland EGL_KHR_platform_wayland"
#endif
            ;
    }
    if (name == __EGL_VENDOR_STRING_PLATFORM_EXTENSIONS) {
        return
""", 1)
open(g, "w", encoding="utf-8").write(t)
print("lata nalozona:", g)
