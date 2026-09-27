/* SPDX-License-Identifier: GPL-2.0 */
/* Wirtualna klawiatura przez /dev/uinput.
 *
 * Konsola tekstowa wiaze sie tylko z urzadzeniami, ktore zglaszaja ZWYKLE
 * klawisze, czyli kody ponizej BTN_MISC.  Urzadzenie zgloszone waskim
 * zestawem kodow widac w evtest, a konsola go nie slucha, wiec deklarujemy
 * caly zakres, i to PRZED utworzeniem urzadzenia: potem kazde zgloszenie
 * nowego kodu konczy sie bledem.
 */
#ifndef KLAWIATURA_WSTRZYKIWANIE_H
#define KLAWIATURA_WSTRZYKIWANIE_H

struct wstrzyk {
	int fd;
};

int wstrzyk_otworz(struct wstrzyk *u, const char *nazwa);
void wstrzyk_zamknij(struct wstrzyk *u);

/* Pelne wcisniecie i puszczenie jednego klawisza. */
int wstrzyk_tap(struct wstrzyk *u, int kod);

/* Modyfikator zostaje wcisniety do osobnego zwolnienia. */
int wstrzyk_mod(struct wstrzyk *u, int kod, int wcisniety);

#endif /* KLAWIATURA_WSTRZYKIWANIE_H */
