// SPDX-License-Identifier: GPL-2.0-only
/*
 * podbicie: podbicie interfejsu na czas interakcji, jak PowerHAL w Androidzie.
 *
 * Po co: zmierzone 25.09.2026 (measurements/2026-09-25-responsywnosc) watki
 * interfejsu (KWin, plasmashell, render Qt) chodza na malych rdzeniach przy
 * 442-507 MHz, bo schedutil widzi krotkie zrywy pracy i nie podnosi taktu.
 * Z uclamp.min = 1024 od dotyku do zatrzasnietej klatki jest 37 ms zamiast
 * 53 ms, a klatki przestaja wypadac (p99 odstepu 16,9 zamiast 33 ms).
 *
 * Jak: czyta zdarzenia dotyku (bez przejmowania urzadzenia). Na pierwsze
 * zdarzenie po bezczynnosci nadaje wszystkim watkom uzytkownika sesji
 * uclamp.min = PODBICIE (sched_setattr z SCHED_FLAG_KEEP_ALL, wiec polityka
 * i priorytet zostaja). Procesy uruchomione w trakcie dziedzicza wartosc po
 * rodzicu. PO ms po ostatnim zdarzeniu wszystkim watkom wraca SPOCZYNEK.
 *
 * Bez listy urzadzen slucha wszystkich /dev/input/event* i dolacza nowe
 * (inotify), wiec obejmuje tez klawiatury Bluetooth i ekrany z uinput.
 *
 * Uzycie: podbicie [-u uid] [-m podbicie] [-s spoczynek] [-t ms] [urzadzenie...]
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/inotify.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define SCHED_FLAG_KEEP_POLICY		0x08
#define SCHED_FLAG_KEEP_PARAMS		0x10
#define SCHED_FLAG_UTIL_CLAMP_MIN	0x20

struct sched_attr {
	uint32_t size;
	uint32_t sched_policy;
	uint64_t sched_flags;
	int32_t sched_nice;
	uint32_t sched_priority;
	uint64_t sched_runtime;
	uint64_t sched_deadline;
	uint64_t sched_period;
	uint32_t sched_util_min;
	uint32_t sched_util_max;
};

static uid_t uid = 10000;
static unsigned int podbicie = 1024, spoczynek, po = 1500;
/*
 * Procesy, ktore rysuja kazda klatke (kompozytor, powloka, klawiatura), maja
 * wlasny prog spoczynkowy, jak SurfaceFlinger i SystemUI: bez niego pierwsze
 * klatki gestu, zanim takty sie rozpedza, wypadaja (2 na 11 gestow).
 */
static char rysujace[256] = "kwin_wayland,plasmashell,plasma-keyboard";
static unsigned int prog_rysujacych = 512;

static int rysuje(const char *pid)
{
	char sciezka[64], nazwa[32], *k;
	const char *p = rysujace;
	FILE *f;
	size_t n;

	snprintf(sciezka, sizeof(sciezka), "/proc/%s/comm", pid);
	f = fopen(sciezka, "r");
	if (!f)
		return 0;
	if (!fgets(nazwa, sizeof(nazwa), f))
		nazwa[0] = 0;
	fclose(f);
	k = strchr(nazwa, '\n');
	if (k)
		*k = 0;
	n = strlen(nazwa);
	while (n && *p) {
		const char *przecinek = strchr(p, ',');
		size_t dl = przecinek ? (size_t)(przecinek - p) : strlen(p);

		if (dl == n && !strncmp(p, nazwa, n))
			return 1;
		if (!przecinek)
			break;
		p = przecinek + 1;
	}
	return 0;
}

static long long teraz_ms(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1000LL + t.tv_nsec / 1000000;
}

/* Nadaje uclamp.min wszystkim watkom procesow danego uzytkownika; zwraca liczbe watkow. */
static int ustaw(unsigned int min)
{
	struct sched_attr a = {
		.size = sizeof(a),
		.sched_flags = SCHED_FLAG_KEEP_POLICY | SCHED_FLAG_KEEP_PARAMS |
			       SCHED_FLAG_UTIL_CLAMP_MIN,
		.sched_util_min = min,
	};
	DIR *proc = opendir("/proc");
	struct dirent *p;
	int n = 0;

	if (!proc)
		return -1;
	while ((p = readdir(proc))) {
		char sciezka[64];
		struct stat st;
		DIR *zad;
		struct dirent *t;

		if (p->d_name[0] < '1' || p->d_name[0] > '9')
			continue;
		snprintf(sciezka, sizeof(sciezka), "/proc/%s", p->d_name);
		if (stat(sciezka, &st) || st.st_uid != uid)
			continue;
		snprintf(sciezka, sizeof(sciezka), "/proc/%s/task", p->d_name);
		zad = opendir(sciezka);
		if (!zad)
			continue;
		a.sched_util_min = min;
		if (min < prog_rysujacych && rysuje(p->d_name))
			a.sched_util_min = prog_rysujacych;
		while ((t = readdir(zad))) {
			if (t->d_name[0] < '1' || t->d_name[0] > '9')
				continue;
			if (!syscall(SYS_sched_setattr, atoi(t->d_name), &a, 0))
				n++;
		}
		closedir(zad);
	}
	closedir(proc);
	return n;
}

#define MAKS_FD 32
static struct pollfd fd[MAKS_FD];
static int nfd;

