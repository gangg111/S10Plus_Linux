// LD_PRELOAD for the Galaxy S10+ (Droidian, libhybris): make eglChooseConfig
// ask for 8 bits per colour channel when the program left the colour sizes
// unset or below 8.  Otherwise the Android EGL hands out RGB_565 configs first
// and Qt takes them, so every transparent part of a window is drawn black
// (seen as a black full-screen maliit keyboard panel and a black status bar).
// Plain C, no Qt, so it is safe to preload into any process.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <EGL/egl.h>

typedef EGLBoolean (*choose_fn)(EGLDisplay, const EGLint *, EGLConfig *, EGLint, EGLint *);

EGLBoolean eglChooseConfig(EGLDisplay dpy, const EGLint *attrib_list, EGLConfig *configs,
                           EGLint config_size, EGLint *num_config)
{
    static choose_fn real;
    if (!real)
        real = (choose_fn)dlsym(RTLD_NEXT, "eglChooseConfig");

    // Alpha too: programs such as maliit-keyboard draw a transparent window
    // without asking for alpha (Mesa gives it anyway), and got RGBX_8888.
    EGLint attrs[128];
    int n = 0, have_r = 0, have_g = 0, have_b = 0, have_a = 0;
    if (attrib_list) {
        for (int i = 0; attrib_list[i] != EGL_NONE && n < 118; i += 2) {
            EGLint key = attrib_list[i], val = attrib_list[i + 1];
            if (key == EGL_RED_SIZE || key == EGL_GREEN_SIZE || key == EGL_BLUE_SIZE || key == EGL_ALPHA_SIZE) {
                if (val < 8)
                    val = 8;
                have_r |= key == EGL_RED_SIZE;
                have_g |= key == EGL_GREEN_SIZE;
                have_b |= key == EGL_BLUE_SIZE;
                have_a |= key == EGL_ALPHA_SIZE;
            }
            attrs[n++] = key;
            attrs[n++] = val;
        }
    }
    if (!have_r) { attrs[n++] = EGL_RED_SIZE; attrs[n++] = 8; }
    if (!have_g) { attrs[n++] = EGL_GREEN_SIZE; attrs[n++] = 8; }
    if (!have_b) { attrs[n++] = EGL_BLUE_SIZE; attrs[n++] = 8; }
    if (!have_a) { attrs[n++] = EGL_ALPHA_SIZE; attrs[n++] = 8; }
    attrs[n] = EGL_NONE;

    EGLBoolean ok = real(dpy, attrs, configs, config_size, num_config);
    if (ok && num_config && *num_config > 0)
        return ok;
    // nothing with 8 bits per channel: fall back to what was asked
    return real(dpy, attrib_list, configs, config_size, num_config);
}
