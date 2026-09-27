// SPDX-License-Identifier: GPL-2.0
/*
 * Prototyp dzwieku przez blok ABOX Exynos9820 bez firmware DSP.
 *
 * Odtwarzanie: RDMA0 -> SPUS (wejscie 0, wyjscie 0 = SIFS1, stan po resecie)
 * -> SIFS1 -> UAIF1 jako master I2S -> dwa CS35L40 (0x40 dolny glosnik,
 * prawy kanal; 0x41 sluchawka, lewy kanal).  Dane ciagnie UAIF1.
 * Nagrywanie: UAIF1 (linia SDOUT wzmacniaczy) -> NSRC0 -> SPUM -> SIFM0 -> WDMA1;
 * wzmacniacze oddaja w swoich slotach np. VMON i IMON.
 * Wskazniki buforow z DMA_STATUS, okresy z hrtimera (przerwania DMA ida do
 * GIC wewnatrz ABOX, nie do AP).  Sekwencja odtwarzania zmierzona
 * w measurements/2026-09-25-dzwiek (eksperyment E3), pola WDMA z funkcji
 * dostepowych firmware (te same co RDMA), tylko 16 bit stereo.
 *
 * Kolejnosc zegara wzgledem wzmacniaczy: DAPM wlacza wzmacniacze po prepare
 * komponentu, a wylacza przed hw_free, i PLL wzmacniacza bierze referencje
 * z BCLK.  Dlatego BCLK (SPK_ENABLE UAIF1) rusza w prepare pierwszego
 * strumienia przy stojacym DMA i gasnie dopiero w hw_free ostatniego;
 * trigger przelacza tylko DMA (i wejscie MIC przy nagrywaniu).
 *
 * Prototyp spoza drzewa, jak decon9820: sam tworzy urzadzenie platformy,
 * a dzielnik BCLK w CMU_AUD i piny UAIF1 pisze wprost, bo seria nie ma
 * jeszcze sterownika zegarow CMU_AUD.  Wymaga domeny AUD wlaczonej przez
 * bootloader (sprawdzane przy starcie).  Wszystkie ruszane rejestry wracaja
 * do wartosci z chwili zaladowania przy usuwaniu.
 */
#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/hrtimer.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/sizes.h>
#include <sound/cs35l41.h>
#include <sound/pcm_params.h>
#include <sound/soc.h>

#include "wm_adsp.h"	/* sound/soc/codecs, sciezka w Makefile */

#define PMU_AUD		0x15861900
#define CMU_AUD		0x18c00000
#define GPIO_AUD	0x18c60000
#define ABOX_SFR	0x18c50000

#define MUX_UAIF1	0x1010
#define DIV_AUDIF	0x1800
#define DIV_UAIF1	0x1830
#define DIV_BUSY	BIT(16)
#define PLL_AUD0_HZ	1179648000UL	/* zmierzone: M 45, K 0x5eff z 26 MHz */
#define GPB1_CON	0x0020

#define SYSPOWER_CTRL	0x0010
#define SYSPOWER_STATUS	0x0014
#define QCH_DISABLE	0x0038
#define QCH_BCLK_UAIF1	BIT(3)
#define ROUTE_CTRL0	0x0040
#define ROUTE_CTRL1	0x0044
#define ROUTE_CTRL2	0x0048
#define SPUS_CTRL0	0x0200
#define SPUS_CTRL1	0x0204
#define SBANK_RDMA0	0x0220
#define SIFS_CNT1	0x0294
#define SPUM_CTRL0	0x0300
#define SBANK_NSRC0	0x0328
#define UAIF1_CTRL0	0x0510
#define UAIF1_CTRL1	0x0514
#define RDMA0		0x1000
#define WDMA1		0x3100	/* SIFMn zasila WDMA(n+1), WDMA0 bierze RECP (route_base_wdma) */

/* uklad RDMA i WDMA jest ten sam (funkcje dostepowe firmware) */
#define DMA_CTRL	0x00
#define DMA_BUF_STR	0x08
#define DMA_BUF_END	0x0c
#define DMA_BUF_OFF	0x10
#define DMA_STR_POINT	0x14
#define DMA_VOL		0x18
#define DMA_VOL_CHANGE	0x1c
#define DMA_STATUS	0x30

#define DMA_ENABLE	BIT(0)
#define DMA_BUF_UPDATE	BIT(5)
#define DMA_BURST_8	(8 << 19)
#define DMA_PROGRESS	BIT(31)

#define NSRC0_ZRODLO	GENMASK(3, 0)	/* ROUTE_CTRL1 */
#define NSRC_UAIF1	9		/* nsrcx_texts producenta */
#define NSRC0_MOST	BIT(20)		/* ROUTE_CTRL2, "NSRC0 Bridge" */
#define NSRC0_ASRC	BIT(4)		/* SPUM_CTRL0 */
#define NSRC0_SIFMS	BIT(7)		/* SPUM_CTRL0, 0 = WDMA */

