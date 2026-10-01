// Test sciezki Camera2 z libcamx.so (strona glibc, jak aplikacja): mozliwosci
// kamery, zdjecie z recznym ISO i czasem plus RAW zapisany jako DNG, seria.
// Kamera nie moze byc w tym czasie otwarta przez aplikacje.
// Budowa: buduj.sh; uruchomienie: LD_PRELOAD=libtls-padding.so ./cam2-test [kamera] [libcamx.so] [katalog]
#include <cstdio>
#include <cstdlib>
#include <string>
#include <dlfcn.h>

#include <camx/cam2.h>
#include <dng-writer.h>

extern "C" {
void *android_dlopen(const char *filename, int flag);
void *android_dlsym(void *handle, const char *symbol);
}

typedef int (*info_t)(const char *, Cam2Info *);
typedef int (*capture_t)(const char *, const Cam2Settings *, cam2_jpeg_cb, cam2_raw_cb, void *, int *, long long *);

struct Wynik {
	std::string katalog, nazwa;
	int jpegi = 0;
	long long bajty = 0;
	bool dng = false;
};

static void naJpeg(void *ctx, const unsigned char *d, int n, int i)
{
	Wynik *w = static_cast<Wynik *>(ctx);
	w->jpegi++;
	w->bajty += n;
	std::string p = w->katalog + "/" + w->nazwa + "-" + std::to_string(i) + ".jpg";
	FILE *f = std::fopen(p.c_str(), "wb");
	std::fwrite(d, 1, n, f);
	std::fclose(f);
	std::printf("  JPEG %d: %d B, poczatek %02x%02x, koniec %02x%02x\n", i, n, d[0], d[1], d[n - 2], d[n - 1]);
}

static void naRaw(void *ctx, const unsigned short *d, const Cam2Dng *m)
{
	Wynik *w = static_cast<Wynik *>(ctx);
	std::string p = w->katalog + "/" + w->nazwa + ".dng";
	w->dng = writeDng(p.c_str(), d, *m, 90, "samsung", "SM-G975F", "2026:10:01 00:00:00");
	long long suma = 0;
	for (int i = 0; i < m->width; i++)
		suma += d[(m->height / 2) * (m->rowStride / 2) + i];
	std::printf("  RAW %dx%d wiersz %d, cfa %d, czern %d/%d/%d/%d, biel %d, neutral %.3f/%.3f/%.3f, "
		    "ISO %d, %lld us, f/%.2f, %.2f mm, srednia srodkowego wiersza %lld -> %s\n",
		    m->width, m->height, m->rowStride, m->cfa, m->black[0], m->black[1], m->black[2], m->black[3],
		    m->white, m->neutral[0], m->neutral[1], m->neutral[2], m->iso, m->expNs / 1000, m->fNumber,
		    m->focalLength, suma / m->width, w->dng ? p.c_str() : "ZAPIS NIEUDANY");
}

int main(int argc, char **argv)
{
	const char *id = argc > 1 ? argv[1] : "0";
	const char *lib = argc > 2 ? argv[2] : "/usr/lib/droidian-camera/libcamx.so";
	Wynik w;
	w.katalog = argc > 3 ? argv[3] : "/tmp";
	void *h = android_dlopen(lib, RTLD_NOW);
	if (!h) {
		std::printf("android_dlopen %s nie powiodl sie\n", lib);
		return 1;
	}
	info_t info = (info_t)android_dlsym(h, "cam2_info");
	capture_t capture = (capture_t)android_dlsym(h, "cam2_capture");
	Cam2Info ci;
	std::printf("cam2_info: %d\n", info(id, &ci));
	std::printf("  ISO %d-%d, czas %lld-%lld us, ostrosc min %.2f dioptrii, manual %d, post %d, raw %d "
		    "(%dx%d), seria %d, OIS %d, JPEG %dx%d\n",
		    ci.isoMin, ci.isoMax, ci.expMinNs / 1000, ci.expMaxNs / 1000, ci.minFocusDiopters, ci.manualSensor,
		    ci.manualPost, ci.raw, ci.rawWidth, ci.rawHeight, ci.burst, ci.ois, ci.jpegWidth, ci.jpegHeight);

	Cam2Settings s = {};
	s.iso = 800;
	s.expNs = 20000000;
	s.focus = -1;
	s.ois = 0;
	s.awb = -1;
	s.jpegWidth = ci.jpegWidth;
	s.jpegHeight = ci.jpegHeight;
	s.quality = 95;
	s.orientation = 90;
	s.zoom = 1;
	s.raw = ci.raw;
	s.count = 1;
	s.effect = -1;
	s.antibanding = -1;
	s.noise = -1;
	s.edge = -1;
	int mi = 0;
	long long me = 0;
	// pojedyncze ujecie z zadanym ISO i czasem (0 = auto): cam2-test id lib katalog ISO czas_us
	if (argc > 5) {
		s.iso = std::atoi(argv[4]);
		s.expNs = std::atoll(argv[5]) * 1000;
		s.raw = 0;
		s.ois = -1;
		w.nazwa = "cam2-proba";
		int r = capture(id, &s, naJpeg, naRaw, &w, &mi, &me);
		std::printf("ISO %d, %lld us: wynik %d, pomiar AE ISO %d %lld us\n", s.iso, s.expNs / 1000, r, mi,
			    me / 1000);
		return 0;
	}
	w.nazwa = "cam2-reczne";
	int r = capture(id, &s, naJpeg, naRaw, &w, &mi, &me);
	std::printf("reczne ISO 800, 20 ms, OIS wyl., RAW: wynik %d, pomiar AE ISO %d %lld us\n", r, mi, me / 1000);

	s.iso = 0;
	s.expNs = 5000000; // pol-reczne: czas zadany, ISO z pomiaru
	s.raw = 0;
	s.ois = -1;
	s.focus = 0; // ostrosc na nieskonczonosc
	s.count = 5;
	s.zoom = 2;
	w.nazwa = "cam2-seria";
	r = capture(id, &s, naJpeg, naRaw, &w, &mi, &me);
	std::printf("seria 5, czas 5 ms, ISO auto, zoom 2, MF nieskonczonosc: wynik %d, pomiar AE ISO %d %lld us\n", r,
		    mi, me / 1000);
	return 0;
}
