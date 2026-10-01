// Renderbuffer RGBA8 o rozmiarach jak w WebKicie: glClear na czerwono i odczyt.
// W procesie tresci WebKita bufor 1920x2420 zwracal zera nawet po glClear.
// cc test-duzy-rb.c -o test-duzy-rb -lEGL -lGLESv2
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <stdio.h>

static void proba(int w, int h)
{
	GLuint rb, fbo;
	glGenRenderbuffers(1, &rb);
	glBindRenderbuffer(GL_RENDERBUFFER, rb);
	glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA8, w, h);
	GLenum e1 = glGetError();
	glGenFramebuffers(1, &fbo);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo);
	glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, rb);
	GLenum st = glCheckFramebufferStatus(GL_FRAMEBUFFER);
	glViewport(0, 0, w, h);
	glClearColor(1.0f, 0.0f, 0.0f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	unsigned char px[16];
	glReadPixels(w / 2, h / 2, 2, 2, GL_RGBA, GL_UNSIGNED_BYTE, px);
	printf("%5dx%-5d storage=%#x status=%#x px=%d,%d,%d,%d blad=%#x\n", w, h, e1, st, px[0], px[1], px[2], px[3],
	       glGetError());
	glDeleteFramebuffers(1, &fbo);
	glDeleteRenderbuffers(1, &rb);
}

int main(void)
{
	EGLDisplay dpy = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	eglInitialize(dpy, NULL, NULL);
	eglBindAPI(EGL_OPENGL_ES_API);
	const EGLint ca[] = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ca);
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx);
	int r[][2] = { { 256, 256 }, { 512, 512 }, { 1024, 1024 }, { 1440, 1440 }, { 1440, 2838 },
		       { 1920, 2420 }, { 2048, 2048 }, { 4096, 4096 } };
	for (unsigned i = 0; i < sizeof(r) / sizeof(r[0]); i++)
		proba(r[i][0], r[i][1]);
	return 0;
}
