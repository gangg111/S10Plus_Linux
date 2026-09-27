// SPDX-License-Identifier: GPL-2.0
/*
 * Eksperyment E1: czy RDMA0 bloku ABOX czyta pamiec, gdy programuje je AP,
 * bez firmware DSP.  Sekwencja zapisow jak w firmware Calliope (funkcja
 * startu 0xf860c, measurements/2026-09-25-dzwiek), zadanie DRAM przez
 * SYSPOWER_CTRL jak w abox.c producenta.  Odbiorcy danych (SIFS, UAIF) nie
 * ma, wiec spodziewane jest kilka paczek do SBANK i zatrzymanie.  Na koniec
 * wszystko wraca do wartosci po resecie; init konczy sie bledem, zeby modul
 * nie zostawal w pamieci.
 */
#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/sizes.h>

#define PMU_AUD		0x15861900
#define ABOX_BASE	0x18c50000
#define VERSION		0x0004
#define SYSPOWER_CTRL	0x0010
#define SYSPOWER_STATUS	0x0014
#define SBANK_RDMA0	0x0220
#define R0		0x1000
#define CTRL0		(R0 + 0x00)
#define CTRL1		(R0 + 0x04)
#define BUF_STR		(R0 + 0x08)
#define BUF_END		(R0 + 0x0c)
#define BUF_OFFSET	(R0 + 0x10)
#define STR_POINT	(R0 + 0x14)
#define VOL_FACTOR	(R0 + 0x18)
#define VOL_CHANGE	(R0 + 0x1c)
#define STATUS		(R0 + 0x30)

#define CTRL0_RESET	0x00400000	/* BURST_LEN 8, odczyt z sondy */
#define ENABLE		BIT(0)
#define BUF_UPDATE	BIT(5)
#define FORMAT_S16_2CH	((1 << 3) | (2 - 1))
#define ROZMIAR		SZ_64K
#define OKRES		SZ_4K

static void zrzut(void __iomem *a, const char *kiedy)
{
	pr_info("abox_e1: %s: CTRL0=%08x STR=%08x END=%08x OFF=%08x PT=%08x STATUS=%08x SBANK=%08x SYSPOWER=%x/%x\n",
		kiedy, readl(a + CTRL0), readl(a + BUF_STR), readl(a + BUF_END),
		readl(a + BUF_OFFSET), readl(a + STR_POINT), readl(a + STATUS),
		readl(a + SBANK_RDMA0), readl(a + SYSPOWER_CTRL),
		readl(a + SYSPOWER_STATUS));
}

static int __init abox_e1_init(void)
{
	struct platform_device *pdev;
	void __iomem *pmu, *a;
	dma_addr_t dma;
	u16 *buf;
	u32 st, poprz = ~0u;
	int i, zmian = 0;

	pmu = ioremap(PMU_AUD, 0x10);
	if (!pmu)
		return -ENOMEM;
	st = readl(pmu + 4);
	iounmap(pmu);
	if (!(st & 1)) {
		pr_err("abox_e1: domena AUD wylaczona (%08x), koniec\n", st);
		return -EAGAIN;
	}
	a = ioremap(ABOX_BASE, 0x10000);
	if (!a)
		return -ENOMEM;
	pr_info("abox_e1: VERSION=%08x\n", readl(a + VERSION));

	pdev = platform_device_register_simple("abox_e1", -1, NULL, 0);
	if (IS_ERR(pdev)) {
		iounmap(a);
		return PTR_ERR(pdev);
	}
	dma_coerce_mask_and_coherent(&pdev->dev, DMA_BIT_MASK(32));
	buf = dma_alloc_coherent(&pdev->dev, ROZMIAR, &dma, GFP_KERNEL);
	if (!buf) {
		pr_err("abox_e1: brak bufora\n");
		goto koniec_dev;
	}
	for (i = 0; i < ROZMIAR / 2; i++)
		buf[i] = (u16)(i * 64);
	pr_info("abox_e1: bufor %pad, %d B\n", &dma, ROZMIAR);

	/* zadanie DRAM, jak abox_request_dram_on() producenta */
	writel(1, a + SYSPOWER_CTRL);
	for (i = 0; i < 100 && !(readl(a + SYSPOWER_STATUS) & 1); i++)
		udelay(100);
	zrzut(a, "przed");
	if (!(readl(a + SYSPOWER_STATUS) & 1)) {
		pr_err("abox_e1: SYSPOWER_STATUS nie wstal, przerywam\n");
		goto sprzatanie;
	}

	writel(128 / 16 << 20, a + SBANK_RDMA0);	/* 128 B jak producent przy krotkim okresie */
	writel(0x800000, a + VOL_FACTOR);
	writel(0, a + VOL_CHANGE);
	writel((u32)dma, a + BUF_STR);
	writel((u32)dma + ROZMIAR, a + BUF_END);
	writel((u32)dma, a + STR_POINT);
	writel(OKRES, a + BUF_OFFSET);
	writel(CTRL0_RESET | FORMAT_S16_2CH << 8 | BUF_UPDATE, a + CTRL0);
	zrzut(a, "zaprogramowane");
	writel(readl(a + CTRL0) | ENABLE, a + CTRL0);

	for (i = 0; i < 200; i++) {
		st = readl(a + STATUS);
		if (st != poprz) {
			if (zmian++ < 20)
				pr_info("abox_e1: t=%d ms STATUS=%08x postep=%u offset=%u cnt=%u\n",
					i, st, st >> 31, (st >> 12) & 0xffff, st & 0xfff);
			poprz = st;
		}
		usleep_range(1000, 1100);
	}
	zrzut(a, "po 200 ms");

	writel(readl(a + CTRL0) & ~ENABLE, a + CTRL0);
	for (i = 0; i < 100 && (readl(a + STATUS) >> 31); i++)
		usleep_range(1000, 1100);
	pr_info("abox_e1: wylaczone po %d ms, STATUS=%08x, zmian stanu %d\n",
		i, readl(a + STATUS), zmian);

sprzatanie:
	writel(CTRL0_RESET, a + CTRL0);
	writel(0, a + BUF_STR);
	writel(0, a + BUF_END);
	writel(0, a + STR_POINT);
	writel(0, a + BUF_OFFSET);
	writel(0, a + VOL_FACTOR);
	writel(0, a + SBANK_RDMA0);
	writel(0, a + SYSPOWER_CTRL);
	zrzut(a, "po sprzataniu");
	dma_free_coherent(&pdev->dev, ROZMIAR, buf, dma);
koniec_dev:
	platform_device_unregister(pdev);
	iounmap(a);
	return -EAGAIN;
}
module_init(abox_e1_init);
MODULE_LICENSE("GPL");
