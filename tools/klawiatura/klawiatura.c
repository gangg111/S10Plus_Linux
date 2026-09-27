// SPDX-License-Identifier: GPL-2.0
// Klawiatura ekranowa dla konsoli tekstowej na Galaxy S10+.
//
// Przycisk Bixby pokazuje ja i chowa.  Gdy jest widoczna, konsola zostaje
// zwezona o tyle wierszy, ile zajmuje klawiatura, wiec tekst nigdy nie wchodzi
// pod palce, a kursor zostaje nad nia.
//
// Uklad, wygladu i zachowania nie wymyslamy: sa przeniesione jeden do jednego
// z klawiatury Qt, ktora napisal uzytkownik.  Uklad idzie z wzorzec/Layouts.qml
// przez generator (patrz uklad.h), a kolory, wymiary, czasy i zachowanie
// klawiszy z wzorzec/Theme.qml, wzorzec/KeyButton.qml, wzorzec/Keyboard.qml
// i wzorzec/AltPopup.qml.  Kazde miejsce, gdzie liczba pochodzi z tamtych
// plikow, ma to zapisane w komentarzu.
//
// Znak wychodzi przy PUSZCZENIU palca, tak jak w KeyButton.qml (TapHandler
// z gesturePolicy: ReleaseWithinBounds): dopiero wtedy wiadomo, czy dotkniecie
// bylo krotkie, czy przeszlo w przytrzymanie, ktore otwiera dymek wariantow.

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/file.h>

#include "ekran.h"
#include "konsola.h"
#include "wejscie.h"
#include "wstrzykiwanie.h"
#include "uklad.h"

#define NAZWA_DOTYKU	"s6sy761"
#define NAZWA_KLAWISZY	"gpio-keys"
#define NAZWA_NASZA	"klawiatura ekranowa"
#define BLOKADA		"/run/klawiatura.lock"

/* Siatka: marginesy i odstepy w pikselach, wysokosc pasa jako czesc ekranu,
 * zaokraglona W GORE do pelnych wierszy konsoli, zeby jej zwezenie wypadalo
 * dokladnie na granicy pasa.
 *
 * Liczona w czesciach ekranu, a nie w wierszach, bo wysokosc wiersza zalezy od
 * zaladowanej czcionki: przy 16x32 wiersz ma 32 piksele, przy 32x64 juz 64,
 * a klawiatura ma zajmowac tyle samo miejsca w obu przypadkach. */
/* Margines na zakrzywione krawedzie panelu siedzi juz w opisie bufora ramki
 * (jest wezszy od panelu o 32 piksele z kazdej strony), wiec tutaj zostaje
 * tylko odstep dla oka. */
/* Wymiary podajemy w MILIMETRACH i przeliczamy przez gestosc ekranu, dokladnie
 * tak, jak robi to Theme.qml klawiatury Qt.  Dzieki temu obie wygladaja tak
 * samo i obie zachowaja sie tak samo na innym panelu.
 *
 * Gestosc liczymy z szerokosci: sterownik panelu deklaruje 70 mm czynnej
 * szerokosci na 1440 pikseli, czyli 20,57 px/mm.
 */
#define SZEROKOSC_PANELU_MM	70

/* Liczby wprost z Theme.qml. */
#define GAP_MM_X100		60	/* Theme.gapMm     0.6 */
#define PROMIEN_MM_X100		120	/* Theme.radiusMm  1.2 */
#define KRZYWIZNA_MM_X100	160	/* Theme.safeMarginMm 1.6 */
#define RZAD_MM_X100		900	/* Theme.rowHeightMm  9.0 */
/* Theme.fontMain = 0.40 * rzad, Theme.fontLabel = 0.26 * rzad. */
#define FONT_GLOWNY_PROC	40
#define FONT_ETYKIETY_PROC	26
/* Tyle palec musi lezec na klawiszu, zeby otworzyl sie dymek wariantow.
 * Wprost longPressThreshold z KeyButton.qml (0,35 s). */
#define PRZYTRZYMANIE_MS	350
/* Autopowtarzanie klawiszy z polem rep: dwa zegary z KeyButton.qml. */
#define AUTO_ZWLOKA_MS		400
#define AUTO_KROK_MS		55

/*
 * Progi ochrony matrycy.  Ten panel to AMOLED, a klawiatura zajmuje staly pas
 * 1440 na 896 pikseli, czyli 29,5 procent ekranu, z czego klawisze pokrywaja
 * 78 procent pasa.  Obraz jest przy tym pikselowo niezmienny, bo rysuje sie
 * tylko ze zdarzen.  Na takim panelu swieci sie kazdy piksel z osobna i
 * starzeje proporcjonalnie do czasu swiecenia, wiec nieruchoma klawiatura
 * jest dokladnie tym, co wypala matryce.
 *
 * Stad trzy progi, liczone od ostatniego dotkniecia, i czwarty od ostatniego
 * przesuniecia:
 *   - po PRZYCIEMNIENIE_MS napisy schodza z bieli na szarosc, bo to one, a
 *     nie ciemne tla klawiszy, daja wiekszosc emisji,
 *   - po MODYFIKATORY_MS gasna zapalone Shift, Ctrl i Alt, bo ich tlo to
 *     czysty niebieski 255, a niebieski subpiksel starzeje sie najszybciej,
 *   - po SCHOWANIE_MS pas gasnie w calosci,
 *   - co PRZESUNIECIE_MS caly uklad przesuwa sie o kilka pikseli, zeby
 *     krawedzie klawiszy i napisy nie staly latami w tym samym miejscu.
 */
#define PRZYCIEMNIENIE_MS	20000
#define MODYFIKATORY_MS		30000
#define SCHOWANIE_MS		90000
#define PRZESUNIECIE_MS		60000
/* Tryby diagnostyczne trzymaja nieruchomy obraz tak dlugo, jak ktos na niego
 * patrzy, a przy pracy nad wygladem znaczy to godziny.  Po tym czasie gasza
 * ekran same, bo zaden z nich nie jest po to, zeby stal przez noc. */
#define DIAGNOSTYKA_MS		300000
/*
 * Dwuklik budzacy zgaszony ekran.
 *
 * Progi sa ostre, bo ten kontroler NIE zglasza puszczenia palca i sypie
 * wspolrzednymi bez przerwy, dopoki cos dotyka szyby (opisane w wejscie.h).
 * Na stocku tego problemu nie ma, bo sterownik producenta przelacza kontroler
 * w tryb niskiego poboru (sec_ts.c, sec_ts_set_lowpowermode) i wtedy uklad
 * sam rozpoznaje dwuklik, a do systemu wysyla JEDNO zdarzenie gestu zamiast
 * strumienia wspolrzednych.  My takiego trybu jeszcze nie programujemy, wiec
 * filtr musi stac po naszej stronie:
 *
 *   - przez pierwsza chwile po zgaszeniu nie budzi nic, bo ta chwila nalezy
 *     do reki, ktora wlasnie nacisnela przycisk,
 *   - dwa stukniecia musi dzielic tyle, ile dzieli dwa OSOBNE dotkniecia,
 *     a nie dwie paczki z tego samego przesuwu palca,
 *   - i musza paść w to samo miejsce, z dokladnoscia kilku milimetrow.
 */
#define DWUKLIK_MS		600
#define DWUKLIK_MIN_MS		120
#define ZWLOKA_PO_ZGASZENIU_MS	1500
#define DWUKLIK_PROMIEN		120	/* pikseli, okolo szesciu milimetrow */

/* Po tylu milisekundach bez zadnego dotkniecia i przycisku ekran gasnie.
 * Liczymy to sami, a nie licznikiem jadra: jadro budzi konsole na samo
 * WCISNIECIE klawisza, a my przelaczamy ekran przy PUSZCZENIU, wiec dwa
 * liczniki naraz dawaly wyscig, widoczny w dzienniku jako zapalenie
 * i zgaszenie w odstepie 55 ms.  consoleblank w wierszu rozruchowym
 * zostaje dluzszy, jako siatka na wypadek, gdyby ten program nie dzialal. */
#define EKRAN_MS		30000

/* Tyle trzeba trzymac sam przycisk zasilania, zeby wylaczyc telefon. */
#define WYLACZENIE_MS		10000

/* Przelacznik trybu niskiego poboru ukladu dotyku (latka 0099). */
#define NISKI_POBOR "/sys/bus/i2c/devices/0-0048/lowpower"

struct stan {
	struct ekran ekran;
	struct konsola konsola;
	struct wejscie wejscie;
	struct wstrzyk uinput;

	int pas_y, pas_h;	/* pas oddany przez konsole */
	int blok_y, blok_h;	/* sama klawiatura: tyle, ile potrzebuje warstwa */
	int rzad_h;		/* Theme.rowHeight */
	/* Wszystko ponizej wyliczone z gestosci ekranu przy starcie. */
	int dpmm_x100;		/* pikseli na milimetr, razy sto */
	int odstep;		/* Theme.gap */
	int promien;		/* Theme.radius */
	int margines_bok;	/* Theme.safeMargin plus polowa odstepu */
	int font_glowny;	/* Theme.fontMain */
	int font_etykiety;	/* Theme.fontLabel */
	int warstwa;
	/* Shift ma trzy stany, jak w Keyboard.qml: zgaszony, jednorazowy
	 * i zablokowany.  Ctrl i Alt gasna po nastepnym znaku. */
	int shift, shift_lock, ctrl, alt, altgr;
	int widoczna;
	int wcisniety_rzad, wcisniety_klawisz;
	long long dotyk_ms;	/* odkad palec stoi na tym klawiszu */
	long long powtorka_ms;	/* ostatnie powtorzenie klawisza z rep */
	int stlumiony;		/* dymek albo powtarzanie zjadlo dotkniecie */