#define UAIF_SPK_EN	BIT(0)
#define UAIF_MIC_EN	BIT(1)
#define UAIF_MASTER	BIT(2)
#define UAIF_BCLK_POL	BIT(23)

#define BUFOR_MAX	SZ_64K

/* rejestry ABOX zapamietywane przy zaladowaniu i przywracane przy usuwaniu */
static const u32 zapamietane[] = {
	QCH_DISABLE, SYSPOWER_CTRL, ROUTE_CTRL0, ROUTE_CTRL1, ROUTE_CTRL2,
	SPUS_CTRL0, SPUS_CTRL1, SBANK_RDMA0, SIFS_CNT1, SPUM_CTRL0, SBANK_NSRC0,
	UAIF1_CTRL0, UAIF1_CTRL1,
	RDMA0 + DMA_CTRL, RDMA0 + DMA_BUF_STR, RDMA0 + DMA_BUF_END,
	RDMA0 + DMA_BUF_OFF, RDMA0 + DMA_STR_POINT, RDMA0 + DMA_VOL,
	RDMA0 + DMA_VOL_CHANGE,
	WDMA1 + DMA_CTRL, WDMA1 + DMA_BUF_STR, WDMA1 + DMA_BUF_END,
	WDMA1 + DMA_BUF_OFF, WDMA1 + DMA_STR_POINT, WDMA1 + DMA_VOL,
	WDMA1 + DMA_VOL_CHANGE,
};

/* stan jednego kierunku: 0 odtwarzanie (RDMA0), 1 nagrywanie (WDMA1) */
struct abox_kier {
	struct snd_pcm_substream *sub;
	struct hrtimer timer;
	ktime_t okres;
	unsigned int bajty_bufora;
	atomic_t gra;
	u32 dma;
	bool zegar;	/* ten kierunek trzyma zegar UAIF1 */
};

struct abox9820 {
	struct device *dev;
	void __iomem *sfr;
	void __iomem *cmu;
	void __iomem *gpio;
	struct abox_kier kier[2];
	struct mutex blokada;	/* zegar UAIF1 i DRAM, wspolne dla kierunkow */
	int zegar_uzytkownicy;
	int dram_uzytkownicy;
	u32 kopia[ARRAY_SIZE(zapamietane)];
	u32 div_uaif1, gpb1_con;
};

static struct platform_device *abox_pdev;
/*
 * Jedna instancja.  drvdata urzadzenia nalezy do karty (snd_soc_register_card
 * wpisuje tam wskaznik na karte), wiec komponent i DAI biora dane stad.
 */
static struct abox9820 *abox_ab;

static struct abox_kier *abox_kier(struct snd_pcm_substream *sub)
{
	return &abox_ab->kier[sub->stream];
}

/* abox_get_format() producenta: (kod szerokosci << 3) | (kanaly - 1) */
static int abox_format(unsigned int szer, unsigned int kan)
{
	if (szer != 16 || kan != 2)
		return -EINVAL;	/* zmierzone tylko 16 bit stereo */
	return 1 << 3 | (kan - 1);
}

static void abox_dram(struct abox9820 *ab, bool wl)
{
	int i;

	mutex_lock(&ab->blokada);
	if (wl ? ab->dram_uzytkownicy++ : --ab->dram_uzytkownicy)
		goto koniec;
	writel(wl, ab->sfr + SYSPOWER_CTRL);
	if (!wl)
		goto koniec;	/* STATUS po zwolnieniu nie spada (E1) */
	for (i = 0; i < 100; i++) {
		if (readl(ab->sfr + SYSPOWER_STATUS) & 1)
			goto koniec;
		udelay(10);
	}
	dev_warn(ab->dev, "SYSPOWER_STATUS nie potwierdzil zadania DRAM\n");
koniec:
	mutex_unlock(&ab->blokada);
}

static void abox_div_uaif1(struct abox9820 *ab, u32 v)
{
	int i;

	writel(v, ab->cmu + DIV_UAIF1);
	for (i = 0; i < 1000 && (readl(ab->cmu + DIV_UAIF1) & DIV_BUSY); i++)
		udelay(1);
}

static void abox_dma_stop(struct abox9820 *ab, u32 dma)
{
	int i;

	writel(readl(ab->sfr + dma + DMA_CTRL) & ~DMA_ENABLE, ab->sfr + dma + DMA_CTRL);
	for (i = 0; i < 20 && (readl(ab->sfr + dma + DMA_STATUS) & DMA_PROGRESS); i++)
		usleep_range(100, 200);
}

/* BCLK rusza z pierwszym strumieniem, zanim DAPM wlaczy wzmacniacze */
static void abox_zegar_wez(struct abox9820 *ab, struct abox_kier *k)
{
	void __iomem *a = ab->sfr;

	if (k->zegar)
		return;	/* prepare po xrun: zegar juz trzymany */
	k->zegar = true;
	mutex_lock(&ab->blokada);
	if (!ab->zegar_uzytkownicy++) {
		writel(readl(a + QCH_DISABLE) | QCH_BCLK_UAIF1, a + QCH_DISABLE);
		writel(readl(a + UAIF1_CTRL0) | UAIF_SPK_EN, a + UAIF1_CTRL0);
	}
	mutex_unlock(&ab->blokada);
}

