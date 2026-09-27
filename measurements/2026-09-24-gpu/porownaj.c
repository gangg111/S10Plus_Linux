// Test poprawnosci renderowania: ta sama scena GLES2 do bufora poza ekranem
// (EGL surfaceless), zapis do PPM.  Uruchomiony raz na panfroscie i raz na
// llvmpipe (LIBGL_ALWAYS_SOFTWARE=1) daje dwa obrazy do porownania.
//
//   porownaj rysuj WYJSCIE.ppm      renderuje scene i zapisuje obraz
//   porownaj diff A.ppm B.ppm       roznice kanalow miedzy dwoma obrazami
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define W 1440
#define H 3040
#define T 256

static const char *vs =
	"attribute vec2 p; attribute vec2 t; varying vec2 uv;\n"
	"uniform mat2 m; uniform vec2 o;\n"
	"void main() { uv = t; gl_Position = vec4(m * p + o, 0.0, 1.0); }\n";

// Wzor proceduralny: trygonometria, fract, mieszanie.
static const char *fs_wzor =
	"precision highp float; varying vec2 uv;\n"
	"void main() {\n"
	"  float a = 0.5 + 0.5 * sin(uv.x * 31.4159) * cos(uv.y * 27.1828);\n"
	"  vec2 f = fract(uv * 7.0);\n"
	"  gl_FragColor = vec4(f.x, a, f.y * (1.0 - a), 1.0);\n"
	"}\n";

// Tekstura z filtrowaniem liniowym i mipmapami, z alfa do mieszania.
static const char *fs_tekstura =
	"precision mediump float; varying vec2 uv; uniform sampler2D s;\n"
	"uniform float alfa;\n"
	"void main() { vec4 c = texture2D(s, uv); gl_FragColor = vec4(c.rgb, c.a * alfa); }\n";

static GLuint program(const char *f)
{
	GLuint p = glCreateProgram();
	const char *src[2] = { vs, f };
	GLenum typ[2] = { GL_VERTEX_SHADER, GL_FRAGMENT_SHADER };
	GLint ok;
	char log[1024];

	for (int i = 0; i < 2; i++) {
		GLuint s = glCreateShader(typ[i]);

		glShaderSource(s, 1, &src[i], NULL);
		glCompileShader(s);
		glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
		if (!ok) {
			glGetShaderInfoLog(s, sizeof(log), NULL, log);
			fprintf(stderr, "shader: %s\n", log);
			exit(1);
		}
		glAttachShader(p, s);
	}
	glBindAttribLocation(p, 0, "p");
	glBindAttribLocation(p, 1, "t");
	glLinkProgram(p);
	glGetProgramiv(p, GL_LINK_STATUS, &ok);
	if (!ok) {
		fprintf(stderr, "link\n");
		exit(1);
	}
	return p;
}

static void kwadrat(GLuint p, float kat, float skala, float ox, float oy)
{
	static const float v[] = { -1, -1, 0, 0,  1, -1, 1, 0,  -1, 1, 0, 1,  1, 1, 1, 1 };
	float c = cosf(kat) * skala, s = sinf(kat) * skala;
	float m[4] = { c, s, -s, c };

	glUseProgram(p);
	glUniformMatrix2fv(glGetUniformLocation(p, "m"), 1, GL_FALSE, m);
	glUniform2f(glGetUniformLocation(p, "o"), ox, oy);
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, v);
	glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, v + 2);
	glEnableVertexAttribArray(0);
	glEnableVertexAttribArray(1);
	glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
}

