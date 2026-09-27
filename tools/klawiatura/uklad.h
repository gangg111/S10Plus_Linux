/* SPDX-License-Identifier: GPL-2.0 */
/* Uklad klawiszy klawiatury ekranowej.
 *
 * PLIK JEST GENEROWANY.  Zrodlem prawdy jest tools/klawiatura/wzorzec/
 * Layouts.qml, czyli uklad klawiatury Qt, a przepisuje go
 * scripts/gen-uklad-klawiatury.py.  Bramka scripts/check-uklad-klawiatury.py
 * pilnuje, ze oba sa zgodne, bo inaczej rozjazd widac dopiero na telefonie.
 *
 * Szerokosc klawisza jest w SETNYCH jednostki klawisza, tak jak pole w w QML,
 * i suma wag w rzedzie NIE musi byc rowna dziesieciu: rzad dzieli swoja
 * szerokosc przez wlasna sume wag.  Wysokosc rzedu jest w setnych wysokosci
 * rzedu wzorcowej (pole rh), bo rzad cyfr jest nizszy.
 */
#ifndef KLAWIATURA_UKLAD_H
#define KLAWIATURA_UKLAD_H

#include <linux/input-event-codes.h>

#include "ekran.h"

enum rola {
	ROLA_ZNAK = 0,		/* wstawia swoj znak */
	ROLA_NAZWANY,		/* klawisz systemowy: kod wprost */
	ROLA_SHIFT,		/* jedno dotkniecie shift, drugie blokada */
	ROLA_WARSTWA,		/* przechodzi do warstwy docel */
	ROLA_MOD,		/* Ctrl albo Alt: zapala sie do nastepnego znaku */
	ROLA_ODSTEP,		/* puste miejsce, nie rysowane i nieklikalne */
};

#define WARSTW		4
#define RZEDOW_MAX	5
#define W_RZEDZIE	11
#define WARIANTOW_MAX	3

struct klawisz {
	const char *etykieta;	/* NULL: rysuj znak */
	const char *znak;	/* tekst wstawiany, NULL dla akcji */
	const char *warianty[WARIANTOW_MAX];
	enum ikona ikona;	/* rysowana zamiast etykiety */
	unsigned short waga;	/* szerokosc w setnych jednostki */
	unsigned char rola;
	unsigned char docel;	/* warstwa dla ROLA_WARSTWA */
	unsigned short kod;	/* KEY_* dla ROLA_NAZWANY i MOD */
	unsigned char powtarza;	/* autopowtarzanie */
};

struct rzad {
	unsigned short wysokosc;	/* w setnych wysokosci rzedu */
	unsigned char ile;
	struct klawisz klawisze[W_RZEDZIE];
};

struct warstwa {
	const char *nazwa;
	unsigned char rzedow;
	struct rzad rzedy[RZEDOW_MAX];
};