static void abox_zegar_oddaj(struct abox9820 *ab, struct abox_kier *k)
{
	void __iomem *a = ab->sfr;

	if (!k->zegar)
		return;
	k->zegar = false;
	mutex_lock(&ab->blokada);
	if (!--ab->zegar_uzytkownicy) {
		/* DAPM wylaczyl juz wzmacniacze; producent czeka 600-1200 us */
		usleep_range(1200, 1500);
		writel(readl(a + UAIF1_CTRL0) & ~(UAIF_SPK_EN | UAIF_MASTER),
		       a + UAIF1_CTRL0);
		writel(readl(a + QCH_DISABLE) & ~QCH_BCLK_UAIF1, a + QCH_DISABLE);
		/* piny UAIF1 z powrotem w stan sprzed zaladowania (bezczynny) */
		writel(ab->gpb1_con, ab->gpio + GPB1_CON);
	}
	mutex_unlock(&ab->blokada);
}

/* --- PCM (RDMA0, WDMA1) --- */

static const struct snd_pcm_hardware abox_pcm_hw = {
	.info = SNDRV_PCM_INFO_INTERLEAVED | SNDRV_PCM_INFO_MMAP |
		SNDRV_PCM_INFO_MMAP_VALID | SNDRV_PCM_INFO_BLOCK_TRANSFER,
	.formats = SNDRV_PCM_FMTBIT_S16_LE,
	.rates = SNDRV_PCM_RATE_48000,
	.rate_min = 48000,
	.rate_max = 48000,
	.channels_min = 2,
	.channels_max = 2,
	.buffer_bytes_max = BUFOR_MAX,
	.period_bytes_min = 256,
	.period_bytes_max = SZ_32K,
	.periods_min = 2,
	.periods_max = 64,
};

static enum hrtimer_restart abox_timer_fn(struct hrtimer *t)
{
	struct abox_kier *k = container_of(t, struct abox_kier, timer);

	if (!atomic_read(&k->gra))
		return HRTIMER_NORESTART;
	/* przy xrun i drain to wola trigger STOP */
	snd_pcm_period_elapsed(k->sub);
	if (!atomic_read(&k->gra))
		return HRTIMER_NORESTART;
	hrtimer_forward_now(t, k->okres);
	return HRTIMER_RESTART;
}

static int abox_pcm_open(struct snd_soc_component *c,
			 struct snd_pcm_substream *sub)
{
	struct abox_kier *k = abox_kier(sub);
	struct snd_pcm_runtime *rt = sub->runtime;
	int ret;

	snd_soc_set_runtime_hwparams(sub, &abox_pcm_hw);
	ret = snd_pcm_hw_constraint_step(rt, 0, SNDRV_PCM_HW_PARAM_PERIOD_BYTES, 16);
	if (ret < 0)
		return ret;
	/*
	 * Nie wiadomo jeszcze, czy RBUF_OFFSET wraca do zera na BUF_END; przy
	 * buforze bedacym potega dwojki modulo w pointer() jest poprawne w obu
	 * przypadkach.
	 */
	ret = snd_pcm_hw_constraint_pow2(rt, 0, SNDRV_PCM_HW_PARAM_BUFFER_BYTES);
	if (ret < 0)
		return ret;
	ret = snd_pcm_hw_constraint_integer(rt, SNDRV_PCM_HW_PARAM_PERIODS);
	if (ret < 0)
		return ret;
	k->sub = sub;
	abox_dram(abox_ab, true);
	return 0;
}

static int abox_pcm_close(struct snd_soc_component *c,
			  struct snd_pcm_substream *sub)
{
	struct abox_kier *k = abox_kier(sub);

	hrtimer_cancel(&k->timer);
	abox_zegar_oddaj(abox_ab, k);
	abox_dram(abox_ab, false);
	k->sub = NULL;
	return 0;
}

static void abox_trasa_odtwarzania(void __iomem *a)
{
	/* jak po resecie: SPUS IN0 = RDMA, OUT0 = SIFS1, SIFS1 = OUT0 */
	writel(128 / 16 << 20, a + SBANK_RDMA0);
	writel(readl(a + SPUS_CTRL0) & ~0x1f, a + SPUS_CTRL0);
	writel(readl(a + SPUS_CTRL1) & ~0xf000, a + SPUS_CTRL1);
	writel(0, a + SIFS_CNT1);
}

