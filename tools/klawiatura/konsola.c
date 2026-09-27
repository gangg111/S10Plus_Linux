// SPDX-License-Identifier: GPL-2.0
// Zwezenie konsoli tekstowej, zeby zwolnila dolny pas ekranu.

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/fb.h>
#include <linux/kd.h>
#include <linux/vt.h>

#include "konsola.h"

static int wysokosc_ekranu(void)
{
	struct fb_var_screeninfo var;
	int fd, h = 0;

	fd = open("/dev/fb0", O_RDONLY);
	if (fd < 0)
		return 0;
	if (ioctl(fd, FBIOGET_VSCREENINFO, &var) == 0)
		h = (int)var.yres;
	close(fd);
	return h;
}

int konsola_otworz(struct konsola *k, const char *sciezka)
{
	struct winsize ws;

	memset(k, 0, sizeof(*k));
	k->fd = open(sciezka, O_RDWR | O_NOCTTY);
	if (k->fd < 0) {
		perror(sciezka);
		return -1;
	}
	if (ioctl(k->fd, TIOCGWINSZ, &ws) < 0 || !ws.ws_row) {
		perror("odczyt rozmiaru konsoli");
		close(k->fd);
		k->fd = -1;
		return -1;
	}

	k->wysokosc_px = wysokosc_ekranu();
	if (!k->wysokosc_px) {
		fprintf(stderr, "nie znam wysokosci ekranu\n");
		close(k->fd);
		k->fd = -1;
		return -1;
	}

	/* Wysokosc znaku bierzemy z ilorazu, bo KDFONTOP zwraca ja tylko dla
	 * czcionek zaladowanych z przestrzeni uzytkownika, a nasza jest
	 * wbudowana w jadro. */
	k->komorka = k->wysokosc_px / ws.ws_row;
	if (k->komorka < 8) {
		fprintf(stderr, "policzona wysokosc znaku %d jest bez sensu\n",
			k->komorka);
		close(k->fd);
		k->fd = -1;
		return -1;
	}
	k->wiersze_pelne = k->wysokosc_px / k->komorka;
	k->kolumny = ws.ws_col;
	return 0;
}

void konsola_zamknij(struct konsola *k)
{
	if (k->fd >= 0)
		close(k->fd);
	memset(k, 0, sizeof(*k));
	k->fd = -1;
}

static int ustaw_wiersze(struct konsola *k, int wiersze)
{
	struct vt_consize cs;
	struct vt_sizes vs;

	memset(&cs, 0, sizeof(cs));
	cs.v_rows = (unsigned short)wiersze;
	cs.v_cols = (unsigned short)k->kolumny;
	cs.v_vlin = (unsigned short)(wiersze * k->komorka);
	cs.v_clin = (unsigned short)k->komorka;
	if (ioctl(k->fd, VT_RESIZEX, &cs) == 0)
		return 0;

	/* Starsze wywolanie nie zna wysokosci znaku; sterownik potrafi odmowic
	 * nowszego, gdy nie ma listy trybow. */
	memset(&vs, 0, sizeof(vs));
	vs.v_rows = (unsigned short)wiersze;
	vs.v_cols = (unsigned short)k->kolumny;
	if (ioctl(k->fd, VT_RESIZE, &vs) == 0)
		return 0;

	perror("zmiana rozmiaru konsoli");
	return -1;
}

int konsola_zwez(struct konsola *k, int px)
{
	int oddane_wiersze = (px + k->komorka - 1) / k->komorka;
	int zostaje = k->wiersze_pelne - oddane_wiersze;

	if (zostaje < 10) {
		fprintf(stderr, "po oddaniu %d pikseli konsoli zostaloby %d wierszy\n",
			px, zostaje);
		return -1;
	}
	if (ustaw_wiersze(k, zostaje) < 0)
		return -1;

	k->zwezona = 1;
	return oddane_wiersze * k->komorka;
}

int konsola_przywroc(struct konsola *k)
{
	/* Liczymy od wysokosci ekranu, a nie od stanu biezacego, zeby
	 * wywolanie bylo bezpieczne po padzie programu i powtarzalne. */
	if (ustaw_wiersze(k, k->wiersze_pelne) < 0)
		return -1;
	k->zwezona = 0;
	return 0;
}

void konsola_odgas(struct konsola *k)
{
	char odgas = 4;		/* TIOCL_UNBLANKSCREEN */

	/* Samo odgaszenie, bez ruszania czasu do wygaszenia: ten ustawia
	 * wiersz rozruchowy (consoleblank) i ma zostac, jaki jest. */
	if (ioctl(k->fd, TIOCLINUX, &odgas) < 0 && errno != EPERM)
		perror("odgaszenie ekranu");
}

void konsola_zgas(struct konsola *k)
{
	char zgas = 14;		/* TIOCL_BLANKSCREEN */

	if (ioctl(k->fd, TIOCLINUX, &zgas) < 0 && errno != EPERM)
		perror("wygaszenie ekranu");
}

int konsola_zgaszona(const struct konsola *k)
{
	char pytanie = 15;	/* TIOCL_BLANKEDSCREEN */

	/* Jadro zwraca numer wygaszonej konsoli powiekszony o jeden, a zero,
	 * gdy zadna nie jest wygaszona. */
	return ioctl(k->fd, TIOCLINUX, &pytanie) > 0;
}

int konsola_aktywna(const struct konsola *k)
{
	struct vt_stat st;

	if (ioctl(k->fd, VT_GETSTATE, &st) < 0)
		return -1;
	return st.v_active;
}
