// Etap 1: Mesa Panfrost na kbase bez okna. EGL surfaceless, kontekst GLES 3,
// trojkat do FBO 256x256, glReadPixels, sprawdzenie pikseli i GL_RENDERER.
// cc test-surfaceless.c -o test-surfaceless -lEGL -lGLESv2
// Uruchamiac z: __EGL_VENDOR_LIBRARY_FILENAMES=<prefiks>/share/glvnd/egl_vendor.d/50_mesa.json
//               MESA_KBASE_NODE=/dev/mali0 LD_LIBRARY_PATH=<prefiks>/lib  (bez LD_PRELOAD)
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define W 256
#define H 256

static GLuint shader(GLenum type, const char *src)
{
	GLuint s = glCreateShader(type);
	glShaderSource(s, 1, &src, NULL);
	glCompileShader(s);
	GLint ok = 0;
	glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
	if (!ok) {
		char log[512];
		glGetShaderInfoLog(s, sizeof(log), NULL, log);
		fprintf(stderr, "shader: %s\n", log);
		exit(3);
	}
	return s;
}

int main(void)
{
	EGLDisplay dpy = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	EGLint ma, mi;
	if (dpy == EGL_NO_DISPLAY || !eglInitialize(dpy, &ma, &mi)) {
		fprintf(stderr, "eglInitialize nie powiodlo sie: %#x\n", eglGetError());
		return 1;
	}
	printf("EGL %d.%d vendor=%s\n", ma, mi, eglQueryString(dpy, EGL_VENDOR));
	eglBindAPI(EGL_OPENGL_ES_API);
	const EGLint ca[] = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ca);
	if (ctx == EGL_NO_CONTEXT || !eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx)) {
		fprintf(stderr, "kontekst nie powstal: %#x\n", eglGetError());
		return 2;
	}
	printf("GL_RENDERER=%s\nGL_VERSION=%s\n", glGetString(GL_RENDERER), glGetString(GL_VERSION));

	GLuint tex, fbo;
	glGenTextures(1, &tex);
	glBindTexture(GL_TEXTURE_2D, tex);
	glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, W, H);
	glGenFramebuffers(1, &fbo);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0);
	printf("FBO: %#x\n", glCheckFramebufferStatus(GL_FRAMEBUFFER));

	GLuint p = glCreateProgram();
	glAttachShader(p, shader(GL_VERTEX_SHADER,
		"#version 300 es\n"
		"const vec2 v[3] = vec2[3](vec2(-1.0,-1.0), vec2(1.0,-1.0), vec2(-1.0,1.0));\n"
		"void main() { gl_Position = vec4(v[gl_VertexID], 0.0, 1.0); }\n"));
	glAttachShader(p, shader(GL_FRAGMENT_SHADER,
		"#version 300 es\nprecision mediump float;\nout vec4 c;\n"
		"void main() { c = vec4(1.0, 0.5, 0.0, 1.0); }\n"));
	glLinkProgram(p);
	glUseProgram(p);

	struct timespec t0, t1;
	clock_gettime(CLOCK_MONOTONIC, &t0);
	glViewport(0, 0, W, H);
	glClearColor(0.0f, 0.0f, 1.0f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	glDrawArrays(GL_TRIANGLES, 0, 3);
	static unsigned char px[W * H * 4];
	glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, px);
	clock_gettime(CLOCK_MONOTONIC, &t1);

	// lewy dolny rog: trojkat (pomaranczowy), prawy gorny: tlo (niebieskie)
	unsigned char *a = &px[(10 * W + 10) * 4], *b = &px[((H - 10) * W + (W - 10)) * 4];
	printf("piksel trojkata: %d %d %d %d\npiksel tla: %d %d %d %d\n", a[0], a[1], a[2], a[3], b[0], b[1], b[2], b[3]);
	printf("czas klatki z odczytem: %.2f ms, glGetError=%#x\n",
	       (t1.tv_sec - t0.tv_sec) * 1e3 + (t1.tv_nsec - t0.tv_nsec) / 1e6, glGetError());
	// WebKit oddaje klatke przez glReadPixels(GL_BGRA) (RenderTargetSHMImage)
	const char *ext = (const char *)glGetString(GL_EXTENSIONS);
	printf("GL_EXT_read_format_bgra: %s\n", ext && strstr(ext, "GL_EXT_read_format_bgra") ? "tak" : "NIE");
	static unsigned char bgra[W * H * 4];
	glReadPixels(0, 0, W, H, 0x80E1 /* GL_BGRA_EXT */, GL_UNSIGNED_BYTE, bgra);
	unsigned char *c = &bgra[(10 * W + 10) * 4];
	printf("odczyt BGRA: glGetError=%#x piksel %d %d %d %d\n", glGetError(), c[0], c[1], c[2], c[3]);

	// WebKit (RenderTargetSHMImage) rysuje do RENDERBUFFERA RGBA8, nie do tekstury
	GLuint rb, fbo2;
	glGenRenderbuffers(1, &rb);
	glBindRenderbuffer(GL_RENDERBUFFER, rb);
	glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA8, W, H);
	glGenFramebuffers(1, &fbo2);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo2);
	glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, rb);
	printf("FBO z renderbufferem: %#x\n", glCheckFramebufferStatus(GL_FRAMEBUFFER));
	glClearColor(1.0f, 0.0f, 0.0f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	glDrawArrays(GL_TRIANGLES, 0, 3);
	static unsigned char rbpx[W * H * 4];
	glReadPixels(0, 0, W, H, 0x80E1 /* GL_BGRA_EXT */, GL_UNSIGNED_BYTE, rbpx);
	unsigned char *d = &rbpx[(10 * W + 10) * 4], *e = &rbpx[((H - 10) * W + (W - 10)) * 4];
	printf("renderbuffer BGRA: glGetError=%#x trojkat %d %d %d %d, tlo %d %d %d %d\n", glGetError(),
	       d[0], d[1], d[2], d[3], e[0], e[1], e[2], e[3]);

	// Kompozytor WebKita rysuje warstwy jako tekstury wgrane z CPU i probkowane
	// w shaderze: tekstura 64x64 zielona z CPU, pelnoekranowy prostokat.
	static unsigned char zielony[64 * 64 * 4];
	for (int i = 0; i < 64 * 64; i++) {
		zielony[i * 4 + 0] = 0;
		zielony[i * 4 + 1] = 255;
		zielony[i * 4 + 2] = 0;
		zielony[i * 4 + 3] = 255;
	}
	GLuint tx;
	glGenTextures(1, &tx);
	glBindTexture(GL_TEXTURE_2D, tx);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, zielony);
	GLuint pt = glCreateProgram();
	glAttachShader(pt, shader(GL_VERTEX_SHADER,
		"#version 300 es\n"
		"const vec2 v[4] = vec2[4](vec2(-1.0,-1.0), vec2(1.0,-1.0), vec2(-1.0,1.0), vec2(1.0,1.0));\n"
		"out vec2 uv;\n"
		"void main() { uv = v[gl_VertexID] * 0.5 + 0.5; gl_Position = vec4(v[gl_VertexID], 0.0, 1.0); }\n"));
	glAttachShader(pt, shader(GL_FRAGMENT_SHADER,
		"#version 300 es\nprecision mediump float;\nuniform sampler2D s;\nin vec2 uv;\nout vec4 c;\n"
		"void main() { c = texture(s, uv); }\n"));
	glLinkProgram(pt);
	glUseProgram(pt);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo2);
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
	glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, rbpx);
	unsigned char *g = &rbpx[(128 * W + 128) * 4];
	printf("tekstura z CPU: glGetError=%#x piksel %d %d %d %d (oczekiwany 0 255 0 255)\n", glGetError(),
	       g[0], g[1], g[2], g[3]);

	// Wspoldzielenie miedzy kontekstami (WebKit: malowanie i kompozytor w roznych
	// kontekstach): tekstura niebieska wgrana w kontekscie B, rysowana w A.
	const EGLint cb[] = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE };
	EGLContext ctxB = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, ctx, cb);
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctxB);
	for (int i = 0; i < 64 * 64; i++) {
		zielony[i * 4 + 0] = 0;
		zielony[i * 4 + 1] = 0;
		zielony[i * 4 + 2] = 255;
	}
	GLuint txB;
	glGenTextures(1, &txB);
	glBindTexture(GL_TEXTURE_2D, txB);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, zielony);
	// SYNC=finish (domyslnie) | flush | fence (eglCreateSync + eglWaitSync w A)
	const char *tryb = getenv("SYNC") ? getenv("SYNC") : "finish";
	EGLSync plot = EGL_NO_SYNC;
	if (!strcmp(tryb, "finish"))
		glFinish();
	else if (!strcmp(tryb, "fence"))
		plot = eglCreateSync(dpy, EGL_SYNC_FENCE, NULL);
	else
		glFlush();
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx);
	if (plot != EGL_NO_SYNC)
		eglWaitSync(dpy, plot, 0);
	printf("tryb synchronizacji: %s\n", tryb);
	glBindTexture(GL_TEXTURE_2D, txB);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo2);
	glClear(GL_COLOR_BUFFER_BIT);
	glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
	glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, rbpx);
	g = &rbpx[(128 * W + 128) * 4];
	printf("tekstura z kontekstu B: ctxB=%p glGetError=%#x piksel %d %d %d %d (oczekiwany 0 0 255 255)\n",
	       ctxB, glGetError(), g[0], g[1], g[2], g[3]);

	// WebKit wgrywa kafelki jako BGRA (GL_EXT_texture_format_BGRA8888), 512x512,
	// przez glTexSubImage2D do tekstury utworzonej wczesniej
	static unsigned char kafel[512 * 512 * 4];
	for (int i = 0; i < 512 * 512; i++) {
		kafel[i * 4 + 0] = 0;   /* B */
		kafel[i * 4 + 1] = 0;   /* G */
		kafel[i * 4 + 2] = 255; /* R */
		kafel[i * 4 + 3] = 255;
	}
	GLuint tb;
	glGenTextures(1, &tb);
	glBindTexture(GL_TEXTURE_2D, tb);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexImage2D(GL_TEXTURE_2D, 0, 0x80E1, 512, 512, 0, 0x80E1, GL_UNSIGNED_BYTE, NULL);
	GLenum e1 = glGetError();
	glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 512, 512, 0x80E1, GL_UNSIGNED_BYTE, kafel);
	GLenum e2 = glGetError();
	glBindFramebuffer(GL_FRAMEBUFFER, fbo2);
	glClear(GL_COLOR_BUFFER_BIT);
	glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
	glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, rbpx);
	g = &rbpx[(128 * W + 128) * 4];
	printf("kafel BGRA: TexImage=%#x TexSubImage=%#x piksel %d %d %d %d (oczekiwany 255 0 0 255)\n",
	       e1, e2, g[0], g[1], g[2], g[3]);

	int ok = a[0] > 240 && a[1] > 110 && a[1] < 140 && a[2] < 15 && b[2] > 240 && b[0] < 15;
	printf("%s\n", ok ? "WYNIK: OK" : "WYNIK: ZLE PIKSELE");
	return ok ? 0 : 4;
}
