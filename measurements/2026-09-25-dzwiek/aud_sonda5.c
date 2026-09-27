// SPDX-License-Identifier: GPL-2.0
/*
 * Sonda tylko do odczytu, etap 5: SysMMU bloku audio (0x18e00000) przy
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
	{ "MMU_CTRL", 0x000 }, { "MMU_CFG", 0x004 }, { "MMU_STATUS", 0x008 },
	{ "MMU_VERSION", 0x034 }, { "CAPA0", 0x870 }, { "CAPA1", 0x874 },
};

static int __init aud_sonda5_init(void)
{
	void __iomem *pd = ioremap(0x15861900, 0x10);
	void __iomem *cmu;
	u32 st;
	int i;

	if (!pd)
		return -ENOMEM;
	st = readl(pd + 4);
	iounmap(pd);
	pr_info("aud_sonda5: AUD STATUS=%08x\n", st);
	if (!(st & 1))
		return -EAGAIN;
	cmu = ioremap(0x18e00000, 0x1000);
	if (!cmu)
		return -ENOMEM;
	for (i = 0; i < ARRAY_SIZE(rej); i++)
		pr_info("aud_sonda5: %-18s +%04x = %08x\n", rej[i].nazwa,
			rej[i].off, readl(cmu + rej[i].off));
	iounmap(cmu);
	return -EAGAIN;
}
module_init(aud_sonda5_init);
MODULE_LICENSE("GPL");
