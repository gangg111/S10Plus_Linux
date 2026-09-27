// SPDX-License-Identifier: GPL-2.0
/*
 * Proba jednorazowa, TYLKO ODCZYT: tablice czestotliwosci i napiec (fvmap),
 * ktore firmware DVFS na APM trzyma w swojej pamieci.  Zadnej wiadomosci do
 * firmware, zadnego zapisu.
 *
 * Droga jak u producenta (acpm.c, fvmap.c):
 *   initdata (SRAM + 0x7000): u32 plugins (przesuniecie w SRAM), u32 num_plugins
 *   struct plugin, 48 B: id +0, base_addr +4, is_attached +32 (u8),
 *                        size +36, stay_attached +40 (u8), fw_name +44
 *   wtyczka z "DVFS" w nazwie, dolaczona na stale:
 *   fvmap = SRAM + (base_addr & ~1) + fvmap_offset (0xa400 z drzewa producenta)
 *   struct fvmap_header, 24 B na domene: dvfs_type +0, num_of_lv +1,
 *   init_lv +8, o_ratevolt +20 (u16, wzgledem fvmap); pary {rate, volt} po u32.
 *
 * Odczyt poza zywym obszarem SRAM APM konczy sie bledem zewnetrznym, wiec
 * kazdy adres jest najpierw sprawdzany wzgledem okna 0x30000.
 */
#include <linux/io.h>
#include <linux/module.h>
#include <linux/string.h>

#define SRAM_BAZA	0x02039000
#define SRAM_ROZMIAR	0x30000
#define INITDATA	0x7000
#define FVMAP_OFFSET	0xa400
#define PLUGIN_ROZMIAR	48
#define DOMEN		15

static const char * const domeny[DOMEN] = {
	"mif", "int", "cpucl0", "cpucl1", "cpucl2", "npu", "disp", "score",
	"aud", "cp", "g3d", "intcam", "cam", "iva", "mfc",
};

static void __iomem *s;

static bool w_oknie(u32 off, u32 len)
{
	return off < SRAM_ROZMIAR && len <= SRAM_ROZMIAR - off;
}

static void czytaj_napis(u32 off, char *buf, int max)
{
	int i;

	buf[0] = 0;
	/*
	 * Zero znaczy brak nazwy (producent sprawdza fw_name != 0), a poczatek
	 * SRAM APM daje blad zewnetrzny: zmierzone, pierwsza wtyczka ma zero.
	 */
	if (!off || !w_oknie(off, max))
		return;
	for (i = 0; i < max - 1; i++) {
		buf[i] = readb(s + off + i);
		if (!buf[i])
			break;
	}
	buf[max - 1] = 0;
}

static int __init fvmap_proba_init(void)
{
	u32 plugins, n, i, fv = 0;
	char nazwa[40];

	s = ioremap(SRAM_BAZA, SRAM_ROZMIAR);
	if (!s)
		return -ENOMEM;

	/*
	 * Spis kanalow IPC (acpm_framework: ipc_channels +8, num +12), opis kanalu
	 * 72 B: id +0, field +4, owner +8 (id wtyczki), type +12, channel_info
	 * +16 (13 slow: q_len +52, q_elem_size +56), ap_poll +68.
	 */
	{
		u32 ch = readl(s + INITDATA + 8), nch = readl(s + INITDATA + 12), k;

		pr_info("fvmap-proba: ipc_channels %#x, num %u\n", ch, nch);
		if (nch <= 32 && w_oknie(ch, nch * 72))
			for (k = 0; k < nch; k++) {
				u32 c = ch + k * 72;

				pr_info("fvmap-proba: kanal id %u field %u owner %d type %u q_len %u q_elem %u ap_poll %u\n",
					readl(s + c), readl(s + c + 4), (s32)readl(s + c + 8),
					readl(s + c + 12), readl(s + c + 52), readl(s + c + 56),
					readl(s + c + 68));
			}
	}

	plugins = readl(s + INITDATA);
	n = readl(s + INITDATA + 4);
	pr_info("fvmap-proba: plugins %#x, num_plugins %u\n", plugins, n);
	if (n > 32 || !w_oknie(plugins, n * PLUGIN_ROZMIAR))
		goto koniec;

	for (i = 0; i < n; i++) {
		u32 p = plugins + i * PLUGIN_ROZMIAR;
		u32 id = readl(s + p), baza = readl(s + p + 4);
		u32 rozmiar = readl(s + p + 36), nazwa_off = readl(s + p + 44);
		u8 dol = readb(s + p + 32), stale = readb(s + p + 40);

		czytaj_napis(nazwa_off, nazwa, sizeof(nazwa));
		pr_info("fvmap-proba: wtyczka %u id %u baza %#x rozmiar %#x attached %u stay %u nazwa '%s'\n",
			i, id, baza, rozmiar, dol, stale, nazwa);
		if (dol == 1 && stale == 1 &&
		    (strstr(nazwa, "DVFS") || strstr(nazwa, "dvfs")))
			fv = (baza & ~1U) + FVMAP_OFFSET;
	}

	if (!fv || !w_oknie(fv, DOMEN * 24)) {
		pr_info("fvmap-proba: brak fvmap (fv %#x)\n", fv);
		goto koniec;
	}
	pr_info("fvmap-proba: fvmap pod SRAM + %#x\n", fv);

	for (i = 0; i < DOMEN; i++) {
		u32 h = fv + i * 24;
		u8 typ = readb(s + h), lv = readb(s + h + 1), init = readb(s + h + 8);
		u16 orv = readw(s + h + 20);
		u32 t = fv + orv, j;

		pr_info("fvmap-proba: %-6s typ %#x poziomow %u init_lv %u o_ratevolt %#x\n",
			domeny[i], typ, lv, init, orv);
		if (lv > 40 || !w_oknie(t, lv * 8))
			continue;
		for (j = 0; j < lv; j++)
			pr_info("fvmap-proba: %-6s lv%-2u %7u kHz %7u uV%s\n",
				domeny[i], j, readl(s + t + j * 8),
				readl(s + t + j * 8 + 4), j == init ? "  <- init" : "");
	}
koniec:
	iounmap(s);
	return 0;
}

static void __exit fvmap_proba_exit(void)
{
}

module_init(fvmap_proba_init);
module_exit(fvmap_proba_exit);
MODULE_DESCRIPTION("Odczyt tablic fvmap firmware DVFS na Exynos 9820");
MODULE_LICENSE("GPL");
