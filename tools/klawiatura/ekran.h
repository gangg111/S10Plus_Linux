/* SPDX-License-Identifier: GPL-2.0 */
/* Rysowanie po buforze ramki: wlasny bufor roboczy, glify z czcionki konsoli.
 *
 * Program rysuje do wlasnego bufora i wysyla na ekran gotowy pas, zeby
 * uzytkownik nie ogladal skladania obrazu.
 *
 * Wysylka idzie przez pwrite, a NIE przez odwzorowanie w pamieci. Powod jest
 * zmierzony w zrodlach: zapis do odwzorowanego bufora sterownika opartego
 * o drm trafia w sciezke deferred_io, ktora czeka HZ/20 przed odswiezeniem
 * (drm_fbdev_shmem.c, fbdefio.delay), a pwrite konczy sie w
 * drm_fb_helper_damage() zwyklym schedule_work bez opoznienia.
 *
 * Ukladu bajtow w pikselu nie zakladamy z gory: bierzemy go z jadra
 * (FBIOGET_VSCREENINFO), bo od sterownika zalezy i kolejnosc kanalow,
 * i dlugosc wiersza.
 */
#ifndef KLAWIATURA_EKRAN_H
#define KLAWIATURA_EKRAN_H

#include <stdint.h>

struct ekran {
	int fd;
	uint8_t *bufor;		/* wlasny bufor roboczy, uklad taki jak ekran */
	uint32_t szerokosc;
	uint32_t wysokosc;
	uint32_t wiersz;	/* dlugosc wiersza w bajtach */
	/* pozycje i dlugosci pol koloru, prosto z jadra */
	uint32_t r_poz, r_dl, g_poz, g_dl, b_poz, b_dl;
};

int ekran_otworz(struct ekran *e, const char *sciezka);
/* Ekran zastepczy: sam bufor, bez urzadzenia.  Sluzy trybowi --zrzut, czyli
 * obejrzeniu klawiatury na komputerze, gdy telefonu nie ma pod reka.  Uklad
 * kanalow bierzemy taki, jaki ma panel tego telefonu (BGRX, 8 bitow na
 * skladowa), zeby zrzut pokazywal te same kolory, co ekran. */
int ekran_zastepczy(struct ekran *e, uint32_t szerokosc, uint32_t wysokosc);
/* Zapis fragmentu bufora do pliku PPM (P6).  Format wybrany dlatego, ze nie
 * wymaga zadnej biblioteki, a kazde narzedzie graficzne go otwiera. */
int ekran_zapisz_ppm(const struct ekran *e, const char *sciezka, int y, int h);
void ekran_zamknij(struct ekran *e);

/* Czy opis ekranu jest nadal taki, jak przy otwarciu.  Sprawdzane przed
 * rysowaniem, bo zmiana wysokosci przez kogos innego sprawia, ze jadro tnie
 * nasz obszar i pas nie pojawia sie wcale, bez zadnego bledu. */
int ekran_ten_sam(const struct ekran *e);

uint32_t ekran_kolor(const struct ekran *e, uint8_t r, uint8_t g, uint8_t b);

void rysuj_prostokat(struct ekran *e, int x, int y, int w, int h, uint32_t kolor);
/* Zaokraglony klawisz z wygladzonym naroznikiem.  tlo_pod to kolor, ktory
 * lezy pod klawiszem: brzeg luku jest z nim mieszany. */
void rysuj_klawisz(struct ekran *e, int x, int y, int w, int h, int promien,
		   uint32_t tlo, uint32_t tlo_pod);
/* Obwodka grubosci jednego piksela wzdluz tego samego zaokraglonego obrysu.
 * Potrzebna dymkowi wariantow: w AltPopup.qml ma border.width 1. */
void rysuj_ramke(struct ekran *e, int x, int y, int w, int h, int promien,
		 uint32_t kolor);
void rysuj_tekst(struct ekran *e, int x, int y, const char *napis, int skala,
		 uint32_t kolor);

/* Ikony klawiszy rysowane, a nie brane z czcionki.
 *
 * Backspace, Enter i Shift nie maja glifow ani w czcionce konsoli, ani w tym,
 * co jest w obrazie telefonu, a napisy "Bksp" i "Shift" wygladaja inaczej niz
 * reszta klawiatury.  Rysunek wektorowy wazy zero, nie zalezy od zadnej
 * czcionki i skaluje sie do rozmiaru klawisza. */
enum ikona {
	IKONA_BRAK = 0,
	IKONA_BACKSPACE,
	IKONA_ENTER,
	IKONA_SHIFT,
	IKONA_GORA,
	IKONA_DOL,
	IKONA_LEWO,
	IKONA_PRAWO,
};

/* Odcinek o zadanej grubosci, z zaokraglonymi koncami. */
void rysuj_odcinek(struct ekran *e, int x0, int y0, int x1, int y1,
		   int grubosc, uint32_t kolor, uint32_t tlo);

/* Ikona wpisana w kwadrat o boku "bok", lewy gorny rog w (x, y). */
void rysuj_ikone(struct ekran *e, int x, int y, int bok, enum ikona co,
		 uint32_t kolor, uint32_t tlo);

/* Napis czcionka proporcjonalna Droid Sans, wygladzona.
 *
 * Kolor tla podajemy jawnie, bo mieszanie krycia robimy na gotowej tablicy
 * szesnastu odcieni miedzy tlem a kolorem napisu, zamiast odczytywac kazdy
 * piksel z bufora.  Klawisz ma tlo jednolite, wiec wynik jest taki sam,
 * a rysowanie prostsze i szybsze.
 *
 * (x, y) to lewy gorny rog PROSTOKATA WIERSZA, nie linia bazowa. */
void rysuj_tekst_sans(struct ekran *e, int x, int y, const char *napis,
		      int rozmiar, uint32_t kolor, uint32_t tlo);
int tekst_sans_szerokosc(const char *napis, int rozmiar);
int tekst_sans_wysokosc(int rozmiar);
int tekst_szerokosc(const char *napis, int skala);
int tekst_wysokosc(int skala);

/* Wysyla na ekran pas o podanej wysokosci; reszta obrazu zostaje nietknieta.
 * Zwraca 0 albo -1, gdy zapis sie nie udal. */
int ekran_wyslij(struct ekran *e, int y, int h);

#endif /* KLAWIATURA_EKRAN_H */
