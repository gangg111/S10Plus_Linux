// SPDX-License-Identifier: GPL-2.0
// Rysowanie po buforze ramki dla klawiatury ekranowej.

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/fb.h>

#include "ekran.h"
#include "czcionka.h"
#include "czcionka-sans.h"

/* Zapowiedzi pomocnikow rysujacych: uzywaja sie nawzajem, wiec kolejnosc
 * definicji w pliku i tak nie da sie ulozyc tak, zeby wystarczyla. */
static void piksel(struct ekran *e, int x, int y, uint32_t kolor);
static void mieszaj(struct ekran *e, int x, int y, uint32_t kolor,
		    uint32_t tlo, int krycie);
static int krycie_brzegu(int d_x100, int r_x100);
static int pierwiastek(int n);

/* Pierwiastek calkowity, zeby nie ciagnac biblioteki matematycznej do
 * statycznej binarki dla jednego wywolania.  Metoda Newtona na liczbach
 * calkowitych: zbiega w kilku krokach dla wartosci, ktore tu wystepuja. */
static int pierwiastek(int n)
{
	int x, y;

	if (n <= 0)
		return 0;
	x = n;
	y = (x + 1) / 2;
	while (y < x) {
		x = y;
		y = (x + n / x) / 2;
	}
	return x;
}

/* Piksel mieszany z tlem wedlug krycia 0..256.
 *
 * Bez tego kazda krzywa jest schodkowa, a klawiatura wyglada jak zlepek
 * prostokatow.  Qt rysuje przez QPainter z wygladzaniem i to wlasnie ta roznica
 * decyduje o tym, czy naroznik klawisza wyglada na zaokraglony, czy na
 * poszarpany.  Skladowe wyciagamy z upakowanych kolorow, bo ile bitow ma ktora
 * wie tylko sterownik. */
static void mieszaj(struct ekran *e, int x, int y, uint32_t kolor,
		    uint32_t tlo, int krycie)
{
	uint32_t maska_r, maska_g, maska_b, kr, kg, kb, tr, tg, tb;

	if (krycie <= 0)
		return;
	if (krycie >= 256) {
		piksel(e, x, y, kolor);
		return;
	}
	maska_r = (1u << e->r_dl) - 1;
	maska_g = (1u << e->g_dl) - 1;
	maska_b = (1u << e->b_dl) - 1;
	kr = (kolor >> e->r_poz) & maska_r;
	kg = (kolor >> e->g_poz) & maska_g;
	kb = (kolor >> e->b_poz) & maska_b;
	tr = (tlo >> e->r_poz) & maska_r;
	tg = (tlo >> e->g_poz) & maska_g;
	tb = (tlo >> e->b_poz) & maska_b;
	piksel(e, x, y,
	       (((tr * (256 - krycie) + kr * krycie) >> 8) << e->r_poz) |
	       (((tg * (256 - krycie) + kg * krycie) >> 8) << e->g_poz) |
	       (((tb * (256 - krycie) + kb * krycie) >> 8) << e->b_poz));
}

/* Krycie piksela odleglego o d (w setnych) od krawedzi o promieniu r.
 * Przejscie rozlozone na jeden piksel, jak w zwyklym wygladzaniu. */
static int krycie_brzegu(int d_x100, int r_x100)
{
	int roznica = r_x100 + 50 - d_x100;

	if (roznica <= 0)
		return 0;
	if (roznica >= 100)
		return 256;
	return roznica * 256 / 100;
}


int ekran_otworz(struct ekran *e, const char *sciezka)
{
	struct fb_var_screeninfo var;
	struct fb_fix_screeninfo fix;

	memset(e, 0, sizeof(*e));
	e->fd = open(sciezka, O_RDWR);
	if (e->fd < 0) {
		perror(sciezka);
		return -1;
	}
	if (ioctl(e->fd, FBIOGET_VSCREENINFO, &var) < 0 ||
	    ioctl(e->fd, FBIOGET_FSCREENINFO, &fix) < 0) {
		perror("odczyt opisu bufora ramki");
		close(e->fd);
		e->fd = -1;
		return -1;
	}
	if (var.bits_per_pixel != 32) {
		fprintf(stderr, "bufor ramki ma %u bitow na piksel, a program umie 32\n",
			var.bits_per_pixel);
		close(e->fd);
		e->fd = -1;
		return -1;
	}

	e->szerokosc = var.xres;
	e->wysokosc = var.yres;
	e->wiersz = fix.line_length;
	e->r_poz = var.red.offset;   e->r_dl = var.red.length;
	e->g_poz = var.green.offset; e->g_dl = var.green.length;
	e->b_poz = var.blue.offset;  e->b_dl = var.blue.length;

	e->bufor = calloc(1, (size_t)e->wiersz * e->wysokosc);
	if (!e->bufor) {
		close(e->fd);
		e->fd = -1;
		return -1;
	}
	return 0;
}