	/* Ochrona matrycy: kiedy ostatnio ktos dotknal, czy napisy sa juz
	 * przyciemnione i o ile pikseli przesuniety jest caly uklad. */
	long long aktywnosc_ms;
	long long przesuniecie_ms;
	long long stuk_ms;	/* poprzednie dotkniecie zgaszonego ekranu */
	long long zgaszono_ms;	/* kiedy ekran zostal zgaszony */
	long long ostatnio_ms;	/* ostatnie dotkniecie albo przycisk */
	int niski_pobor;	/* uklad dotyku sam rozpoznaje dwuklik */
	int wylaczanie;		/* telefon juz sie wylacza */
	int stuk_x, stuk_y;	/* gdzie padlo poprzednie stukniecie */
	int ekran_zgaszony;
	int przyciemniona;
	int przesun_x, przesun_y;
	int krok_przesuniecia;

	/* Dymek wariantow (AltPopup.qml): lista znakow nad klawiszem. */
	const char *const *dymek;
	int dymek_ile, dymek_x, dymek_y, dymek_w;

	/* Paleta przeniesiona z Theme.qml co do bajtu. */
	uint32_t tlo;		/* Theme.bg          #000000 */
	uint32_t klaw;		/* Theme.keyBg       #1c1c1e */
	uint32_t klaw_spec;	/* Theme.keyBgAlt    #131315 */
	uint32_t klaw_aktywny;	/* Theme.keyBgActive #2c2c2e */
	uint32_t wcisniety;	/* Theme.keyBgDown   #0a84ff */
	uint32_t napis;		/* Theme.text        #f2f2f7 */
	uint32_t napis_slaby;	/* Theme.textDim     #8e8e93 */
	uint32_t akcent;	/* Theme.accent      #0a84ff */
};

static volatile sig_atomic_t koniec;
static volatile sig_atomic_t zadano_przelaczenia;

static void na_sygnal(int nr)
{
	/* Osobny sygnal na przelaczenie daje to samo, co przycisk Bixby, ale
	 * bez palca: bez tego nie da sie zrobic zrzutu ekranu z klawiatura
	 * ani sprawdzic jej zdalnie. */
	if (nr == SIGUSR1)
		zadano_przelaczenia = 1;
	else
		koniec = 1;
}

/* ------------------------------------------------------------------ uklad */

static const struct rzad *rzad_w(const struct stan *s, int r)
{
	return &UKLAD[s->warstwa].rzedy[r];
}

static int rzedow(const struct stan *s)
{
	return UKLAD[s->warstwa].rzedow;
}

static int klawiszy_w_rzedzie(const struct stan *s, int rzad)
{
	return rzad_w(s, rzad)->ile;
}

static const struct klawisz *klawisz_w(const struct stan *s, int rzad, int nr)
{
	if (rzad < 0 || rzad >= rzedow(s))
		return NULL;
	if (nr < 0 || nr >= klawiszy_w_rzedzie(s, rzad))
		return NULL;
	return &rzad_w(s, rzad)->klawisze[nr];
}

/* Suma wag rzedu.  W Keyboard.qml kazdy rzad dzieli swoja szerokosc przez
 * WLASNA sume (weightSum), a nie przez stala: rzad z Enterem ma 10,5
 * jednostki, rzad liter 10, wiec staly dzielnik rozjechalby jeden z nich. */
static int waga_rzedu(const struct stan *s, int rzad)
{
	const struct rzad *r = rzad_w(s, rzad);
	int suma = 0, i;

	for (i = 0; i < r->ile; i++)
		suma += r->klawisze[i].waga;
	return suma ? suma : 1;
}

/* Wysokosc warstwy w pikselach: odstep u gory plus rzedy, kazdy przeskalowany
 * swoim polem rh.  To jest implicitHeight z Keyboard.qml. */
static int wysokosc_warstwy(const struct stan *s, int warstwa)
{
	int h = s->odstep, i;

	for (i = 0; i < UKLAD[warstwa].rzedow; i++)
		h += s->rzad_h * UKLAD[warstwa].rzedy[i].wysokosc / 100;
	return h;
}

/* Polozenie klawisza w pikselach.
 *
 * Klawiatura jest przyklejona do DOLU pasa, tak jak w Main.qml, gdzie siedzi
 * przy dolnej krawedzi okna.  Warstwa symboli ma o jeden rzad mniej niz
 * litery, wiec przy gornej krawedzi zostaje tlo, a klawisze nie skacza spod
 * palca przy przelaczeniu. */
static void geometria(const struct stan *s, int rzad, int nr, int *x, int *y,
		      int *w, int *h)
{
	int uzyteczna = (int)s->ekran.szerokosc - 2 * s->margines_bok;
	int suma = waga_rzedu(s, rzad);
	const struct rzad *r = rzad_w(s, rzad);
	int przed = 0, i;

	for (i = 0; i < nr; i++)
		przed += r->klawisze[i].waga;

	*x = s->margines_bok + (int)((long long)przed * uzyteczna / suma);
	*w = (int)((long long)r->klawisze[nr].waga * uzyteczna / suma);
	*h = s->rzad_h * r->wysokosc / 100;

	*y = s->blok_y + s->odstep / 2;
	for (i = 0; i < rzad; i++)
		*y += s->rzad_h * rzad_w(s, i)->wysokosc / 100;

	/* Ostatni klawisz dociagamy do krawedzi, zeby zaokraglenia nie
	 * zostawialy szpary. */
	if (nr == r->ile - 1)
		*w = (int)s->ekran.szerokosc - s->margines_bok - *x;
	if (*w < 1)
		*w = 1;

	/* Przesuniecie przeciw wypaleniu wchodzi TUTAJ, a nie w rysowaniu, bo
	 * z tej samej funkcji korzysta trafianie w klawisz.  Gdyby obraz
	 * jezdzil, a trafianie nie, palec zaczalby chybiac o tyle, o ile
	 * przesuniety jest uklad. */
	*x += s->przesun_x;
	*y += s->przesun_y;
}

static int trafiony(const struct stan *s, int px, int py, int *rzad, int *nr)
{
	int r, n;

	for (r = 0; r < rzedow(s); r++) {
		for (n = 0; n < klawiszy_w_rzedzie(s, r); n++) {
			int x, y, w, h;

			/* Odstep to margines WEWNATRZ pola klawisza (jak
			 * anchors.margins w KeyButton.qml), wiec pola dotyku
			 * stykaja sie i zaden dotyk nie przepada. */
			if (klawisz_w(s, r, n)->rola == ROLA_ODSTEP)
				continue;
			geometria(s, r, n, &x, &y, &w, &h);
			if (px >= x && px < x + w &&
			    py >= y && py < y + h) {
				*rzad = r;
				*nr = n;
				return 1;
			}
		}
	}
	return 0;
}

/* --------------------------------------------------------------- rysowanie */

static void kolory(struct stan *s)
{
	struct ekran *e = &s->ekran;

	/* Kazdy kolor wprost z Theme.qml; komentarz podaje nazwe z tamtego
	 * pliku, zeby dalo sie sprawdzic jednym spojrzeniem. */
	s->tlo = ekran_kolor(e, 0x00, 0x00, 0x00);		/* bg */
	s->klaw = ekran_kolor(e, 0x1c, 0x1c, 0x1e);		/* keyBg */
	s->klaw_spec = ekran_kolor(e, 0x13, 0x13, 0x15);	/* keyBgAlt */
	s->klaw_aktywny = ekran_kolor(e, 0x2c, 0x2c, 0x2e);	/* keyBgActive */
	s->wcisniety = ekran_kolor(e, 0x0a, 0x84, 0xff);	/* keyBgDown */
	s->napis = ekran_kolor(e, 0xf2, 0xf2, 0xf7);		/* text */
	s->napis_slaby = ekran_kolor(e, 0x8e, 0x8e, 0x93);	/* textDim */
	s->akcent = ekran_kolor(e, 0x0a, 0x84, 0xff);		/* accent */
}

/* Napis na klawiszu.
 *
 * To jest glyph z KeyButton.qml: etykieta, gdy jest, inaczej znak, a przy
 * zapalonym Shifcie jego wielka odmiana.  Wielkie litery robimy tylko dla
 * ASCII, bo tylko takie znaki maja klawisze w ukladzie. */
static const char *etykieta(const struct stan *s, const struct klawisz *k)
{
	static char duza[2];

	if (k->etykieta)
		return k->etykieta;
	if (!k->znak)
		return "";
	if ((s->shift || s->shift_lock) && !k->znak[1] &&
	    k->znak[0] >= 'a' && k->znak[0] <= 'z') {
		duza[0] = (char)(k->znak[0] - 'a' + 'A');
		duza[1] = 0;
		return duza;
	}
	return k->znak;
}

/* Nazwa klawisza do wypisania w trybie diagnostycznym.
 *
 * Klawisz z ikona nie ma etykiety, wiec sam napis daje pusto i nie da sie
 * odczytac, w co trafil palec. */