static void abox_trasa_nagrywania(void __iomem *a)
{
	/* NSRC0 = UAIF1, bez mostu i ASRC, wyjscie NSRC0 (SIFM0) do WDMA1 */
	writel((readl(a + ROUTE_CTRL1) & ~NSRC0_ZRODLO) | NSRC_UAIF1, a + ROUTE_CTRL1);
	writel(readl(a + ROUTE_CTRL2) & ~NSRC0_MOST, a + ROUTE_CTRL2);
	writel(readl(a + SPUM_CTRL0) & ~(NSRC0_ASRC | NSRC0_SIFMS), a + SPUM_CTRL0);
	/*
	 * Jak firmware przy starcie (tablice 0x22570/0x2258c): NSRC0 od bajtu
	 * 0x400 wspolnej pamieci SBANK, 512 B, czyli za RDMA0 (0..0x7f).
	 */
	writel(512 / 16 << 20 | 0x400, a + SBANK_NSRC0);
}

static int abox_pcm_prepare(struct snd_soc_component *c,
			    struct snd_pcm_substream *sub)
{
	struct abox9820 *ab = abox_ab;
	struct abox_kier *k = abox_kier(sub);
	struct snd_pcm_runtime *rt = sub->runtime;
	void __iomem *d = ab->sfr + k->dma;
	u32 start = (u32)rt->dma_addr;
	int fmt;

	fmt = abox_format(snd_pcm_format_physical_width(rt->format), rt->channels);
	if (fmt < 0)
		return fmt;
	if (upper_32_bits(rt->dma_addr) || (start & 0xf)) {
		dev_err(ab->dev, "bufor %pad poza zasiegiem DMA\n", &rt->dma_addr);
		return -EINVAL;
	}
	k->bajty_bufora = snd_pcm_lib_buffer_bytes(sub);
	k->okres = ns_to_ktime(div_u64((u64)rt->period_size * NSEC_PER_SEC,
				       rt->rate));

	abox_dma_stop(ab, k->dma);
	if (sub->stream == SNDRV_PCM_STREAM_PLAYBACK)
		abox_trasa_odtwarzania(ab->sfr);
	else
		abox_trasa_nagrywania(ab->sfr);

	writel(0x800000, d + DMA_VOL);
	writel(0, d + DMA_VOL_CHANGE);
	writel(start, d + DMA_BUF_STR);
	writel(start + k->bajty_bufora, d + DMA_BUF_END);
	writel(start, d + DMA_STR_POINT);
	writel(snd_pcm_lib_period_bytes(sub), d + DMA_BUF_OFF);
	/* EXPEND/REDUCE (bit 13) = 0: firmware ustawia go tylko w szczegolnych formatach */
	writel(DMA_BURST_8 | fmt << 8 | DMA_BUF_UPDATE, d + DMA_CTRL);

	abox_zegar_wez(ab, k);
	return 0;
}

static int abox_pcm_trigger(struct snd_soc_component *c,
			    struct snd_pcm_substream *sub, int cmd)
{
	struct abox9820 *ab = abox_ab;
	struct abox_kier *k = abox_kier(sub);
	bool nagr = sub->stream == SNDRV_PCM_STREAM_CAPTURE;
	void __iomem *a = ab->sfr;

	switch (cmd) {
	case SNDRV_PCM_TRIGGER_START:
	case SNDRV_PCM_TRIGGER_RESUME:
	case SNDRV_PCM_TRIGGER_PAUSE_RELEASE:
		/* WDMA gotowe, zanim UAIF zacznie oddawac probki */
		writel(readl(a + k->dma + DMA_CTRL) | DMA_ENABLE, a + k->dma + DMA_CTRL);
		if (nagr)	/* jak abox_uaif_trigger() producenta */
			writel(readl(a + UAIF1_CTRL0) | UAIF_MIC_EN, a + UAIF1_CTRL0);
		atomic_set(&k->gra, 1);
		hrtimer_start(&k->timer, k->okres, HRTIMER_MODE_REL_SOFT);
		return 0;
	case SNDRV_PCM_TRIGGER_STOP:
	case SNDRV_PCM_TRIGGER_SUSPEND:
	case SNDRV_PCM_TRIGGER_PAUSE_PUSH:
		atomic_set(&k->gra, 0);
		hrtimer_try_to_cancel(&k->timer);
		if (nagr)
			writel(readl(a + UAIF1_CTRL0) & ~UAIF_MIC_EN, a + UAIF1_CTRL0);
		writel(readl(a + k->dma + DMA_CTRL) & ~DMA_ENABLE, a + k->dma + DMA_CTRL);
		return 0;
	default:
		return -EINVAL;
	}
}

static int abox_pcm_sync_stop(struct snd_soc_component *c,
			      struct snd_pcm_substream *sub)
{
	struct abox_kier *k = abox_kier(sub);

	hrtimer_cancel(&k->timer);
	abox_dma_stop(abox_ab, k->dma);
	return 0;
}

static int abox_pcm_hw_free(struct snd_soc_component *c,
			    struct snd_pcm_substream *sub)
{
	struct abox9820 *ab = abox_ab;
	struct abox_kier *k = abox_kier(sub);

	if (sub->stream == SNDRV_PCM_STREAM_CAPTURE)
		writel(readl(ab->sfr + UAIF1_CTRL0) & ~UAIF_MIC_EN, ab->sfr + UAIF1_CTRL0);
	abox_dma_stop(ab, k->dma);
	abox_zegar_oddaj(ab, k);
	return 0;
}

