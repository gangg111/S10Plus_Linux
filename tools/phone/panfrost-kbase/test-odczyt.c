// Odczyt klatki jak w WebKicie (RenderTargetSHMImage): renderbuffer RGBA8
// 1440x2838, glReadPixels(GL_BGRA). Kazda klatka ma inny kolor, wiec stara
// zawartosc pamieci podrecznej CPU zostalaby wykryta. Mierzy czas odczytu.
// cc -O2 test-odczyt.c -o test-odczyt -lEGL -lGLESv2
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define W 1440
#define H 2838

static double ms(void)
{
	struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1e3 + t.tv_nsec / 1e6;
}

int main(void)
{
	EGLDisplay dpy = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	eglInitialize(dpy, NULL, NULL);
	eglBindAPI(EGL_OPENGL_ES_API);
	const EGLint ca[] = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ca);
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx);
	GLuint rb, fbo;
	glGenRenderbuffers(1, &rb);
	glBindRenderbuffer(GL_RENDERBUFFER, rb);
	glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA8, W, H);
	glGenFramebuffers(1, &fbo);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo);
	glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, rb);
	glViewport(0, 0, W, H);
	unsigned char *px = malloc(W * H * 4);
	int zle = 0;
	double suma = 0, najg = 0;
	for (int i = 0; i < 20; i++) {
		int r = (i * 37) % 256, g = (i * 91) % 256, b = (i * 53) % 256;
		glClearColor(r / 255.0f, g / 255.0f, b / 255.0f, 1.0f);
		glClear(GL_COLOR_BUFFER_BIT);
		double t0 = ms();
		glReadPixels(0, 0, W, H, 0x80E1 /* GL_BGRA */, GL_UNSIGNED_BYTE, px);
		double t = ms() - t0;
		suma += t;
		if (t > najg)
			najg = t;
		// sprawdz trzy miejsca (poczatek, srodek, koniec)
		for (int k = 0; k < 3; k++) {
			unsigned char *p = px + ((size_t)(k * (H - 1) / 2) * W + k * (W - 1) / 2) * 4;
			if (abs(p[2] - r) > 1 || abs(p[1] - g) > 1 || abs(p[0] - b) > 1)
				zle++;
		}
	}
	printf("20 odczytow %dx%d BGRA: srednio %.1f ms, najdluzej %.1f ms, zlych probek %d z 60\n", W, H,
	       suma / 20, najg, zle);
	return zle ? 1 : 0;
}
