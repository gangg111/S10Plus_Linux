// Linkowanie programu Skii (tekst z atlasu glifow), ktory pada w WebKicie na
// Panfroscie-kbase ("link failed but did not provide an info log"), w
// wariantach: pelny, bez noperspective, bez flat, bez atrybutu uvec2.
// cc test-shader.c -o test-shader -lEGL -lGLESv2
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl32.h>
#include <stdio.h>
#include <string.h>

static const char *VS =
	"#version 320 es\n"
	"%s"
	"precision mediump float;\n"
	"uniform highp vec4 sk_RTAdjust;\n"
	"uniform highp vec2 uAtlasSizeInv_S0;\n"
	"in highp vec2 inPosition;\n"
	"in mediump vec4 inColor;\n"
	"in mediump %s inTextureCoords;\n"
	"%s out highp vec2 vTextureCoords_S0;\n"
	"%s out highp float vTexIndex_S0;\n"
	"%s out mediump vec4 vinColor_S0;\n"
	"void main() {\n"
	"vTextureCoords_S0 = vec2(float(inTextureCoords.x), float(inTextureCoords.y)) * uAtlasSizeInv_S0;\n"
	"vTexIndex_S0 = 0.0;\n"
	"vinColor_S0 = inColor;\n"
	"gl_Position = vec4(inPosition, 0.0, 1.0);\n"
	"gl_Position = vec4(gl_Position.xy * sk_RTAdjust.xz + gl_Position.ww * sk_RTAdjust.yw, 0.0, gl_Position.w);\n"
	"}\n";

static const char *FS =
	"#version 320 es\n"
	"%s"
	"precision mediump float;\n"
	"precision mediump sampler2D;\n"
	"out mediump vec4 sk_FragColor;\n"
	"uniform sampler2D uTextureSampler_0_S0;\n"
	"%s in highp vec2 vTextureCoords_S0;\n"
	"%s in highp float vTexIndex_S0;\n"
	"%s in mediump vec4 vinColor_S0;\n"
	"void main() {\n"
	"mediump vec4 texColor = texture(uTextureSampler_0_S0, vTextureCoords_S0, -0.475).xxxx;\n"
	"sk_FragColor = vinColor_S0 * texColor;\n"
	"}\n";

static GLuint compile(GLenum type, const char *src)
{
	GLuint s = glCreateShader(type);
	glShaderSource(s, 1, &src, NULL);
	glCompileShader(s);
	GLint ok = 0;
	glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
	char log[1024] = "";
	glGetShaderInfoLog(s, sizeof(log), NULL, log);
	if (!ok || *log)
		printf("   kompilacja %s: ok=%d log=%s\n", type == GL_VERTEX_SHADER ? "VS" : "FS", ok, log);
	return s;
}

static void wariant(const char *nazwa, int np, int flat, const char *attr)
{
	char vs[4096], fs[4096];
	const char *ext = np ? "#extension GL_NV_shader_noperspective_interpolation : require\n" : "";
	const char *q = np ? "noperspective" : "";
	const char *f = flat ? "flat" : "";
	snprintf(vs, sizeof(vs), VS, ext, attr, q, f, q);
	snprintf(fs, sizeof(fs), FS, ext, q, f, q);
	GLuint p = glCreateProgram();
	glAttachShader(p, compile(GL_VERTEX_SHADER, vs));
	glAttachShader(p, compile(GL_FRAGMENT_SHADER, fs));
	glLinkProgram(p);
	GLint ok = 0;
	glGetProgramiv(p, GL_LINK_STATUS, &ok);
	char log[2048] = "";
	glGetProgramInfoLog(p, sizeof(log), NULL, log);
	printf("%-28s link=%s %s\n", nazwa, ok ? "OK" : "PADA", log);
}

int main(void)
{
	EGLDisplay dpy = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	eglInitialize(dpy, NULL, NULL);
	eglBindAPI(EGL_OPENGL_ES_API);
	const EGLint ca[] = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_CONTEXT_MINOR_VERSION, 2, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ca);
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx);
	printf("%s | %s\n", glGetString(GL_RENDERER), glGetString(GL_VERSION));
	wariant("pelny (jak Skia)", 1, 1, "uvec2");
	wariant("bez noperspective", 0, 1, "uvec2");
	wariant("bez flat", 1, 0, "uvec2");
	wariant("bez uvec2 (vec2)", 1, 1, "vec2");
	wariant("bez niczego", 0, 0, "vec2");
	return 0;
}
