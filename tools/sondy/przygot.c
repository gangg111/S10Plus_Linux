// SPDX-License-Identifier: GPL-2.0
/*
 * Odtwarza DOKLADNIE to, co nasz sterownik jednostki zasilania robi na rdzeniu
 * zerowym tuz przed wywolaniem CPU_ON dla rdzenia 1, i nic wiecej.  Procedura
 * jest zarejestrowana na CPUHP_BP_PREPARE_DYN, wiec biegnie PRZED PSCI, i do
 * tej pory nikt nie sprawdzil, czy to nie ona kladzie telefon.
 *
 * Komunikaty ida na panel, bo jesli telefon padnie, dziennik zginie z nim.
 */
#include <linux/kernel.h>
#include <linux/mfd/syscon.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/regmap.h>

#define GRP2_INTR_BID_ENABLE	0x0200
#define GRP2_INTR_BID_UPEND	0x0208
#define GRP2_INTR_BID_CLEAR	0x020c
#define CPU_INFORM(cpu)		(0x0860 + ((cpu) & 7) * 4)

#define RDZEN			1

static int __init sonda_init(void)
{
	struct device_node *np;
	struct regmap *pmureg, *intrgen;
	unsigned int reg;
	u32 mask = BIT(RDZEN);

	np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-pmu");
	if (!np) {
		pr_emerg("przygot: brak wezla jednostki zasilania\n");
		return -ENODEV;
	}

	pmureg = syscon_node_to_regmap(np);
	intrgen = syscon_regmap_lookup_by_phandle(np,
						  "samsung,pmu-intr-gen-syscon");
	of_node_put(np);

	if (IS_ERR(pmureg) || IS_ERR(intrgen)) {
		pr_emerg("przygot: brak regmapy (%ld, %ld)\n",
			 IS_ERR(pmureg) ? PTR_ERR(pmureg) : 0,
			 IS_ERR(intrgen) ? PTR_ERR(intrgen) : 0);
		return -ENODEV;
	}

	pr_emerg("przygot: KROK 1, czyszcze podpowiedz CPU_INFORM(0)\n");
	regmap_write(pmureg, CPU_INFORM(0), 0);

	pr_emerg("przygot: KROK 2, gasze bit rdzenia w GRP2_INTR_BID_ENABLE\n");
	regmap_update_bits(intrgen, GRP2_INTR_BID_ENABLE, mask, 0);

	pr_emerg("przygot: KROK 3, czytam GRP2_INTR_BID_UPEND\n");
	regmap_read(intrgen, GRP2_INTR_BID_UPEND, &reg);
	pr_emerg("przygot: UPEND = 0x%08x\n", reg);

	pr_emerg("przygot: KROK 4, kasuje przez GRP2_INTR_BID_CLEAR\n");
	regmap_write(intrgen, GRP2_INTR_BID_CLEAR, reg & mask);

	pr_emerg("przygot: PRZESZLO WSZYSTKIE CZTERY KROKI\n");

	return -EAGAIN;
}
module_init(sonda_init);

MODULE_DESCRIPTION("Sama procedura przygotowawcza przed CPU_ON");
MODULE_LICENSE("GPL");
