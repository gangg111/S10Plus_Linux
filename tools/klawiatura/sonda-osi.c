// SPDX-License-Identifier: GPL-2.0
// Bezobslugowy opis urzadzenia dotykowego i jego protokolu.
//
// Po co osobno od sondy-dotyku.  Tamta wymaga czlowieka: prosi o dotkniecie
// czterech rogow, zeby ustalic orientacje.  Ta nie prosi o nic i odpowiada na
// pytania, ktore da sie rozstrzygnac bez palca:
//
//   - jakie osie urzadzenie w ogole ma, z zakresem ORAZ z rozdzielczoscia
//     (rozdzielczosc jest tym, czego brakuje bibliotekom przestrzeni
//     uzytkownika do liczenia odleglosci w milimetrach, a od tego zaleza
//     progi gestow),
//   - ile jest slotow, czyli ile palcow naraz jadro potrafi sledzic,
//   - czy urzadzenie deklaruje sie jako bezposrednie (INPUT_PROP_DIRECT),
//   - a gdy podac czas nasluchu, takze JAK wyglada strumien: czy przychodzi
//     identyfikator sladu i czy konczy sie wartoscia -1 przy oderwaniu palca,
//     czy BTN_TOUCH przelacza sie w obie strony, ile slotow uzywanych jest
//     naraz i jak gesto ida paczki.
//
// Ostatnia czesc jest tu dlatego, ze komentarz w wejscie.c twierdzi, ze ten
// kontroler NIE wysyla identyfikatora sladu i ze koniec dotyku trzeba
// wykrywac po przerwie w strumieniu.  To twierdzenie pochodzi sprzed
// wlasciwego sterownika i wymaga sprawdzenia, bo sterownik moze generowac
// identyfikatory sam.  Roznica decyduje o tym, czy da sie rozpoznac gest.
//
// Uzycie:
//   sonda-osi /dev/input/eventN           sam opis, bez nasluchu
//   sonda-osi /dev/input/eventN 10        opis i 10 sekund nasluchu

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/input.h>

#define BITY_NA_DLUGA	(8 * sizeof(unsigned long))
#define SLOW(n)		(((n) + BITY_NA_DLUGA - 1) / BITY_NA_DLUGA)

static int bit(const unsigned long *tab, int n)
{
	return (tab[n / BITY_NA_DLUGA] >> (n % BITY_NA_DLUGA)) & 1;
}

static const char *nazwa_osi(int os)
{
	switch (os) {
	case ABS_X:			return "ABS_X";
	case ABS_Y:			return "ABS_Y";
	case ABS_PRESSURE:		return "ABS_PRESSURE";
	case ABS_MT_SLOT:		return "ABS_MT_SLOT";
	case ABS_MT_TOUCH_MAJOR:	return "ABS_MT_TOUCH_MAJOR";
	case ABS_MT_TOUCH_MINOR:	return "ABS_MT_TOUCH_MINOR";
	case ABS_MT_WIDTH_MAJOR:	return "ABS_MT_WIDTH_MAJOR";
	case ABS_MT_WIDTH_MINOR:	return "ABS_MT_WIDTH_MINOR";
	case ABS_MT_ORIENTATION:	return "ABS_MT_ORIENTATION";
	case ABS_MT_POSITION_X:		return "ABS_MT_POSITION_X";
	case ABS_MT_POSITION_Y:		return "ABS_MT_POSITION_Y";
	case ABS_MT_TOOL_TYPE:		return "ABS_MT_TOOL_TYPE";
	case ABS_MT_BLOB_ID:		return "ABS_MT_BLOB_ID";
	case ABS_MT_TRACKING_ID:	return "ABS_MT_TRACKING_ID";
	case ABS_MT_PRESSURE:		return "ABS_MT_PRESSURE";
	case ABS_MT_DISTANCE:		return "ABS_MT_DISTANCE";
	default:			return NULL;
	}
}

static long long teraz_us(const struct input_event *ev)
{
	return (long long)ev->time.tv_sec * 1000000 + ev->time.tv_usec;
}

