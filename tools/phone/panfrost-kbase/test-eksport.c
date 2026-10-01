// Sprawdza lata-gralloc-eksport.py tak, jak uzywa jej WebKit (RenderTargetTexture):
// tekstura GL_RGBA -> obraz EGL -> eglExportDMABUFImageQueryMESA/MESA. Z plaszczyzn
// eksportu sklada uchwyt gralloc wedlug konwencji libhybris (lata-dmabuf-wayland.py),
// importuje go i czyta piksele przez blokade gralloc (sciezka Androida, bez Panfrosta).
// cc -O2 test-eksport.c -o test-eksport $(pkg-config --cflags --libs libgralloc) -lEGL -lGLESv2
// Uruchamiac z PAN_GRALLOC_EXPORT=1, LD_PRELOAD=libtls-padding.so i glvnd na Mesie.
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <hybris/gralloc/gralloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define W 1440
#define H 2838

int main(void)
{
	EGLDisplay dpy = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	eglInitialize(dpy, NULL, NULL);
	eglBindAPI(EGL_OPENGL_ES_API);
	const EGLint ca[] = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ca);
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx);
	printf("renderer: %s\n", glGetString(GL_RENDERER));

	GLuint tex;
	glGenTextures(1, &tex);
	glBindTexture(GL_TEXTURE_2D, tex);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, W, H, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);

	PFNEGLCREATEIMAGEKHRPROC createImage = (PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
	PFNEGLEXPORTDMABUFIMAGEQUERYMESAPROC query =
		(PFNEGLEXPORTDMABUFIMAGEQUERYMESAPROC)eglGetProcAddress("eglExportDMABUFImageQueryMESA");
	PFNEGLEXPORTDMABUFIMAGEMESAPROC eksport = (PFNEGLEXPORTDMABUFIMAGEMESAPROC)eglGetProcAddress("eglExportDMABUFImageMESA");
	EGLImageKHR img = createImage(dpy, ctx, EGL_GL_TEXTURE_2D_KHR, (EGLClientBuffer)(uintptr_t)tex, NULL);
	int fourcc = 0, nplanes = 0;
	EGLuint64KHR mods[4] = { 0 };
	if (!img || !query(dpy, img, &fourcc, &nplanes, mods) || nplanes < 1 || nplanes > 4) {
		printf("zapytanie o eksport nie powiodlo sie (img=%p nplanes=%d)\n", img, nplanes);
		return 1;
	}
	int fds[4] = { -1, -1, -1, -1 }, strides[4] = { 0 }, offsets[4] = { 0 };
	if (!eksport(dpy, img, fds, strides, offsets)) {
		printf("eksport nie powiodl sie\n");
		return 1;
	}
	printf("eksport: fourcc %.4s, plaszczyzn %d, modifier %#llx\n", (char *)&fourcc, nplanes,
	       (unsigned long long)mods[0]);
	for (int i = 0; i < nplanes; i++) {
		off_t rozmiar = lseek(fds[i], 0, SEEK_END);
		printf("  plaszczyzna %d: fd %d, stride %d, offset %d, rozmiar %ld\n", i, fds[i], strides[i], offsets[i],
		       (long)rozmiar);
	}
	if (nplanes < 2) {
		printf("WYNIK: brak plaszczyzn gralloc (czy PAN_GRALLOC_EXPORT=1?)\n");
		return 2;
	}

	// rysowanie do tekstury: pomaranczowe tlo, niebieski dolny lewy kwadrat w GL
	GLuint fbo;
	glGenFramebuffers(1, &fbo);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0);
	glViewport(0, 0, W, H);
	glClearColor(1.0f, 0.5f, 0.0f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	glEnable(GL_SCISSOR_TEST);
	glScissor(0, 0, W / 2, H / 2);
	glClearColor(0.0f, 0.0f, 1.0f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	glFinish();

	// uchwyt gralloc z plaszczyzn, jak w libhybris
	int meta = fds[nplanes - 1], naglowek[4];
	if (pread(meta, naglowek, sizeof(naglowek), 0) != sizeof(naglowek) || naglowek[0] != -1 ||
	    naglowek[2] != nplanes - 1) {
		printf("WYNIK: zly naglowek memfd\n");
		return 3;
	}
	native_handle_t *nh = native_handle_create(naglowek[2], naglowek[3]);
	nh->version = naglowek[1];
	for (int i = 0; i < naglowek[2]; i++)
		nh->data[i] = fds[i];
	pread(meta, &nh->data[naglowek[2]], naglowek[3] * sizeof(int), sizeof(naglowek));
	buffer_handle_t h = NULL;
	int r = hybris_gralloc_import_buffer(nh, &h);
	printf("gralloc import: %d, numFds=%d numInts=%d\n", r, naglowek[2], naglowek[3]);
	if (r || !h)
		return 4;
	void *va = NULL;
	if (hybris_gralloc_lock(h, 0x3 /* SW_READ_OFTEN */, 0, 0, W, H, &va) || !va) {
		printf("gralloc lock nie powiodl sie\n");
		return 5;
	}
	int stride_px = strides[0] / 4;
	unsigned char *p = va;
	unsigned char *a = p + ((size_t)10 * stride_px + 10) * 4;
	unsigned char *b = p + ((size_t)(H - 10) * stride_px + 10) * 4;
	printf("gralloc CPU: wiersz 10 %d %d %d %d, wiersz H-10 %d %d %d %d\n", a[0], a[1], a[2], a[3], b[0], b[1], b[2],
	       b[3]);
	hybris_gralloc_unlock(h);
	int ok = (a[2] > 240 && a[0] < 20 && b[0] > 240 && b[2] < 20) || (b[2] > 240 && b[0] < 20 && a[0] > 240 && a[2] < 20);
	printf("%s\n", ok ? "WYNIK: eksport niesie bufor gralloc z trescia z Panfrosta" : "WYNIK: ZLE PIKSELE");
	return ok ? 0 : 6;
}
