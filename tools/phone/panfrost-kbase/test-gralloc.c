// Fundament przekazywania klatek bez kopii: bufor z gralloc Androida (przez
// libhybris), jego dma-buf zaimportowany do Mesy Panfrost na kbase jako obraz
// EGL (EGL_LINUX_DMA_BUF_EXT), rysowanie do niego i odczyt przez blokade
// gralloc (sciezka CPU sterownika Androida), bez udzialu Panfrosta.
// cc -O2 test-gralloc.c -o test-gralloc -lEGL -lGLESv2 -lgralloc
// Uruchamiac z LD_PRELOAD=libtls-padding.so (biblioteki Androida) i glvnd
// ograniczonym do Mesy Panfrost (__EGL_VENDOR_LIBRARY_FILENAMES, MESA_KBASE_NODE).
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <hybris/gralloc/gralloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

#define W 1440
#define H 2838
#define HAL_RGBA_8888 1
#define USAGE_SW_READ_RARELY 0x2
#define USAGE_HW_TEXTURE 0x100
#define USAGE_HW_RENDER 0x200
#define FOURCC_ABGR8888 0x34324241 /* DRM_FORMAT_ABGR8888: bajty R,G,B,A */

int main(int argc, char **argv)
{
	int usage = USAGE_HW_TEXTURE | USAGE_HW_RENDER | USAGE_SW_READ_RARELY;
	if (argc > 1)
		usage = (int)strtol(argv[1], NULL, 0);

	hybris_gralloc_initialize(0);
	buffer_handle_t h = NULL;
	uint32_t stride = 0;
	int r = hybris_gralloc_allocate(W, H, HAL_RGBA_8888, usage, &h, &stride);
	if (r || !h) {
		printf("gralloc allocate nie powiodlo sie: %d\n", r);
		return 1;
	}
	printf("gralloc: usage=%#x stride=%u px, numFds=%d numInts=%d fd0=%d\n", usage, stride, h->numFds,
	       h->numInts, h->data[0]);
	for (int i = 0; i < h->numFds; i++) {
		char link[64], cel[256] = "";
		snprintf(link, sizeof(link), "/proc/self/fd/%d", h->data[i]);
		ssize_t n = readlink(link, cel, sizeof(cel) - 1);
		if (n > 0)
			cel[n] = 0;
		struct stat st;
		fstat(h->data[i], &st);
		off_t rozmiar = lseek(h->data[i], 0, SEEK_END);
		printf("  fd[%d]=%d -> %s inode=%lu rozmiar=%ld\n", i, h->data[i], cel, (unsigned long)st.st_ino,
		       (long)rozmiar);
	}
	printf("  ints:");
	for (int i = 0; i < h->numInts; i++)
		printf(" %d", h->data[h->numFds + i]);
	printf("\n");

	EGLDisplay dpy = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	eglInitialize(dpy, NULL, NULL);
	eglBindAPI(EGL_OPENGL_ES_API);
	const EGLint ca[] = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ca);
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx);
	printf("renderer: %s\n", glGetString(GL_RENDERER));

	const EGLint ia[] = {
		EGL_WIDTH, W, EGL_HEIGHT, H, EGL_LINUX_DRM_FOURCC_EXT, FOURCC_ABGR8888,
		EGL_DMA_BUF_PLANE0_FD_EXT, h->data[0], EGL_DMA_BUF_PLANE0_OFFSET_EXT, 0,
		EGL_DMA_BUF_PLANE0_PITCH_EXT, (EGLint)(stride * 4), EGL_NONE
	};
	PFNEGLCREATEIMAGEKHRPROC createImage = (PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
	PFNGLEGLIMAGETARGETTEXTURE2DOESPROC target =
		(PFNGLEGLIMAGETARGETTEXTURE2DOESPROC)eglGetProcAddress("glEGLImageTargetTexture2DOES");
	EGLImageKHR img = createImage(dpy, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, NULL, ia);
	printf("eglCreateImage(dma-buf z gralloc): %p err=%#x\n", img, eglGetError());
	if (img == EGL_NO_IMAGE_KHR)
		return 2;

	GLuint tex, fbo;
	glGenTextures(1, &tex);
	glBindTexture(GL_TEXTURE_2D, tex);
	target(GL_TEXTURE_2D, img);
	glGenFramebuffers(1, &fbo);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0);
	printf("FBO na buforze gralloc: %#x\n", glCheckFramebufferStatus(GL_FRAMEBUFFER));
	glViewport(0, 0, W, H);
	glClearColor(1.0f, 0.5f, 0.0f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	glEnable(GL_SCISSOR_TEST);
	glScissor(0, 0, W / 2, H / 2);
	glClearColor(0.0f, 0.0f, 1.0f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	glFinish();
	printf("glGetError=%#x\n", glGetError());

	void *va = NULL;
	r = hybris_gralloc_lock(h, USAGE_SW_READ_RARELY, 0, 0, W, H, &va);
	if (r || !va) {
		printf("gralloc lock nie powiodlo sie: %d\n", r);
		return 3;
	}
	unsigned char *p = va;
	// wiersz 0 bufora = gora obrazu; lewy dolny kwadrat (niebieski) to wiersze H/2..H
	unsigned char *gora = p + ((size_t)10 * stride + 10) * 4;
	unsigned char *dol = p + ((size_t)(H - 10) * stride + 10) * 4;
	printf("gralloc CPU: piksel gora-lewo %d %d %d %d, dol-lewo %d %d %d %d\n", gora[0], gora[1], gora[2],
	       gora[3], dol[0], dol[1], dol[2], dol[3]);
	hybris_gralloc_unlock(h);
	int ok = (gora[0] > 240 && gora[2] < 20 && dol[2] > 240 && dol[0] < 20) ||
		 (dol[0] > 240 && dol[2] < 20 && gora[2] > 240 && gora[0] < 20);
	printf("%s\n", ok ? "WYNIK: Panfrost narysowal do bufora gralloc" : "WYNIK: ZLE PIKSELE");
	return ok ? 0 : 4;
}