static const char *opis_klawisza(const struct stan *s,
				 const struct klawisz *k)
{
	static const char *const NAZWY[] = {
		"", "Backspace", "Enter", "Shift", "gora", "dol", "lewo",
		"prawo",
	};
	const char *napis = etykieta(s, k);

	if (napis[0])
		return napis;
	if (k->ikona > IKONA_BRAK &&
	    (size_t)k->ikona < sizeof(NAZWY) / sizeof(NAZWY[0]))
		return NAZWY[k->ikona];
	return "(bez napisu)";
}

/* Polowa jasnosci kazdej skladowej, bez ruszania kanalu alfa.  Na AMOLED
 * emisja jest wprost proporcjonalna do wartosci skladowej, wiec polowa
 * wartosci to polowa pradu przez diode i polowa tempa starzenia. */
static uint32_t przygas(uint32_t kolor)
{
	uint32_t r = (kolor >> 16) & 0xff;
	uint32_t g = (kolor >> 8) & 0xff;
	uint32_t b = kolor & 0xff;

	return (kolor & 0xff000000u) | ((r / 2) << 16) | ((g / 2) << 8) |
	       (b / 2);
}

static void rysuj_jeden(struct stan *s, int rzad, int nr)
{
	const struct klawisz *k = klawisz_w(s, rzad, nr);
	int x, y, w, h, wx, wy, ww, wh, rozmiar, tx, ty;
	uint32_t tlo, kolor_napisu;
	const char *napis;
	/* KeyButton.qml: special to kazdy klawisz z polem act albo k, czyli
	 * wszystko poza wstawiajacymi znak. */
	int specjalny;

	if (!k || k->rola == ROLA_ODSTEP)
		return;
	geometria(s, rzad, nr, &x, &y, &w, &h);
	napis = etykieta(s, k);
	specjalny = k->rola != ROLA_ZNAK;

	/* Stany tla.  Trzy pierwsze sa wprost z KeyButton.qml:
	 *   wcisniety      -> Theme.keyBgDown
	 *   klawisz zwykly -> Theme.keyBg
	 *   klawisz z akcja albo systemowy -> Theme.keyBgAlt
	 *
	 * Czwarty jest nasz i jest swiadomym odejsciem od wzorca: ZABLOKOWANY
	 * Shift pali sie na klawiszu, az ktos go zgasi.  Wzorzec pokazywal to
	 * napisem CAPS w narozniku, co znaczy, ze stan trzeba bylo czytac gdzie
	 * indziej niz tam, gdzie sie go wlacza, a sam napis nachodzil na rzad
	 * cyfr.  Shift jednorazowy zostaje bez podswietlenia, bo widac go po
	 * wielkich literach na klawiszach. */
	tlo = specjalny ? s->klaw_spec : s->klaw;
	/* Kolor akcentu znaczy STAN, ktory trwa: zablokowany Shift oraz Ctrl
	 * i Alt czekajace na nastepny znak.  Widac go, dopoki ktos go nie
	 * zgasi. */
	if (k->rola == ROLA_SHIFT && s->shift_lock)
		tlo = s->wcisniety;
	if (k->rola == ROLA_MOD &&
	    ((k->kod == KEY_LEFTCTRL && s->ctrl) ||
	     (k->kod == KEY_LEFTALT && s->alt)))
		tlo = s->wcisniety;
	/* Samo pisanie to co innego: klawisz pod palcem tylko JASNIEJE, i to
	 * ostatnie, wiec widac nacisniecie takze na klawiszu juz zapalonym.
	 * Gdyby pisanie tez dawalo akcent, kazde uderzenie wygladalo by jak
	 * wlaczenie stanu, ktory zaraz sam gasnie. */
	if (rzad == s->wcisniety_rzad && nr == s->wcisniety_klawisz)
		tlo = s->klaw_aktywny;
	/* Kolor napisu jest staly (Text ma color: Theme.text) dopoki ktos
	 * pisze.  Po chwili bezczynnosci schodzi na Theme.textDim, a cala
	 * reszta pasa zjezdza na polowe jasnosci: napisy wypalaja najszybciej,
	 * ale to tla klawiszy daja wiekszosc emisji, bo zajmuja 78 procent
	 * powierzchni.  Zmierzone: samo przyciemnienie napisow scina srednia
	 * luminancje pasa o 8 procent, razem z tlami o 47. */
	kolor_napisu = s->przyciemniona ? s->napis_slaby : s->napis;
	/* Napis schodzi na Theme.textDim i na tym koniec: puszczony jeszcze raz
	 * przez przygas() mialby kontrast okolo 2:1, czyli bylby nieczytelny.
	 * Tla klawiszy to inna sprawa, one daja wiekszosc emisji. */
	if (s->przyciemniona)
		tlo = przygas(tlo);

	/* Margines wewnatrz pola, jak anchors.margins: Theme.gap / 2. */
	wx = x + s->odstep / 2;
	wy = y + s->odstep / 2;
	ww = w - s->odstep;
	wh = h - s->odstep;
	rysuj_klawisz(&s->ekran, wx, wy, ww, wh, s->promien, tlo, s->tlo);

	if (k->ikona != IKONA_BRAK) {
		/* Ikona zamiast znaku Unicode, ktorego czcionka nie ma: bok
		 * 1,35 razy Theme.fontMain, jak KeyIcon w QML. */
		int bok = s->font_glowny * 135 / 100;

		if (bok > wh * 3 / 4)
			bok = wh * 3 / 4;
		rysuj_ikone(&s->ekran, wx + (ww - bok) / 2, wy + (wh - bok) / 2,
			    bok, k->ikona, kolor_napisu, tlo);
		return;
	}

	/* font.pixelSize: key.special ? Theme.fontLabel : Theme.fontMain. */
	rozmiar = specjalny ? s->font_etykiety : s->font_glowny;
	while (rozmiar > 8 && tekst_sans_szerokosc(napis, rozmiar) > ww - 4)
		rozmiar -= 2;
	tx = wx + (ww - tekst_sans_szerokosc(napis, rozmiar)) / 2;
	ty = wy + (wh - tekst_sans_wysokosc(rozmiar)) / 2;
	rysuj_tekst_sans(&s->ekran, tx, ty, napis, rozmiar, kolor_napisu, tlo);

}

/* Dymek z wariantami nad klawiszem: AltPopup.qml.
 *
 * Wymiary stamtad: wysokosc rowna rzedowi, szerokosc rowna liczbie wariantow
 * razy rzad, obwodka w kolorze akcentu, tlo Theme.keyBgActive.  Dymek stoi
 * nad klawiszem i jest trzymany w granicach ekranu, zeby skrajne kolumny nie
 * uciekaly za krawedz. */
/* Kolor taki, jak ma byc w biezacym stanie pasa: jasny przy pracy, przygaszony
 * po chwili ciszy.  Dymek rysuje sie tymi samymi barwami co klawisze, wiec
 * bez tego bylby najjasniejsza rzecza na przyciemnionym ekranie. */
static uint32_t barwa(const struct stan *s, uint32_t kolor)
{
	return s->przyciemniona ? przygas(kolor) : kolor;
}

static void rysuj_dymek(struct stan *s)
{
	int i;

	if (!s->dymek_ile)
		return;
	rysuj_klawisz(&s->ekran, s->dymek_x, s->dymek_y, s->dymek_w, s->rzad_h,
		      s->promien, barwa(s, s->klaw_aktywny), s->tlo);
	rysuj_ramke(&s->ekran, s->dymek_x, s->dymek_y, s->dymek_w, s->rzad_h,
		    s->promien, barwa(s, s->akcent));
	for (i = 0; i < s->dymek_ile; i++) {
		const char *z = s->dymek[i];
		int komorka = s->rzad_h;
		int x = s->dymek_x + i * komorka;
		int tx = x + (komorka - tekst_sans_szerokosc(z, s->font_glowny)) / 2;
		int ty = s->dymek_y +
			 (s->rzad_h - tekst_sans_wysokosc(s->font_glowny)) / 2;

		rysuj_tekst_sans(&s->ekran, tx, ty, z, s->font_glowny,
				 barwa(s, s->napis), barwa(s, s->klaw_aktywny));
	}
}

static void rysuj_calosc(struct stan *s)
{
	int r, n;

	s->blok_h = wysokosc_warstwy(s, s->warstwa);
	if (s->blok_h > s->pas_h)
		s->blok_h = s->pas_h;
	s->blok_y = s->pas_y + s->pas_h - s->blok_h;

	rysuj_prostokat(&s->ekran, 0, s->pas_y, (int)s->ekran.szerokosc,
			s->pas_h, s->tlo);
	for (r = 0; r < rzedow(s); r++)
		for (n = 0; n < klawiszy_w_rzedzie(s, r); n++)
			rysuj_jeden(s, r, n);
	rysuj_dymek(s);
}



static void pokaz(struct stan *s)
{
	if (!ekran_ten_sam(&s->ekran)) {
		fprintf(stderr, "opis ekranu zmienil sie, nie rysuje\n");
		return;
	}
	rysuj_calosc(s);
	ekran_wyslij(&s->ekran, s->pas_y, s->pas_h);
}

/* ------------------------------------------------------------- wpisywanie */

/* Zapowiedzi tablic znakow: stoja nizej, przy trybie --wpisz, ktory byl
 * pierwszym ich uzytkownikiem. */
static int znak_na_kod(char z, int *shift);
static int ogonek_na_kod(unsigned int znak, int *shift);

