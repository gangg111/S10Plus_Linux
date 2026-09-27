// SPDX-License-Identifier: GPL-2.0-only
/*
 * M1a uruchamiania DECON: jednorazowa podmiana bufora na potoku zostawionym
 * przez S-Boot.  Przydziela z CMA bufor 1440x3040 ARGB8888 ponizej 4 GB,
 * rysuje wzor, wpisuje jego adres do IDMA GF0 (IN_BASE_ADDR_Y), zglasza
 * aktualizacje cienia i po `czas` sekundach przywraca 0xca000000 tym samym
 * sposobem.  Bufor zwalnia dopiero, gdy zadanie aktualizacji po przywroceniu
 * zostalo wykonane.  Init zwraca -EAGAIN.
 *
 * tryb 0: SHADOW_REG_UPDATE_REQ = WIN(okno), jak decon_reg_update_req_window
 * tryb 1: SHADOW_REG_UPDATE_REQ = GLOBAL | 0x3f
 * tryb 2: IDMA_ENABLE |= SFR_UPDATE_FORCE, potem WIN(okno)
 */
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_clk.h>
#include <linux/platform_device.h>

#define SZER	1440
#define WYS	3040
#define ROZMIAR	(SZER * WYS * 4)
#define FB_BOOT	0xca000000

#define DECON_BAZA		0x19030000
#define DECON_SHADOW_REQ	0x0060
#define REQ_GLOBAL		BIT(31)
#define IDMA_BAZA		0x19071000
#define IDMA_ENABLE		0x0000
#define IDMA_SFR_UPDATE_FORCE	BIT(4)
#define IDMA_IN_BASE_ADDR_Y	0x0040

static int tryb;
module_param(tryb, int, 0444);
static int czas = 8;
module_param(czas, int, 0444);
static int okno = 5;
module_param(okno, int, 0444);

static void __iomem *decon, *idma;

static int zglos(const char *kiedy)
{
	u32 req, v;
	ktime_t t0 = ktime_get();
	int ret;

	if (tryb == 2)
		writel(readl(idma + IDMA_ENABLE) | IDMA_SFR_UPDATE_FORCE,
		       idma + IDMA_ENABLE);
	req = tryb == 1 ? REQ_GLOBAL | 0x3f : BIT(okno);
	writel(readl(decon + DECON_SHADOW_REQ) | req, decon + DECON_SHADOW_REQ);
	ret = readl_poll_timeout(decon + DECON_SHADOW_REQ, v, !(v & req), 100, 200000);
	pr_info("m1a: %s: zadanie 0x%08x %s po %lld us, 0x060=0x%08x, IDMA base=0x%08x enable=0x%08x\n",
		kiedy, req, ret ? "NIE WYKONANE" : "wykonane",
		ktime_us_delta(ktime_get(), t0), v,
		readl(idma + IDMA_IN_BASE_ADDR_Y), readl(idma + IDMA_ENABLE));
	return ret;
}

static void wzor(u32 *p)
{
	static const u32 pasy[8] = { 0xffff0000, 0xff00ff00, 0xff0000ff, 0xffffff00,
				     0xffff00ff, 0xff00ffff, 0xffffffff, 0xff404040 };
	int x, y;

	for (y = 0; y < WYS; y++)
		for (x = 0; x < SZER; x++) {
			u32 c = pasy[x * 8 / SZER];

			if (x % 180 < 4 || y % 190 < 4 || x < 8 || y < 8 ||
			    x >= SZER - 8 || y >= WYS - 8)
				c = 0xff000000;
			if (y >= WYS / 2 - 100 && y < WYS / 2 + 100)
				c = (y / 20 + x / 20) & 1 ? 0xffffffff : 0xff000000;
			p[y * SZER + x] = c;
		}
}

static int __init m1a_init(void)
{
	static const int zegary[] = { 5, 6, 13, 14 };	/* APB DECON0, DPU_DMA */
	struct of_phandle_args a = { .args_count = 1 };
	struct platform_device *pdev;
	dma_addr_t dma;
	void *buf;
	int i, ret = -EAGAIN;

	a.np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-cmu-dpu");
	if (!a.np)
		return -ENODEV;
	for (i = 0; i < ARRAY_SIZE(zegary); i++) {
		struct clk *c;

		a.args[0] = zegary[i];
		c = of_clk_get_from_provider(&a);
		if (IS_ERR(c) || clk_prepare_enable(c)) {
			of_node_put(a.np);
			return -EIO;
		}
	}
	of_node_put(a.np);

	pdev = platform_device_register_simple("m1a-flip", -1, NULL, 0);
	if (IS_ERR(pdev))
		return PTR_ERR(pdev);
	dma_set_mask_and_coherent(&pdev->dev, DMA_BIT_MASK(32));
	buf = dma_alloc_coherent(&pdev->dev, ROZMIAR, &dma, GFP_KERNEL);
	if (!buf) {
		pr_err("m1a: brak %d B w CMA ponizej 4 GB\n", ROZMIAR);
		platform_device_unregister(pdev);
		return -ENOMEM;
	}
	pr_info("m1a: bufor 0x%llx, %d B\n", (unsigned long long)dma, ROZMIAR);
	wzor(buf);
	wmb();

	decon = ioremap(DECON_BAZA, 0x100);
	idma = ioremap(IDMA_BAZA, 0x100);
	if (!decon || !idma || readl(idma + IDMA_IN_BASE_ADDR_Y) != FB_BOOT) {
		pr_err("m1a: IDMA nie czyta 0x%x (0x%08x), nic nie zmieniam\n", FB_BOOT,
		       idma ? readl(idma + IDMA_IN_BASE_ADDR_Y) : 0);
		goto zwolnij;
	}

	writel(lower_32_bits(dma), idma + IDMA_IN_BASE_ADDR_Y);
	zglos("wzor");
	msleep(czas * 1000);
	writel(FB_BOOT, idma + IDMA_IN_BASE_ADDR_Y);
	if (zglos("powrot")) {
		/* Bufor moze byc dalej czytany: lepiej go zostawic niz zwolnic. */
		pr_err("m1a: powrot niepotwierdzony, bufor zostaje przydzielony\n");
		goto bez_zwalniania;
	}
	msleep(50);
zwolnij:
	dma_free_coherent(&pdev->dev, ROZMIAR, buf, dma);
	platform_device_unregister(pdev);
bez_zwalniania:
	if (decon)
		iounmap(decon);
	if (idma)
		iounmap(idma);
	return ret;
}
module_init(m1a_init);

MODULE_DESCRIPTION("M1a DECON: jednorazowa podmiana bufora IDMA po S-Boocie");
MODULE_LICENSE("GPL");