int ekran_zastepczy(struct ekran *e, uint32_t szerokosc, uint32_t wysokosc)
{
	memset(e, 0, sizeof(*e));
	e->fd = -1;
	e->szerokosc = szerokosc;
	e->wysokosc = wysokosc;
	e->wiersz = szerokosc * 4;
	/* Ten sam uklad, co melduje sterownik panelu: BGRX. */
	e->r_poz = 16; e->r_dl = 8;
	e->g_poz = 8;  e->g_dl = 8;
	e->b_poz = 0;  e->b_dl = 8;
	e->bufor = calloc(1, (size_t)e->wiersz * e->wysokosc);
	return e->bufor ? 0 : -1;
}

int ekran_zapisz_ppm(const struct ekran *e, const char *sciezka, int y, int h)
{
	FILE *f;
	int i, j;

	if (y < 0)
		y = 0;
	if (h <= 0 || (uint32_t)y >= e->wysokosc)
		return -1;
	if ((uint32_t)(y + h) > e->wysokosc)
		h = (int)e->wysokosc - y;

	f = fopen(sciezka, "wb");
	if (!f) {
		perror(sciezka);
		return -1;
	}
	fprintf(f, "P6%c%u %d%c255%c", 10, e->szerokosc, h, 10, 10);
	for (j = 0; j < h; j++) {
		const uint8_t *w = e->bufor + (size_t)(y + j) * e->wiersz;

		for (i = 0; i < (int)e->szerokosc; i++) {
			uint32_t p = *(const uint32_t *)(w + (size_t)i * 4);
			unsigned char rgb[3];

			rgb[0] = (unsigned char)((p >> e->r_poz) &
						 ((1u << e->r_dl) - 1));
			rgb[1] = (unsigned char)((p >> e->g_poz) &
						 ((1u << e->g_dl) - 1));
			rgb[2] = (unsigned char)((p >> e->b_poz) &
						 ((1u << e->b_dl) - 1));
			fwrite(rgb, 1, 3, f);
		}
	}
	fclose(f);
	return 0;
}

void ekran_zamknij(struct ekran *e)
{
	free(e->bufor);
	if (e->fd >= 0)
		close(e->fd);
	memset(e, 0, sizeof(*e));
	e->fd = -1;
}

int ekran_ten_sam(const struct ekran *e)
{
	struct fb_var_screeninfo var;

	if (ioctl(e->fd, FBIOGET_VSCREENINFO, &var) < 0)
		return 0;
	return var.xres == e->szerokosc && var.yres == e->wysokosc &&
	       var.bits_per_pixel == 32;
}

uint32_t ekran_kolor(const struct ekran *e, uint8_t r, uint8_t g, uint8_t b)
{
	/* Kazda skladowa skracana do tylu bitow, ile zglosil sterownik. */
	uint32_t rr = (uint32_t)r >> (8 - e->r_dl);
	uint32_t gg = (uint32_t)g >> (8 - e->g_dl);
	uint32_t bb = (uint32_t)b >> (8 - e->b_dl);

	return (rr << e->r_poz) | (gg << e->g_poz) | (bb << e->b_poz);
}

static void piksel(struct ekran *e, int x, int y, uint32_t kolor)
{
	if (x < 0 || y < 0 ||
	    (uint32_t)x >= e->szerokosc || (uint32_t)y >= e->wysokosc)
		return;
	*(uint32_t *)(e->bufor + (size_t)y * e->wiersz + (size_t)x * 4) = kolor;
}

void rysuj_prostokat(struct ekran *e, int x, int y, int w, int h, uint32_t kolor)
{
	int i, j;

	for (j = y; j < y + h; j++)
		for (i = x; i < x + w; i++)
			piksel(e, i, j, kolor);
}

