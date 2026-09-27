// SPDX-License-Identifier: GPL-2.0
/*
 * Eksperyment E3: RDMA0 -> SPUS -> SIFS -> UAIF1 jako master I2S 48 kHz,
 * 16 bit, 2 kanaly, bez firmware DSP.  UAIF1 pobiera probki i to on ma
 * ciagnac DMA.  Piny UAIF1 zostaja nietkniete, wiec sygnal nie wychodzi do
 * wzmacniaczy.  sciezka=0: przez mikser do SIFS0, sciezka=1: do SIFS1.
 * Wszystkie ruszone rejestry (ABOX i dzielnik UAIF1 w CMU_AUD) wracaja do
 * wartosci odczytanych na starcie; init konczy sie bledem.
 */
#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/sizes.h>

static int sciezka = 1;
module_param(sciezka, int, 0444);
static int czas = 200;
module_param(czas, int, 0444);

#define PMU_AUD		0x15861900
#define CMU_AUD		0x18c00000
#define DIV_UAIF1	0x1830
#define MUX_UAIF1	0x1010
#define GAT_BCLK_UAIF1	0x2024
#define DIV_BUSY	BIT(16)
#define ABOX_BASE	0x18c50000
#define SYSPOWER_CTRL	0x0010
#define SYSPOWER_STATUS	0x0014
#define QCH_DISABLE	0x0038
#define QCH_BCLK_UAIF1	BIT(3)
#define ROUTE_CTRL0	0x0040
#define SPUS_CTRL0	0x0200
#define SPUS_CTRL1	0x0204
#define SBANK_RDMA0	0x0220
#define SBANK_MIXP	0x0280
#define SIFS_CNT0	0x0290
#define SIFS_CNT1	0x0294
#define UAIF1_CTRL0	0x0510
#define UAIF1_CTRL1	0x0514
#define UAIF1_STATUS	0x051c
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
#define UAIF_MASTER	BIT(2)
#define UAIF_SPK_EN	BIT(0)
/* FORMAT 0x09, BCLK_POLARITY 1, WS_MODE 0 (I2S), SLOT_MAX 1, SBIT_MAX 15 */
#define UAIF1_I2S_16_2	0x0984F000
#define BCLK_DZIELNIK	384	/* 589,824 MHz / 384 = 1,536 MHz = 48 kHz * 32 */
#define ROZMIAR		SZ_64K
#define OKRES		SZ_4K

static const u32 zapamietane[] = {
	QCH_DISABLE, SYSPOWER_CTRL, ROUTE_CTRL0, SPUS_CTRL0, SPUS_CTRL1,
	SBANK_RDMA0, SBANK_MIXP, SIFS_CNT0, SIFS_CNT1, UAIF1_CTRL0, UAIF1_CTRL1,
	CTRL0, BUF_STR, BUF_END, BUF_OFFSET, STR_POINT, VOL_FACTOR, VOL_CHANGE,
};

static u32 pozycja(u32 st)
{
	return ((st >> 12) & 0xffff) * 16 + (st & 0xfff);
}

static void div_ustaw(void __iomem *cmu, u32 v)
{
	int i;

	writel(v, cmu + DIV_UAIF1);
	for (i = 0; i < 1000 && (readl(cmu + DIV_UAIF1) & DIV_BUSY); i++)
		udelay(1);
}