static void opisz(int fd)
{
	unsigned long ev_bity[SLOW(EV_MAX + 1)];
	unsigned long abs_bity[SLOW(ABS_MAX + 1)];
	unsigned long key_bity[SLOW(KEY_MAX + 1)];
	unsigned long prop_bity[SLOW(INPUT_PROP_MAX + 1)];
	struct input_absinfo a;
	char nazwa[128] = "";
	int os;

	memset(ev_bity, 0, sizeof(ev_bity));
	memset(abs_bity, 0, sizeof(abs_bity));
	memset(key_bity, 0, sizeof(key_bity));
	memset(prop_bity, 0, sizeof(prop_bity));

	if (ioctl(fd, EVIOCGNAME(sizeof(nazwa)), nazwa) >= 0)
		printf("urzadzenie: %s\n", nazwa);

	if (ioctl(fd, EVIOCGPROP(sizeof(prop_bity)), prop_bity) >= 0) {
		printf("wlasciwosci: ");
		if (bit(prop_bity, INPUT_PROP_DIRECT))
			printf("INPUT_PROP_DIRECT ");
		if (bit(prop_bity, INPUT_PROP_POINTER))
			printf("INPUT_PROP_POINTER ");
		if (bit(prop_bity, INPUT_PROP_BUTTONPAD))
			printf("INPUT_PROP_BUTTONPAD ");
		printf("\n");
	}

	if (ioctl(fd, EVIOCGBIT(0, sizeof(ev_bity)), ev_bity) >= 0) {
		printf("rodzaje zdarzen: ");
		if (bit(ev_bity, EV_SYN))	printf("EV_SYN ");
		if (bit(ev_bity, EV_KEY))	printf("EV_KEY ");
		if (bit(ev_bity, EV_ABS))	printf("EV_ABS ");
		if (bit(ev_bity, EV_REL))	printf("EV_REL ");
		if (bit(ev_bity, EV_SW))	printf("EV_SW ");
		printf("\n");
	}

	if (ioctl(fd, EVIOCGBIT(EV_KEY, sizeof(key_bity)), key_bity) >= 0) {
		printf("klawisze: ");
		if (bit(key_bity, BTN_TOUCH))		printf("BTN_TOUCH ");
		if (bit(key_bity, BTN_TOOL_FINGER))	printf("BTN_TOOL_FINGER ");
		if (bit(key_bity, KEY_WAKEUP))		printf("KEY_WAKEUP ");
		if (bit(key_bity, KEY_POWER))		printf("KEY_POWER ");
		printf("\n");
	}

	printf("\nosie (zakres, ziarno, martwa strefa, ROZDZIELCZOSC):\n");
	if (ioctl(fd, EVIOCGBIT(EV_ABS, sizeof(abs_bity)), abs_bity) < 0) {
		perror("EVIOCGBIT(EV_ABS)");
		return;
	}
	for (os = 0; os <= ABS_MAX; os++) {
		const char *n;

		if (!bit(abs_bity, os))
			continue;
		memset(&a, 0, sizeof(a));
		if (ioctl(fd, EVIOCGABS(os), &a) < 0)
			continue;
		n = nazwa_osi(os);
		printf("  %-20s %5d .. %-5d  fuzz=%d flat=%d  res=%d%s\n",
		       n ? n : "(inna)", a.minimum, a.maximum, a.fuzz, a.flat,
		       a.resolution,
		       a.resolution ? "" : "  <-- BRAK, milimetry nieliczalne");
		if (os == ABS_MT_SLOT)
			printf("  %-20s %d\n", "slotow razem",
			       a.maximum - a.minimum + 1);
	}
}

// Stan slotow prosto z jadra, a nie ze strumienia.
//
// To jest pomiar rozstrzygajacy pytanie, ktorego ze strumienia rozstrzygnac
// sie NIE DA: identyfikator sladu wysylany jest tylko przy PRZEJSCIU slotu
// z wolnego na zajety, wiec slot, ktory raz sie zajal i nigdy nie zwolnil,
// wyglada w strumieniu dokladnie tak samo jak sterownik, ktory identyfikatorow
// nie wysyla wcale.  Jadro trzyma jednak biezacy identyfikator kazdego slotu
// i oddaje go przez EVIOCGMTSLOTS.  Wartosc -1 znaczy slot wolny.
//
// Odczyt przy NIEDOTYKANYM ekranie: same -1 znacza, ze zwalnianie dziala.
// Cokolwiek innego znaczy slot zawieszony na stale.
static void sloty(int fd)
{
	struct input_absinfo a;
	int ile, i;
	int *bufor;

	memset(&a, 0, sizeof(a));
	if (ioctl(fd, EVIOCGABS(ABS_MT_SLOT), &a) < 0)
		return;
	ile = a.maximum - a.minimum + 1;
	if (ile <= 0 || ile > 64)
		return;

	/* Uklad bufora narzuca jadro: pierwsze slowo to kod osi, po nim
	 * po jednej wartosci na slot. */
	bufor = calloc(ile + 1, sizeof(int));
	if (!bufor)
		return;
	bufor[0] = ABS_MT_TRACKING_ID;
	if (ioctl(fd, EVIOCGMTSLOTS((ile + 1) * sizeof(int)), bufor) < 0) {
		perror("EVIOCGMTSLOTS");
		free(bufor);
		return;
	}

	printf("\nidentyfikatory sladu w slotach (-1 = slot wolny):\n ");
	for (i = 0; i < ile; i++) {
		printf(" %d:%d", i, bufor[i + 1]);
		if ((i % 6) == 5)
			printf("\n ");
	}
	printf("\n");
	for (i = 0; i < ile; i++) {
		if (bufor[i + 1] >= 0) {
			printf("  UWAGA: slot %d zajety, choc nikt nie dotyka;"
			       " sterownik go nie zwalnia\n", i);
			break;
		}
	}
	free(bufor);
}