void rysuj_klawisz(struct ekran *e, int x, int y, int w, int h, int promien,
		   uint32_t tlo, uint32_t tlo_pod)
{
	int i, j;

	/* Srodek jednym prostokatem, a cztery naroznikowe kwadraty pikselem po
	 * pikselu z kryciem liczonym z odleglosci od srodka luku.  Poprzednia
	 * wersja skracala wiersze o stala, wiec rogi byly SCIETE, a nie
	 * zaokraglone, i do tego schodkowe.  Tlo pod klawiszem podajemy jawnie,
	 * bo bez niego nie ma z czym mieszac brzegu. */
	rysuj_prostokat(e, x, y + promien, w, h - 2 * promien, tlo);
	rysuj_prostokat(e, x + promien, y, w - 2 * promien, promien, tlo);
	rysuj_prostokat(e, x + promien, y + h - promien, w - 2 * promien,
			promien, tlo);

	for (j = 0; j < promien; j++)
		for (i = 0; i < promien; i++) {
			/* Odleglosc od srodka luku, liczona w setnych piksela,
			 * dla srodka piksela (stad dodane 50). */
			int dx = promien * 100 - (i * 100 + 50);
			int dy = promien * 100 - (j * 100 + 50);
			int d = pierwiastek(dx * dx + dy * dy);
			int k = krycie_brzegu(d, promien * 100);

			mieszaj(e, x + i, y + j, tlo, tlo_pod, k);
			mieszaj(e, x + w - 1 - i, y + j, tlo, tlo_pod, k);
			mieszaj(e, x + i, y + h - 1 - j, tlo, tlo_pod, k);
			mieszaj(e, x + w - 1 - i, y + h - 1 - j, tlo, tlo_pod, k);
		}
}

void rysuj_ramke(struct ekran *e, int x, int y, int w, int h, int promien,
		 uint32_t kolor)
{
	int i, j;

	/* Cztery boki bez naroznikow, potem sam luk: piksel nalezy do obwodki,
	 * gdy jego odleglosc od srodka luku miesci sie w ostatnim pikselu
	 * promienia.  Grubosc jednego piksela, jak border.width w QML. */
	rysuj_prostokat(e, x + promien, y, w - 2 * promien, 1, kolor);
	rysuj_prostokat(e, x + promien, y + h - 1, w - 2 * promien, 1, kolor);
	rysuj_prostokat(e, x, y + promien, 1, h - 2 * promien, kolor);
	rysuj_prostokat(e, x + w - 1, y + promien, 1, h - 2 * promien, kolor);

	for (j = 0; j < promien; j++)
		for (i = 0; i < promien; i++) {
			int dx = promien * 100 - (i * 100 + 50);
			int dy = promien * 100 - (j * 100 + 50);
			int d = pierwiastek(dx * dx + dy * dy);

			if (d > promien * 100 || d < (promien - 1) * 100)
				continue;
			piksel(e, x + i, y + j, kolor);
			piksel(e, x + w - 1 - i, y + j, kolor);
			piksel(e, x + i, y + h - 1 - j, kolor);
			piksel(e, x + w - 1 - i, y + h - 1 - j, kolor);
		}
}

static void glif(struct ekran *e, int x, int y, unsigned char znak, int skala,
		 uint32_t kolor)
{
	const unsigned char *dane = CZCIONKA + (size_t)znak * CZCIONKA_NA_GLIF;
	int w, k, sx, sy;

	for (w = 0; w < CZCIONKA_WYSOKOSC; w++) {
		unsigned int bity = ((unsigned int)dane[w * 2] << 8) | dane[w * 2 + 1];

		for (k = 0; k < CZCIONKA_SZEROKOSC; k++) {
			if (!(bity & (1u << (CZCIONKA_SZEROKOSC - 1 - k))))
				continue;
			for (sy = 0; sy < skala; sy++)
				for (sx = 0; sx < skala; sx++)
					piksel(e, x + k * skala + sx,
					       y + w * skala + sy, kolor);
		}
	}
}

void rysuj_tekst(struct ekran *e, int x, int y, const char *napis, int skala,
		 uint32_t kolor)
{
	const unsigned char *p;

	for (p = (const unsigned char *)napis; *p; p++) {
		glif(e, x, y, *p, skala, kolor);
		x += CZCIONKA_SZEROKOSC * skala;
	}
}

int tekst_szerokosc(const char *napis, int skala)
{
	return (int)strlen(napis) * CZCIONKA_SZEROKOSC * skala;
}

int tekst_wysokosc(int skala)
{
	return CZCIONKA_WYSOKOSC * skala;
}

