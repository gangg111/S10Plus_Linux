// Test libcamx.so od strony Linuksa (glibc), jak w aplikacji aparatu: kamera przez
// warstwe zgodnosci libhybris, libcamx przez android_dlopen. Sprawdza zgodnosc ukladu
// CameraControl, a potem zapis i odczyt kluczy, ktorych warstwa zgodnosci nie ma.
// Uruchamiac z LD_PRELOAD=libtls-padding.so (biblioteki Androida w procesie glibc).
// Uzycie: camx-test [kamera] [sciezka libcamx.so]
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <unistd.h>
#include <hybris/camera/camera_compatibility_layer.h>
#include <hybris/camera/camera_compatibility_layer_capabilities.h>

extern void *android_dlopen(const char *filename, int flag);
extern void *android_dlsym(void *handle, const char *symbol);

typedef int (*check_t)(void *, void *);
typedef int (*set_t)(void *, const char *, const char *);
typedef int (*get_t)(void *, const char *, char *, int);
typedef int (*dump_t)(void *, char *, int);

int main(int argc, char **argv)
{
	int id = argc > 1 ? atoi(argv[1]) : 0;
	const char *sciezka = argc > 2 ? argv[2] : "/usr/lib/droidian-camera/libcamx.so";
	struct CameraControlListener *l = calloc(1, sizeof(*l));
	struct CameraControl *cc = android_camera_connect_by_id(id, l);
	if (!cc) {
		printf("nie polaczono z kamera %d\n", id);
		return 1;
	}
	void *h = android_dlopen(sciezka, RTLD_NOW);
	if (!h) {
		printf("android_dlopen %s nie powiodl sie\n", sciezka);
		return 2;
	}
	check_t check = (check_t)android_dlsym(h, "camx_check");
	set_t set = (set_t)android_dlsym(h, "camx_set");
	get_t get = (get_t)android_dlsym(h, "camx_get");
	dump_t dump = (dump_t)android_dlsym(h, "camx_dump");
	printf("symbole: %p %p %p %p\n", check, set, get, dump);
	int ok = check(cc, l);
	printf("camx_check: %d\n", ok);
	int zle = check(cc, (void *)0x1234);
	printf("camx_check z obcym listenerem (ma byc 0): %d\n", zle);
	ok = check(cc, l);
	if (!ok)
		return 3;

	char v[256], *d = malloc(65536);
	dump(cc, d, 65536);
	printf("zrzut parametrow: %zu znakow\n", strlen(d));

	const char *proby[][2] = {
		{ "exposure-compensation", "20" }, { "exposure-compensation", "-20" },
		{ "exposure-compensation", "99" }, { "auto-exposure-lock", "true" },
		{ "auto-whitebalance-lock", "true" }, { "antibanding", "off" },
		{ "exposure-compensation", "0" }, { "auto-exposure-lock", "false" },
		{ "auto-whitebalance-lock", "false" }, { "antibanding", "auto" },
	};
	for (unsigned i = 0; i < sizeof(proby) / sizeof(proby[0]); i++) {
		int r = set(cc, proby[i][0], proby[i][1]);
		get(cc, proby[i][0], v, sizeof(v));
		printf("set %-24s = %-5s -> kod %d, kamera ma: %s\n", proby[i][0], proby[i][1], r, v);
	}

	// tryby ostrosci z warstwy zgodnosci: co HAL faktycznie dostaje
	const char *nazwy[] = { "OFF", "CONTINUOUS_VIDEO", "AUTO", "MACRO", "CONTINUOUS_PICTURE", "INFINITY" };
	for (int m = 0; m < 6; m++) {
		android_camera_set_auto_focus_mode(cc, m);
		get(cc, "focus-mode", v, sizeof(v));
		printf("android_camera_set_auto_focus_mode(%s) -> focus-mode=%s\n", nazwy[m], v);
	}

	// twarze: posrednik zdarzen + wykrywanie sprzetowe, podglad musi dzialac
	typedef int (*listen_t)(void *);
	typedef int (*cmd_t)(void *, int, int, int);
	typedef int (*faces_t)(int *, int, unsigned *);
	listen_t listen = (listen_t)android_dlsym(h, "camx_listen");
	cmd_t cmd = (cmd_t)android_dlsym(h, "camx_command");
	faces_t faces = (faces_t)android_dlsym(h, "camx_faces");
	printf("camx_listen: %d\n", listen(cc));
	android_camera_set_preview_size(cc, 1920, 1080);
	android_camera_set_preview_texture(cc, 0);
	android_camera_start_preview(cc);
	printf("START_FACE_DETECTION: %d\n", cmd(cc, 6, 0, 0));
	int f[16 * 6], n = 0;
	unsigned p0 = 0, p = 0;
	faces(f, 16, &p0);
	for (int s = 0; s < 5; s++) {
		sleep(1);
		n = faces(f, 16, &p);
		printf("po %d s: paczek metadanych %u, twarzy %d", s + 1, p - p0, n);
		if (n)
			printf(" pierwsza [%d,%d,%d,%d] score %d", f[0], f[1], f[2], f[3], f[4]);
		printf("\n");
	}
	printf("STOP_FACE_DETECTION: %d\n", cmd(cc, 7, 0, 0));
	android_camera_stop_preview(cc);
	android_camera_disconnect(cc);
	android_camera_delete(cc);
	return 0;
}
