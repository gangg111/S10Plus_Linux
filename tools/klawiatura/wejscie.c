// SPDX-License-Identifier: GPL-2.0
// Czytanie ekranu dotykowego i przyciskow obudowy.

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/input.h>

#include "wejscie.h"

long long teraz_ms(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static int otworz_po_nazwie(const char *szukana)
{
	DIR *d = opendir("/dev/input");
	struct dirent *w;
	int fd = -1;

	if (!d) {
		perror("/dev/input");
		return -1;
	}
	while ((w = readdir(d))) {
		char sciezka[280], nazwa[128] = "";

		if (strncmp(w->d_name, "event", 5))
			continue;
		snprintf(sciezka, sizeof(sciezka), "/dev/input/%s", w->d_name);
		fd = open(sciezka, O_RDONLY | O_NONBLOCK);
		if (fd < 0)
			continue;
		if (ioctl(fd, EVIOCGNAME(sizeof(nazwa)), nazwa) >= 0 &&
		    !strcmp(nazwa, szukana))
			break;
		close(fd);
		fd = -1;
	}
	closedir(d);
	if (fd < 0)
		fprintf(stderr, "nie ma urzadzenia wejsciowego o nazwie \"%s\"\n",
			szukana);
	return fd;
}

static void pobierz_zakres(int fd, int os, int *min, int *max)
{
	struct input_absinfo a;

	memset(&a, 0, sizeof(a));
	if (ioctl(fd, EVIOCGABS(os), &a) < 0 || a.maximum <= a.minimum) {
		*min = 0;
		*max = 4096;
		return;
	}
	*min = a.minimum;
	*max = a.maximum;
}

/*
 * Zabiera urzadzenie na wylacznosc, zeby jego zdarzenia nie szly dalej.
 *
 * Oba urzadzenia maja w jadrze uchwyt kbd, czyli wszystko, co z nich
 * przychodzi, trafia do konsoli jako naciskany klawisz.  Zmierzone
 * 23.09.2026: przycisk sciszania wpisywal w wiersz logowania ^[[26~, a przy
 * zgaszonym ekranie te znaki czekaly i wylewaly sie po obudzeniu.  Przy
 * wpisywaniu hasla to nie jest kosmetyka.  Ekran dotykowy ma uchwyt kbd od
 * latki 0099, bo zglasza KEY_WAKEUP.
 *
 * Wylacznosc znika sama z zamknieciem deskryptora, wiec po padzie tego
 * programu przyciski wracaja do konsoli i nic nie zostaje zablokowane.
 */
static void zabierz(int fd, const char *co)
{
	if (ioctl(fd, EVIOCGRAB, 1) < 0)
		fprintf(stderr, "nie zabralem %s na wylacznosc: %s\n", co,
			strerror(errno));
}

int wejscie_otworz(struct wejscie *w, const char *nazwa_dotyku,
		   const char *nazwa_klawiszy, int szer, int wys)
{
	memset(w, 0, sizeof(*w));
	w->fd_dotyk = otworz_po_nazwie(nazwa_dotyku);
	if (w->fd_dotyk < 0)
		return -1;
	w->fd_klawisze = otworz_po_nazwie(nazwa_klawiszy);
	if (w->fd_klawisze < 0) {
		close(w->fd_dotyk);
		w->fd_dotyk = -1;
		return -1;
	}

	zabierz(w->fd_dotyk, nazwa_dotyku);
	zabierz(w->fd_klawisze, nazwa_klawiszy);

	pobierz_zakres(w->fd_dotyk, ABS_MT_POSITION_X, &w->x_min, &w->x_max);
	pobierz_zakres(w->fd_dotyk, ABS_MT_POSITION_Y, &w->y_min, &w->y_max);
	w->szer = szer;
	w->wys = wys;
	w->surowy_x = -1;
	w->surowy_y = -1;
	w->cisza_ms = 80;
	w->mowi_o_puszczeniu = 0;
	return 0;
}

void wejscie_zamknij(struct wejscie *w)
{
	if (w->fd_dotyk >= 0)
		close(w->fd_dotyk);
	if (w->fd_klawisze >= 0)
		close(w->fd_klawisze);
	memset(w, 0, sizeof(*w));
	w->fd_dotyk = -1;
	w->fd_klawisze = -1;
}

/* Osie dotyku pokrywaja sie z osiami panelu: X w poziomie, Y w pionie, obie
 * rosnace, obie znormalizowane do 0..4096 niezaleznie od proporcji ekranu.
 *
 * Wczesniej bylo tu przeliczenie z obrotem o 90 stopni, wyciagniete z pomiaru
 * czterech rogow.  Pomiar byl prawdziwy, ale wniosek falszywy: telefon lezal
 * wtedy inaczej, niz zakladalem, wiec "lewy gorny rog" nie byl lewym gornym.
 * Rozstrzygnela dopiero zywa klawiatura: dotkniecie klawisza r trafialo w 8,
 * a te same surowe wartosci przy mapowaniu bez obrotu wypadaja w srodku r.
 */
static void przelicz(struct wejscie *w)
{
	int zx = w->x_max - w->x_min;
	int zy = w->y_max - w->y_min;
	long long px, py;

	if (zx <= 0 || zy <= 0)
		return;

	px = (long long)(w->surowy_x - w->x_min) * w->szer / zx;
	py = (long long)(w->surowy_y - w->y_min) * w->wys / zy;

	if (px < 0)
		px = 0;
	if (py < 0)
		py = 0;
	if (px > w->szer - 1)
		px = w->szer - 1;
	if (py > w->wys - 1)
		py = w->wys - 1;

	w->x = (int)px;
	w->y = (int)py;
}

/* Czyta strumien panelu i zwraca jedno zdarzenie na RAMKE.
 *
 * Ramka konczy sie SYN_REPORT i dopiero na nim wolno cokolwiek orzekac.
 * Zmierzone, czemu to wazne: ramka puszczenia wyglada tak jak
 *   ABS_MT_TRACKING_ID -1, BTN_TOUCH 0, SYN_REPORT,
 * wiec wyjscie z petli zaraz po zwolnieniu sladu zostawialo w kolejce
 * BTN_TOUCH i SYN_REPORT.  Nastepne wywolanie bralo ten SYN_REPORT za nowa
 * ramke i przy ostatniej znanej pozycji zglaszalo POSTAWIENIE palca, ktorego
 * nie bylo: jedno dotkniecie sztucznego palca dawalo dwa razy "z".  Skoro
 * znak wychodzi teraz przy puszczeniu, taki duch wpisalby litere dwa razy.
 *
 * Puszczenie poznajemy po BTN_TOUCH albo po zwolnieniu sladu, a nie po ciszy
 * w strumieniu: panel nie przysyla paczek, dopoki palec lezy bez ruchu, wiec
 * cisza znaczylaby, ze przytrzymanie nigdy nie doczeka swoich 350 ms.
 * Sterownik po poprawkach 0093 i 0094 wysyla oba znaki zycia (zmierzone
 * w measurements/2026-09-21-dotyk-protokol), a cisza zostaje jako droga
 * zapasowa dla panelu, ktory o puszczeniu nie mowi nic.
 */
static enum zdarzenie czytaj_dotyk(struct wejscie *w)
{
	struct input_event ev;
	enum zdarzenie wynik = ZD_BRAK;
	int puszczony = 0, budzenie = 0, byly_osie = 0;

	while (read(w->fd_dotyk, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
		/* Dwuklik przy zgaszonym ekranie rozpoznaje sam uklad i oddaje
		 * go jako KEY_WAKEUP, bez zadnych wspolrzednych (latka 0099).
		 * Jego ramki nie wolno potraktowac jak dotkniecia: SYN_REPORT
		 * bez osi zglosilby postawienie palca w ostatnim znanym
		 * miejscu, czyli ducha, o ktorym mowa wyzej. */
		if (ev.type == EV_KEY && ev.code == KEY_WAKEUP) {
			if (ev.value == 1)
				budzenie = 1;
			continue;
		}
		if (ev.type == EV_ABS) {
			byly_osie = 1;
			switch (ev.code) {
			case ABS_MT_POSITION_X:
			case ABS_X:
				w->surowy_x = ev.value;
				break;
			case ABS_MT_POSITION_Y:
			case ABS_Y:
				w->surowy_y = ev.value;
				break;
			case ABS_MT_TRACKING_ID:
				if (ev.value < 0) {
					w->mowi_o_puszczeniu = 1;
					puszczony = 1;
				}
				break;
			}
			continue;
		}
		if (ev.type == EV_KEY && ev.code == BTN_TOUCH) {
			w->mowi_o_puszczeniu = 1;
			if (!ev.value)
				puszczony = 1;
			continue;
		}
		if (ev.type != EV_SYN || ev.code != SYN_REPORT)
			continue;

		if (!byly_osie && !puszczony)
			continue;
		byly_osie = 0;

		if (puszczony) {
			puszczony = 0;
			if (w->dotyka) {
				w->dotyka = 0;
				return ZD_DOTYK_KONIEC;
			}
			continue;
		}
		if (w->surowy_x < 0 || w->surowy_y < 0)
			continue;

		w->ostatnia_paczka_ms = teraz_ms();
		przelicz(w);
		if (!w->dotyka) {
			w->dotyka = 1;
			wynik = ZD_DOTYK_START;
		} else if (wynik == ZD_BRAK) {
			wynik = ZD_DOTYK_RUCH;
		}
	}
	if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR)
		return ZD_BLAD;
	if (budzenie)
		return ZD_BUDZENIE;
	return wynik;
}

/* Dluzej niz tyle to juz nie jest krotkie nacisniecie, tylko przytrzymanie,
 * i przy puszczeniu ekranu nie przelaczamy. */
#define ZASILANIE_KROTKO_MS	1500

static enum zdarzenie czytaj_klawisze(struct wejscie *w)
{
	struct input_event ev;
	enum zdarzenie wynik = ZD_BRAK;

	while (read(w->fd_klawisze, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
		/* Autopowtarzanie (wartosc 2) nic tu nie znaczy. */
		if (ev.type != EV_KEY || ev.value == 2)
			continue;

		/* Przycisk zasilania nie wylacza tu telefonu jednym
		 * nacisnieciem, tylko gasi i budzi ekran, jak w kazdym
		 * telefonie; wylacza dopiero dziesiec sekund przytrzymania,
		 * liczone w petli glownej.  Zeby systemd nie wlaczal sie
		 * w to po swojemu, obraz niesie HandlePowerKey=ignore i
		 * HandlePowerKeyLongPress=ignore. */
		if (ev.code == KEY_POWER) {
			if (ev.value == 1) {
				w->zasilanie = 1;
				w->zasilanie_od_ms = teraz_ms();
				w->kombinacja = w->inne_wcisniete > 0;
			} else if (w->zasilanie) {
				long long ile = teraz_ms() - w->zasilanie_od_ms;

				w->zasilanie = 0;
				if (!w->kombinacja && ile < ZASILANIE_KROTKO_MS)
					wynik = ZD_EKRAN;
			}
			continue;
		}

		/* Kazdy inny przycisk obudowy.  Wcisniety razem z zasilaniem,
		 * w dowolnej kolejnosci, robi z calosci kombinacje. */
		if (ev.value == 1) {
			w->inne_wcisniete++;
			if (w->zasilanie)
				w->kombinacja = 1;
			else if (ev.code == KEY_COFFEE)
				wynik = ZD_PRZELACZ;
		} else if (w->inne_wcisniete > 0) {
			w->inne_wcisniete--;
		}
	}
	if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR)
		return ZD_BLAD;
	return wynik;
}

enum zdarzenie wejscie_pobierz(struct wejscie *w, int czekaj_ms)
{
	struct pollfd p[2];
	enum zdarzenie z;
	int limit = czekaj_ms;

	/* Skoro koniec dotkniecia poznajemy po ciszy, czekanie nie moze byc
	 * dluzsze niz ta cisza, dopoki palec jest na ekranie.  Gdy panel mowi
	 * o puszczeniu wprost, skracanie nie jest do niczego potrzebne. */
	if (w->dotyka && !w->mowi_o_puszczeniu &&
	    (limit < 0 || limit > w->cisza_ms))
		limit = w->cisza_ms;

	p[0].fd = w->fd_dotyk;
	p[0].events = POLLIN;
	p[1].fd = w->fd_klawisze;
	p[1].events = POLLIN;

	if (poll(p, 2, limit) < 0 && errno != EINTR)
		return ZD_BLAD;

	if (p[1].revents & POLLIN) {
		z = czytaj_klawisze(w);
		if (z != ZD_BRAK)
			return z;
	}
	if (p[0].revents & POLLIN) {
		z = czytaj_dotyk(w);
		if (z != ZD_BRAK)
			return z;
	}
	if (w->dotyka && !w->mowi_o_puszczeniu &&
	    teraz_ms() - w->ostatnia_paczka_ms >= w->cisza_ms) {
		w->dotyka = 0;
		return ZD_DOTYK_KONIEC;
	}
	return ZD_BRAK;
}