int ekran_wyslij(struct ekran *e, int y, int h)
{
	size_t poczatek, zostalo, zrobione = 0;

	if (y < 0) {
		h += y;
		y = 0;
	}
	if (h <= 0 || (uint32_t)y >= e->wysokosc)
		return 0;
	if ((uint32_t)(y + h) > e->wysokosc)
		h = (int)e->wysokosc - y;

	poczatek = (size_t)y * e->wiersz;
	zostalo = (size_t)h * e->wiersz;

	/* pwrite potrafi zapisac mniej, niz poproszono, wiec domykamy petla. */
	while (zostalo) {
		ssize_t n = pwrite(e->fd, e->bufor + poczatek + zrobione,
				   zostalo, (off_t)(poczatek + zrobione));

		if (n < 0) {
			if (errno == EINTR)
				continue;
			perror("zapis do bufora ramki");
			return -1;
		}
		if (n == 0)
			return -1;
		zrobione += (size_t)n;
		zostalo -= (size_t)n;
	}
	return 0;
}

/* Wypelnione kolo; cegielka, z ktorej sklada sie odcinek o grubosci. */
static void dysk(struct ekran *e, int sx, int sy, int r, uint32_t kolor,
		 uint32_t tlo)
{
	int dx, dy;

	for (dy = -r - 1; dy <= r + 1; dy++)
		for (dx = -r - 1; dx <= r + 1; dx++) {
			int d = pierwiastek((dx * dx + dy * dy) * 10000);

			mieszaj(e, sx + dx, sy + dy, kolor, tlo,
				krycie_brzegu(d, r * 100));
		}
}

void rysuj_odcinek(struct ekran *e, int x0, int y0, int x1, int y1,
		   int grubosc, uint32_t kolor, uint32_t tlo)
{
	/* Dysk wedrujacy po odcinku, a nie obracany prostokat: konce wychodza
	 * zaokraglone, zalamania lacza sie bez szpar, i nie trzeba ani jednej
	 * funkcji trygonometrycznej.  Ikony sa male, wiec koszt nie gra roli. */
	int r = grubosc / 2;
	int dx = x1 - x0, dy = y1 - y0;
	int krokow = abs(dx) > abs(dy) ? abs(dx) : abs(dy);
	int i;

	if (r < 1)
		r = 1;
	if (krokow == 0) {
		dysk(e, x0, y0, r, kolor, tlo);
		return;
	}
	for (i = 0; i <= krokow; i++)
		dysk(e, x0 + dx * i / krokow, y0 + dy * i / krokow, r, kolor,
		     tlo);
}

/* Ksztalty opisane w kwadracie 0..1000, zeby nie uzywac ulamkow.  Kazdy wpis
 * to lamana: liczba punktow, potem pary wspolrzednych.  Lamana zamknieta ma
 * liczbe punktow ze znakiem minus. */
static const short IKONA_BACKSPACE_RAMKA[] = {
	-5,  80,500,  340,200,  920,200,  920,800,  340,800
};
static const short IKONA_BACKSPACE_X1[] = { 2, 520,380,  780,620 };
static const short IKONA_BACKSPACE_X2[] = { 2, 780,380,  520,620 };
static const short IKONA_ENTER_KRESKA[] = { 3, 840,220,  840,680,  260,680 };
static const short IKONA_ENTER_GROT[]   = { 3, 460,500,  240,680,  460,860 };
static const short IKONA_SHIFT_OBRYS[]  = {
	-7,  500,140,  860,500,  660,500,  660,840,  340,840,  340,500,  140,500
};
static const short IKONA_STRZALKA_TRZON[] = { 2, 500,840,  500,200 };
static const short IKONA_STRZALKA_GROT[]  = { 3, 280,440,  500,200,  720,440 };

/* Obrot punktu o cwierc obrotu w prawo, wokol srodka kwadratu 0..1000. */
static void cwiartka(int *px, int *py, int ile)
{
	int i;

	for (i = 0; i < ile; i++) {
		int t = *px;

		*px = 1000 - *py;
		*py = t;
	}
}

