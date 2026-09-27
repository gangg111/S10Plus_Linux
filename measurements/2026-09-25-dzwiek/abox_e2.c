// SPDX-License-Identifier: GPL-2.0
/*
 * Eksperyment E2-0: RDMA0 -> SPUS -> SIFS drenowany wlasnym licznikiem, bez
 * UAIF i bez pinow wzmacniaczy.  sciezka=0: przez mikser do SIFS0 (trasa
 * Androida), sciezka=1: wprost do SIFS1 (trasa po resecie: SPUS OUT0 = SIFS1,
 * SIFS1 = SPUS OUT0).  Licznik SIFS jak sifsx_cnt_val() producenta
 * z zegara CNT odczytanego z dzielnikow CMU_AUD.  Stan wyjsciowy zapisany na
 * starcie i przywracany na koncu; init konczy sie bledem.
 */
#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/sizes.h>

static int sciezka;
module_param(sciezka, int, 0444);
static uint qch;
module_param(qch, uint, 0444);
static int buftype;
module_param(buftype, int, 0444);
static int czas = 200;
module_param(czas, int, 0444);
static int misc;
module_param(misc, int, 0444);

#define SYSREG_AUD	0x18c10000
#define MISC_CON	0x0504

#define PMU_AUD		0x15861900
#define CMU_AUD		0x18c00000
#define PLL_AUD0_HZ	1179648000ULL	/* zmierzone: M 45, K 0x5eff z 26 MHz */
#define DIV_AUDIF	0x1800
#define DIV_CNT		0x180c
#define GAT_BCLK_CNT	0x2018
#define ABOX_BASE	0x18c50000
#define SYSPOWER_CTRL	0x0010
#define SYSPOWER_STATUS	0x0014
#define QCH_DISABLE	0x0038
#define ROUTE_CTRL0	0x0040
#define SPUS_CTRL0	0x0200
#define SPUS_CTRL1	0x0204
#define SBANK_RDMA0	0x0220
#define SBANK_MIXP	0x0280
#define SIFS_CNT0	0x0290
#define SIFS_CNT1	0x0294
#define R0		0x1000
#define CTRL0		(R0 + 0x00)
#define BUF_STR		(R0 + 0x08)
#define BUF_END		(R0 + 0x0c)
#define BUF_OFFSET	(R0 + 0x10)
#define STR_POINT	(R0 + 0x14)
#define VOL_FACTOR	(R0 + 0x18)
#define VOL_CHANGE	(R0 + 0x1c)
#define STATUS		(R0 + 0x30)
#define ENABLE		BIT(0)
#define BUF_UPDATE	BIT(5)
#define FORMAT_S16_2CH	((1 << 3) | (2 - 1))
#define ROZMIAR		SZ_64K
#define OKRES		SZ_4K

static const u32 zapamietane[] = {
	QCH_DISABLE, SYSPOWER_CTRL, SPUS_CTRL0, SPUS_CTRL1, SBANK_RDMA0, SBANK_MIXP,
	SIFS_CNT0, SIFS_CNT1, CTRL0, BUF_STR, BUF_END, BUF_OFFSET, STR_POINT,
	VOL_FACTOR, VOL_CHANGE,
};

static u32 stan(u32 st)
{
	return ((st >> 12) & 0xffff) * 16 + (st & 0xfff);
}