static snd_pcm_uframes_t abox_pcm_pointer(struct snd_soc_component *c,
					  struct snd_pcm_substream *sub)
{
	struct abox_kier *k = abox_kier(sub);
	u32 st = readl(abox_ab->sfr + k->dma + DMA_STATUS);
	/* RBUF_OFFSET (bity 12-27) i RBUF_CNT (bity 0-11) licza po 16 B */
	u32 poz = (((st >> 12) & 0xffff) + (st & 0xfff)) * 16;

	if (k->bajty_bufora)
		poz %= k->bajty_bufora;
	return bytes_to_frames(sub->runtime, poz);
}

static int abox_pcm_new(struct snd_soc_component *c,
			struct snd_soc_pcm_runtime *rtd)
{
	struct abox9820 *ab = abox_ab;

	snd_pcm_set_managed_buffer_all(rtd->pcm, SNDRV_DMA_TYPE_DEV, ab->dev,
				       BUFOR_MAX, BUFOR_MAX);
	return 0;
}

/* --- CPU DAI (UAIF1) --- */

static int abox_uaif_set_fmt(struct snd_soc_dai *dai, unsigned int fmt)
{
	/* tylko I2S z ABOX jako dostawca zegarow, jak dla wzmacniaczy */
	if ((fmt & SND_SOC_DAIFMT_FORMAT_MASK) != SND_SOC_DAIFMT_I2S ||
	    (fmt & SND_SOC_DAIFMT_INV_MASK) != SND_SOC_DAIFMT_NB_NF ||
	    (fmt & SND_SOC_DAIFMT_CLOCK_PROVIDER_MASK) != SND_SOC_DAIFMT_BP_FP)
		return -EINVAL;
	return 0;
}

static int abox_uaif_hw_params(struct snd_pcm_substream *sub,
			       struct snd_pcm_hw_params *p,
			       struct snd_soc_dai *dai)
{
	struct abox9820 *ab = abox_ab;
	unsigned int szer = params_physical_width(p);
	unsigned int kan = params_channels(p);
	unsigned long audif, bclk = params_rate(p) * kan * szer;
	void __iomem *a = ab->sfr;
	int fmt;

	fmt = abox_format(szer, kan);
	if (fmt < 0)
		return fmt;
	audif = PLL_AUD0_HZ / ((readl(ab->cmu + DIV_AUDIF) & 0x1ff) + 1);
	if (audif % bclk || audif / bclk > 512) {
		dev_err(ab->dev, "BCLK %lu Hz nie wychodzi z AUDIF %lu Hz\n",
			bclk, audif);
		return -EINVAL;
	}

	mutex_lock(&ab->blokada);
	/*
	 * Drugi kierunek przy pracujacym zegarze: parametry sa symetryczne
	 * (DAI), wiec UAIF1 juz jest ustawiony i nie wolno go ruszac w biegu.
	 */
	if (ab->zegar_uzytkownicy)
		goto koniec;
	abox_div_uaif1(ab, (ab->div_uaif1 & ~0x1ff) | (audif / bclk - 1));

	/* UAIF1 = SIFS1 w ROUTE_CTRL0 (bity 4-7) */
	writel((readl(a + ROUTE_CTRL0) & ~0xf0) | 2 << 4, a + ROUTE_CTRL0);
	writel(readl(a + UAIF1_CTRL0) | UAIF_MASTER, a + UAIF1_CTRL0);
	/* FORMAT 24-28, BCLK_POLARITY 23, WS_MODE 0 (I2S), SLOT_MAX 18-20, SBIT_MAX 12-17 */
	writel(fmt << 24 | UAIF_BCLK_POL | (kan - 1) << 18 | (szer - 1) << 12,
	       a + UAIF1_CTRL1);

	/* piny gpb1-0..3 w funkcji I2S (2), jak aud-i2s1-bus producenta */
	writel((ab->gpb1_con & ~0xffff) | 0x2222, ab->gpio + GPB1_CON);

	dev_info(ab->dev, "UAIF1: %u Hz, %u x %u bit, BCLK %lu Hz, dzielnik %lu, CTRL1 %08x\n",
		 params_rate(p), kan, szer, bclk, audif / bclk,
		 readl(a + UAIF1_CTRL1));
koniec:
	mutex_unlock(&ab->blokada);
	return 0;
}

static const struct snd_soc_dai_ops abox_uaif_ops = {
	.set_fmt = abox_uaif_set_fmt,
	.hw_params = abox_uaif_hw_params,
};

