// SPDX-License-Identifier: GPL-2.0
/*
 * Jednorazowa sonda: czyta wybrane rejestry jednostki zasilania i wypisuje je
 * do dziennika jadra.  Nie zostaje w pamieci, bo init celowo zwraca blad.
 *
 * Po co osobny modul.  Na tym telefonie /dev/mem odmawia odczytu rejestrow
 * peryferiow ("Bad address"), a zrzut calego okna przez debugfs wywala proces
 * czytajacy, bo w oknie sa adresy, ktorych odczyt nie przechodzi.  Regmapa,
 * ktorej jadro juz uzywa do zapisu trybu rozruchu, dziala, wiec sonda idzie
 * ta sama droga i tylko po adresy, ktore maja uzasadnienie.
 *
 * Adresy: INFORM0..7 i SWRESET sa w drzewie tego telefonu, RST_STAT z mapy
 * gs101 w mainline, ktora dla tego bloku zgadza sie z naszym ukladem: ten sam
 * plik daje GS101_INFORM3 = 0x080c, czyli dokladnie rejestr trybu rozruchu
 * z naszego drzewa.
 */
#include <linux/kernel.h>
#include <linux/mfd/syscon.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/regmap.h>

struct sonda {
	const char *nazwa;
	u32 offset;
};

/* Kolejnosc nie jest przypadkowa: najpewniejsze adresy pierwsze. */
static const struct sonda rejestry[] = {
	{ "INFORM0",      0x0800 },
	{ "INFORM1",      0x0804 },
	{ "INFORM2",      0x0808 },
	{ "INFORM3",      0x080c },
	{ "INFORM4",      0x0810 },
	{ "INFORM5",      0x0814 },
	{ "INFORM6",      0x0818 },
	{ "INFORM7",      0x081c },
	{ "SWRESET",      0x3a00 },
	{ "RST_STAT",     0x3b44 },
	{ "RST_STAT_PMU", 0x3b48 },
};

static int __init sonda_init(void)
{
	struct device_node *np;
	struct regmap *map;
	unsigned int i;

	np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-pmu");
	if (!np) {
		pr_err("pmuczyt: nie ma wezla jednostki zasilania\n");
		return -ENODEV;
	}

	map = syscon_node_to_regmap(np);
	of_node_put(np);
	if (IS_ERR(map)) {
		pr_err("pmuczyt: nie ma regmapy (%ld)\n", PTR_ERR(map));
		return PTR_ERR(map);
	}

	for (i = 0; i < ARRAY_SIZE(rejestry); i++) {
		unsigned int wartosc;
		int ret;

		ret = regmap_read(map, rejestry[i].offset, &wartosc);
		if (ret)
			pr_info("pmuczyt: %-13s 0x%04x -> blad %d\n",
				rejestry[i].nazwa, rejestry[i].offset, ret);
		else
			pr_info("pmuczyt: %-13s 0x%04x = 0x%08x\n",
				rejestry[i].nazwa, rejestry[i].offset, wartosc);
	}

	/* Odczyt zrobiony; modul nie ma po co zostawac. */
	return -EAGAIN;
}
module_init(sonda_init);

MODULE_DESCRIPTION("Jednorazowy odczyt rejestrow jednostki zasilania Exynos 9820");
MODULE_LICENSE("GPL");