/* Jedno uderzenie klawisza z modyfikatorami dolozonymi na ten czas.
 *
 * Modyfikatory trzymamy jako FLAGI, nie jako wcisniete klawisze: tak robi
 * wzorzec (Uinput.tapChar dostaje ctrl i alt argumentami) i dzieki temu nie da
 * sie zostawic w konsoli wcisnietego Ctrl po wyjsciu programu. */
static void wyslij(struct stan *s, int kod, int shift, int altgr)
{
	if (!kod)
		return;
	if (shift)
		wstrzyk_mod(&s->uinput, KEY_LEFTSHIFT, 1);
	if (altgr)
		wstrzyk_mod(&s->uinput, KEY_RIGHTALT, 1);
	if (s->ctrl)
		wstrzyk_mod(&s->uinput, KEY_LEFTCTRL, 1);
	if (s->alt)
		wstrzyk_mod(&s->uinput, KEY_LEFTALT, 1);

	wstrzyk_tap(&s->uinput, kod);

	if (s->alt)
		wstrzyk_mod(&s->uinput, KEY_LEFTALT, 0);
	if (s->ctrl)
		wstrzyk_mod(&s->uinput, KEY_LEFTCTRL, 0);
	if (altgr)
		wstrzyk_mod(&s->uinput, KEY_RIGHTALT, 0);
	if (shift)
		wstrzyk_mod(&s->uinput, KEY_LEFTSHIFT, 0);
}

/* Znak z klawisza albo z dymka.
 *
 * Polski ogonek wysylamy jako prawy Alt i litere bazowa; znak sklada mapa `pl`
 * jadra, wczytana przez usluge.  Wielka litera powstaje tylko dla a do z,
 * dokladnie jak toUpperCase w KeyButton.qml: przy zapalonym Shifcie przecinek
 * zostaje przecinkiem, a nie zamienia sie w znak mniejszosci.
 *
 * Znaki z dymka ida BEZ Shifta stanu, bo w AltPopup.qml wstawiane sa przez
 * Uinput.typeText(ch) wprost, bez pytania o modyfikatory. */
static void wyslij_znak(struct stan *s, const char *znak, int wg_shifta)
{
	int shift = 0, kod;

	if (!znak || !znak[0])
		return;
	if ((unsigned char)znak[0] >= 0xc0 && znak[1]) {
		unsigned int z = (unsigned int)
			(((unsigned char)znak[0] & 0x1f) << 6) |
			((unsigned char)znak[1] & 0x3f);

		kod = ogonek_na_kod(z, &shift);
		wyslij(s, kod, shift, 1);
		return;
	}

	{
		char c = znak[0];

		if (wg_shifta && (s->shift || s->shift_lock) &&
		    c >= 'a' && c <= 'z')
			c = (char)(c - 'a' + 'A');
		kod = znak_na_kod(c, &shift);
	}
	wyslij(s, kod, shift, 0);
}

static void zwolnij_modyfikatory(struct stan *s)
{
	s->shift = s->shift_lock = s->ctrl = s->alt = s->altgr = 0;
}

/* Reakcja na dotkniecie klawisza: handle() z Keyboard.qml, punkt po punkcie. */
static void obsluz(struct stan *s, const struct klawisz *k)
{
	switch (k->rola) {
	case ROLA_SHIFT:
		/* Trzy stany: jedno dotkniecie shift, drugie blokada, trzecie
		 * zgaszenie. */
		if (s->shift && !s->shift_lock)
			s->shift_lock = 1;
		else if (s->shift_lock)
			s->shift = s->shift_lock = 0;
		else
			s->shift = 1;
		pokaz(s);
		return;
	case ROLA_WARSTWA:
		s->warstwa = k->docel;
		s->shift = s->shift_lock = 0;
		pokaz(s);
		return;
	case ROLA_MOD:
		if (k->kod == KEY_LEFTCTRL)
			s->ctrl = !s->ctrl;
		else
			s->alt = !s->alt;
		pokaz(s);
		return;
	case ROLA_NAZWANY:
		wyslij(s, k->kod, s->shift || s->shift_lock, 0);
		break;
	case ROLA_ZNAK:
		wyslij_znak(s, k->znak, 1);
		break;
	default:
		return;
	}

	/* Shift jednorazowy gasnie po znaku, blokada zostaje; Ctrl i Alt gasna
	 * zawsze. */
	if (s->shift && !s->shift_lock)
		s->shift = 0;
	if (s->ctrl || s->alt)
		s->ctrl = s->alt = 0;
	pokaz(s);
}

/* ------------------------------------------------------------------- praca */

/* Zapowiedz: dymek zamyka sie takze przy chowaniu pasa, a jego definicja
 * stoi nizej, przy obsludze dotkniec. */
static void zamknij_dymek(struct stan *s);

static void schowaj(struct stan *s)
{
	if (!s->widoczna)
		return;
	zwolnij_modyfikatory(s);
	zamknij_dymek(s);
	s->widoczna = 0;
	s->wcisniety_rzad = -1;
	s->stlumiony = 0;
	/* Gasimy pas SAMI, zanim oddamy go konsoli.  Wczesniej znikniecie
	 * klawiatury zalezalo wylacznie od tego, ze fbcon przemaluje ekran po
	 * zmianie liczby wierszy; gdyby tego nie zrobil, jasny pas zostalby na
	 * panelu, a tego wlasnie na AMOLED nie wolno zostawiac. */
	if (ekran_ten_sam(&s->ekran)) {
		rysuj_prostokat(&s->ekran, 0, s->pas_y,
				(int)s->ekran.szerokosc, s->pas_h, s->tlo);
		ekran_wyslij(&s->ekran, s->pas_y, s->pas_h);
	}
	konsola_przywroc(&s->konsola);
}

static void pokaz_pas(struct stan *s)
{
	int oddane;

	if (s->widoczna)
		return;
	oddane = konsola_zwez(&s->konsola, s->pas_h);
	if (oddane < 0)
		return;
	s->widoczna = 1;
	s->wcisniety_rzad = -1;
	s->przyciemniona = 0;
	s->aktywnosc_ms = teraz_ms();
	s->przesuniecie_ms = s->aktywnosc_ms;
	konsola_odgas(&s->konsola);
	pokaz(s);
}

/*
 * Ochrona matrycy, liczona przy kazdym obrocie glownej petli.
 *
 * Petla i tak budzi sie co najwyzej po 500 ms, wiec nie ma tu zadnego nowego
 * zegara ani watku.  Kolejnosc progow jest od najlzejszego do najciezszego,
 * a kazdy z nich konczy sie przerysowaniem pasa, bo inaczej zmiana zostalaby
 * tylko w pamieci.
 */
/* Kazde przejscie ekranu miedzy stanami zostawia slad w dzienniku.  Bez tego
 * jedynym sposobem sprawdzenia, CZEMU ekran nie gasnie, jest pytanie
 * czlowieka, co widzi, a to nie jest pomiar. */
static void slad(const struct stan *s, const char *co)
{
	fprintf(stderr, "ekran: %s (nasz stan %d, jadro %d)\n", co,
		s->ekran_zgaszony, konsola_zgaszona(&s->konsola));
}

/*
 * Tryb niskiego poboru ukladu dotyku.  Przy zgaszonym ekranie uklad przestaje
 * zglaszac wspolrzedne i sam rozpoznaje dwuklik, wiec zadne przypadkowe
 * dotkniecie, ani reka trzymajaca telefon, ani kieszen, ekranu nie obudzi.
 * Zmierzone przed napisaniem latki: pieciosekundowy przesuw palca nie dal
 * w tym trybie ani jednego przerwania, dwuklik dal dokladnie jedno.
 *
 * Gdy sterownik jadra tego nie umie (starsze jadro, uklad bez biblioteki
 * gestow), zostaje filtr programowy w dotyk_przy_zgaszonym().
 */
static void niski_pobor(struct stan *s, int wlacz)
{
	int fd = open(NISKI_POBOR, O_WRONLY);
	int ok = 0;

	if (fd >= 0) {
		ok = write(fd, wlacz ? "1" : "0", 1) == 1;
		close(fd);
	}
	s->niski_pobor = wlacz && ok;
	if (!ok)
		fprintf(stderr, "ekran: uklad dotyku nie przyjal trybu %d\n",
			wlacz);
}

static void zgas_ekran(struct stan *s)
{
	if (s->ekran_zgaszony) {
		slad(s, "gasic nie trzeba, juz zgaszony");
		return;
	}
	/*
	 * Czern malujemy SAMI, zanim poprosimy jadro o wygaszenie.  Samo
	 * wygaszenie konczy sie w simpledrm wyzerowaniem prawdziwego bufora,
	 * ale emulacja fbdev przepisuje do niego zmiany z bufora cienia
	 * z opoznieniem, wiec ostatni rysunek potrafil dojechac PO zerowaniu
	 * i zapalic obraz z powrotem.  Zmierzone 23.09.2026: DRM mowil
	 * dpms Off, a panel swiecil.  Czarny cien nie ma czego przywrocic;
	 * przerwa daje przepisaniu czas, zanim jadro zatrzyma plaszczyzne.
	 * Obraz wraca przy obudzeniu: konsole przemaluje jadro z bufora
	 * tekstowego, a pas klawiatury pokaz().
	 */
	if (ekran_ten_sam(&s->ekran)) {
		rysuj_prostokat(&s->ekran, 0, 0, (int)s->ekran.szerokosc,
				(int)s->ekran.wysokosc, s->tlo);
		ekran_wyslij(&s->ekran, 0, (int)s->ekran.wysokosc);
		usleep(120000);
	}
	konsola_zgas(&s->konsola);
	s->ekran_zgaszony = 1;
	s->stuk_ms = 0;
	s->zgaszono_ms = teraz_ms();
	niski_pobor(s, 1);
	slad(s, "zgaszony");
}