static struct snd_soc_dai_driver abox_dai = {
	.name = "abox9820-uaif1",
	.playback = {
		.stream_name = "UAIF1 Playback",
		.channels_min = 2,
		.channels_max = 2,
		.rates = SNDRV_PCM_RATE_48000,
		.formats = SNDRV_PCM_FMTBIT_S16_LE,
	},
	.capture = {
		.stream_name = "UAIF1 Capture",
		.channels_min = 2,
		.channels_max = 2,
		.rates = SNDRV_PCM_RATE_48000,
		.formats = SNDRV_PCM_FMTBIT_S16_LE,
	},
	.ops = &abox_uaif_ops,
	/* jeden UAIF1 i jeden BCLK na oba kierunki */
	.symmetric_rate = 1,
	.symmetric_channels = 1,
	.symmetric_sample_bits = 1,
};

static const struct snd_soc_component_driver abox_component = {
	.name = "abox9820",
	.open = abox_pcm_open,
	.close = abox_pcm_close,
	.prepare = abox_pcm_prepare,
	.trigger = abox_pcm_trigger,
	.sync_stop = abox_pcm_sync_stop,
	.hw_free = abox_pcm_hw_free,
	.pointer = abox_pcm_pointer,
	.pcm_new = abox_pcm_new,
	/*
	 * Karta i komponent sa w tym samym module: referencja brana przy
	 * sondowaniu karty blokowalaby rmmod na zawsze.
	 */
	.module_get_upon_open = 1,
};

/* --- karta --- */

/*
 * 0x40 dolny glosnik to prawy kanal (cirrus,right-channel-amp producenta).
 * Nagrywanie: kazdy wzmacniacz oddaje ASPTX1 w slocie swojego kanalu, wiec
 * w nagraniu lewy kanal to sluchawka, prawy to dolny glosnik.
 */
static const unsigned int mapa_prawy[] = { 1, 0 };
static const unsigned int mapa_lewy[] = { 0, 1 };
static const unsigned int tx_prawy[] = { 1 };
static const unsigned int tx_lewy[] = { 0 };

static int karta_hw_params(struct snd_pcm_substream *sub,
			   struct snd_pcm_hw_params *p)
{
	struct snd_soc_pcm_runtime *rtd = snd_soc_substream_to_rtd(sub);
	unsigned int bclk = params_rate(p) * params_channels(p) *
			    params_physical_width(p);
	struct snd_soc_dai *dai;
	int i, ret;

	for_each_rtd_codec_dais(rtd, i, dai) {
		ret = snd_soc_dai_set_sysclk(dai, CS35L41_CLKID_SCLK, bclk,
					     SND_SOC_CLOCK_IN);
		if (ret < 0)
			return ret;
		ret = snd_soc_component_set_sysclk(dai->component,
						   CS35L41_CLKID_SCLK, 0, bclk,
						   SND_SOC_CLOCK_IN);
		if (ret < 0)
			return ret;
		ret = snd_soc_dai_set_channel_map(dai, 1, i == 0 ? tx_prawy : tx_lewy,
						  2, i == 0 ? mapa_prawy : mapa_lewy);
		if (ret < 0)
			return ret;
	}
	return 0;
}

static const struct snd_soc_ops karta_ops = {
	.hw_params = karta_hw_params,
};

static struct snd_soc_dai_link_component karta_cpu[] = {
	{ .dai_name = "abox9820-uaif1" },
};

/* kolejnosc: 0x40 (dolny, prawy), 0x41 (sluchawka, lewy); of_node w probe */
static struct snd_soc_dai_link_component karta_kodeki[] = {
	{ .dai_name = "cs35l41-pcm" },
	{ .dai_name = "cs35l41-pcm" },
};

static struct snd_soc_dai_link_component karta_platforma[] = {
	{ .name = "abox9820" },
};

static struct snd_soc_dai_link karta_link = {
	.name = "Glosniki",
	.stream_name = "Glosniki",
	.dai_fmt = SND_SOC_DAIFMT_I2S | SND_SOC_DAIFMT_NB_NF |
		   SND_SOC_DAIFMT_CBC_CFC,
	.ops = &karta_ops,
	.cpus = karta_cpu,
	.num_cpus = ARRAY_SIZE(karta_cpu),
	.codecs = karta_kodeki,
	.num_codecs = ARRAY_SIZE(karta_kodeki),
	.platforms = karta_platforma,
	.num_platforms = ARRAY_SIZE(karta_platforma),
};

static const struct snd_soc_dapm_widget karta_widgets[] = {
	SND_SOC_DAPM_SPK("Bottom Speaker", NULL),
	SND_SOC_DAPM_SPK("Top Speaker", NULL),
};

static const struct snd_soc_dapm_route karta_routes[] = {
	{ "Bottom Speaker", NULL, "Bottom SPK" },
	{ "Top Speaker", NULL, "Top SPK" },
};

/*
 * Firmware ochrony glosnikow jest wspolne, ale strojenie (.bin) rozne dla
 * dolnego glosnika i sluchawki, wiec wm_adsp musi szukac plikow z nazwa
 * systemu i prefiksem: cirrus/cs35l41-dsp1-spk-prot-samsung-beyond2lte-
 * {bottom,top}.{wmfw,bin}.  Docelowo "cirrus,subsystem-id" w DT; w
 * prototypie ustawiane tu, przed pierwszym zaladowaniem firmware.
 */