static void lamana(struct ekran *e, int x, int y, int bok, int cwiartek,
		   const short *op, int grubosc, uint32_t kolor, uint32_t tlo)
{
	int n = op[0] < 0 ? -op[0] : op[0];
	int zamknieta = op[0] < 0;
	int i;

	for (i = 0; i < n; i++) {
		int j = (i + 1) % n;
		int ax, ay, bx, by;

		if (!zamknieta && i == n - 1)
			break;

		ax = op[1 + 2 * i];     ay = op[2 + 2 * i];
		bx = op[1 + 2 * j];     by = op[2 + 2 * j];
		cwiartka(&ax, &ay, cwiartek);
		cwiartka(&bx, &by, cwiartek);

		rysuj_odcinek(e, x + ax * bok / 1000, y + ay * bok / 1000,
			      x + bx * bok / 1000, y + by * bok / 1000,
			      grubosc, kolor, tlo);
	}
}

void rysuj_ikone(struct ekran *e, int x, int y, int bok, enum ikona co,
		 uint32_t kolor, uint32_t tlo)
{
	int g = bok * 75 / 1000;		/* grubosc kreski, jak w QML */
	int cwiartek = 0;

	if (g < 3)
		g = 3;

	switch (co) {
	case IKONA_BACKSPACE:
		lamana(e, x, y, bok, 0, IKONA_BACKSPACE_RAMKA, g, kolor, tlo);
		lamana(e, x, y, bok, 0, IKONA_BACKSPACE_X1, g, kolor, tlo);
		lamana(e, x, y, bok, 0, IKONA_BACKSPACE_X2, g, kolor, tlo);
		return;
	case IKONA_ENTER:
		lamana(e, x, y, bok, 0, IKONA_ENTER_KRESKA, g, kolor, tlo);
		lamana(e, x, y, bok, 0, IKONA_ENTER_GROT, g, kolor, tlo);
		return;
	case IKONA_SHIFT:
		lamana(e, x, y, bok, 0, IKONA_SHIFT_OBRYS, g, kolor, tlo);
		return;
	case IKONA_GORA:	cwiartek = 0; break;
	case IKONA_PRAWO:	cwiartek = 1; break;
	case IKONA_DOL:		cwiartek = 2; break;
	case IKONA_LEWO:	cwiartek = 3; break;
	default:
		return;
	}
	lamana(e, x, y, bok, cwiartek, IKONA_STRZALKA_TRZON, g, kolor, tlo);
	lamana(e, x, y, bok, cwiartek, IKONA_STRZALKA_GROT, g, kolor, tlo);
}

/* ---------------------------------------------------------------- */
/* Napisy czcionka proporcjonalna z wygladzeniem.                    */

/* Jeden znak z napisu w UTF-8: zwraca kod i przesuwa wskaznik.
 *
 * Potrzebne, bo etykiety z polskimi znakami (a z ogonkiem, l z kreska) to
 * w C ciagi dwubajtowe.  Obslugujemy dwa i trzy bajty, bo tyle wystarcza na
 * wszystko, co klawiatura rysuje; dluzsze sekwencje i bledne bajty daja znak
 * zapytania, zamiast psuc caly napis. */
static unsigned int znak_utf8(const char **p)
{
	const unsigned char *u = (const unsigned char *)*p;
	unsigned int k;

	if (u[0] < 0x80) {
		*p += 1;
		return u[0];
	}
	if ((u[0] & 0xe0) == 0xc0 && (u[1] & 0xc0) == 0x80) {
		k = ((u[0] & 0x1fu) << 6) | (u[1] & 0x3fu);
		*p += 2;
		return k;
	}
	if ((u[0] & 0xf0) == 0xe0 && (u[1] & 0xc0) == 0x80 &&
	    (u[2] & 0xc0) == 0x80) {
		k = ((u[0] & 0x0fu) << 12) | ((u[1] & 0x3fu) << 6) |
		    (u[2] & 0x3fu);
		*p += 3;
		return k;
	}
	*p += 1;
	return '?';
}

static const struct glif_sans *glif_sans(unsigned int kod)
{
	int i;

	if (kod >= SANS_PIERWSZY && kod <= SANS_OSTATNI)
		return &SANS_GLIFY[kod - SANS_PIERWSZY];
	for (i = 0; i < SANS_DODATKOWYCH; i++)
		if (SANS_DODATKOWE[i].kod == kod)
			return &SANS_DODATKOWE[i].glif;
	return &SANS_GLIFY['?' - SANS_PIERWSZY];
}

int tekst_sans_szerokosc(const char *napis, int rozmiar)
{
	int suma = 0;

	while (*napis)
		suma += glif_sans(znak_utf8(&napis))->zaliczka;
	return suma * rozmiar / SANS_ROZMIAR;
}

int tekst_sans_wysokosc(int rozmiar)
{
	return SANS_WYSOKOSC * rozmiar / SANS_ROZMIAR;
}