struct obraz {
	int slad_widziany;	/* czy w ogole przyszedl ABS_MT_TRACKING_ID */
	int slad_zwolniony;	/* czy przyszedl z wartoscia -1 */
	int btn_wcisniety;	/* czy BTN_TOUCH przyszedl z 1 */
	int btn_zwolniony;	/* czy BTN_TOUCH przyszedl z 0 */
	int slot_max;		/* najwyzszy uzyty numer slotu */
	int x_min, x_max;
	int y_min, y_max;
	int paczek;
	long long odstep_min, odstep_max, odstep_suma;
};

static void nasluch(int fd, int sekund)
{
	struct obraz o;
	struct input_event ev;
	long long start = -1, ostatnia = 0;
	int slot = 0;

	memset(&o, 0, sizeof(o));
	o.x_min = o.y_min = INT_MAX;
	o.x_max = o.y_max = -1;
	o.slot_max = -1;
	o.odstep_min = -1;

	printf("\nnasluch %d s; dotykaj ekranu, zeby bylo co mierzyc\n", sekund);
	fflush(stdout);

	while (read(fd, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
		long long t = teraz_us(&ev);

		if (start < 0)
			start = t;
		if (t - start > (long long)sekund * 1000000)
			break;

		if (ev.type == EV_ABS) {
			switch (ev.code) {
			case ABS_MT_SLOT:
				slot = ev.value;
				if (slot > o.slot_max)
					o.slot_max = slot;
				break;
			case ABS_MT_TRACKING_ID:
				o.slad_widziany = 1;
				if (ev.value < 0)
					o.slad_zwolniony = 1;
				else if (slot > o.slot_max)
					o.slot_max = slot;
				break;
			case ABS_MT_POSITION_X:
			case ABS_X:
				if (ev.value < o.x_min) o.x_min = ev.value;
				if (ev.value > o.x_max) o.x_max = ev.value;
				break;
			case ABS_MT_POSITION_Y:
			case ABS_Y:
				if (ev.value < o.y_min) o.y_min = ev.value;
				if (ev.value > o.y_max) o.y_max = ev.value;
				break;
			}
			continue;
		}
		if (ev.type == EV_KEY && ev.code == BTN_TOUCH) {
			if (ev.value)
				o.btn_wcisniety = 1;
			else
				o.btn_zwolniony = 1;
			continue;
		}
		if (ev.type != EV_SYN || ev.code != SYN_REPORT)
			continue;

		o.paczek++;
		if (ostatnia) {
			long long d = t - ostatnia;

			/* Przerwy dluzsze niz pol sekundy to czas miedzy
			 * dotknieciami, a nie tempo raportowania. */
			if (d < 500000) {
				if (o.odstep_min < 0 || d < o.odstep_min)
					o.odstep_min = d;
				if (d > o.odstep_max)
					o.odstep_max = d;
				o.odstep_suma += d;
			}
		}
		ostatnia = t;
	}

	printf("\nco widac w strumieniu:\n");
	printf("  paczek (SYN_REPORT)        %d\n", o.paczek);
	if (!o.paczek) {
		printf("  NIC NIE PRZYSZLO: albo nikt nie dotykal, albo uklad milczy\n");
		return;
	}
	printf("  ABS_MT_TRACKING_ID         %s\n",
	       o.slad_widziany ? "JEST" : "BRAK");
	printf("  zwolnienie sladu (-1)      %s\n",
	       o.slad_zwolniony ? "JEST" : "BRAK, koniec dotyku nierozpoznawalny wprost");
	printf("  BTN_TOUCH wcisniecie       %s\n",
	       o.btn_wcisniety ? "JEST" : "BRAK");
	printf("  BTN_TOUCH zwolnienie       %s\n",
	       o.btn_zwolniony ? "JEST" : "BRAK");
	printf("  najwyzszy uzyty slot       %d\n", o.slot_max);
	printf("  X od %d do %d\n", o.x_min, o.x_max);
	printf("  Y od %d do %d\n", o.y_min, o.y_max);
	if (o.odstep_min > 0)
		printf("  odstep paczek us: min %lld, sredni %lld, max %lld\n",
		       o.odstep_min, o.odstep_suma / (o.paczek > 1 ? o.paczek - 1 : 1),
		       o.odstep_max);
}

int main(int argc, char **argv)
{
	int fd, sekund = 0;

	if (argc < 2) {
		fprintf(stderr, "uzycie: %s /dev/input/eventN [sekund nasluchu]\n",
			argv[0]);
		return 2;
	}
	if (argc > 2)
		sekund = atoi(argv[2]);

	fd = open(argv[1], O_RDONLY);
	if (fd < 0) {
		perror(argv[1]);
		return 1;
	}
	opisz(fd);
	sloty(fd);
	if (sekund > 0)
		nasluch(fd, sekund);
	close(fd);
	return 0;
}