static void zapal_ekran(struct stan *s)
{
	if (s->niski_pobor)
		niski_pobor(s, 0);
	konsola_odgas(&s->konsola);
	s->ostatnio_ms = teraz_ms();
	s->ekran_zgaszony = 0;
	s->stuk_ms = 0;
	s->aktywnosc_ms = teraz_ms();
	s->przesuniecie_ms = s->aktywnosc_ms;
	if (s->widoczna) {
		/* Konsole przemaluje jadro z bufora tekstowego, ale pas
		 * klawiatury nie jest konsola i nikt go za nas nie odtworzy. */
		s->przyciemniona = 0;
		pokaz(s);
	}
	slad(s, "zapalony");
}

/*
 * Dotkniecie zgaszonego ekranu: budzi dopiero DRUGIE, w odstepie krotszym niz
 * DWUKLIK_MS.  Zwraca 1, gdy dotkniecie zostalo zjedzone i nie ma isc dalej,
 * bo przy zgaszonym ekranie nikt nie chce wpisywac znaku, ktorego nie widzi.
 */
static int blisko(int a, int b)
{
	int r = a - b;

	return (r < 0 ? -r : r) <= DWUKLIK_PROMIEN;
}

/*
 * Wylaczenie telefonu po dziesieciu sekundach trzymania zasilania.
 *
 * Najpierw gasimy ekran: jesli wylaczanie stanie w polowie (znana pulapka tego
 * portu: synchronizacja pamieci UFS potrafi zawisnac), panel zostanie czarny,
 * a nie z ostatnim obrazem wypalanym do wyczerpania baterii.  Samo
 * wylaczenie robi systemd, bo tylko on zamknie uslugi i odmontuje dyski.
 */
static void wylacz_telefon(struct stan *s)
{
	pid_t pid;

	slad(s, "dziesiec sekund zasilania, wylaczam");
	if (s->widoczna)
		schowaj(s);
	zgas_ekran(s);
	sync();

	pid = fork();
	if (pid == 0) {
		execl("/usr/bin/systemctl", "systemctl", "poweroff", (char *)NULL);
		_exit(127);
	}
}

static int dotyk_przy_zgaszonym(struct stan *s)
{
	long long teraz;

	if (!s->ekran_zgaszony)
		return 0;

	/* Przy trybie sprzetowym budzi wylacznie KEY_WAKEUP od ukladu. */
	if (s->niski_pobor)
		return 1;

	teraz = teraz_ms();

	/* Chwila po zgaszeniu nalezy do reki, ktora nacisnela przycisk. */
	if (teraz - s->zgaszono_ms < ZWLOKA_PO_ZGASZENIU_MS) {
		s->stuk_ms = 0;
		return 1;
	}

	if (s->stuk_ms && teraz - s->stuk_ms >= DWUKLIK_MIN_MS &&
	    teraz - s->stuk_ms <= DWUKLIK_MS &&
	    blisko(s->stuk_x, s->wejscie.x) &&
	    blisko(s->stuk_y, s->wejscie.y)) {
		slad(s, "dwuklik budzi");
		zapal_ekran(s);
		return 1;
	}

	s->stuk_ms = teraz;
	s->stuk_x = s->wejscie.x;
	s->stuk_y = s->wejscie.y;

	return 1;
}

static void ochrona_matrycy(struct stan *s)
{
	static const int krok_x[8] = { 0, 2, 3, 2, 0, -2, -3, -2 };
	static const int krok_y[8] = { 0, -1, -2, -1, 0, 1, 2, 1 };
	long long teraz;

	/* Wygasic moze takze samo jadro, po uplywie consoleblank, i wtedy nikt
	 * nam tego nie zglasza.  Bez tego pytania pierwsze dotkniecie po
	 * takim wygaszeniu wpisaloby znak zamiast obudzic ekran. */
	if (!s->ekran_zgaszony && konsola_zgaszona(&s->konsola)) {
		s->ekran_zgaszony = 1;
		s->stuk_ms = 0;
		slad(s, "to jadro wygasilo konsole samo");
	} else if (s->ekran_zgaszony && !konsola_zgaszona(&s->konsola)) {
		slad(s, "jadro odgasilo konsole bez nas");
		zapal_ekran(s);
	}

	if (!s->ekran_zgaszony && !s->wejscie.zasilanie &&
	    teraz_ms() - s->ostatnio_ms >= EKRAN_MS) {
		slad(s, "trzydziesci sekund ciszy");
		zgas_ekran(s);
	}

	if (!s->widoczna || s->ekran_zgaszony)
		return;

	teraz = teraz_ms();

	/* Palec na klawiszu to aktywnosc, nawet gdy nic sie nie wysyla. */
	if (s->wcisniety_rzad >= 0)
		s->aktywnosc_ms = teraz;

	if (teraz - s->aktywnosc_ms >= SCHOWANIE_MS) {
		schowaj(s);
		return;
	}

	if (teraz - s->aktywnosc_ms >= MODYFIKATORY_MS &&
	    (s->shift || s->shift_lock || s->ctrl || s->alt || s->altgr)) {
		zwolnij_modyfikatory(s);
		pokaz(s);
	}

	if (!s->przyciemniona && teraz - s->aktywnosc_ms >= PRZYCIEMNIENIE_MS) {
		s->przyciemniona = 1;
		pokaz(s);
	}

	/* Przesuwamy tylko obraz, ktorego nikt nie dotyka.  geometria() liczy
	 * z przesunieciem takze trafienie w klawisz, wiec skok o dwa piksele
	 * miedzy postawieniem a puszczeniem palca potrafi zamienic klawisz na
	 * sasiedni i zgubic znak bez sladu.  Otwarty dymek ma juz policzone
	 * wspolrzedne, wiec po przesunieciu wisialby obok swojego klawisza. */
	if (s->wcisniety_rzad < 0 && !s->dymek_ile &&
	    teraz - s->aktywnosc_ms >= PRZYCIEMNIENIE_MS &&
	    teraz - s->przesuniecie_ms >= PRZESUNIECIE_MS) {
		s->krok_przesuniecia = (s->krok_przesuniecia + 1) & 7;
		s->przesun_x = krok_x[s->krok_przesuniecia];
		s->przesun_y = krok_y[s->krok_przesuniecia];
		s->przesuniecie_ms = teraz;
		pokaz(s);
	}
}



/* Dymek wariantow: otwiera go przytrzymanie, zamyka nastepne dotkniecie.
 *
 * Wymiary i ograniczenia wprost z AltPopup.qml: szerokosc to liczba wariantow
 * razy wysokosc rzedu, dymek stoi nad klawiszem, a gdy nie miesci sie
 * w szerokosci, dosuwa sie do krawedzi. */
static void otworz_dymek(struct stan *s, int rzad, int nr)
{
	const struct klawisz *k = klawisz_w(s, rzad, nr);
	int x, y, w, h, ile = 0, lewo, prawo;

	while (ile < WARIANTOW_MAX && k->warianty[ile])
		ile++;
	if (!ile)
		return;
	geometria(s, rzad, nr, &x, &y, &w, &h);

	s->dymek = k->warianty;
	s->dymek_ile = ile;
	s->dymek_w = ile * s->rzad_h;
	lewo = s->margines_bok;
	prawo = (int)s->ekran.szerokosc - s->margines_bok - s->dymek_w;
	s->dymek_x = x + w / 2 - s->dymek_w / 2;
	if (s->dymek_x > prawo)
		s->dymek_x = prawo;
	if (s->dymek_x < lewo)
		s->dymek_x = lewo;
	s->dymek_y = y - s->rzad_h - s->odstep;
	if (s->dymek_y < s->blok_y)
		s->dymek_y = s->blok_y;
	/* Dotkniecie, ktore otworzylo dymek, nie moze juz wpisac litery. */
	s->stlumiony = 1;
	pokaz(s);
}

static void zamknij_dymek(struct stan *s)
{
	s->dymek = NULL;
	s->dymek_ile = 0;
}

static void dotkniecie(struct stan *s)
{
	int rzad, nr;
	const struct klawisz *k;

	if (!s->widoczna)
		return;

	/* Kazde dotkniecie budzi konsole i cofa przyciemnienie.  Odgaszenie
	 * idzie przez jadro, bo to ono wygasilo panel i tylko ono umie
	 * przemalowac konsole z bufora tekstowego. */
	konsola_odgas(&s->konsola);
	s->aktywnosc_ms = teraz_ms();
	if (s->przyciemniona) {
		s->przyciemniona = 0;
		pokaz(s);
	}

	/* Przy otwartym dymku dotkniecie wybiera wariant albo go zamyka, tak
	 * jak dwa TapHandlery w AltPopup.qml. */
	if (s->dymek_ile) {
		int w_dymku = s->wejscie.x >= s->dymek_x &&
			      s->wejscie.x < s->dymek_x + s->dymek_w &&
			      s->wejscie.y >= s->dymek_y &&
			      s->wejscie.y < s->dymek_y + s->rzad_h;
		int ktory = (s->wejscie.x - s->dymek_x) / s->rzad_h;

		if (w_dymku && ktory >= 0 && ktory < s->dymek_ile)
			wyslij_znak(s, s->dymek[ktory], 0);
		zamknij_dymek(s);
		s->wcisniety_rzad = -1;
		pokaz(s);
		return;
	}

	if (s->wejscie.y < s->blok_y)
		return;
	if (!trafiony(s, s->wejscie.x, s->wejscie.y, &rzad, &nr))
		return;
	k = klawisz_w(s, rzad, nr);
	if (!k || k->rola == ROLA_ODSTEP)
		return;

	/* Dotkniecie tylko podswietla klawisz.  Co z niego wyjdzie, wiadomo
	 * dopiero przy puszczeniu palca albo po przekroczeniu progu
	 * przytrzymania. */
	s->wcisniety_rzad = rzad;
	s->wcisniety_klawisz = nr;
	s->dotyk_ms = teraz_ms();
	s->powtorka_ms = 0;
	s->stlumiony = 0;
	pokaz(s);
}