static int __init abox_e3_init(void)
{
	u32 kopia[ARRAY_SIZE(zapamietane)], div_przed = 0, st, poprz = ~0u, ust;
	void __iomem *pmu, *cmu = NULL, *a = NULL;
	struct platform_device *pdev = NULL;
	u32 poz_start = 0, poz_kon = 0;
	int i, zmian = 0, t_pierwszy = -1;
	dma_addr_t dma;
	u16 *buf = NULL;

	pmu = ioremap(PMU_AUD, 0x10);
	if (!pmu)
		return -ENOMEM;
	st = readl(pmu + 4);
	iounmap(pmu);
	if (!(st & 1)) {
		pr_err("abox_e3: domena AUD wylaczona (%08x)\n", st);
		return -EAGAIN;
	}
	cmu = ioremap(CMU_AUD, 0x4000);
	a = ioremap(ABOX_BASE, 0x10000);
	if (!cmu || !a)
		goto mapy;
	div_przed = readl(cmu + DIV_UAIF1);
	pr_info("abox_e3: sciezka=%d CMU: DIV_UAIF1=%08x MUX_UAIF1=%08x GAT_BCLK_UAIF1=%08x\n",
		sciezka, div_przed, readl(cmu + MUX_UAIF1), readl(cmu + GAT_BCLK_UAIF1));
	pr_info("abox_e3: przed: QCH=%08x ROUTE0=%08x UAIF1: CTRL0=%08x CTRL1=%08x STATUS=%08x\n",
		readl(a + QCH_DISABLE), readl(a + ROUTE_CTRL0), readl(a + UAIF1_CTRL0),
		readl(a + UAIF1_CTRL1), readl(a + UAIF1_STATUS));
	for (i = 0; i < ARRAY_SIZE(zapamietane); i++)
		kopia[i] = readl(a + zapamietane[i]);

	pdev = platform_device_register_simple("abox_e3", -1, NULL, 0);
	if (IS_ERR(pdev)) {
		pdev = NULL;
		goto mapy;
	}
	dma_coerce_mask_and_coherent(&pdev->dev, DMA_BIT_MASK(32));
	buf = dma_alloc_coherent(&pdev->dev, ROZMIAR, &dma, GFP_KERNEL);
	if (!buf)
		goto mapy;
	for (i = 0; i < ROZMIAR / 2; i++)
		buf[i] = (u16)(i * 64);

	writel(1, a + SYSPOWER_CTRL);
	for (i = 0; i < 100 && !(readl(a + SYSPOWER_STATUS) & 1); i++)
		udelay(100);
	if (!(readl(a + SYSPOWER_STATUS) & 1)) {
		pr_err("abox_e3: brak DRAM (SYSPOWER)\n");
		goto przywroc;
	}

	/* trasa */
	writel(128 / 16 << 20, a + SBANK_RDMA0);
	if (sciezka == 0) {
		writel(0x00803000, a + SBANK_MIXP);
		writel((readl(a + SPUS_CTRL0) & ~0x1f) | 0x2, a + SPUS_CTRL0);
		writel((readl(a + SPUS_CTRL1) & ~0x1f) | FORMAT_S16_2CH, a + SPUS_CTRL1);
		writel((readl(a + ROUTE_CTRL0) & ~0xf0) | 1 << 4, a + ROUTE_CTRL0);
	} else {
		writel(readl(a + SPUS_CTRL0) & ~0x1f, a + SPUS_CTRL0);
		writel(readl(a + SPUS_CTRL1) & ~0xf000, a + SPUS_CTRL1);
		writel((readl(a + ROUTE_CTRL0) & ~0xf0) | 2 << 4, a + ROUTE_CTRL0);
	}
	/* UAIF1: master, zegar 1,536 MHz z wlasnego dzielnika, format I2S 16/2 */
	writel(readl(a + UAIF1_CTRL0) | UAIF_MASTER, a + UAIF1_CTRL0);
	div_ustaw(cmu, (div_przed & ~0x1ff) | (BCLK_DZIELNIK - 1));
	writel(UAIF1_I2S_16_2, a + UAIF1_CTRL1);
	writel(0, a + (sciezka ? SIFS_CNT1 : SIFS_CNT0));

	/* RDMA0 jak w firmware, bez ENABLE */
	writel(0x800000, a + VOL_FACTOR);
	writel(0, a + VOL_CHANGE);
	writel((u32)dma, a + BUF_STR);
	writel((u32)dma + ROZMIAR, a + BUF_END);
	writel((u32)dma, a + STR_POINT);
	writel(OKRES, a + BUF_OFFSET);
	writel(0x00400000 | FORMAT_S16_2CH << 8 | BUF_UPDATE, a + CTRL0);

	writel(readl(a + QCH_DISABLE) | QCH_BCLK_UAIF1, a + QCH_DISABLE);
	writel(readl(a + UAIF1_CTRL0) | UAIF_SPK_EN, a + UAIF1_CTRL0);
	pr_info("abox_e3: zaprogramowane: ROUTE0=%08x SPUS0=%08x SPUS1=%08x UAIF1 CTRL0=%08x CTRL1=%08x DIV=%08x QCH=%08x RDMA=%08x\n",
		readl(a + ROUTE_CTRL0), readl(a + SPUS_CTRL0), readl(a + SPUS_CTRL1),
		readl(a + UAIF1_CTRL0), readl(a + UAIF1_CTRL1), readl(cmu + DIV_UAIF1),
		readl(a + QCH_DISABLE), readl(a + CTRL0));
	writel(readl(a + CTRL0) | ENABLE, a + CTRL0);

	for (i = 0; i < czas; i++) {
		st = readl(a + STATUS);
		ust = readl(a + UAIF1_STATUS);
		if (st != poprz) {
			if (t_pierwszy < 0 && (st >> 31)) {
				t_pierwszy = i;
				poz_start = pozycja(st);
			}
			if (zmian++ < 12)
				pr_info("abox_e3: t=%d ms RDMA=%08x postep=%u pozycja=%u B UAIF1=%08x\n",
					i, st, st >> 31, pozycja(st), ust);
			poprz = st;
		}
		usleep_range(1000, 1050);
	}
	poz_kon = pozycja(readl(a + STATUS));
	pr_info("abox_e3: po %d ms: RDMA=%08x UAIF1=%08x zmian=%d pierwszy postep t=%d pozycja %u -> %u\n",
		czas, readl(a + STATUS), readl(a + UAIF1_STATUS), zmian, t_pierwszy,
		poz_start, poz_kon);

	/* stop jak producent: RDMA, odczekanie, UAIF, Q-channel */
	writel(readl(a + CTRL0) & ~ENABLE, a + CTRL0);
	for (i = 0; i < 100 && (readl(a + STATUS) >> 31); i++)
		usleep_range(1000, 1050);
	usleep_range(1200, 1500);
	writel(readl(a + UAIF1_CTRL0) & ~UAIF_SPK_EN, a + UAIF1_CTRL0);
	pr_info("abox_e3: RDMA stop po %d ms, RDMA=%08x UAIF1=%08x\n", i,
		readl(a + STATUS), readl(a + UAIF1_STATUS));

przywroc:
	for (i = ARRAY_SIZE(zapamietane) - 1; i >= 0; i--)
		writel(kopia[i], a + zapamietane[i]);
	div_ustaw(cmu, div_przed);
	pr_info("abox_e3: przywrocone: ROUTE0=%08x SPUS0=%08x SPUS1=%08x UAIF1 %08x/%08x DIV=%08x QCH=%08x RDMA=%08x SYSPOWER=%x\n",
		readl(a + ROUTE_CTRL0), readl(a + SPUS_CTRL0), readl(a + SPUS_CTRL1),
		readl(a + UAIF1_CTRL0), readl(a + UAIF1_CTRL1), readl(cmu + DIV_UAIF1),
		readl(a + QCH_DISABLE), readl(a + CTRL0), readl(a + SYSPOWER_CTRL));
mapy:
	if (buf)
		dma_free_coherent(&pdev->dev, ROZMIAR, buf, dma);
	if (pdev)
		platform_device_unregister(pdev);
	if (a)
		iounmap(a);
	if (cmu)
		iounmap(cmu);
	return -EAGAIN;
}
module_init(abox_e3_init);
MODULE_LICENSE("GPL");
