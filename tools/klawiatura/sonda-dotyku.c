// SPDX-License-Identifier: GPL-2.0
// Pomiar wejsciowy przed napisaniem klawiatury ekranowej.
//
// Po co: obie osie ekranu dotykowego maja ten sam zakres 0 do 4096, wiec
// z opisu urzadzenia NIE WYNIKA ani orientacja, ani ktore pole odpowiada osi
// poziomej panelu, ani czy ktoras os jest odwrocona. Mapowanie dotkniecia na
// piksel bez tego pomiaru byloby zgadywaniem, a pomylka daje klawiature
// dzialajaca w lustrzanym odbiciu.
//
// Nowy punkt rozpoznajemy po PRZERWIE w strumieniu, a nie po identyfikatorze
// sladu: ten kontroler go nie wysyla, wiec czekanie na niego konczy sie
// programem, ktory milczy mimo dotykania ekranu (zmierzone).
//
// Uzycie: sonda-dotyku /dev/input/eventN [ile punktow] [przerwa w ms]

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/input.h>

static void zakres(int fd, int os, const char *nazwa)
{
	struct input_absinfo a;

	memset(&a, 0, sizeof(a));
	if (ioctl(fd, EVIOCGABS(os), &a) < 0)
		return;
	printf("  %-18s od %d do %d, biezaca %d\n", nazwa, a.minimum, a.maximum,
	       a.value);
}

int main(int argc, char **argv)
{
	static const char *PUNKTY[] = {
		"lewy GORNY rog",
		"prawy GORNY rog",
		"lewy DOLNY rog",
		"prawy DOLNY rog",
		"SRODEK ekranu",
	};
	const int PUNKTOW = sizeof(PUNKTY) / sizeof(PUNKTY[0]);
	struct input_event ev;
	char nazwa[128] = "";
	long long ostatnia = 0, przerwa_us;
	int fd, ile, numer = 0, odstepow = 0;
	int x = -1, y = -1, nacisk = -1;
	int nowy = 1;

	if (argc < 2) {
		fprintf(stderr, "uzycie: %s /dev/input/eventN [ile] [przerwa ms]\n",
			argv[0]);
		return 2;
	}
	ile = (argc > 2) ? atoi(argv[2]) : PUNKTOW;
	if (ile > PUNKTOW)
		ile = PUNKTOW;
	przerwa_us = ((argc > 3) ? atoi(argv[3]) : 400) * 1000LL;

	fd = open(argv[1], O_RDONLY);
	if (fd < 0) {
		perror(argv[1]);
		return 1;
	}
	if (ioctl(fd, EVIOCGNAME(sizeof(nazwa)), nazwa) >= 0)
		printf("urzadzenie: %s\n", nazwa);
	printf("zakresy osi prosto z jadra:\n");
	zakres(fd, ABS_MT_POSITION_X, "ABS_MT_POSITION_X");
	zakres(fd, ABS_MT_POSITION_Y, "ABS_MT_POSITION_Y");
	zakres(fd, ABS_MT_SLOT, "ABS_MT_SLOT");
	printf("\ndotknij %d punktow, kazdy jednym palcem, z sekunda przerwy\n\n",
	       ile);
	printf("=> teraz: %s\n", PUNKTY[0]);
	fflush(stdout);

	while (numer < ile) {
		long long teraz;

		if (read(fd, &ev, sizeof(ev)) != sizeof(ev))
			break;
		teraz = (long long)ev.time.tv_sec * 1000000 + ev.time.tv_usec;

		if (ev.type == EV_ABS) {
			/* Slot nas nie obchodzi: mierzymy jeden palec naraz,
			 * a kontroler potrafi przydzielic mu dowolny numer. */
			if (ev.code == ABS_MT_POSITION_X || ev.code == ABS_X)
				x = ev.value;
			else if (ev.code == ABS_MT_POSITION_Y || ev.code == ABS_Y)
				y = ev.value;
			else if (ev.code == ABS_MT_PRESSURE)
				nacisk = ev.value;
			continue;
		}
		if (ev.type != EV_SYN || ev.code != SYN_REPORT)
			continue;

		if (ostatnia && teraz - ostatnia > przerwa_us)
			nowy = 1;

		if (nowy && x >= 0 && y >= 0) {
			printf("   %-18s X=%4d  Y=%4d  nacisk=%d\n",
			       PUNKTY[numer], x, y, nacisk);
			numer++;
			if (numer < ile)
				printf("=> teraz: %s\n", PUNKTY[numer]);
			nowy = 0;
			fflush(stdout);
		} else if (odstepow < 8 && ostatnia &&
			   teraz - ostatnia < przerwa_us) {
			/* Jak czesto uklad zglasza ruch, czyli ile czasu ma
			 * petla klawiatury miedzy paczkami. */
			printf("      odstep paczek %lld us\n", teraz - ostatnia);
			odstepow++;
			fflush(stdout);
		}
		ostatnia = teraz;
	}

	printf("\npomiar zakonczony\n");
	close(fd);
	return 0;
}