/* Palec stoi na klawiszu: po progu otwieramy dymek albo zaczynamy powtarzac. */
static void sprawdz_przytrzymanie(struct stan *s)
{
	const struct klawisz *k;
	long long teraz;

	if (!s->widoczna || s->wcisniety_rzad < 0 || s->dymek_ile)
		return;
	k = klawisz_w(s, s->wcisniety_rzad, s->wcisniety_klawisz);
	if (!k)
		return;
	teraz = teraz_ms();

	if (k->warianty[0] && !s->stlumiony &&
	    teraz - s->dotyk_ms >= PRZYTRZYMANIE_MS) {
		otworz_dymek(s, s->wcisniety_rzad, s->wcisniety_klawisz);
		return;
	}

	/* Autopowtarzanie klawiszy z polem rep: zwloka, potem staly krok. */
	if (!k->powtarza)
		return;
	if (!s->powtorka_ms) {
		if (teraz - s->dotyk_ms < AUTO_ZWLOKA_MS)
			return;
	} else if (teraz - s->powtorka_ms < AUTO_KROK_MS) {
		return;
	}
	s->powtorka_ms = teraz;
	/* Powtarzanie zjada dotkniecie, wiec puszczenie palca nie doda
	 * jeszcze jednego znaku (w QML robi to repeatTimer.fired). */
	s->stlumiony = 1;
	obsluz(s, k);
}

static void koniec_dotkniecia(struct stan *s)
{
	const struct klawisz *k;
	int rzad, nr;
	int wcisniety_rzad = s->wcisniety_rzad;
	int wcisniety_nr = s->wcisniety_klawisz;

	if (!s->widoczna || wcisniety_rzad < 0)
		return;
	k = klawisz_w(s, wcisniety_rzad, wcisniety_nr);
	s->wcisniety_rzad = -1;

	/* gesturePolicy: ReleaseWithinBounds z KeyButton.qml: znak wychodzi
	 * tylko wtedy, gdy palec zszedl z TEGO klawisza, na ktory stanal. */
	if (k && !s->stlumiony &&
	    trafiony(s, s->wejscie.x, s->wejscie.y, &rzad, &nr) &&
	    rzad == wcisniety_rzad && nr == wcisniety_nr) {
		obsluz(s, k);
		return;
	}
	s->stlumiony = 0;
	pokaz(s);
}

/* ------------------------------------------------------------------- tryby */

/* Znak na kod klawisza i potrzebe Shifta; tylko to, co przyda sie w tescie.
 *
 * Litery wypisane sa po jednej, bo kody klawiszy ida w kolejnosci ukladu
 * QWERTY, a nie alfabetu: liczenie ich jako KEY_A plus pozycja w alfabecie
 * daje z "test123" napis "ngbn123" (zmierzone). */
static int znak_na_kod(char z, int *shift)
{
	static const int LITERY[26] = {
		KEY_A, KEY_B, KEY_C, KEY_D, KEY_E, KEY_F, KEY_G, KEY_H,
		KEY_I, KEY_J, KEY_K, KEY_L, KEY_M, KEY_N, KEY_O, KEY_P,
		KEY_Q, KEY_R, KEY_S, KEY_T, KEY_U, KEY_V, KEY_W, KEY_X,
		KEY_Y, KEY_Z,
	};
	static const struct { char z; int kod; int sh; } INNE[] = {
		{ '1', KEY_1, 0 }, { '2', KEY_2, 0 }, { '3', KEY_3, 0 },
		{ '4', KEY_4, 0 }, { '5', KEY_5, 0 }, { '6', KEY_6, 0 },
		{ '7', KEY_7, 0 }, { '8', KEY_8, 0 }, { '9', KEY_9, 0 },
		{ '0', KEY_0, 0 }, { ' ', KEY_SPACE, 0 }, { '-', KEY_MINUS, 0 },
		{ '.', KEY_DOT, 0 }, { '/', KEY_SLASH, 0 }, { ',', KEY_COMMA, 0 },
		{ '\n', KEY_ENTER, 0 }, { '_', KEY_MINUS, 1 },
		{ '|', KEY_BACKSLASH, 1 }, { '~', KEY_GRAVE, 1 },
		{ '`', KEY_GRAVE, 0 }, { '=', KEY_EQUAL, 0 }, { '+', KEY_EQUAL, 1 },
		{ '[', KEY_LEFTBRACE, 0 }, { ']', KEY_RIGHTBRACE, 0 },
		{ '{', KEY_LEFTBRACE, 1 }, { '}', KEY_RIGHTBRACE, 1 },
		{ '\\', KEY_BACKSLASH, 0 }, { ';', KEY_SEMICOLON, 0 },
		{ ':', KEY_SEMICOLON, 1 }, { '\'', KEY_APOSTROPHE, 0 },
		{ '"', KEY_APOSTROPHE, 1 }, { '<', KEY_COMMA, 1 },
		{ '>', KEY_DOT, 1 }, { '?', KEY_SLASH, 1 },
		{ '!', KEY_1, 1 }, { '@', KEY_2, 1 }, { '#', KEY_3, 1 },
		{ '$', KEY_4, 1 }, { '%', KEY_5, 1 }, { '^', KEY_6, 1 },
		{ '&', KEY_7, 1 }, { '*', KEY_8, 1 }, { '(', KEY_9, 1 },
		{ ')', KEY_0, 1 },
	};
	unsigned int i;

	*shift = 0;
	if (z >= 'A' && z <= 'Z') {
		*shift = 1;
		z = (char)(z - 'A' + 'a');
	}
	if (z >= 'a' && z <= 'z')
		return LITERY[z - 'a'];
	for (i = 0; i < sizeof(INNE) / sizeof(INNE[0]); i++)
		if (INNE[i].z == z) {
			*shift = INNE[i].sh;
			return INNE[i].kod;
		}
	return 0;
}

/* Polski znak na klawisz podstawowy; prawy Alt dokladany jest przez wolacego.
 *
 * Po co: tryb --wpisz to jedyny sposob sprawdzenia sciezki ogonkow bez palca
 * na ekranie.  Tablica jest odwrotnoscia wariant_polski, rozszerzona o wielkie
 * litery, bo te siedza w mapie `pl` pod prawym Altem z Shiftem. */
static int ogonek_na_kod(unsigned int znak, int *shift)
{
	static const struct {
		unsigned int znak;
		char baza;
		int duzy;
	} TABLICA[] = {
		{ 0x0105, 'a', 0 }, { 0x0104, 'a', 1 },
		{ 0x0107, 'c', 0 }, { 0x0106, 'c', 1 },
		{ 0x0119, 'e', 0 }, { 0x0118, 'e', 1 },
		{ 0x0142, 'l', 0 }, { 0x0141, 'l', 1 },
		{ 0x0144, 'n', 0 }, { 0x0143, 'n', 1 },
		{ 0x00f3, 'o', 0 }, { 0x00d3, 'o', 1 },
		{ 0x015b, 's', 0 }, { 0x015a, 's', 1 },
		{ 0x017a, 'x', 0 }, { 0x0179, 'x', 1 },
		{ 0x017c, 'z', 0 }, { 0x017b, 'z', 1 },
	};
	size_t i;

	for (i = 0; i < sizeof(TABLICA) / sizeof(TABLICA[0]); i++)
		if (TABLICA[i].znak == znak) {
			int bez_znaczenia;

			*shift = TABLICA[i].duzy;
			return znak_na_kod(TABLICA[i].baza, &bez_znaczenia);
		}
	return 0;
}

static int tryb_wpisz(const char *tekst)
{
	struct wstrzyk u;
	const char *p;

	if (wstrzyk_otworz(&u, NAZWA_NASZA) < 0)
		return 1;
	/* Konsola wiaze sie z nowym urzadzeniem asynchronicznie; bez tej
	 * przerwy pierwsze znaki przepadaja. */
	usleep(300000);

	for (p = tekst; *p; p++) {
		int shift, kod, altgr = 0;

		/* Kazdy polski ogonek ma w UTF-8 dwa bajty, wiec starczy ten
		 * jeden przypadek; dluzsze ciagi pomijamy. */
		if ((unsigned char)*p >= 0xc0 && (unsigned char)p[1]) {
			unsigned int znak = (unsigned int)
				(((unsigned char)*p & 0x1f) << 6) |
				((unsigned char)p[1] & 0x3f);

			kod = ogonek_na_kod(znak, &shift);
			altgr = 1;
			p++;
		} else {
			kod = znak_na_kod(*p, &shift);
		}

		if (!kod)
			continue;
		if (shift)
			wstrzyk_mod(&u, KEY_LEFTSHIFT, 1);
		if (altgr)
			wstrzyk_mod(&u, KEY_RIGHTALT, 1);
		wstrzyk_tap(&u, kod);
		if (altgr)
			wstrzyk_mod(&u, KEY_RIGHTALT, 0);
		if (shift)
			wstrzyk_mod(&u, KEY_LEFTSHIFT, 0);
		usleep(20000);
	}
	usleep(200000);
	wstrzyk_zamknij(&u);
	return 0;
}