static void dodaj(const char *sciezka)
{
	unsigned long typy = 0;
	int f;

	if (nfd >= MAKS_FD)
		return;
	f = open(sciezka, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
	if (f < 0)
		return;
	/*
	 * Tylko urzadzenia, ktore daja interakcje.  Otwarcie samego silnika
	 * wibracji (tylko EV_FF) wlacza w sterowniku max77693-haptic jego
	 * zasilanie i trzyma je, dopoki deskryptor zyje: zmierzone 27.09.2026,
	 * vdd_motor enabled users=1 przez caly czas dzialania tego programu.
	 */
	if (ioctl(f, EVIOCGBIT(0, sizeof(typy)), &typy) < 0 ||
	    !(typy & (1UL << EV_KEY | 1UL << EV_ABS | 1UL << EV_REL))) {
		close(f);
		return;
	}
	fd[nfd].fd = f;
	fd[nfd].events = POLLIN;
	fd[nfd].revents = 0;
	nfd++;
}

static void dodaj_wszystkie(void)
{
	DIR *d = opendir("/dev/input");
	struct dirent *e;
	char sciezka[288];

	if (!d)
		return;
	while ((e = readdir(d)))
		if (!strncmp(e->d_name, "event", 5)) {
			snprintf(sciezka, sizeof(sciezka), "/dev/input/%s", e->d_name);
			dodaj(sciezka);
		}
	closedir(d);
}

int main(int argc, char **argv)
{
	int c, aktywne = 0, ino = -1, stale;
	long long koniec = 0;

	while ((c = getopt(argc, argv, "u:m:s:t:r:R:")) != -1) {
		switch (c) {
		case 'u': uid = atoi(optarg); break;
		case 'm': podbicie = atoi(optarg); break;
		case 's': spoczynek = atoi(optarg); break;
		case 't': po = atoi(optarg); break;
		case 'r': snprintf(rysujace, sizeof(rysujace), "%s", optarg); break;
		case 'R': prog_rysujacych = atoi(optarg); break;
		default:
			fprintf(stderr, "uzycie: %s [-u uid] [-m podbicie] [-s spoczynek] [-t ms] [-r procesy,...] [-R prog] [urzadzenie...]\n", argv[0]);
			return 2;
		}
	}
	if (optind < argc) {
		for (; optind < argc; optind++)
			dodaj(argv[optind]);
	} else {
		/* Pierwsze miejsce zajmuje inotify na /dev/input. */
		ino = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
		if (ino >= 0 && inotify_add_watch(ino, "/dev/input", IN_CREATE | IN_ATTRIB) >= 0) {
			fd[0].fd = ino;
			fd[0].events = POLLIN;
			nfd = 1;
		} else if (ino >= 0) {
			close(ino);
			ino = -1;
		}
		dodaj_wszystkie();
	}
	stale = ino >= 0 ? 1 : 0;
	if (nfd <= stale)
		return 1;
	fprintf(stderr, "podbicie: uid %u, %u w interakcji, %u w spoczynku, %u ms po ostatnim dotyku, urzadzen %d\n",
		(unsigned int)uid, podbicie, spoczynek, po, nfd);
	ustaw(spoczynek);

	for (;;) {
		int czekaj = aktywne ? (int)(koniec - teraz_ms()) : -1;
		int zdarzenie = 0, i;

		if (aktywne && czekaj <= 0) {
			ustaw(spoczynek);
			aktywne = 0;
			continue;
		}
		if (poll(fd, nfd, czekaj) < 0 && errno != EINTR)
			return 1;
		for (i = stale; i < nfd; i++) {
			struct input_event ev[64];
			ssize_t r;

			if (!(fd[i].revents & (POLLIN | POLLERR | POLLHUP)))
				continue;
			while ((r = read(fd[i].fd, ev, sizeof(ev))) > 0)
				zdarzenie = 1;
			if (r < 0 && errno == ENODEV) {
				/* Urzadzenie zniknelo (np. koniec uinput): zamknij i usun. */
				close(fd[i].fd);
				fd[i] = fd[--nfd];
				i--;
			}
		}
		if (ino >= 0 && (fd[0].revents & POLLIN)) {
			char buf[4096] __attribute__((aligned(__alignof__(struct inotify_event))));
			ssize_t r = read(ino, buf, sizeof(buf));
			char *p;

			for (p = buf; r > 0 && p < buf + r;) {
				struct inotify_event *e = (struct inotify_event *)p;
				char sciezka[288];
				int j, jest = 0;

				if (e->len && !strncmp(e->name, "event", 5)) {
					snprintf(sciezka, sizeof(sciezka), "/dev/input/%s", e->name);
					for (j = stale; j < nfd; j++) {
						char lnk[64], cel[288];
						ssize_t k;

						snprintf(lnk, sizeof(lnk), "/proc/self/fd/%d", fd[j].fd);
						k = readlink(lnk, cel, sizeof(cel) - 1);
						if (k > 0) {
							cel[k] = 0;
							if (!strcmp(cel, sciezka))
								jest = 1;
						}
					}
					if (!jest)
						dodaj(sciezka);
				}
				p += sizeof(*e) + e->len;
			}
		}
		if (!zdarzenie)
			continue;
		koniec = teraz_ms() + po;
		if (!aktywne) {
			ustaw(podbicie);
			aktywne = 1;
		}
	}
}
