// SPDX-License-Identifier: GPL-2.0
/*
 * Proba jednorazowa: czy firmware APM na Exynos 9820 odpowiada na polecenia
 * ACPM TMU z mainline (INIT 0x01, READ_TEMP 0x02) na kanale 9, tym samym,
 * ktory producent opisuje w wezle acpm_tmu.  Strefy producenta: 0 BIG,
 * 1 MID, 2 LITTLE, 3 G3D, 4 ISP.  Nic nie zapisuje do sprzetu poza
 * wiadomosciami do firmware; nie rejestruje zadnej strefy termicznej.
 */
#include <linux/delay.h>
#include <linux/io.h>
#include <linux/firmware/samsung/exynos-acpm-protocol.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

static unsigned int kanal = 9;
module_param(kanal, uint, 0444);

static struct platform_device *pdev;

static int __init tmu_proba_init(void)
{
	static const char * const nazwy[] = { "BIG", "MID", "LITTLE", "G3D", "ISP" };
	struct device_node *np;
	struct acpm_handle *h;
	int ret, tz, t, r;

	np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-acpm-ipc");
	if (!np)
		return -ENODEV;

	pdev = platform_device_register_simple("s10-tmu-proba", -1, NULL, 0);
	if (IS_ERR(pdev)) {
		of_node_put(np);
		return PTR_ERR(pdev);
	}

	h = devm_acpm_get_by_node(&pdev->dev, np);
	of_node_put(np);
	if (IS_ERR(h)) {
		ret = PTR_ERR(h);
		pr_err("tmu-proba: brak uchwytu ACPM: %d\n", ret);
		platform_device_unregister(pdev);
		return ret;
	}

	/*
	 * Tylko odczyt stanu MMIO obu blokow wedlug ukladu 9820 producenta
	 * (exynos_tmu.c, blok CONFIG_SOC_EXYNOS9820): TRIMINFO0 0x00,
	 * CONTROL 0x50 (bit 0 CORE_EN, bit 12 THERM_TRIP_EN, bity 15:13
	 * TRIP_MODE), CONTROL1 0x54, STATUS 0x80, CURRENT_TEMP1_0 0x84,
	 * THD_TEMP0 0xd0..0xdc (progi RISE poziomow 0..7 sondy 0).
	 * Bramki PCLK obu blokow sa wlaczone (clk_summary).
	 */
	{
		static const phys_addr_t baza[] = { 0x10090000, 0x100a0000 };
		static const char * const blok[] = { "TOP", "SUB" };
		int b;

		for (b = 0; b < 2; b++) {
			void __iomem *r = ioremap(baza[b], 0x100);
			u32 ctl;

			if (!r)
				continue;
			ctl = readl(r + 0x50);
			pr_info("tmu-proba: %s TRIMINFO0 %08x CONTROL %08x (CORE_EN %u THERM_TRIP_EN %u TRIP_MODE %u) CONTROL1 %08x STATUS %08x TEMP %08x\n",
				blok[b], readl(r), ctl, ctl & 1, (ctl >> 12) & 1,
				(ctl >> 13) & 7, readl(r + 0x54), readl(r + 0x80),
				readl(r + 0x84));
			pr_info("tmu-proba: %s THD_TEMP0 %08x %08x %08x %08x\n",
				blok[b], readl(r + 0xd0), readl(r + 0xd4),
				readl(r + 0xd8), readl(r + 0xdc));
			iounmap(r);
		}
	}

	ret = h->ops->tmu.init(h, kanal);
	pr_info("tmu-proba: kanal %u, INIT -> %d\n", kanal, ret);

	for (r = 0; r < 3; r++) {
		for (tz = 0; tz < ARRAY_SIZE(nazwy); tz++) {
			t = -1000;
			ret = h->ops->tmu.read_temp(h, kanal, tz, &t);
			pr_info("tmu-proba: odczyt %d strefa %d (%s) -> %d, %d C\n",
				r, tz, nazwy[tz], ret, t);
		}
		msleep(500);
	}

	return 0;
}

static void __exit tmu_proba_exit(void)
{
	platform_device_unregister(pdev);
}

module_init(tmu_proba_init);
module_exit(tmu_proba_exit);
MODULE_DESCRIPTION("Proba odczytu temperatury przez ACPM TMU na Exynos 9820");
MODULE_LICENSE("GPL");
