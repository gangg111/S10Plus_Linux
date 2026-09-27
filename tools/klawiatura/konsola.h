/* SPDX-License-Identifier: GPL-2.0 */
/* Oddanie dolnego pasa ekranu przez zwezenie konsoli tekstowej.
 *
 * Bez tego konsola rysuje po calym ekranie i zamalowuje klawiature, a kursor
 * stoi pod nia, wiec uzytkownik nie widzi tego, co pisze.  Ograniczenie
 * obszaru przewijania (ESC[1;60r) nie wystarcza: clear, vi, less i wylogowanie
 * maluja po calym ekranie, nie tylko w obszarze przewijania.
 *
 * Zwezenie jest TRWALYM stanem jadra i dotyczy wszystkich konsol, wiec musi
 * byc cofniete takze wtedy, gdy program zostanie zabity: sluzy do tego osobne
 * wywolanie, ktore liczy pelny rozmiar od wysokosci ekranu, a nie od stanu
 * biezacego.
 */
#ifndef KLAWIATURA_KONSOLA_H
#define KLAWIATURA_KONSOLA_H

struct konsola {
	int fd;
	int wiersze_pelne;	/* ile wierszy miesci ekran */
	int kolumny;
	int komorka;		/* wysokosc znaku w pikselach */
	int wysokosc_px;
	int zwezona;
};

int konsola_otworz(struct konsola *k, const char *sciezka);
void konsola_zamknij(struct konsola *k);

/* Oddaje dolne "px" pikseli: zaokragla w gore do pelnych wierszy.
 * Zwraca liczbe realnie oddanych pikseli albo -1. */
int konsola_zwez(struct konsola *k, int px);

/* Przywraca pelna wysokosc; bezpieczne do wywolania wielokrotnie. */
int konsola_przywroc(struct konsola *k);

/* Odgasza ekran, nie ruszajac czasu do wygaszenia.  Wygaszony panel wyglada
 * dokladnie jak martwy dotyk: zdarzenia nie doleca, a nic o tym nie mowi,
 * wiec klawiatura budzi konsole sama przy kazdym dotknieciu.
 *
 * Wczesniej bylo tu wylaczenie wygaszacza na zawsze (ESC[9;0]) i to jest ten
 * jeden powod, dla ktorego panel tego telefonu nigdy sam nie gasl: pierwsze
 * pokazanie klawiatury zabijalo wygaszacz CALEMU systemowi, a nikt go potem
 * nie wlaczal z powrotem.  Na AMOLED to nie jest drobiazg, tylko wypalona
 * matryca po kilku dniach stania na napisie logowania. */
void konsola_odgas(struct konsola *k);

/* Gasi konsole i trzyma ja wygaszona, takze przy nacisnietym klawiszu.
 * Budzi wylacznie konsola_odgas(), czyli u nas przycisk zasilania albo
 * dwuklik w szybe: telefon w kieszeni dotyka sie sam i nie ma budzic. */
void konsola_zgas(struct konsola *k);

/* Czy konsola jest teraz wygaszona.  Pytamy o to jadra, bo wygasic moze ja
 * takze ono samo, po uplywie consoleblank, i wtedy nikt nam tego nie zglasza. */
int konsola_zgaszona(const struct konsola *k);

/* Numer aktywnej konsoli albo -1. */
int konsola_aktywna(const struct konsola *k);

#endif /* KLAWIATURA_KONSOLA_H */
