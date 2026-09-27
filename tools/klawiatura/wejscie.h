/* SPDX-License-Identifier: GPL-2.0 */
/* Czytanie ekranu dotykowego i przyciskow obudowy.
 *
 * Dwie rzeczy, ktore trzeba tu wiedziec o TYM sprzecie, bo obie lamia
 * podrecznikowy schemat (zmierzone 20 wrzesnia 2026):
 *
 * 1. Kontroler NIE wysyla identyfikatora sladu przy nowym palcu ani -1 przy
 *    puszczeniu, i nie wysyla BTN_TOUCH.  Program czekajacy na te zdarzenia
 *    milczy mimo dotykania ekranu.  Koniec dotkniecia poznajemy po CISZY
 *    w strumieniu, a nie po zdarzeniu.
 *
 * 2. Osie dotyku pokrywaja sie z osiami panelu, obie znormalizowane do
 *    0..4096.  Pomiar czterech rogow zdawal sie mowic co innego, ale to
 *    telefon lezal inaczej, niz zakladalem; rozstrzygnela zywa klawiatura.
 */
#ifndef KLAWIATURA_WEJSCIE_H
#define KLAWIATURA_WEJSCIE_H

enum zdarzenie {
	ZD_BRAK = 0,
	ZD_DOTYK_START,
	ZD_DOTYK_RUCH,
	ZD_DOTYK_KONIEC,
	ZD_PRZELACZ,		/* przycisk Bixby */
	ZD_EKRAN,		/* krotkie nacisniecie samego zasilania */
	ZD_BUDZENIE,		/* dwuklik rozpoznany przez uklad dotyku */
	ZD_BLAD,
};

struct wejscie {
	int fd_dotyk;
	int fd_klawisze;
	int x_min, x_max;	/* zakres osi urzadzenia */
	int y_min, y_max;
	int szer, wys;		/* rozmiar ekranu w pikselach */
	int surowy_x, surowy_y;	/* ostatnie wartosci z urzadzenia */
	int x, y;		/* przeliczone na piksele */
	int dotyka;
	long long ostatnia_paczka_ms;
	int cisza_ms;		/* po tylu ms bez paczki palec uznajemy za puszczony */
	/* Ustawiane, gdy panel przynajmniej raz powiedzial wprost, ze palec
	 * zszedl z ekranu (BTN_TOUCH albo slad -1).  Wtedy cisza przestaje
	 * znaczyc puszczenie, bo palec moze po prostu lezec bez ruchu. */
	int mowi_o_puszczeniu;

	/* Przyciski obudowy.  Zasilanie liczy sie jako gest dopiero przy
	 * puszczeniu, bo dopiero wtedy wiadomo, czy bylo krotkie, dlugie,
	 * czy bylo czescia kombinacji z innym przyciskiem.  Kombinacja to
	 * osobna komenda i zadna akcja samego zasilania jej nie dotyczy. */
	int zasilanie;
	long long zasilanie_od_ms;
	int kombinacja;
	int inne_wcisniete;
};

int wejscie_otworz(struct wejscie *w, const char *nazwa_dotyku,
		   const char *nazwa_klawiszy, int szer, int wys);
void wejscie_zamknij(struct wejscie *w);

/* Czeka najwyzej "czekaj_ms" i zwraca jedno zdarzenie.  Wartosc ujemna
 * w czekaj_ms oznacza czekanie bez konca. */
enum zdarzenie wejscie_pobierz(struct wejscie *w, int czekaj_ms);

long long teraz_ms(void);

#endif /* KLAWIATURA_WEJSCIE_H */
