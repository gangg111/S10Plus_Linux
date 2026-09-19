/* Harness: liczy tablice gamma silnikiem PRODUCENTA (dimming.c) dla zadanego MTP. */
#include "dimming.h"
#include "panel_data.h"
#define S6E3HA9_NR_TP 12
#define RED 0
#define GREEN 1
#define BLUE 2

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void copy_tpout_center(u8 *output, u32 value, u32 v, u32 color)
{
	int index = (S6E3HA9_NR_TP - v - 1);

	if (v == S6E3HA9_NR_TP - 1) {
		output[0] &= ~(0x3 << ((MAX_COLOR - color - 1) * 2));
		output[0] |= (((value >> 8) & 0x03) << ((MAX_COLOR - color - 1) * 2));
		output[color + 1] = value & 0x00FF;
		if (value > 1023)
			/* pr_err removed */;
	} else if (v == 1) {
		if (color == RED) {
			output[index * MAX_COLOR + 1] &= ~(0xF << 4);
			output[index * MAX_COLOR + 1] |= (value & 0xF) << 4;
		} else if (color == GREEN) {
			output[index * MAX_COLOR + 1] &= ~0xF;
			output[index * MAX_COLOR + 1] |= (value & 0xF);
		} else if (color == BLUE) {
			output[index * MAX_COLOR + 2] &= ~(0xF << 4);
			output[index * MAX_COLOR + 2] |= (value & 0xF) << 4;
		}
		if (value > 15)
			/* pr_err removed */;
	} else if (v == 0) {
		if (color == RED) {
			output[(index - 1) * MAX_COLOR + 2] &= ~0xF;
			output[(index - 1) * MAX_COLOR + 2] |= (value & 0xF);
		} else if (color == GREEN) {
			output[(index - 1) * MAX_COLOR + 3] &= ~(0xF << 4);
			output[(index - 1) * MAX_COLOR + 3] |= (value & 0xF) << 4;
		} else if (color == BLUE) {
			output[(index - 1) * MAX_COLOR + 3] &= ~0xF;
			output[(index - 1) * MAX_COLOR + 3] |= (value & 0xF);
		}
		if (value > 15)
			/* pr_err removed */;
	} else {
		output[index * MAX_COLOR + color + 1] = value & 0x00FF;
		if (value > 255)
			/* pr_err removed */;
	}
}

/*
 * Dekoder MTP producenta, przepisany co do znaku z sources/ds/s6e3ha9.c:31-74
 * (gamma_ctoi i mtp_ctoi).  Obie funkcje sa tam statyczne i siedza w pliku,
 * ktorego ten harness nie kompiluje, wiec musza byc tutaj.  Nie wolno ich
 * "poprawiac": ich zadaniem jest byc druga strona porownania.
 */
static void vendor_gamma_ctoi(s32 (*dst)[MAX_COLOR], u8 *src, int nr_tp)
{
	unsigned int i, c, pos = 1;

	for (i = nr_tp - 1; i > 1; i--) {
		for (c = 0; c < MAX_COLOR; c++) {
			if (i == nr_tp - 1)
				dst[i][c] = ((src[0] >> ((MAX_COLOR - c - 1) * 2)) & 0x03) << 8 | src[pos++];
			else
				dst[i][c] = src[pos++];
		}
	}

	dst[1][RED] = (src[pos + 0] >> 4) & 0xF;
	dst[1][GREEN] = src[pos + 0] & 0xF;
	dst[1][BLUE] = (src[pos + 1] >> 4) & 0xF;

	dst[0][RED] = src[pos + 1] & 0xF;
	dst[0][GREEN] = (src[pos + 2] >> 4) & 0xF;
	dst[0][BLUE] = src[pos + 2] & 0xF;
}

static void vendor_mtp_ctoi(s32 (*dst)[MAX_COLOR], u8 *src, int nr_tp)
{
	int v, c, sign, value;
	int signed_bit[S6E3HA9_NR_TP] = {
		-1, -1, 7, 7, 7, 7, 7, 7, 7, 7, 7, 9
	};
	int value_mask[S6E3HA9_NR_TP] = {
		0xF, 0xF, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x1FF
	};

	vendor_gamma_ctoi(dst, src, nr_tp);
	for (v = 0; v < nr_tp; v++) {
		for (c = 0; c < MAX_COLOR; c++) {
			sign = (signed_bit[v] < 0) ? 1 :
				(dst[v][c] & (0x1 << signed_bit[v])) ? -1 : 1;
			value = dst[v][c] & value_mask[v];
			dst[v][c] = sign * value;
		}
	}
}

int main(int argc, char **argv)
{
	struct dimming_init_info init = {
		.name = "s6e3ha9_beyond2_a3_s0",
		.nr_tp = S6E3HA9_NR_TP,
		.tp = s6e3ha9_beyond_tp,
		.nr_luminance = S6E3HA9_NR_LUMINANCE,
		.vregout = 114085069LL,
		.vref = 16777216LL,
		.bitshift = 24,
		.vt_voltage = { 0, 24, 48, 72, 96, 120, 144, 168, 192, 216,
				276, 296, 316, 336, 356, 372 },
		.v0_voltage = { 0, 12, 24, 36, 48, 60, 72, 84, 96, 108,
				120, 132, 144, 156, 168, 180 },
		.target_luminance = S6E3HA9_BEYOND_TARGET_LUMINANCE,
		.target_gamma = 220,
		.dim_lut = beyond2_a3_s0_dimming_lut,
	};
	static struct dimming_info dim_info;
	s32 mtp[S6E3HA9_NR_TP][MAX_COLOR];
	unsigned seed = (argc > 1) ? (unsigned)atoi(argv[1]) : 1;
	u8 raw[34];
	u8 out[64];
	int i, l;

	if (init_dimming_info(&dim_info, &init) < 0)
		return 1;

	/*
	 * Losowy SUROWY ladunek odczytu 0xC8, ten sam ciag co po stronie portu
	 * (ta sama biblioteka rand i to samo ziarno), rozpakowany dekoderem
	 * producenta.  Porownanie obejmuje wiec i dekoder, i silnik.
	 */
	srand(seed);
	for (i = 0; i < 34; i++)
		raw[i] = rand() & 0xff;
	vendor_mtp_ctoi(mtp, raw, S6E3HA9_NR_TP);

	if (init_dimming_mtp(&dim_info, mtp) < 0)
		return 1;
	if (process_dimming(&dim_info) < 0)
		return 1;

	for (l = 0; l < S6E3HA9_NR_LUMINANCE; l++) {
		memset(out, 0, sizeof(out));
		get_dimming_gamma(&dim_info, dim_info.dim_lut[l].luminance, out, copy_tpout_center);
		printf("lum %3d:", l);
		for (i = 0; i < 34; i++)
			printf(" %02x", out[i]);
		printf("\n");
	}

	return 0;
}
