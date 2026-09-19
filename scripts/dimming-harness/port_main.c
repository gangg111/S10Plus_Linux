/* Harness: liczy tablice gamma NASZYM portem, tym samym MTP co harness producenta. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef uint8_t u8; typedef int8_t s8; typedef int16_t s16; typedef uint16_t u16;
typedef int32_t s32; typedef uint32_t u32; typedef int64_t s64; typedef uint64_t u64;
#define do_div(n, base) ({ u64 __r = (n) % (base); (n) = (n) / (base); __r; })
#define clamp(v, lo, hi) ((v) < (lo) ? (lo) : ((v) > (hi) ? (hi) : (v)))
#define clamp_t(t, v, lo, hi) ((t)clamp((t)(v), (t)(lo), (t)(hi)))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define BIT(n) (1UL << (n))
#include "panel-samsung-s6e3ha9-dimming.h"
#include "panel-samsung-s6e3ha9-dimming.c"

/*
 * Surowy ladunek odczytu 0xC8, taki, jaki przychodzi z panelu.  Losujemy
 * BAJTY, nie gotowe offsety, z dwoch powodow.
 *
 * Pierwszy: tylko tak w ogole uruchamia sie dekoder.  Wczesniejsza wersja
 * wpisywala liczby wprost do dim.mtp i s6e3ha9_dimming_unpack_mtp nie byla
 * wolana ani razu, wiec bramka mowila "74/74 poziomy zgodne" o silniku,
 * a o pakowaniu bajtow nie mowila nic.
 *
 * Drugi: zakres.  Poprzednie losowanie dawalo wszystkim punktom wartosci
 * od -7 do 7, podczas gdy realny zakres to plus minus 511 dla V255, plus
 * minus 127 dla punktow srodkowych i 0 do 15 BEZ ZNAKU dla VT oraz V0
 * (sources/ds/s6e3ha9.c:58-63).  Zaden przebieg nie dotykal wiec scian
 * nasycenia, a punktom VT i V0 podawal wartosci ujemne, ktore w sprzecie
 * nie moga wystapic.  Losowe bajty pokrywaja caly realny zakres z definicji,
 * bo dokladnie z takich bajtow panel sklada odpowiedz.
 */
static void losuj_mtp(u8 *raw, int len)
{
	int i;

	for (i = 0; i < len; i++)
		raw[i] = rand() & 0xff;
}

int main(int argc, char **argv)
{
	static struct s6e3ha9_dimming dim;
	unsigned seed = (argc > 1) ? (unsigned)atoi(argv[1]) : 1;
	u8 raw[S6E3HA9_MTP_LEN];
	int i, l;

	srand(seed);
	losuj_mtp(raw, sizeof(raw));
	s6e3ha9_dimming_unpack_mtp(&dim, raw);

	s6e3ha9_dimming_process(&dim);

	for (l = 0; l < S6E3HA9_NR_LUMINANCE; l++) {
		printf("lum %3d:", l);
		for (i = 0; i < S6E3HA9_GAMMA_LEN; i++)
			printf(" %02x", dim.gamma[l][i]);
		printf("\n");
	}
	return 0;
}
