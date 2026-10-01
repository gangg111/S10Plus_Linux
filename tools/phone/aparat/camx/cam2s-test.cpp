// Test sesji Camera2 z libcamx.so (strona glibc), bez aplikacji: zdjecie PRO w sesji
// (podglad, reczne ISO, JPEG i DNG), pol-reczne ISO, nagranie wideo z dzwiekiem.
// Ekran musi byc WLACZONY (mobile-power-saver dlawi watki RT przy zgaszonym).
// Uzycie: LD_PRELOAD=libtls-padding.so ./cam2s-test [lib] [katalog]
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <dlfcn.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include <camx/cam2.h>
#include <dng-writer.h>

extern "C" {
void *android_dlopen(const char *filename, int flag);
void *android_dlsym(void *handle, const char *symbol);
}

#define FN(name) auto name = (decltype(&::name))android_dlsym(h, #name)

static std::string katalog;
static int jpegi;

static void naJpeg(void *, const unsigned char *d, int n, int i)
{
	jpegi++;
	FILE *f = std::fopen((katalog + "/sesja-" + std::to_string(i) + ".jpg").c_str(), "wb");
	std::fwrite(d, 1, n, f);
	std::fclose(f);
}

static void naRaw(void *, const unsigned short *d, const Cam2Dng *m)
{
	bool ok = writeDng((katalog + "/sesja.dng").c_str(), d, *m, 90, "samsung", "SM-G975F", "2026:10:01 00:00:00");
	std::printf("  DNG %dx%d ISO %d %lld us -> %s\n", m->width, m->height, m->iso, m->expNs / 1000, ok ? "ok" : "BLAD");
}

static long long nowUs()
{
	timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1000000LL + t.tv_nsec / 1000;
}

static Cam2Settings domyslne()
{
	Cam2Settings s = {};
	s.focus = -1;
	s.ois = -1;
	s.awb = -1;
	s.effect = -1;
	s.antibanding = -1;
	s.noise = -1;
	s.edge = -1;
	s.zoom = 1;
	s.quality = 95;
	s.orientation = 90;
	return s;
}