static const char karta_system[] = "samsung-beyond2lte";

static void karta_nazwa_systemu(struct snd_soc_card *card, bool ustaw)
{
	struct snd_soc_component *c;
	struct wm_adsp *dsp;

	for_each_card_components(card, c) {
		if (strcmp(c->driver->name, "cs35l41-codec"))
			continue;
		/* struct wm_adsp jest pierwszym polem cs35l41_private */
		dsp = snd_soc_component_get_drvdata(c);
		if (ustaw && !dsp->system_name)
			dsp->system_name = karta_system;
		else if (!ustaw && dsp->system_name == karta_system)
			dsp->system_name = NULL;
	}
}

static int karta_late_probe(struct snd_soc_card *card)
{
	karta_nazwa_systemu(card, true);
	return 0;
}

static int karta_remove(struct snd_soc_card *card)
{
	karta_nazwa_systemu(card, false);
	return 0;
}

static struct snd_soc_card karta = {
	.name = "S10Plus",
	.owner = THIS_MODULE,
	.late_probe = karta_late_probe,
	.remove = karta_remove,
	.dai_link = &karta_link,
	.num_links = 1,
	.dapm_widgets = karta_widgets,
	.num_dapm_widgets = ARRAY_SIZE(karta_widgets),
	.dapm_routes = karta_routes,
	.num_dapm_routes = ARRAY_SIZE(karta_routes),
};

/* wezly wzmacniaczy po adresie I2C, niezaleznie od numeru magistrali */
static int karta_znajdz_kodeki(struct device *dev)
{
	struct device_node *np;
	u32 reg;

	for_each_compatible_node(np, NULL, "cirrus,cs35l40") {
		if (of_property_read_u32(np, "reg", &reg))
			continue;
		if (reg == 0x40 && !karta_kodeki[0].of_node)
			karta_kodeki[0].of_node = of_node_get(np);
		else if (reg == 0x41 && !karta_kodeki[1].of_node)
			karta_kodeki[1].of_node = of_node_get(np);
	}
	if (!karta_kodeki[0].of_node || !karta_kodeki[1].of_node)
		return dev_err_probe(dev, -ENODEV, "brak wezlow cirrus,cs35l40 0x40/0x41\n");
	return 0;
}

static void abox9820_przywroc(void *dane)
{
	struct abox9820 *ab = dane;
	int i;

	for (i = 0; i < 2; i++) {
		hrtimer_cancel(&ab->kier[i].timer);
		abox_dma_stop(ab, ab->kier[i].dma);
	}
	writel(readl(ab->sfr + UAIF1_CTRL0) & ~(UAIF_SPK_EN | UAIF_MIC_EN),
	       ab->sfr + UAIF1_CTRL0);
	for (i = ARRAY_SIZE(zapamietane) - 1; i >= 0; i--)
		writel(ab->kopia[i], ab->sfr + zapamietane[i]);
	abox_div_uaif1(ab, ab->div_uaif1);
	writel(ab->gpb1_con, ab->gpio + GPB1_CON);
}

static int abox9820_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct abox9820 *ab;
	void __iomem *pmu, *a;
	u32 st;
	int i, ret;

	pmu = ioremap(PMU_AUD, 0x10);
	if (!pmu)
		return -ENOMEM;
	st = readl(pmu + 4);
	iounmap(pmu);
	if (!(st & 1))
		return dev_err_probe(dev, -ENODEV, "domena AUD wylaczona (%08x)\n", st);

	ab = devm_kzalloc(dev, sizeof(*ab), GFP_KERNEL);
	if (!ab)
		return -ENOMEM;
	ab->dev = dev;
	ab->sfr = devm_ioremap(dev, ABOX_SFR, 0x10000);
	ab->cmu = devm_ioremap(dev, CMU_AUD, 0x4000);
	ab->gpio = devm_ioremap(dev, GPIO_AUD, 0x100);
	if (!ab->sfr || !ab->cmu || !ab->gpio)
		return -ENOMEM;
	/* drugim rodzicem muxa jest zewnetrzny pin, wtedy dzielnik nic nie znaczy */
	if (readl(ab->cmu + MUX_UAIF1) & 1)
		return dev_err_probe(dev, -EINVAL, "MUX_CLK_AUD_UAIF1 nie wybiera dzielnika\n");
	mutex_init(&ab->blokada);
	ab->kier[SNDRV_PCM_STREAM_PLAYBACK].dma = RDMA0;
	ab->kier[SNDRV_PCM_STREAM_CAPTURE].dma = WDMA1;
	for (i = 0; i < 2; i++) {
		hrtimer_setup(&ab->kier[i].timer, abox_timer_fn, CLOCK_MONOTONIC,
			      HRTIMER_MODE_REL_SOFT);
		atomic_set(&ab->kier[i].gra, 0);
	}
	abox_ab = ab;

	a = ab->sfr;
	for (i = 0; i < ARRAY_SIZE(zapamietane); i++)
		ab->kopia[i] = readl(a + zapamietane[i]);
	ab->div_uaif1 = readl(ab->cmu + DIV_UAIF1);
	ab->gpb1_con = readl(ab->gpio + GPB1_CON);
	dev_info(dev, "ABOX %08x, UAIF1 %08x, DIV_UAIF1 %08x, GPB1_CON %08x\n",
		 readl(a + 0x4), readl(a + UAIF1_CTRL0), ab->div_uaif1,
		 ab->gpb1_con);
	dev_info(dev, "ROUTE1 %08x ROUTE2 %08x SPUM0 %08x SBANK_RDMA0 %08x SBANK_NSRC0 %08x WDMA1 %08x/%08x\n",
		 readl(a + ROUTE_CTRL1), readl(a + ROUTE_CTRL2), readl(a + SPUM_CTRL0),
		 readl(a + SBANK_RDMA0), readl(a + SBANK_NSRC0),
		 readl(a + WDMA1 + DMA_CTRL), readl(a + WDMA1 + DMA_STATUS));

	ret = karta_znajdz_kodeki(dev);
	if (ret)
		return ret;
	/* rejestrowane przed komponentem i karta, wiec biegnie po ich usunieciu */
	ret = devm_add_action_or_reset(dev, abox9820_przywroc, ab);
	if (ret)
		return ret;
	ret = devm_snd_soc_register_component(dev, &abox_component, &abox_dai, 1);
	if (ret)
		return ret;
	karta.dev = dev;
	return devm_snd_soc_register_card(dev, &karta);
}