static int __init abox_e2_init(void)
{
	u32 kopia[ARRAY_SIZE(zapamietane)], st, poprz = ~0u, cnt, sifs;
	void __iomem *pmu, *cmu = NULL, *a = NULL, *sys = NULL;
	u32 misc_przed;
	struct platform_device *pdev;
	unsigned long long clk_cnt;
	dma_addr_t dma;
	u16 *buf;
	int i, zmian = 0, t_pierwszy = -1;
	u32 poz_start = 0, poz_kon = 0;

	pmu = ioremap(PMU_AUD, 0x10);
	if (!pmu)
		return -ENOMEM;
	st = readl(pmu + 4);
	iounmap(pmu);
	if (!(st & 1)) {
		pr_err("abox_e2: domena AUD wylaczona (%08x)\n", st);
		return -EAGAIN;
	}
	cmu = ioremap(CMU_AUD, 0x4000);
	a = ioremap(ABOX_BASE, 0x10000);
	sys = ioremap(SYSREG_AUD, 0x1000);
	if (!cmu || !a || !sys)
		goto mapy;
	misc_przed = readl(sys + MISC_CON);
	pr_info("abox_e2: sysreg AUD: L2_CACHE_CON=%08x MISC_CON=%08x\n",
		readl(sys), misc_przed);
	if (misc)
		writel(1, sys + MISC_CON);

	clk_cnt = PLL_AUD0_HZ / ((readl(cmu + DIV_AUDIF) & 0x1ff) + 1) /
		  ((readl(cmu + DIV_CNT) & 0xff) + 1);
	cnt = DIV_ROUND_CLOSEST_ULL(clk_cnt * 2 * (32 / 16), 2 * 48000) - 5 + 4;
	sifs = sciezka ? SIFS_CNT1 : SIFS_CNT0;
	pr_info("abox_e2: sciezka=%d DIV_AUDIF=%08x DIV_CNT=%08x GAT_BCLK_CNT=%08x zegar CNT %llu Hz -> licznik %u (0x%x)\n",
		sciezka, readl(cmu + DIV_AUDIF), readl(cmu + DIV_CNT),
		readl(cmu + GAT_BCLK_CNT), clk_cnt, cnt, cnt);
	pr_info("abox_e2: przed: QCH=%08x ROUTE0=%08x SPUS0=%08x SPUS1=%08x SBANK_R0=%08x SBANK_MIXP=%08x CNT0=%08x CNT1=%08x\n",
		readl(a + QCH_DISABLE), readl(a + ROUTE_CTRL0), readl(a + SPUS_CTRL0),
		readl(a + SPUS_CTRL1), readl(a + SBANK_RDMA0), readl(a + SBANK_MIXP),
		readl(a + SIFS_CNT0), readl(a + SIFS_CNT1));
	for (i = 0; i < ARRAY_SIZE(zapamietane); i++)
		kopia[i] = readl(a + zapamietane[i]);

	pdev = platform_device_register_simple("abox_e2", -1, NULL, 0);
	if (IS_ERR(pdev))
		goto mapy;
	dma_coerce_mask_and_coherent(&pdev->dev, DMA_BIT_MASK(32));
	buf = dma_alloc_coherent(&pdev->dev, ROZMIAR, &dma, GFP_KERNEL);
	if (!buf)
		goto dev;
	for (i = 0; i < ROZMIAR / 2; i++)
		buf[i] = (u16)(i * 64);

	writel(qch, a + QCH_DISABLE);
	writel(1, a + SYSPOWER_CTRL);
	for (i = 0; i < 100 && !(readl(a + SYSPOWER_STATUS) & 1); i++)
		udelay(100);
	if (!(readl(a + SYSPOWER_STATUS) & 1)) {
		pr_err("abox_e2: brak DRAM (SYSPOWER)\n");
		goto przywroc;
	}

	writel(128 / 16 << 20, a + SBANK_RDMA0);
	if (sciezka == 0) {
		writel(0x00803000, a + SBANK_MIXP);
		/* SPUS IN0 = RDMA, OUT0 = SIFS0 (1 w bitach 1-3), ASRC0 wylaczony */
		writel((readl(a + SPUS_CTRL0) & ~0x1f) | 0x2, a + SPUS_CTRL0);
		/* format miksera = format RDMA0, bez ASRC */
		writel((readl(a + SPUS_CTRL1) & ~0x1f) | FORMAT_S16_2CH, a + SPUS_CTRL1);
	} else {
		/* stan po resecie: OUT0 = SIFS1 (0), SIFS1 <- SPUS OUT0 (0) */
		writel(readl(a + SPUS_CTRL0) & ~0x1f, a + SPUS_CTRL0);
		writel(readl(a + SPUS_CTRL1) & ~0xf000, a + SPUS_CTRL1);
	}
	writel(cnt & 0xffffff, a + sifs);

	writel(0x800000, a + VOL_FACTOR);
	writel(0, a + VOL_CHANGE);
	writel((u32)dma, a + BUF_STR);
	writel((u32)dma + ROZMIAR, a + BUF_END);
	writel((u32)dma, a + STR_POINT);
	writel(OKRES, a + BUF_OFFSET);
	writel(0x00400000 | FORMAT_S16_2CH << 8 | BUF_UPDATE | (buftype ? BIT(4) : 0), a + CTRL0);
	pr_info("abox_e2: zaprogramowane: SPUS0=%08x SPUS1=%08x CNT=%08x CTRL0=%08x\n",
		readl(a + SPUS_CTRL0), readl(a + SPUS_CTRL1), readl(a + sifs),
		readl(a + CTRL0));
	writel(readl(a + CTRL0) | ENABLE, a + CTRL0);

	for (i = 0; i < czas; i++) {
		st = readl(a + STATUS);
		if (st != poprz) {
			if (t_pierwszy < 0 && (st >> 31)) {
				t_pierwszy = i;
				poz_start = stan(st);
			}
			if (zmian++ < 12)
				pr_info("abox_e2: t=%d ms STATUS=%08x postep=%u pozycja=%u B\n",
					i, st, st >> 31, stan(st));
			poprz = st;
		}
		usleep_range(1000, 1050);
	}
	poz_kon = stan(readl(a + STATUS));
	pr_info("abox_e2: misc=%d qch=%x buftype=%d po %d ms: STATUS=%08x zmian=%d pierwszy postep t=%d ms pozycja %u -> %u\n",
		misc, qch, buftype, czas, readl(a + STATUS), zmian, t_pierwszy, poz_start, poz_kon);

	writel(readl(a + CTRL0) & ~ENABLE, a + CTRL0);
	for (i = 0; i < 100 && (readl(a + STATUS) >> 31); i++)
		usleep_range(1000, 1050);
	pr_info("abox_e2: RDMA wylaczone po %d ms, STATUS=%08x\n", i, readl(a + STATUS));

przywroc:
	for (i = ARRAY_SIZE(zapamietane) - 1; i >= 0; i--)
		writel(kopia[i], a + zapamietane[i]);
	pr_info("abox_e2: przywrocone: SPUS0=%08x SPUS1=%08x CNT0=%08x CNT1=%08x CTRL0=%08x SYSPOWER=%x\n",
		readl(a + SPUS_CTRL0), readl(a + SPUS_CTRL1), readl(a + SIFS_CNT0),
		readl(a + SIFS_CNT1), readl(a + CTRL0), readl(a + SYSPOWER_CTRL));
	dma_free_coherent(&pdev->dev, ROZMIAR, buf, dma);
	writel(misc_przed, sys + MISC_CON);
dev:
	platform_device_unregister(pdev);
mapy:
	if (sys)
		iounmap(sys);
	if (a)
		iounmap(a);
	if (cmu)
		iounmap(cmu);
	return -EAGAIN;
}
module_init(abox_e2_init);
MODULE_LICENSE("GPL");