/* Skala od obu krawedzi ekranu.
 *
 * Panel tego telefonu jest zakrzywiony po bokach, wiec czesc pikseli przy
 * krawedzi jest nieczytelna. Ile dokladnie, nie wynika z zadnego rejestru ani
 * z drzewa: trzeba popatrzec. Ten tryb rysuje ponumerowane paski co 16 pikseli
 * od lewej i od prawej, zeby zamiast zgadywac, odczytac numer pierwszego
 * paska, ktory widac w calosci. */
static int tryb_linijka(struct stan *s)
{
	const int KROK = 16, SZER = 6, WYS = 240, ILE = 8;
	uint32_t tlo = ekran_kolor(&s->ekran, 0x00, 0x00, 0x00);
	uint32_t jasny = ekran_kolor(&s->ekran, 0xff, 0xff, 0xff);
	uint32_t akcent = ekran_kolor(&s->ekran, 0x00, 0xd0, 0xe0);
	int gora = (int)s->ekran.wysokosc / 3;
	int i;

	rysuj_prostokat(&s->ekran, 0, 0, (int)s->ekran.szerokosc,
			(int)s->ekran.wysokosc, tlo);

	for (i = 0; i < ILE; i++) {
		char podpis[4];
		int xl = i * KROK;
		int xp = (int)s->ekran.szerokosc - SZER - i * KROK;
		uint32_t kolor = (i % 2) ? akcent : jasny;

		rysuj_prostokat(&s->ekran, xl, gora, SZER, WYS, kolor);
		rysuj_prostokat(&s->ekran, xp, gora + WYS + 40, SZER, WYS, kolor);

		snprintf(podpis, sizeof(podpis), "%d", i);
		rysuj_tekst(&s->ekran, xl, gora + WYS + 8, podpis, 2, kolor);
		rysuj_tekst(&s->ekran, xp - 24, gora + WYS + 40 + WYS + 8,
			    podpis, 2, kolor);
	}

	rysuj_tekst(&s->ekran, 200, gora - 80, "skala co 16 px", 2, jasny);
	ekran_wyslij(&s->ekran, 0, (int)s->ekran.wysokosc);
	printf("paski co %d px, numer N stoi %d px od krawedzi\n", KROK, KROK);
	printf("gorny rzad liczy od LEWEJ, dolny od PRAWEJ; Ctrl+C konczy\n");
	fflush(stdout);

	/* Nie stoimy tu bez konca: to jest AMOLED, a te paski maja staly
	 * ksztalt i pelna jasnosc.  Po DIAGNOSTYKA_MS gasimy ekran i
	 * wychodzimy, tak samo jakby ktos wcisnal Ctrl+C. */
	{
		long long do_kiedy = teraz_ms() + DIAGNOSTYKA_MS;

		while (!koniec && teraz_ms() < do_kiedy)
			sleep(1);
	}

	rysuj_prostokat(&s->ekran, 0, 0, (int)s->ekran.szerokosc,
			(int)s->ekran.wysokosc, tlo);
	ekran_wyslij(&s->ekran, 0, (int)s->ekran.wysokosc);
	return 0;
}

static int tryb_surowy(struct stan *s)
{
	/* Klawiatura jest widoczna, zeby bylo w co celowac, ale urzadzenie
	 * wpisujace nie istnieje, wiec ten tryb nic nie wysyla do konsoli. */
	long long do_kiedy;

	s->uinput.fd = -1;
	pokaz_pas(s);
	printf("dotykaj klawiszy; wyjscie przez Ctrl+C\n");
	/* Ten sam sufit co w pozostalych trybach diagnostycznych: pas swieci
	 * przez caly czas ich trwania, a przy kalibracji telefon potrafi lezec
	 * godzinami. */
	do_kiedy = teraz_ms() + DIAGNOSTYKA_MS;
	for (;;) {
		enum zdarzenie z = wejscie_pobierz(&s->wejscie, 1000);

		if (teraz_ms() >= do_kiedy)
			break;
		ochrona_matrycy(s);

		if (koniec)
			break;
		if (z == ZD_DOTYK_START) {
			int rzad, nr;
			const struct klawisz *k = NULL;

			if (trafiony(s, s->wejscie.x, s->wejscie.y, &rzad, &nr))
				k = klawisz_w(s, rzad, nr);
			printf("surowe X=%4d Y=%4d  ->  piksel %4d %4d  ->  %s\n",
			       s->wejscie.surowy_x, s->wejscie.surowy_y,
			       s->wejscie.x, s->wejscie.y,
			       k ? opis_klawisza(s, k) : "(poza klawiatura)");
		}
		else if (z == ZD_PRZELACZ)
			printf("przycisk Bixby\n");
		fflush(stdout);
	}
	return 0;
}

/* -------------------------------------------------------------------- main */

static int wez_blokade(void)
{
	int fd = open(BLOKADA, O_RDWR | O_CREAT, 0600);

	if (fd < 0) {
		perror(BLOKADA);
		return -1;
	}
	if (flock(fd, LOCK_EX | LOCK_NB) < 0) {
		fprintf(stderr, "klawiatura juz dziala (blokada %s)\n", BLOKADA);
		close(fd);
		return -1;
	}
	return fd;
}

