# SPDX-License-Identifier: GPL-2.0
# Klawiatura ekranowa dla telefonu; budowana krzyzowo, bo na telefonie nie ma
# kompilatora.  Statycznie, zeby nie zalezec od wersji bibliotek w obrazie.
#
#   make                      buduje przez aarch64-linux-gnu-gcc
#   make CC=gcc NATYWNIE=1    buduje na PC do testow rysowania
#
CROSS ?= aarch64-linux-gnu-
# CC jest w make zmienna wbudowana, wiec ?= jej NIE ustawi i build
# po cichu poszedlby natywnym kompilatorem; sprawdzamy pochodzenie.
ifeq ($(origin CC),default)
CC = $(CROSS)gcc
endif
CFLAGS ?= -O2 -Wall -Wextra -static
CFLAGS += -Wno-unused-parameter

OBJ = klawiatura.o ekran.o konsola.o wejscie.o wstrzykiwanie.o

klawiatura: $(OBJ)
	$(CC) $(CFLAGS) -o $@ $(OBJ)

klawiatura.o: klawiatura.c ekran.h konsola.h wejscie.h wstrzykiwanie.h uklad.h
ekran.o: ekran.c ekran.h czcionka.h czcionka-sans.h
konsola.o: konsola.c konsola.h
wejscie.o: wejscie.c wejscie.h
wstrzykiwanie.o: wstrzykiwanie.c wstrzykiwanie.h

# Dwie sondy diagnostyczne, kazda jednoplikowa i niezalezna od klawiatury.
# sonda-dotyku wymaga czlowieka (prosi o dotkniecie rogow), sonda-osi nie.
sondy: sonda-dotyku sonda-osi palec

sonda-dotyku: sonda-dotyku.c
	$(CC) $(CFLAGS) -o $@ $<

sonda-osi: sonda-osi.c
	$(CC) $(CFLAGS) -o $@ $<

# Sztuczny palec: pozwala sprawdzic przytrzymanie klawisza bez czlowieka.
palec: palec.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f klawiatura sonda-dotyku sonda-osi palec $(OBJ)

.PHONY: clean sondy