int main(int argc, char **argv)
{
	const char *lib = argc > 1 ? argv[1] : "/usr/lib/droidian-camera/libcamx.so";
	katalog = argc > 2 ? argv[2] : "/tmp";
	void *h = android_dlopen(lib, RTLD_NOW);
	if (!h)
		return 1;
	FN(cam2s_open);
	FN(cam2s_close);
	FN(cam2s_controls);
	FN(cam2s_state);
	FN(cam2s_acquire);
	FN(cam2s_release);
	FN(cam2s_still);
	FN(cam2s_record_start);
	FN(cam2s_record_audio);
	FN(cam2s_record_pump);
	FN(cam2s_record_stop);

	auto podglad = [&](void *S, int ms) {
		int n = 0;
		void *poprz = nullptr;
		for (int t = 0; t < ms; t += 10) {
			usleep(10000);
			void *ahb = nullptr;
			void *f = cam2s_acquire(S, &ahb);
			if (f) {
				n++;
				cam2s_release(S, poprz);
				poprz = f;
			}
		}
		cam2s_release(S, poprz);
		return n;
	};

	// tryb "pp": przetwarzanie reczne (Kelvin, kontrast, szum) przy latarce, zdjecia
	// sesja-pp-<nazwa>-0.jpg do porownania liczbowego
	if (argc > 3 && std::string(argv[3]) == "pp") {
		Cam2SessionConfig c = {};
		c.previewWidth = 1280;
		c.previewHeight = 720;
		c.stillWidth = 4032;
		c.stillHeight = 2268;
		int err = 0;
		void *S = cam2s_open("0", &c, &err);
		if (!S)
			return 4;
		struct Wariant {
			const char *nazwa;
			int kelvin, contrast, noise;
		} w[] = { { "auto", 0, 0, -1 }, { "k3000", 3000, 0, -1 }, { "k8000", 8000, 0, -1 },
			  { "kontrast-2", 0, -2, -1 }, { "kontrast2", 0, 2, -1 }, { "szum0", 0, 0, 0 }, { "szum2", 0, 0, 2 } };
		for (const Wariant &v : w) {
			Cam2Settings s = domyslne();
			s.torch = 1;
			s.iso = 200;
			s.expNs = 20000000; // stala ekspozycja, roznice tylko z przetwarzania
			s.kelvin = v.kelvin;
			s.contrast = v.contrast;
			s.noise = v.noise;
			cam2s_controls(S, &s);
			podglad(S, 1500);
			const std::string stara = katalog;
			katalog = stara + "/pp-" + v.nazwa;
			mkdir(katalog.c_str(), 0755);
			int r = cam2s_still(S, &s, naJpeg, naRaw, nullptr);
			katalog = stara;
			std::printf("  %s: %d JPEG\n", v.nazwa, r);
		}
		cam2s_close(S);
		return 0;
	}

	// 1. sesja zdjeciowa z recznym ISO i czasem, RAW
	Cam2SessionConfig c = {};
	c.previewWidth = 1280;
	c.previewHeight = 720;
	c.stillWidth = 4032;
	c.stillHeight = 2268;
	c.raw = 1;
	int err = 0;
	void *S = cam2s_open("0", &c, &err);
	std::printf("sesja zdjeciowa: %p blad %d\n", S, err);
	if (!S)
		return 2;
	Cam2Settings s = domyslne();
	s.iso = 400;
	s.expNs = 10000000;
	cam2s_controls(S, &s);
	int n = podglad(S, 1000);
	Cam2State st;
	cam2s_state(S, &st);
	std::printf("  podglad %d klatek/s, stan ISO %d %lld us\n", n, st.iso, st.expNs / 1000);
	s.raw = 1;
	int r = cam2s_still(S, &s, naJpeg, naRaw, nullptr);
	std::printf("  zdjecie: %d JPEG\n", r);

	// 2. pol-reczne: ISO 800, czas z pomiaru
	s = domyslne();
	s.iso = 800;
	cam2s_controls(S, &s);
	for (int i = 0; i < 20; i++) {
		podglad(S, 100);
		cam2s_state(S, &st);
	}
	std::printf("  pol-reczne ISO 800: stan ISO %d %lld us\n", st.iso, st.expNs / 1000);
	cam2s_close(S);

	// 3. sesja wideo, 5 s z dzwiekiem (sinus 440 Hz jak z mikrofonu, czas monotoniczny)
	c = {};
	c.previewWidth = 1280;
	c.previewHeight = 720;
	c.video = 1;
	c.videoWidth = 1920;
	c.videoHeight = 1080;
	c.fps = 30;
	S = cam2s_open("0", &c, &err);
	std::printf("sesja wideo: %p blad %d\n", S, err);
	if (!S)
		return 3;
	s = domyslne();
	cam2s_controls(S, &s);
	podglad(S, 500);
	for (int rund = 0; rund < 2; rund++) {
		const std::string plik = katalog + "/sesja-" + std::to_string(rund) + ".mp4";
		int fd = open(plik.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
		r = cam2s_record_start(S, fd, 90, 48000, 2);
		long long t0 = nowUs(), ramki = 0;
		int klatki = 0;
		std::vector<short> pcm(2048);
		void *poprz = nullptr;
		while (nowUs() - t0 < 5000000) {
			usleep(5000);
			while ((nowUs() - t0) * 48 / 1000 >= ramki + 1024) {
				for (int k = 0; k < 1024; k++)
					pcm[2 * k] = pcm[2 * k + 1] = (short)(8000 * std::sin(2 * M_PI * 440 * (ramki + k) / 48000.0));
				cam2s_record_audio(S, pcm.data(), 4096, t0 + ramki * 1000000 / 48000);
				ramki += 1024;
			}
			cam2s_record_pump(S);
			void *ahb = nullptr;
			void *f = cam2s_acquire(S, &ahb);
			if (f) {
				klatki++;
				cam2s_release(S, poprz);
				poprz = f;
			}
		}
		cam2s_release(S, poprz);
		cam2s_record_stop(S);
		int koniec = 0, k = 0;
		for (; k < 300 && !koniec; k++) {
			koniec = cam2s_record_pump(S) == 1;
			usleep(10000);
		}
		close(fd);
		std::printf("  nagranie %d: start %d, podglad w trakcie %d klatek, zamkniete %d po %d ms -> %s\n", rund, r,
			    klatki, koniec, k * 10, plik.c_str());
	}
	cam2s_close(S);
	std::printf("JPEG zapisanych: %d\n", jpegi);
	return 0;
}