static const struct warstwa UKLAD[WARSTW] = {
	{ "letters", 5, {
	{ 78, 10, {
		{ NULL, "1", { "!", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "2", { "@", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "3", { "#", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "4", { "$", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "5", { "%", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "6", { "^", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "7", { "&", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "8", { "*", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "9", { "(", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "0", { ")", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
	} },
	{ 100, 10, {
		{ NULL, "q", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "w", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "e", { "\xc4\x99", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "r", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "t", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "y", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "u", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "i", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "o", { "\xc3\xb3", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "p", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
	} },
	{ 100, 11, {
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_BRAK, 50, ROLA_ODSTEP, 0, 0, 0 },
		{ NULL, "a", { "\xc4\x85", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "s", { "\xc5\x9b", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "d", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "f", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "g", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "h", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "j", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "k", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "l", { "\xc5\x82", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_BRAK, 50, ROLA_ODSTEP, 0, 0, 0 },
	} },
	{ 100, 9, {
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_SHIFT, 150, ROLA_SHIFT, 0, 0, 0 },
		{ NULL, "z", { "\xc5\xbc", "\xc5\xba", NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "x", { "\xc5\xba", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "c", { "\xc4\x87", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "v", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "b", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "n", { "\xc5\x84", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "m", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_BACKSPACE, 150, ROLA_NAZWANY, 0, KEY_BACKSPACE, 1 },
	} },
	{ 100, 6, {
		{ "?123", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 150, ROLA_WARSTWA, 1, 0, 0 },
		{ NULL, ",", { ";", NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ "", " ", { NULL, NULL, NULL }, IKONA_BRAK, 450, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ".", { "!", "?", ":" }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ "Fn", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_WARSTWA, 3, 0, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_ENTER, 150, ROLA_NAZWANY, 0, KEY_ENTER, 0 },
	} },
	} },
	{ "symbols", 4, {
	{ 100, 10, {
		{ NULL, "1", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "2", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "3", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "4", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "5", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "6", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "7", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "8", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "9", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "0", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
	} },
	{ 100, 10, {
		{ NULL, "@", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "#", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "$", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "%", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "&", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "-", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "+", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "(", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ")", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "/", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
	} },
	{ 100, 9, {
		{ "=\\<", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 150, ROLA_WARSTWA, 2, 0, 0 },
		{ NULL, "*", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "\"", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "'", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ":", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ";", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "!", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "?", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_BACKSPACE, 150, ROLA_NAZWANY, 0, KEY_BACKSPACE, 1 },
	} },
	{ 100, 6, {
		{ "ABC", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 150, ROLA_WARSTWA, 0, 0, 0 },
		{ NULL, "_", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ "", " ", { NULL, NULL, NULL }, IKONA_BRAK, 450, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ".", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ "Fn", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_WARSTWA, 3, 0, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_ENTER, 150, ROLA_NAZWANY, 0, KEY_ENTER, 0 },
	} },
	} },
	{ "symbols2", 4, {
	{ 100, 10, {
		{ NULL, "~", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "`", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "|", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "^", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "=", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "<", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ">", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "{", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "}", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "\\", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
	} },
	{ 100, 10, {
		{ NULL, "[", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "]", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "(", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ")", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "+", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "-", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "*", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "/", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "%", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "#", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
	} },
	{ 100, 9, {
		{ "?123", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 150, ROLA_WARSTWA, 1, 0, 0 },
		{ NULL, "&", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "$", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "@", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "!", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, "?", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ":", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ";", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_BACKSPACE, 150, ROLA_NAZWANY, 0, KEY_BACKSPACE, 1 },
	} },
	{ 100, 6, {
		{ "ABC", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 150, ROLA_WARSTWA, 0, 0, 0 },
		{ NULL, "_", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ "", " ", { NULL, NULL, NULL }, IKONA_BRAK, 450, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, ".", { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_ZNAK, 0, 0, 0 },
		{ "Fn", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_WARSTWA, 3, 0, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_ENTER, 150, ROLA_NAZWANY, 0, KEY_ENTER, 0 },
	} },
	} },
	{ "nav", 4, {
	{ 100, 8, {
		{ "Esc", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_ESC, 0 },
		{ "Tab", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_TAB, 0 },
		{ "Home", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_HOME, 0 },
		{ "End", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_END, 0 },
		{ "PgUp", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_PAGEUP, 0 },
		{ "PgDn", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_PAGEDOWN, 0 },
		{ "Del", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_DELETE, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_BACKSPACE, 100, ROLA_NAZWANY, 0, KEY_BACKSPACE, 1 },
	} },
	{ 100, 8, {
		{ "F1", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F1, 0 },
		{ "F2", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F2, 0 },
		{ "F3", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F3, 0 },
		{ "F4", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F4, 0 },
		{ "F5", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F5, 0 },
		{ "F6", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F6, 0 },
		{ "F7", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F7, 0 },
		{ "F8", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F8, 0 },
	} },
	{ 100, 8, {
		{ "F9", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F9, 0 },
		{ "F10", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F10, 0 },
		{ "F11", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F11, 0 },
		{ "F12", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 100, ROLA_NAZWANY, 0, KEY_F12, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_GORA, 100, ROLA_NAZWANY, 0, KEY_UP, 1 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_DOL, 100, ROLA_NAZWANY, 0, KEY_DOWN, 1 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_LEWO, 100, ROLA_NAZWANY, 0, KEY_LEFT, 1 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_PRAWO, 100, ROLA_NAZWANY, 0, KEY_RIGHT, 1 },
	} },
	{ 100, 5, {
		{ "ABC", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 150, ROLA_WARSTWA, 0, 0, 0 },
		{ "Ctrl", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 150, ROLA_MOD, 0, KEY_LEFTCTRL, 0 },
		{ "Alt", NULL, { NULL, NULL, NULL }, IKONA_BRAK, 150, ROLA_MOD, 0, KEY_LEFTALT, 0 },
		{ "", " ", { NULL, NULL, NULL }, IKONA_BRAK, 300, ROLA_ZNAK, 0, 0, 0 },
		{ NULL, NULL, { NULL, NULL, NULL }, IKONA_ENTER, 150, ROLA_NAZWANY, 0, KEY_ENTER, 0 },
	} },
	} },
};
#endif /* KLAWIATURA_UKLAD_H */
