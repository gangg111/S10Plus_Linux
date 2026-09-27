// SPDX-License-Identifier: GPL-2.0
// Wirtualna klawiatura przez /dev/uinput.

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/uinput.h>

#include "wstrzykiwanie.h"

static int wyslij(int fd, unsigned short typ, unsigned short kod, int wartosc)
{
	struct input_event ev;

	memset(&ev, 0, sizeof(ev));
	ev.type = typ;
	ev.code = kod;
	ev.value = wartosc;
	if (write(fd, &ev, sizeof(ev)) != (ssize_t)sizeof(ev)) {
		perror("zapis zdarzenia klawisza");
		return -1;
	}
	return 0;
}

int wstrzyk_otworz(struct wstrzyk *u, const char *nazwa)
{
	struct uinput_setup opis;
	int kod;

	u->fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
	if (u->fd < 0) {
		perror("/dev/uinput");
		return -1;
	}
	if (ioctl(u->fd, UI_SET_EVBIT, EV_KEY) < 0 ||
	    ioctl(u->fd, UI_SET_EVBIT, EV_SYN) < 0) {
		perror("zgloszenie rodzajow zdarzen");
		close(u->fd);
		u->fd = -1;
		return -1;
	}

	/* Caly zakres zwyklych klawiszy; przyciski myszy i pady zaczynaja sie
	 * od BTN_MISC i konsoli nie obchodza. */
	for (kod = KEY_ESC; kod < BTN_MISC; kod++) {
		if (ioctl(u->fd, UI_SET_KEYBIT, kod) < 0) {
			perror("zgloszenie kodu klawisza");
			close(u->fd);
			u->fd = -1;
			return -1;
		}
	}

	memset(&opis, 0, sizeof(opis));
	opis.id.bustype = BUS_VIRTUAL;
	opis.id.vendor = 0x0001;
	opis.id.product = 0x0001;
	opis.id.version = 1;
	snprintf(opis.name, sizeof(opis.name), "%s", nazwa);

	if (ioctl(u->fd, UI_DEV_SETUP, &opis) < 0 ||
	    ioctl(u->fd, UI_DEV_CREATE) < 0) {
		perror("utworzenie wirtualnej klawiatury");
		close(u->fd);
		u->fd = -1;
		return -1;
	}
	return 0;
}

void wstrzyk_zamknij(struct wstrzyk *u)
{
	int kod;

	if (u->fd < 0)
		return;
	/* Zwolnienie wszystkiego, zeby nie zostawic wcisnietego modyfikatora
	 * w konsoli po naszym wyjsciu. */
	for (kod = KEY_ESC; kod < BTN_MISC; kod++)
		wyslij(u->fd, EV_KEY, kod, 0);
	wyslij(u->fd, EV_SYN, SYN_REPORT, 0);

	ioctl(u->fd, UI_DEV_DESTROY);
	close(u->fd);
	u->fd = -1;
}

int wstrzyk_tap(struct wstrzyk *u, int kod)
{
	/* Tryby diagnostyczne dzialaja bez urzadzenia; wtedy nie wpisujemy. */
	if (u->fd < 0)
		return 0;
	if (wyslij(u->fd, EV_KEY, (unsigned short)kod, 1) < 0 ||
	    wyslij(u->fd, EV_SYN, SYN_REPORT, 0) < 0 ||
	    wyslij(u->fd, EV_KEY, (unsigned short)kod, 0) < 0 ||
	    wyslij(u->fd, EV_SYN, SYN_REPORT, 0) < 0)
		return -1;
	return 0;
}

int wstrzyk_mod(struct wstrzyk *u, int kod, int wcisniety)
{
	if (u->fd < 0)
		return 0;
	if (wyslij(u->fd, EV_KEY, (unsigned short)kod, wcisniety ? 1 : 0) < 0 ||
	    wyslij(u->fd, EV_SYN, SYN_REPORT, 0) < 0)
		return -1;
	return 0;
}
