// SPDX-License-Identifier: GPL-2.0
/*
 * Sonda tylko do odczytu, etap 4: rejestry PLL_AUD w CMU_AUD przy
 * wlaczonej domenie AUD (sprawdzone w etapie 1: STATUS=1).  Najpierw jeszcze
 * raz status domeny; przy wylaczonej nie czyta CMU, bo to wiesza magistrale.
 * Offsety z sources/ds/cmucal-sfr.c.  Niczego nie zapisuje.
 */
#include <linux/io.h>
#include <linux/module.h>

static const struct {
	const char *nazwa;
	u32 off;
} rej[] = {
	{ "PLL_CON0_AUD0", 0x120 }, { "PLL_CON1_AUD0", 0x124 },
	{ "PLL_CON2_AUD0", 0x128 }, { "PLL_CON3_AUD0", 0x12c },
	{ "PLL_CON4_AUD0", 0x130 }, { "PLL_CON5_AUD0", 0x134 },
	{ "PLL_CON0_AUD1", 0x140 }, { "PLL_CON1_AUD1", 0x144 },
	{ "PLL_CON3_AUD1", 0x14c },
};

static int __init aud_sonda_init(void)
{
	void __iomem *pd = ioremap(0x15861900, 0x10);
	void __iomem *cmu;
	u32 st;
	int i;

	if (!pd)
		return -ENOMEM;
	st = readl(pd + 4);
	iounmap(pd);
	pr_info("aud_sonda: AUD STATUS=%08x\n", st);
	if (!(st & 1))
		return -EAGAIN;
	cmu = ioremap(0x18c00000, 0x8000);
	if (!cmu)
		return -ENOMEM;
	for (i = 0; i < ARRAY_SIZE(rej); i++)
		pr_info("aud_sonda: %-18s +%04x = %08x\n", rej[i].nazwa,
			rej[i].off, readl(cmu + rej[i].off));
	iounmap(cmu);
	return -EAGAIN;
}
module_init(aud_sonda_init);
MODULE_LICENSE("GPL");