int main(int argc, char **argv)
{
	struct stan s;
	struct sigaction sa;
	int blokada, i;
	int tylko_rysuj = 0, surowy = 0, od_razu = 0, linijka = 0, podglad = 0;
	long long koniec_podgladu;
	int startowa_warstwa = 0;
	const char *wpisz = NULL;
	/* Urzadzenie dotyku da sie podmienic, zeby proba gestu obeszla sie
	 * bez czlowieka: patrz tools/klawiatura/palec.c. */
	const char *nazwa_dotyku = NAZWA_DOTYKU;
	/* --zrzut rysuje klawiature do pliku zamiast na panel: jedyny sposob
	 * obejrzenia zmiany w wygladzie, gdy telefonu nie ma pod reka. */
	const char *zrzut = NULL;

	memset(&s, 0, sizeof(s));
	s.wcisniety_rzad = -1;

	for (i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--przywroc")) {
			struct konsola k;

			if (konsola_otworz(&k, "/dev/tty0") < 0)
				return 1;
			konsola_przywroc(&k);
			printf("konsola ma z powrotem %d wierszy\n", k.wiersze_pelne);
			konsola_zamknij(&k);
			return 0;
		} else if (!strcmp(argv[i], "--tylko-rysuj")) {
			tylko_rysuj = 1;
		} else if (!strcmp(argv[i], "--surowy")) {
			surowy = 1;
		} else if (!strcmp(argv[i], "--linijka")) {
			linijka = 1;
		} else if (!strcmp(argv[i], "--warstwa") && i + 1 < argc) {
			/* Do zrzutow: pokaz od razu wskazana warstwe. */
			startowa_warstwa = atoi(argv[++i]);
		} else if (!strcmp(argv[i], "--widoczna")) {
			od_razu = 1;
		} else if (!strcmp(argv[i], "--podglad-stanow")) {
			/* Rysuje pasek ze WSZYSTKIMI stanami klawisza naraz:
			 * jeden wcisniety i dwa zapalone modyfikatory.  Bez
			 * tego stanu wcisnietego nie da sie pokazac inaczej
			 * niz palcem, a wlasnie on niesie kolor Theme.keyBgDown
			 * i on rozstrzyga, czy paleta zostala przeniesiona
			 * w calosci. */
			podglad = 1;
			tylko_rysuj = 1;
			od_razu = 1;
		} else if (!strcmp(argv[i], "--wpisz") && i + 1 < argc) {
			wpisz = argv[++i];
		} else if (!strcmp(argv[i], "--dotyk") && i + 1 < argc) {
			nazwa_dotyku = argv[++i];
		} else if (!strcmp(argv[i], "--zrzut") && i + 1 < argc) {
			zrzut = argv[++i];
		} else {
			fprintf(stderr,
				"uzycie: %s [--widoczna] [--tylko-rysuj] [--surowy]\n"
				"        [--wpisz TEKST] [--dotyk NAZWA]"
			" [--zrzut PLIK.ppm] [--przywroc]\n", argv[0]);
			return 2;
		}
	}

	if (wpisz)
		return tryb_wpisz(wpisz);

	/* Zrzut nie dotyka ani panelu, ani konsoli, ani wejscia, wiec nie bierze
	 * tez blokady: da sie go zrobic na komputerze, obok dzialajacej
	 * klawiatury na telefonie. */
	if (!zrzut) {
		blokada = wez_blokade();
		if (blokada < 0)
			return 1;
	} else {
		blokada = -1;
	}

	memset(&sa, 0, sizeof(sa));
	sa.sa_handler = na_sygnal;
	sigaction(SIGINT, &sa, NULL);
	sigaction(SIGTERM, &sa, NULL);
	sigaction(SIGHUP, &sa, NULL);
	sigaction(SIGUSR1, &sa, NULL);

	if (zrzut) {
		/* Rozmiar panelu tego telefonu i komorka konsoli przy czcionce
		 * 32x64, czyli to samo, co zmierzyloby sie na urzadzeniu. */
		if (ekran_zastepczy(&s.ekran, 1440, 3040) < 0)
			return 1;
		s.konsola.komorka = 64;
		s.konsola.fd = -1;
	} else {
		if (ekran_otworz(&s.ekran, "/dev/fb0") < 0)
			return 1;
		if (konsola_otworz(&s.konsola, "/dev/tty0") < 0) {
			ekran_zamknij(&s.ekran);
			return 1;
		}
		if (wejscie_otworz(&s.wejscie, nazwa_dotyku, NAZWA_KLAWISZY,
				   (int)s.ekran.szerokosc,
				   (int)s.ekran.wysokosc) < 0) {
			konsola_zamknij(&s.konsola);
			ekran_zamknij(&s.ekran);
			return 1;
		}
	}

	/* Gestosc ekranu, a z niej wszystkie wymiary podane w milimetrach. */
	s.dpmm_x100 = (int)s.ekran.szerokosc * 100 / SZEROKOSC_PANELU_MM;
	s.odstep = s.dpmm_x100 * GAP_MM_X100 / 10000;
	if (s.odstep < 2)
		s.odstep = 2;
	s.promien = s.dpmm_x100 * PROMIEN_MM_X100 / 10000;
	s.margines_bok = s.dpmm_x100 * KRZYWIZNA_MM_X100 / 10000 + s.odstep / 2;
	s.rzad_h = s.dpmm_x100 * RZAD_MM_X100 / 10000;

	/* Pas oddawany przez konsole liczymy z NAJWYZSZEJ warstwy, bo tylko
	 * wtedy przelaczenie warstwy nie musi ruszac konsoli: zwezenie jest
	 * trwalym stanem jadra i kazda zmiana mrugalaby calym ekranem.
	 * Warstwa nizsza zostawia u gory pasa tlo, dokladnie tak, jak w Main.qml
	 * zostawia je obszar nad klawiatura. */
	s.pas_h = 0;
	for (i = 0; i < WARSTW; i++) {
		int h = wysokosc_warstwy(&s, i);

		if (h > s.pas_h)
			s.pas_h = h;
	}
	s.pas_h = (s.pas_h + s.konsola.komorka - 1) / s.konsola.komorka *
		  s.konsola.komorka;
	s.pas_y = (int)s.ekran.wysokosc - s.pas_h;
	s.blok_h = s.pas_h;
	s.blok_y = s.pas_y;
	s.font_glowny = s.rzad_h * FONT_GLOWNY_PROC / 100;
	s.font_etykiety = s.rzad_h * FONT_ETYKIETY_PROC / 100;
	kolory(&s);
	if (startowa_warstwa > 0 && startowa_warstwa < WARSTW)
		s.warstwa = startowa_warstwa;

	printf("ekran %ux%u, komorka konsoli %d px, pas %d px od %d, rzad %d px\n",
	       s.ekran.szerokosc, s.ekran.wysokosc, s.konsola.komorka,
	       s.pas_h, s.pas_y, s.rzad_h);

	if (zrzut) {
		int rc;

		s.widoczna = 1;
		if (podglad) {
			/* Wszystkie stany naraz: klawisz wcisniety, zapalone
			 * Ctrl i Alt oraz ZABLOKOWANY Shift, ktory pali sie
			 * na wlasnym klawiszu. */
			s.wcisniety_rzad = 2;
			s.wcisniety_klawisz = 1;
			s.shift_lock = 1;
			s.ctrl = 1;
			s.alt = 1;
		}
		rysuj_calosc(&s);
		rc = ekran_zapisz_ppm(&s.ekran, zrzut, s.pas_y, s.pas_h);
		if (!rc)
			printf("zapisano %s (%d na %d)\n", zrzut,
			       (int)s.ekran.szerokosc, s.pas_h);
		ekran_zamknij(&s.ekran);
		return rc ? 1 : 0;
	}

	if (linijka) {
		int rc = tryb_linijka(&s);

		wejscie_zamknij(&s.wejscie);
		konsola_zamknij(&s.konsola);
		ekran_zamknij(&s.ekran);
		close(blokada);
		return rc;
	}

	if (surowy) {
		int rc = tryb_surowy(&s);

		schowaj(&s);
		wejscie_zamknij(&s.wejscie);
		konsola_zamknij(&s.konsola);
		ekran_zamknij(&s.ekran);
		close(blokada);
		return rc;
	}

	if (!tylko_rysuj && wstrzyk_otworz(&s.uinput, NAZWA_NASZA) < 0) {
		wejscie_zamknij(&s.wejscie);
		konsola_zamknij(&s.konsola);
		ekran_zamknij(&s.ekran);
		return 1;
	}

	if (tylko_rysuj || od_razu)
		pokaz_pas(&s);

	if (podglad) {
		/* Litera "a" w rzedzie a..l (zerowy element tego rzedu to
		 * odstep): klawisz zwykly, wiec widac na nim kolor wcisniecia,
		 * a nie odcien klawisza funkcyjnego.  Ustawiamy to PO pokaz_pas,
		 * bo ono samo zeruje wcisniety klawisz tuz przed rysowaniem. */
		s.wcisniety_rzad = 2;
		s.wcisniety_klawisz = 1;
		s.shift_lock = 1;
		s.ctrl = 1;
		s.alt = 1;
		pokaz(&s);
	}

	/* Ten sam limit co w linijce: tryb podgladu rysuje raz i czeka, wiec
	 * bez niego nieruchoma klawiatura stalaby na panelu do konca swiata. */
	koniec_podgladu = teraz_ms() + DIAGNOSTYKA_MS;
	/* Od startu liczy sie cisza; bez tego pierwszy obrot petli uznalby,
	 * ze od zera zegara minelo juz duzo wiecej niz EKRAN_MS. */
	s.ostatnio_ms = teraz_ms();

	while (!koniec) {
		/* Z palcem na ekranie budzimy sie czesto, bo inaczej nie da sie
		 * zauwazyc, ze przytrzymanie przekroczylo PRZYTRZYMANIE_MS. */
		enum zdarzenie z = wejscie_pobierz(&s.wejscie,
						   s.wcisniety_rzad >= 0
						   ? 40 : 500);

		if (zadano_przelaczenia) {
			zadano_przelaczenia = 0;
			z = ZD_PRZELACZ;
		}
		if (z == ZD_BLAD)
			break;
		ochrona_matrycy(&s);
		if (tylko_rysuj) {
			if (z == ZD_PRZELACZ || teraz_ms() >= koniec_podgladu)
				break;
			continue;
		}
		/* Kazde zdarzenie przy zapalonym ekranie odsuwa jego
		 * wygaszenie o pelne EKRAN_MS. */
		if (z != ZD_BRAK && !s.ekran_zgaszony)
			s.ostatnio_ms = teraz_ms();

		/* Dziesiec sekund samego zasilania wylacza telefon. */
		if (s.wejscie.zasilanie && !s.wejscie.kombinacja &&
		    !s.wylaczanie &&
		    teraz_ms() - s.wejscie.zasilanie_od_ms >= WYLACZENIE_MS) {
			s.wylaczanie = 1;
			wylacz_telefon(&s);
		}

		switch (z) {
		case ZD_BUDZENIE:
			if (s.ekran_zgaszony) {
				slad(&s, "dwuklik rozpoznany przez uklad");
				zapal_ekran(&s);
			}
			break;
		case ZD_EKRAN:
			/* Zwykly przelacznik.  Gasimy przez TIOCL_BLANKSCREEN,
			 * ktory jawnie KAZE jadru zignorowac klawisze (ustawia
			 * ignore_poke), wiec obudzic ekran musimy sami; to
			 * zmierzone, nie zalozone: log zdarzen pokazal, ze
			 * kolejne przycisniecia zasilania przy wygaszonym
			 * panelu zostawialy blanked=1. */
			if (s.ekran_zgaszony)
				zapal_ekran(&s);
			else
				zgas_ekran(&s);
			break;
		case ZD_PRZELACZ:
			/* Przy zgaszonym ekranie Bixby nic nie robi: budzi
			 * wylacznie zasilanie i dwuklik w szybe. */
			if (s.ekran_zgaszony)
				break;
			if (s.widoczna)
				schowaj(&s);
			else
				pokaz_pas(&s);
			break;
		case ZD_DOTYK_START:
			if (dotyk_przy_zgaszonym(&s))
				break;
			/* Dotkniecie zapalonego ekranu odsuwa wygaszenie,
			 * takze wtedy, gdy klawiatura jest schowana. */
			konsola_odgas(&s.konsola);
			dotkniecie(&s);
			break;
		case ZD_DOTYK_KONIEC:
			if (s.ekran_zgaszony)
				break;
			koniec_dotkniecia(&s);
			break;
		default:
			break;
		}
		sprawdz_przytrzymanie(&s);
	}

	schowaj(&s);
	if (!tylko_rysuj)
		wstrzyk_zamknij(&s.uinput);
	wejscie_zamknij(&s.wejscie);
	konsola_zamknij(&s.konsola);
	ekran_zamknij(&s.ekran);
	close(blokada);
	printf("koniec, konsola przywrocona\n");
	return 0;
}