/* stan sciezek do diagnostyki: cat /sys/devices/platform/abox9820/rejestry */
static ssize_t rejestry_show(struct device *dev, struct device_attribute *attr,
			     char *buf)
{
	static const struct { const char *n; u32 r; } lista[] = {
		{ "SYSPOWER", SYSPOWER_STATUS }, { "QCH", QCH_DISABLE },
		{ "ROUTE0", ROUTE_CTRL0 }, { "ROUTE1", ROUTE_CTRL1 },
		{ "ROUTE2", ROUTE_CTRL2 }, { "SPUS0", SPUS_CTRL0 },
		{ "SBANK_RDMA0", SBANK_RDMA0 }, { "SPUM0", SPUM_CTRL0 },
		{ "SBANK_NSRC0", SBANK_NSRC0 }, { "UAIF1_CTRL0", UAIF1_CTRL0 },
		{ "UAIF1_CTRL1", UAIF1_CTRL1 }, { "UAIF1_STATUS", UAIF1_CTRL0 + 0xc },
		{ "RDMA0_CTRL", RDMA0 + DMA_CTRL }, { "RDMA0_STATUS", RDMA0 + DMA_STATUS },
		{ "WDMA1_CTRL", WDMA1 + DMA_CTRL }, { "WDMA1_STR", WDMA1 + DMA_BUF_STR },
		{ "WDMA1_END", WDMA1 + DMA_BUF_END }, { "WDMA1_OFF", WDMA1 + DMA_BUF_OFF },
		{ "WDMA1_STATUS", WDMA1 + DMA_STATUS },
	};
	int i, n = 0;

	if (!abox_ab)
		return -ENODEV;
	for (i = 0; i < ARRAY_SIZE(lista); i++)
		n += sysfs_emit_at(buf, n, "%s %08x\n", lista[i].n,
				   readl(abox_ab->sfr + lista[i].r));
	n += sysfs_emit_at(buf, n, "DIV_UAIF1 %08x\n", readl(abox_ab->cmu + DIV_UAIF1));
	return n;
}
static DEVICE_ATTR_RO(rejestry);

static struct attribute *abox_attrs[] = {
	&dev_attr_rejestry.attr,
	NULL,
};
ATTRIBUTE_GROUPS(abox);

static struct platform_driver abox9820_driver = {
	.probe = abox9820_probe,
	.driver = {
		.name = "abox9820",
		.dev_groups = abox_groups,
	},
};

static int __init abox9820_init(void)
{
	int ret;

	abox_pdev = platform_device_register_simple("abox9820", -1, NULL, 0);
	if (IS_ERR(abox_pdev))
		return PTR_ERR(abox_pdev);
	ret = dma_coerce_mask_and_coherent(&abox_pdev->dev, DMA_BIT_MASK(32));
	if (!ret)
		ret = platform_driver_register(&abox9820_driver);
	if (ret)
		platform_device_unregister(abox_pdev);
	return ret;
}

static void __exit abox9820_exit(void)
{
	platform_driver_unregister(&abox9820_driver);
	platform_device_unregister(abox_pdev);
	of_node_put(karta_kodeki[0].of_node);
	of_node_put(karta_kodeki[1].of_node);
}

module_init(abox9820_init);
module_exit(abox9820_exit);
MODULE_DESCRIPTION("Exynos9820 ABOX: RDMA0 i WDMA1 przez UAIF1 bez firmware DSP (prototyp)");
MODULE_LICENSE("GPL");
