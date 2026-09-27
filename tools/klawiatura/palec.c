// SPDX-License-Identifier: GPL-2.0
// Sztuczny palec: ekran dotykowy z /dev/uinput, do prob bez czlowieka.
//
// Po co to jest.  Przytrzymanie klawisza rozni sie od dotkniecia tylko CZASEM,
// wiec bez palca na szybie nie da sie sprawdzic, czy krotkie dotkniecie daje
// litere, a dlugie jej ogonek.  Ten program udaje panel: zglasza te same
// zdarzenia, co sterownik s6sy761 po poprawkach 0093 i 0094, czyli slad
// (ABS_MT_TRACKING_ID), pozycje i BTN_TOUCH.  Klawiatura uruchomiona
// z --dotyk "sztuczny palec" czyta z niego zamiast z szyby.
//
// Wazne dla proby przytrzymania: miedzy postawieniem i zdjeciem palca program
// NIE wysyla NICZEGO.  Prawdziwy panel tez milczy, dopoki palec sie nie rusza,
// wiec tylko tak sprawdza sie, czy klawiatura nie uzna ciszy za puszczenie.
//
//   palec [--czekaj MS] X Y MS [X Y MS ...]
//
// --czekaj daje czas na wystartowanie klawiatury, bo ona szuka urzadzenia po
// nazwie RAZ, przy starcie: najpierw musi istniec palec, potem klawiatura.
//
// Wspolrzedne sa w pikselach ekranu, bo urzadzenie zglasza zakres 0..1439
// i 0..3039, czyli jeden do jednego z panelem telefonu.
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/uinput.h>

#define SZEROKOSC	1439
#define WYSOKOSC	3039

static int wyslij(int fd, unsigned short typ, unsigned short kod, int wartosc)
{
	struct input_event ev;

	memset(&ev, 0, sizeof(ev));
	ev.type = typ;
	ev.code = kod;
	ev.value = wartosc;
	if (write(fd, &ev, sizeof(ev)) != (ssize_t)sizeof(ev)) {
		perror("zapis zdarzenia dotyku");
		return -1;
	}
	return 0;
}

static void spij_ms(int ms)
{
	struct timespec t;

	t.tv_sec = ms / 1000;
	t.tv_nsec = (long)(ms % 1000) * 1000000;
	nanosleep(&t, NULL);
}

static int os(int fd, unsigned short kod, int min, int max)
{
	struct uinput_abs_setup a;

	memset(&a, 0, sizeof(a));
	a.code = kod;
	a.absinfo.minimum = min;
	a.absinfo.maximum = max;
	if (ioctl(fd, UI_ABS_SETUP, &a) < 0) {
		perror("opis osi");
		return -1;
	}
	return 0;
}

static int otworz(void)
{
	struct uinput_setup opis;
	int fd = open("/dev/uinput", O_WRONLY);

	if (fd < 0) {
		perror("/dev/uinput");
		return -1;
	}
	if (ioctl(fd, UI_SET_EVBIT, EV_ABS) < 0 ||
	    ioctl(fd, UI_SET_EVBIT, EV_KEY) < 0 ||
	    ioctl(fd, UI_SET_EVBIT, EV_SYN) < 0 ||
	    ioctl(fd, UI_SET_KEYBIT, BTN_TOUCH) < 0 ||
	    /* Bez tej wlasciwosci jadro widzi gladzik, a nie szybe, i inaczej
	     * traktuje wspolrzedne. */
	    ioctl(fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT) < 0) {
		perror("zgloszenie rodzajow zdarzen");
		close(fd);
		return -1;
	}
	if (os(fd, ABS_MT_SLOT, 0, 9) < 0 ||
	    os(fd, ABS_MT_TRACKING_ID, 0, 65535) < 0 ||
	    os(fd, ABS_MT_POSITION_X, 0, SZEROKOSC) < 0 ||
	    os(fd, ABS_MT_POSITION_Y, 0, WYSOKOSC) < 0 ||
	    os(fd, ABS_X, 0, SZEROKOSC) < 0 ||
	    os(fd, ABS_Y, 0, WYSOKOSC) < 0) {
		close(fd);
		return -1;
	}

	memset(&opis, 0, sizeof(opis));
	opis.id.bustype = BUS_VIRTUAL;
	opis.id.vendor = 0x0002;
	opis.id.product = 0x0002;
	opis.id.version = 1;
	snprintf(opis.name, sizeof(opis.name), "sztuczny palec");
	if (ioctl(fd, UI_DEV_SETUP, &opis) < 0 ||
	    ioctl(fd, UI_DEV_CREATE) < 0) {
		perror("utworzenie sztucznego palca");
		close(fd);
		return -1;
	}
	return fd;
}

static int postaw(int fd, int x, int y, int slad)
{
	return wyslij(fd, EV_ABS, ABS_MT_SLOT, 0) ||
	       wyslij(fd, EV_ABS, ABS_MT_TRACKING_ID, slad) ||
	       wyslij(fd, EV_ABS, ABS_MT_POSITION_X, x) ||
	       wyslij(fd, EV_ABS, ABS_MT_POSITION_Y, y) ||
	       wyslij(fd, EV_ABS, ABS_X, x) ||
	       wyslij(fd, EV_ABS, ABS_Y, y) ||
	       wyslij(fd, EV_KEY, BTN_TOUCH, 1) ||
	       wyslij(fd, EV_SYN, SYN_REPORT, 0);
}

static int zdejmij(int fd)
{
	return wyslij(fd, EV_ABS, ABS_MT_SLOT, 0) ||
	       wyslij(fd, EV_ABS, ABS_MT_TRACKING_ID, -1) ||
	       wyslij(fd, EV_KEY, BTN_TOUCH, 0) ||
	       wyslij(fd, EV_SYN, SYN_REPORT, 0);
}

int main(int argc, char **argv)
{
	int fd, i, slad = 1, czekaj = 400, pierwszy = 1;

	if (argc > 2 && !strcmp(argv[1], "--czekaj")) {
		czekaj = atoi(argv[2]);
		pierwszy = 3;
	}
	if (argc - pierwszy < 3 || (argc - pierwszy) % 3) {
		fprintf(stderr, "uzycie: %s [--czekaj MS] X Y MS"
			" [X Y MS ...]\n", argv[0]);
		return 2;
	}

	fd = otworz();
	if (fd < 0)
		return 1;
	/* Klawiatura szuka urzadzenia po nazwie raz, przy starcie, wiec musi
	 * zdazyc je zobaczyc; udev nadaje prawa z opoznieniem. */
	printf("palec gotowy, czekam %d ms\n", czekaj);
	fflush(stdout);
	spij_ms(czekaj);

	for (i = pierwszy; i + 2 < argc; i += 3) {
		int x = atoi(argv[i]);
		int y = atoi(argv[i + 1]);
		int ms = atoi(argv[i + 2]);

		printf("palec: %d %d na %d ms\n", x, y, ms);
		fflush(stdout);
		if (postaw(fd, x, y, slad++))
			break;
		spij_ms(ms);
		if (zdejmij(fd))
			break;
		/* Przerwa miedzy dotknieciami, zeby nie zlaly sie w jedno. */
		spij_ms(400);
	}

	spij_ms(200);
	ioctl(fd, UI_DEV_DESTROY);
	close(fd);
	return 0;
}