/* Krycie piksela maski: jeden bajt na piksel, wierszami. */
static int krycie(const struct glif_sans *g, int gx, int gy)
{
	return SANS_ALFA[g->offset + (unsigned int)gy * g->szer + gx];
}

void rysuj_tekst_sans(struct ekran *e, int x, int y, const char *napis,
		      int rozmiar, uint32_t kolor, uint32_t tlo)
{
	uint32_t paleta[256];
	int i, pioro = x;

	/* Odcien na kazdy z 256 poziomow krycia.  Tyle samo poziomow ma
	 * wygladzanie w Qt, wiec obwodka litery wypada tak samo gruba; przy
	 * szesnastu poziomach litera mierzyla sie o piksel wieksza.  Skladowe
	 * wyciagamy z upakowanych kolorow, bo tylko sterownik wie, ile bitow
	 * ma ktora. */
	for (i = 0; i < 256; i++) {
		uint32_t maska_r = (1u << e->r_dl) - 1;
		uint32_t maska_g = (1u << e->g_dl) - 1;
		uint32_t maska_b = (1u << e->b_dl) - 1;
		uint32_t kr = (kolor >> e->r_poz) & maska_r;
		uint32_t kg = (kolor >> e->g_poz) & maska_g;
		uint32_t kb = (kolor >> e->b_poz) & maska_b;
		uint32_t tr = (tlo >> e->r_poz) & maska_r;
		uint32_t tg = (tlo >> e->g_poz) & maska_g;
		uint32_t tb = (tlo >> e->b_poz) & maska_b;
		uint32_t mr = tr + (kr - tr) * i / 255;
		uint32_t mg = tg + (kg - tg) * i / 255;
		uint32_t mb = tb + (kb - tb) * i / 255;

		paleta[i] = (mr << e->r_poz) | (mg << e->g_poz) | (mb << e->b_poz);
	}

	while (*napis) {
		const struct glif_sans *g = glif_sans(znak_utf8(&napis));
		int dw = g->szer * rozmiar / SANS_ROZMIAR;
		int dh = g->wys * rozmiar / SANS_ROZMIAR;
		int px, py;

		if (dw > 0 && dh > 0) {
			int gx0 = pioro + g->lewo * rozmiar / SANS_ROZMIAR;
			int gy0 = y + g->gora * rozmiar / SANS_ROZMIAR;

			for (py = 0; py < dh; py++) {
				for (px = 0; px < dw; px++) {
					/* Probkowanie dwuliniowe w setnych piksela.
					 *
					 * Poprzednia wersja usredniala PUDELKO
					 * pikseli zrodlowych i przy powiekszaniu
					 * pudelko schodzilo do jednego piksela,
					 * a na brzegach litery dokladalo pelny
					 * rzad obwodki: litera rosla o kilka
					 * procent i miala inne proporcje niz ta
					 * sama litera w Qt.  Interpolacja czterech
					 * sasiadow trzyma ksztalt i wyglada
					 * gladziej. */
					int sx = (px * 2 + 1) * g->szer * 50 / dw - 50;
					int sy = (py * 2 + 1) * g->wys * 50 / dh - 50;
					int x0 = sx / 100, y0 = sy / 100;
					int fx = sx - x0 * 100, fy = sy - y0 * 100;
					int x1, y1, a00, a10, a01, a11, gora, dol, a;

					if (sx < 0) { x0 = 0; fx = 0; }
					if (sy < 0) { y0 = 0; fy = 0; }
					x1 = x0 + 1 < g->szer ? x0 + 1 : x0;
					y1 = y0 + 1 < g->wys ? y0 + 1 : y0;
					if (x0 >= g->szer) x0 = x1 = g->szer - 1;
					if (y0 >= g->wys) y0 = y1 = g->wys - 1;

					a00 = krycie(g, x0, y0);
					a10 = krycie(g, x1, y0);
					a01 = krycie(g, x0, y1);
					a11 = krycie(g, x1, y1);
					gora = a00 * (100 - fx) + a10 * fx;
					dol  = a01 * (100 - fx) + a11 * fx;
					a = (gora * (100 - fy) + dol * fy) / 10000;
					if (a > 0)
						piksel(e, gx0 + px, gy0 + py,
						       paleta[a > 255 ? 255 : a]);
				}
			}
		}
		pioro += g->zaliczka * rozmiar / SANS_ROZMIAR;
	}
}
