// SPDX-License-Identifier: GPL-2.0-only
/*
 * M0 uruchamiania DECON: zrzut stanu potoku wyswietlania zostawionego przez
 * S-Boot, wylacznie odczyty.  Najpierw otwiera bramki APB kazdego czytanego
 * bloku przez API zegarow (zapis tylko do CMU_DPU; przy clk_ignore_unused
 * bramki i tak sa zwykle otwarte), potem czyta rejestry przez ioremap.
 * Nie dotyka portow kolejek DSIM (0x58, 0x5c, 0x60).  Nie wylacza zegarow
 * przy wyjsciu.  Init zwraca -EAGAIN, modul nie zostaje w pamieci.
 */
#include <linux/clk.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_clk.h>

/* Identyfikatory CMU_DPU z dt-bindings/clock/samsung,exynos9820.h. */
static const int zegary_dpu[] = {
	5, 6,		/* AD_APB_DECON0 PCLKM, PCLKS */
	11, 12,		/* AD_APB_DPP PCLKM, PCLKS */
	13, 14,		/* AD_APB_DPU_DMA PCLKM, PCLKS */
	21,		/* AD_APB_MIPI_DSIM0 PCLKS (DSIM i D-PHY) */
	23, 24,		/* AD_APB_SYSMMU_DPUD0 PCLKM, PCLKS */
	27, 28,		/* AD_APB_SYSMMU_DPUD1 PCLKM, PCLKS */
	31, 32,		/* AD_APB_SYSMMU_DPUD2 PCLKM, PCLKS */
	63,		/* SYSREG_DPU PCLK */
	64,		/* DCPHY_COMBO_TOP PCLK (bias D-PHY) */
};

struct zakres {
	const char *nazwa;
	phys_addr_t baza;
	u32 od, do_;	/* [od, do_) wzgledem bazy */
};

static const struct zakres zakresy[] = {
	/* PMU pominiete: 0x700 i 0x1e10 daja synchroniczny abort. */
	{ "DSIM0-A",		0x19080000, 0x0000, 0x0058 },
	{ "DSIM0-B",		0x19080000, 0x0064, 0x0100 },
	{ "DECON",		0x19030000, 0x0000, 0x0300 },
	{ "DECON-WIN",		0x19030000, 0x1000, 0x1100 },
	{ "DECON-DSC0",		0x19030000, 0x4000, 0x4100 },
	{ "DECON-DSC1",		0x19030000, 0x5000, 0x5100 },
	{ "DECON-CIEN",		0x19030000, 0x7000, 0x7300 },
	{ "DPU-DMA",		0x19070000, 0x0000, 0x0040 },
	{ "IDMA-GF0",		0x19070000, 0x1000, 0x1100 },
	{ "DPP",		0x19020000, 0x0000, 0x0040 },
	{ "DPP0",		0x19020000, 0x1000, 0x1100 },
	{ "SYSREG-DPU",		0x19011000, 0x0000, 0x0010 },
	{ "DPHY-PLL",		0x19161000, 0x0100, 0x0150 },
	{ "DPHY-BIAS",		0x19160000, 0x0000, 0x0020 },
	{ "SYSMMU0",		0x190a0000, 0x0000, 0x0040 },
	{ "SYSMMU0-CAPA",	0x190a0000, 0x0870, 0x0880 },
	{ "SYSMMU1",		0x190b0000, 0x0000, 0x0040 },
	{ "SYSMMU1-CAPA",	0x190b0000, 0x0870, 0x0880 },
	{ "SYSMMU2",		0x190c0000, 0x0000, 0x0040 },
	{ "SYSMMU2-CAPA",	0x190c0000, 0x0870, 0x0880 },
};

static void zrzut(const struct zakres *z)
{
	void __iomem *m = ioremap(z->baza, z->do_);
	u32 off, w[4];
	int i;

	if (!m) {
		pr_err("m0-dpu3: %s: ioremap sie nie udal\n", z->nazwa);
		return;
	}
	for (off = z->od; off < z->do_; off += 16) {
		for (i = 0; i < 4; i++)
			w[i] = off + 4 * i < z->do_ ? readl(m + off + 4 * i) : 0;
		pr_info("m0-dpu3: %-13s %08llx: %08x %08x %08x %08x\n", z->nazwa,
			(unsigned long long)(z->baza + off), w[0], w[1], w[2], w[3]);
	}
	iounmap(m);
}

static int __init m0_dpu3_init(void)
{
	struct of_phandle_args a = { .args_count = 1 };
	int i, bledy = 0;

	a.np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-cmu-dpu");
	if (!a.np)
		return -ENODEV;
	for (i = 0; i < ARRAY_SIZE(zegary_dpu); i++) {
		struct clk *c;

		a.args[0] = zegary_dpu[i];
		c = of_clk_get_from_provider(&a);
		if (IS_ERR(c) || clk_prepare_enable(c)) {
			pr_err("m0-dpu3: zegar CMU_DPU %d niedostepny\n", zegary_dpu[i]);
			bledy++;
		}
	}
	/* Rdzenie SYSMMU maja osobne bramki (sysmmu clock z DT). */
	for (i = 0; i < 3; i++) {
		static const char * const sciezki[] = {
			"/soc@0/iommu@190a0000", "/soc@0/iommu@190b0000", "/soc@0/iommu@190c0000" };
		struct device_node *n = of_find_node_by_path(sciezki[i]);
		struct clk *c = n ? of_clk_get_by_name(n, "sysmmu") : ERR_PTR(-ENODEV);

		if (IS_ERR(c) || clk_prepare_enable(c)) {
			pr_err("m0-dpu3: zegar sysmmu %s niedostepny\n", sciezki[i]);
			bledy++;
		}
		of_node_put(n);
	}
	of_node_put(a.np);
	if (bledy) {
		pr_err("m0-dpu3: %d zegarow niedostepnych, nic nie czytam\n", bledy);
		return -EIO;
	}

	for (i = 0; i < ARRAY_SIZE(zakresy); i++)
		zrzut(&zakresy[i]);
	pr_info("m0-dpu3: koniec zrzutu\n");
	return -EAGAIN;
}
module_init(m0_dpu3_init);

MODULE_DESCRIPTION("M0 DECON: zrzut rejestrow potoku po S-Boocie, tylko odczyt");
MODULE_LICENSE("GPL");