static int rysuj(const char *wyjscie)
{
	PFNEGLGETPLATFORMDISPLAYEXTPROC gpd = (void *)eglGetProcAddress("eglGetPlatformDisplayEXT");
	EGLDisplay d = gpd(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	static const EGLint ka[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	static unsigned char tex[T * T * 4], obraz[W * H * 4];
	GLuint fbo, cel, tx, p_wzor, p_tex;
	EGLContext k;
	FILE *f;

	if (!eglInitialize(d, NULL, NULL) || !eglBindAPI(EGL_OPENGL_ES_API))
		return 1;
	k = eglCreateContext(d, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ka);
	if (k == EGL_NO_CONTEXT || !eglMakeCurrent(d, EGL_NO_SURFACE, EGL_NO_SURFACE, k))
		return 1;
	fprintf(stderr, "renderer: %s\n", glGetString(GL_RENDERER));

	glGenTextures(1, &cel);
	glBindTexture(GL_TEXTURE_2D, cel);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, W, H, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
	glGenFramebuffers(1, &fbo);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, cel, 0);
	if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
		return 1;
	glViewport(0, 0, W, H);

	// Szachownica z gradientem i alfa, generowana na CPU.
	for (int y = 0; y < T; y++)
		for (int x = 0; x < T; x++) {
			unsigned char *t = tex + 4 * (y * T + x);
			int pole = ((x / 16) ^ (y / 16)) & 1;

			t[0] = pole ? 255 : x;
			t[1] = pole ? y : 40;
			t[2] = (x + y) / 2;
			t[3] = 128 + (x ^ y) / 2;
		}
	glGenTextures(1, &tx);
	glBindTexture(GL_TEXTURE_2D, tx);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, T, T, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex);
	glGenerateMipmap(GL_TEXTURE_2D);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);

	p_wzor = program(fs_wzor);
	p_tex = program(fs_tekstura);

	glClearColor(0.1f, 0.2f, 0.3f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	kwadrat(p_wzor, 0.0f, 1.0f, 0.0f, 0.0f);
	glEnable(GL_BLEND);
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
	glUseProgram(p_tex);
	glUniform1i(glGetUniformLocation(p_tex, "s"), 0);
	for (int i = 0; i < 6; i++) {
		glUniform1f(glGetUniformLocation(p_tex, "alfa"), 0.4f + 0.1f * i);
		// Od powiekszenia do silnego pomniejszenia: wszystkie poziomy mipmap.
		kwadrat(p_tex, 0.3f * i, 0.9f / (1 + i * i), -0.5f + 0.2f * i, 0.6f - 0.25f * i);
	}
	glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, obraz);
	if (glGetError() != GL_NO_ERROR)
		return 1;

	f = fopen(wyjscie, "wb");
	if (!f)
		return 1;
	fprintf(f, "P6\n%d %d\n255\n", W, H);
	for (int i = 0; i < W * H; i++)
		fwrite(obraz + 4 * i, 1, 3, f);
	fclose(f);
	return 0;
}

static unsigned char *czytaj(const char *n)
{
	unsigned char *b = malloc(W * H * 3);
	FILE *f = fopen(n, "rb");
	int w, h, m;

	if (!f || fscanf(f, "P6 %d %d %d", &w, &h, &m) != 3 || w != W || h != H)
		exit(1);
	fgetc(f);
	if (fread(b, 1, W * H * 3, f) != (size_t)W * H * 3)
		exit(1);
	fclose(f);
	return b;
}

int main(int argc, char **argv)
{
	if (argc == 3 && !strcmp(argv[1], "rysuj"))
		return rysuj(argv[2]);
	if (argc == 4 && !strcmp(argv[1], "diff")) {
		unsigned char *a = czytaj(argv[2]), *b = czytaj(argv[3]);
		long hist[256] = { 0 };
		int max = 0;

		for (long i = 0; i < (long)W * H * 3; i++) {
			int r = abs(a[i] - b[i]);

			hist[r]++;
			if (r > max)
				max = r;
		}
		printf("kanalow: %ld, identycznych: %ld, roznica 1: %ld, 2: %ld, 3-8: ",
		       (long)W * H * 3, hist[0], hist[1], hist[2]);
		long s = 0;
		for (int i = 3; i <= 8; i++)
			s += hist[i];
		printf("%ld, >8: ", s);
		s = 0;
		for (int i = 9; i < 256; i++)
			s += hist[i];
		printf("%ld, max %d\n", s, max);
		return 0;
	}
	fprintf(stderr, "uzycie: porownaj rysuj X.ppm | porownaj diff A.ppm B.ppm\n");
	return 2;
}
