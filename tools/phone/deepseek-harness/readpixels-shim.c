// LD_PRELOAD dla procesu tresci WebKita: obklada glReadPixels, ktorym
// RenderTargetSHMImage oddaje klatke do pamieci wspoldzielonej.
// DSH_RP_LOG=1 wypisuje stan GL i pierwszy piksel kazdego odczytu.
// Jesli podpiety jest GL_PIXEL_PACK_BUFFER, odczyt poszedlby do niego zamiast
// do wskazanej pamieci (wtedy bufor klatki zostaje zerowy), wiec na czas
// odczytu jest odpinany.
// cc -O2 -shared -fPIC readpixels-shim.c -o libdsh-readpixels.so -ldl
#define _GNU_SOURCE
#include <GLES3/gl3.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

typedef void (*rp_t)(GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void *);
typedef void (*gi_t)(GLenum, GLint *);
typedef void (*bb_t)(GLenum, GLuint);
typedef GLenum (*ge_t)(void);

void glReadPixels(GLint x, GLint y, GLsizei w, GLsizei h, GLenum format, GLenum type, void *data)
{
	static rp_t real;
	static gi_t geti;
	static bb_t bind;
	static ge_t err;
	if (!real) {
		real = (rp_t)dlsym(RTLD_NEXT, "glReadPixels");
		geti = (gi_t)dlsym(RTLD_NEXT, "glGetIntegerv");
		bind = (bb_t)dlsym(RTLD_NEXT, "glBindBuffer");
		err = (ge_t)dlsym(RTLD_NEXT, "glGetError");
	}
	GLint pack = 0, readfb = 0;
	geti(GL_PIXEL_PACK_BUFFER_BINDING, &pack);
	geti(GL_READ_FRAMEBUFFER_BINDING, &readfb);
	if (pack)
		bind(GL_PIXEL_PACK_BUFFER, 0);
	real(x, y, w, h, format, type, data);
	GLenum e = err();
	if (pack)
		bind(GL_PIXEL_PACK_BUFFER, (GLuint)pack);
	if (getenv("DSH_RP_LOG")) {
		const unsigned char *p = data;
		fprintf(stderr, "[readpixels] %dx%d fmt=%#x pack=%d readfb=%d err=%#x px0=%d,%d,%d,%d\n",
			w, h, format, pack, readfb, e, p ? p[0] : -1, p ? p[1] : -1, p ? p[2] : -1, p ? p[3] : -1);
	}
}
