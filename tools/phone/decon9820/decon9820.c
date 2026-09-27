// SPDX-License-Identifier: GPL-2.0-only
/*
 * Eksperymentalny sterownik KMS dla DECON Exynos 9820 na potoku, ktory
 * zostawia S-Boot (tryb polecen DSI, TE, DSC, okno 5, IDMA GF0).
 *
 * Nie dotyka DSIM ani panelu i nie robi modesetu: jedyna plaszczyzna to
 * IDMA GF0 w oknie 5, a flip to zapis adresu bufora do IDMA_IN_BASE_ADDR_Y
 * i zgloszenie aktualizacji cienia okna (SHADOW_REG_UPDATE_REQ = BIT(5)),
 * jak w decon_reg_update_req_window producenta.  Bufory sa ciagle (GEM DMA,
 * CMA ponizej 4 GB): SYSMMU DPU jest po S-Boocie w bypassie, a IDMA bierze
 * adres 32-bitowy.  Zmierzone 24.09.2026: zadanie aktualizacji wraca do 0
 * po 4-8 ms, obraz z bufora CMA poprawny (measurements/2026-09-24-decon-m0-m1a).
 *
 * Bez obslugi vblank: aktualizacja plaszczyzny czeka, az DECON zatrzasnie
 * nowy adres na ramce TE, a DRM wysyla zdarzenie flipa zaraz potem
 * (no_vblank, drm_atomic_helper_fake_vblank).  Tempo klatek idzie wiec za
 * TE panelu, a stary bufor wraca do KWin dopiero, gdy nie jest czytany.
 * Na zatrzask czekamy do przerwania poczatku ramki (SPI 183, zbocze jak
 * u producenta); gdy przerwanie nie przychodzi, odpytujemy rejestr.
 * Wylaczenie plaszczyzny odsyla skan na framebuffer S-Boota (0xca000000,
 * no-map w reserved-memory).  Panel gasi i zapala latka 0100 przez klase
 * LCD; ta rozpoznaje tylko wezel simple-framebuffer, stad urzadzenie
 * posrednie z tym wezlem.
 *
 * Modulu nie da sie wyladowac (brak module_exit, brak unbind z sysfs):
 * /dev/fb0 nie trzyma referencji na modul.  Odwrot przez restart.
 */
#include <linux/aperture.h>
#include <linux/clk.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/interrupt.h>
#include <linux/iopoll.h>
#include <linux/lcd.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_clk.h>
#include <linux/of_irq.h>
#include <linux/platform_device.h>

#include <drm/clients/drm_client_setup.h>
#include <drm/drm_atomic.h>
#include <drm/drm_atomic_helper.h>
#include <drm/drm_crtc_helper.h>
#include <drm/drm_drv.h>
#include <drm/drm_edid.h>
#include <drm/drm_fb_dma_helper.h>
#include <drm/drm_fbdev_dma.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_framebuffer.h>
#include <drm/drm_gem_atomic_helper.h>
#include <drm/drm_gem_dma_helper.h>
#include <drm/drm_gem_framebuffer_helper.h>
#include <drm/drm_managed.h>
#include <drm/drm_modeset_helper_vtables.h>
#include <drm/drm_prime.h>
#include <drm/drm_print.h>
#include <drm/drm_probe_helper.h>
#include <drm/drm_simple_kms_helper.h>

#include "decon9820-edid.h"

#define SZER		1440
#define WYS		3040
#define FB_BOOT		0xca000000u
#define FB_BOOT_ROZMIAR	(SZER * WYS * 4)

#define DECON_BAZA		0x19030000
#define DECON_INT_PENDING	0x004c
#define DECON_FRAME_START_PEND	BIT(12)
#define DECON_FRAME_DONE_PEND	BIT(13)
#define DECON_SHADOW_REQ	0x0060
#define OKNO			5
#define IDMA_BAZA		0x19071000
#define IDMA_IN_CON		0x0008
#define IDMA_IMG_FORMAT_MASK	(0x3f << 11)
#define IDMA_IMG_FORMAT(v)	((v) << 11)
#define IDMA_FMT_ARGB8888	0
#define IDMA_FMT_XRGB8888	4
#define IDMA_IN_BASE_ADDR_Y	0x0040

struct decon9820 {
	struct drm_device drm;
	void __iomem *decon;
	void __iomem *idma;
	u32 in_con_boot;
	/* Tylko of_node = simple-framebuffer, dla controls_device latki 0100. */
	struct device lcd_posrednik;
	/* Bufor, ktory IDMA moze jeszcze czytac po niezatrzasnietej zmianie. */
	struct drm_framebuffer *wiszacy;
	/*
	 * Przerwanie poczatku ramki (SPI 183): cien okna zatrzaskuje sie na
	 * poczatku ramki, wiec zamiast odpytywac 0x060 spimy do tego zgloszenia.
	 * Bez przerwan (odpytuj) wracamy do odpytywania.
	 */
	int irq;
	bool odpytuj;
	atomic_t przerwania;
	wait_queue_head_t kolejka;
	struct drm_plane plane;
	struct drm_crtc crtc;
	struct drm_encoder encoder;
	struct drm_connector connector;
};

static struct decon9820 *to_d(struct drm_device *drm)
{
	return container_of(drm, struct decon9820, drm);
}

static irqreturn_t decon9820_przerwanie(int irq, void *dane)
{
	struct decon9820 *d = dane;
	u32 p = readl(d->decon + DECON_INT_PENDING);

	if (!(p & (DECON_FRAME_START_PEND | DECON_FRAME_DONE_PEND)))
		return IRQ_NONE;
	writel(p & (DECON_FRAME_START_PEND | DECON_FRAME_DONE_PEND),
	       d->decon + DECON_INT_PENDING);
	atomic_inc(&d->przerwania);
	wake_up(&d->kolejka);
	return IRQ_HANDLED;
}

static bool decon9820_zatrzasniete(struct decon9820 *d)
{
	return !(readl(d->decon + DECON_SHADOW_REQ) & BIT(OKNO));
}

/* Zapis adresu i formatu, zgloszenie cienia okna i czekanie na zatrzask. */
static int decon9820_pokaz(struct decon9820 *d, u32 adres, u32 fmt)
{
	u32 v;
	int ret;

	v = readl(d->idma + IDMA_IN_CON);
	v = (v & ~IDMA_IMG_FORMAT_MASK) | IDMA_IMG_FORMAT(fmt);
	writel(v, d->idma + IDMA_IN_CON);
	writel(adres, d->idma + IDMA_IN_BASE_ADDR_Y);
	if (d->irq > 0 && !d->odpytuj) {
		int n0;

		/* Stare zgloszenie trzyma linie w gorze i zjada nastepne zbocze. */
		writel(DECON_FRAME_START_PEND | DECON_FRAME_DONE_PEND,
		       d->decon + DECON_INT_PENDING);
		n0 = atomic_read(&d->przerwania);
		writel(readl(d->decon + DECON_SHADOW_REQ) | BIT(OKNO),
		       d->decon + DECON_SHADOW_REQ);
		enable_irq(d->irq);
		/* Zatrzask na najblizszej ramce TE: 60 Hz, wiec do ok. 17 ms. */
		ret = wait_event_timeout(d->kolejka, decon9820_zatrzasniete(d),
					 msecs_to_jiffies(50));
		disable_irq(d->irq);
		if (!ret && atomic_read(&d->przerwania) == n0) {
			d->odpytuj = true;
			dev_warn(d->drm.dev,
				 "brak przerwan poczatku ramki (irq %d), wracam do odpytywania\n",
				 d->irq);
		}
	} else {
		writel(readl(d->decon + DECON_SHADOW_REQ) | BIT(OKNO),
		       d->decon + DECON_SHADOW_REQ);
	}
	ret = readl_poll_timeout(d->decon + DECON_SHADOW_REQ, v,
				 !(v & BIT(OKNO)), 200, 50000);
	if (ret)
		dev_warn_ratelimited(d->drm.dev,
				     "aktualizacja okna nie zatrzasnieta (0x060=0x%08x)\n", v);
	return ret;
}

/*
 * Po nieudanym zatrzasku IDMA czyta dalej poprzedni bufor: trzymamy go,
 * dopoki kolejna zmiana sie nie zatrzasnie.
 */
static void decon9820_po_zmianie(struct decon9820 *d, int ret,
				 struct drm_framebuffer *stary)
{
	if (ret) {
		if (!d->wiszacy && stary) {
			drm_framebuffer_get(stary);
			d->wiszacy = stary;
		}
	} else if (d->wiszacy) {
		drm_framebuffer_put(d->wiszacy);
		d->wiszacy = NULL;
	}
}

static int decon9820_parkuj(struct decon9820 *d)
{
	return decon9820_pokaz(d, FB_BOOT,
			       (d->in_con_boot & IDMA_IMG_FORMAT_MASK) >> 11);
}

static const u32 decon9820_formaty[] = {
	DRM_FORMAT_XRGB8888,
	DRM_FORMAT_ARGB8888,
};

static const u64 decon9820_modyfikatory[] = {
	DRM_FORMAT_MOD_LINEAR,
	DRM_FORMAT_MOD_INVALID,
};

static int decon9820_plane_atomic_check(struct drm_plane *plane,
					struct drm_atomic_commit *state)
{
	struct drm_plane_state *ps = drm_atomic_get_new_plane_state(state, plane);
	struct drm_crtc_state *cs;
	struct drm_framebuffer *fb = ps->fb;
	int ret;

	if (!ps->crtc)
		return 0;
	cs = drm_atomic_get_new_crtc_state(state, ps->crtc);
	ret = drm_atomic_helper_check_plane_state(ps, cs, DRM_PLANE_NO_SCALING,
						  DRM_PLANE_NO_SCALING, false, false);
	if (ret || !ps->visible)
		return ret;
	/* IDMA bierze caly obraz z bufora o szerokosci ekranu, bez przesuniec. */
	if (fb->width != SZER || fb->height != WYS || fb->pitches[0] != SZER * 4 ||
	    fb->offsets[0] || ps->src_x || ps->src_y || ps->crtc_x || ps->crtc_y)
		return -EINVAL;
	/* IDMA bierze adres 32-bitowy, a SYSMMU jest w bypassie. */
	if (upper_32_bits(drm_fb_dma_get_gem_addr(fb, ps, 0) + FB_BOOT_ROZMIAR - 1))
		return -EINVAL;
	return 0;
}

static void decon9820_plane_atomic_update(struct drm_plane *plane,
					  struct drm_atomic_commit *state)
{
	struct drm_plane_state *ps = drm_atomic_get_new_plane_state(state, plane);
	struct drm_plane_state *stary = drm_atomic_get_old_plane_state(state, plane);
	struct decon9820 *d = to_d(plane->dev);
	u32 fmt;
	int ret;

	if (!ps->fb || !ps->visible) {
		ret = decon9820_parkuj(d);
	} else {
		fmt = ps->fb->format->format == DRM_FORMAT_ARGB8888 ?
		      IDMA_FMT_ARGB8888 : IDMA_FMT_XRGB8888;
		ret = decon9820_pokaz(d, lower_32_bits(drm_fb_dma_get_gem_addr(ps->fb, ps, 0)),
				      fmt);
	}
	decon9820_po_zmianie(d, ret, stary->fb);
}

static void decon9820_plane_atomic_disable(struct drm_plane *plane,
					   struct drm_atomic_commit *state)
{
	struct drm_plane_state *stary = drm_atomic_get_old_plane_state(state, plane);
	struct decon9820 *d = to_d(plane->dev);

	decon9820_po_zmianie(d, decon9820_parkuj(d), stary->fb);
}

static const struct drm_plane_helper_funcs decon9820_plane_helper = {
	.atomic_check = decon9820_plane_atomic_check,
	.atomic_update = decon9820_plane_atomic_update,
	.atomic_disable = decon9820_plane_atomic_disable,
};

static const struct drm_plane_funcs decon9820_plane_funcs = {
	.update_plane = drm_atomic_helper_update_plane,
	.disable_plane = drm_atomic_helper_disable_plane,
	.destroy = drm_plane_cleanup,
	.reset = drm_atomic_helper_plane_reset,
	.atomic_duplicate_state = drm_atomic_helper_plane_duplicate_state,
	.atomic_destroy_state = drm_atomic_helper_plane_destroy_state,
};

static int decon9820_crtc_atomic_check(struct drm_crtc *crtc,
				       struct drm_atomic_commit *state)
{
	struct drm_crtc_state *cs = drm_atomic_get_new_crtc_state(state, crtc);

	if (!cs->enable)
		return 0;
	return drm_atomic_helper_check_crtc_primary_plane(cs);
}

/*
 * Potok DECON/DSIM zostaje wlaczony (TE plynie przy wygaszonym panelu),
 * wiec DPMS to tylko polecenia 0x29/0x28 wysylane przez latke 0100.
 */
static void decon9820_crtc_atomic_enable(struct drm_crtc *crtc,
					 struct drm_atomic_commit *state)
{
	lcd_notify_blank_all(&to_d(crtc->dev)->lcd_posrednik, LCD_POWER_ON);
}

static void decon9820_crtc_atomic_disable(struct drm_crtc *crtc,
					  struct drm_atomic_commit *state)
{
	lcd_notify_blank_all(&to_d(crtc->dev)->lcd_posrednik, LCD_POWER_OFF);
}

static const struct drm_crtc_helper_funcs decon9820_crtc_helper = {
	.atomic_check = decon9820_crtc_atomic_check,
	.atomic_enable = decon9820_crtc_atomic_enable,
	.atomic_disable = decon9820_crtc_atomic_disable,
};

static const struct drm_crtc_funcs decon9820_crtc_funcs = {
	.reset = drm_atomic_helper_crtc_reset,
	.destroy = drm_crtc_cleanup,
	.set_config = drm_atomic_helper_set_config,
	.page_flip = drm_atomic_helper_page_flip,
	.atomic_duplicate_state = drm_atomic_helper_crtc_duplicate_state,
	.atomic_destroy_state = drm_atomic_helper_crtc_destroy_state,
};

/*
 * EDID panelu (generuj_edid.py): kolorymetria Display P3 i luminancje, zeby
 * kompozytor znal gamut panelu zamiast zakladac sRGB. Tryby dalej tylko ze
 * stalego trybu ponizej; EDID nie deklaruje PQ ani BT.2020.
 */
static int decon9820_get_modes(struct drm_connector *connector)
{
	static const struct drm_display_mode tryb = {
		DRM_MODE_INIT(60, SZER, WYS, 69, 147),
	};
	const struct drm_edid *edid = drm_edid_alloc(decon9820_edid, sizeof(decon9820_edid));

	drm_edid_connector_update(connector, edid);
	drm_edid_free(edid);
	return drm_connector_helper_get_modes_fixed(connector, &tryb);
}

static const struct drm_connector_helper_funcs decon9820_connector_helper = {
	.get_modes = decon9820_get_modes,
};

static const struct drm_connector_funcs decon9820_connector_funcs = {
	.reset = drm_atomic_helper_connector_reset,
	.fill_modes = drm_helper_probe_single_connector_modes,
	.destroy = drm_connector_cleanup,
	.atomic_duplicate_state = drm_atomic_helper_connector_duplicate_state,
	.atomic_destroy_state = drm_atomic_helper_connector_destroy_state,
};

static const struct drm_mode_config_funcs decon9820_mode_config_funcs = {
	.fb_create = drm_gem_fb_create,
	.atomic_check = drm_atomic_helper_check,
	.atomic_commit = drm_atomic_helper_commit,
};

/*
 * Bez SYSMMU skanujemy tylko wlasne, ciagle bufory CMA.  Obcy dmabuf
 * (np. klient panfrosta przy bezposrednim scanoucie) przy masce 32 bity
 * przeszedlby przez SWIOTLB i DECON skanowalby jednorazowa kopie.
 */
static struct drm_gem_object *
decon9820_gem_prime_import(struct drm_device *dev, struct dma_buf *buf)
{
	if (drm_gem_is_prime_exported_dma_buf(dev, buf))
		return drm_gem_prime_import(dev, buf);
	return ERR_PTR(-EOPNOTSUPP);
}

DEFINE_DRM_GEM_DMA_FOPS(decon9820_fops);

static const struct drm_driver decon9820_driver = {
	.driver_features = DRIVER_GEM | DRIVER_MODESET | DRIVER_ATOMIC,
	.fops = &decon9820_fops,
	.name = "decon9820",
	.desc = "Exynos9820 DECON na potoku S-Boota",
	.major = 0,
	.minor = 4,
	DRM_GEM_DMA_DRIVER_OPS,
	.gem_prime_import = decon9820_gem_prime_import,
	DRM_FBDEV_DMA_DRIVER_OPS,
};

static int decon9820_zegary(void)
{
	/* APB DECON0 PCLKM/PCLKS, APB DPU_DMA PCLKM/PCLKS w CMU_DPU. */
	static const int id[] = { 5, 6, 13, 14 };
	struct of_phandle_args a = { .args_count = 1 };
	int i, ret = 0;

	a.np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-cmu-dpu");
	if (!a.np)
		return -ENODEV;
	for (i = 0; i < ARRAY_SIZE(id) && !ret; i++) {
		struct clk *c;

		a.args[0] = id[i];
		c = of_clk_get_from_provider(&a);
		if (IS_ERR(c)) {
			ret = PTR_ERR(c);
		} else {
			/* Zegar zostaje wlaczony dla potoku S-Boota, uchwyt oddajemy. */
			ret = clk_prepare_enable(c);
			clk_put(c);
		}
	}
	of_node_put(a.np);
	return ret;
}

/* fbdev i trzy bufory KWin, kazdy ciagly i ponizej 4 GB, zanim zabierzemy ekran. */
static int decon9820_sprawdz_cma(struct device *dev)
{
	void *p[4] = {};
	dma_addr_t a[4];
	int i, ret = 0;

	for (i = 0; i < ARRAY_SIZE(p) && !ret; i++) {
		p[i] = dma_alloc_wc(dev, FB_BOOT_ROZMIAR, &a[i], GFP_KERNEL | __GFP_NOWARN);
		if (!p[i])
			ret = -ENOMEM;
	}
	for (i = 0; i < ARRAY_SIZE(p); i++)
		if (p[i])
			dma_free_wc(dev, FB_BOOT_ROZMIAR, p[i], a[i]);
	return ret;
}

static int decon9820_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct device_node *fb_np;
	struct decon9820 *d;
	struct drm_device *drm;
	int ret;

	ret = dma_coerce_mask_and_coherent(dev, DMA_BIT_MASK(32));
	if (ret)
		return ret;
	ret = decon9820_zegary();
	if (ret)
		return dev_err_probe(dev, ret, "zegary APB DPU\n");

	d = devm_drm_dev_alloc(dev, &decon9820_driver, struct decon9820, drm);
	if (IS_ERR(d))
		return PTR_ERR(d);
	drm = &d->drm;
	d->decon = devm_ioremap(dev, DECON_BAZA, 0x100);
	d->idma = devm_ioremap(dev, IDMA_BAZA, 0x100);
	if (!d->decon || !d->idma)
		return -ENOMEM;
	if (readl(d->idma + IDMA_IN_BASE_ADDR_Y) != FB_BOOT)
		return dev_err_probe(dev, -ENODEV,
				     "IDMA nie czyta framebuffera S-Boota (0x%08x)\n",
				     readl(d->idma + IDMA_IN_BASE_ADDR_Y));
	d->in_con_boot = readl(d->idma + IDMA_IN_CON);

	/* Wezel zostaje przypiety na zawsze: modulu nie da sie wyladowac. */
	fb_np = of_find_compatible_node(NULL, NULL, "simple-framebuffer");
	if (!fb_np)
		return dev_err_probe(dev, -ENODEV, "brak wezla simple-framebuffer\n");
	d->lcd_posrednik.of_node = fb_np;

	/*
	 * Linia z wezla DECON w DT.  DT deklaruje poziom, a jadro producenta
	 * obsluguje te linie zboczem (HW-39); zbocze dziala w obu przypadkach,
	 * bo przed kazdym czekaniem kasujemy zgloszenie.
	 */
	init_waitqueue_head(&d->kolejka);
	fb_np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-decon");
	d->irq = fb_np ? of_irq_get_byname(fb_np, "frame-start") : -ENODEV;
	of_node_put(fb_np);
	ret = d->irq > 0 ? devm_request_irq(dev, d->irq, decon9820_przerwanie,
					    IRQF_NO_AUTOEN | IRQF_TRIGGER_RISING,
					    "decon9820", d) : d->irq;
	if (ret) {
		dev_warn(dev, "bez przerwania poczatku ramki (%d), odpytuje\n", ret);
		d->odpytuj = true;
	}

	ret = decon9820_sprawdz_cma(dev);
	if (ret)
		return dev_err_probe(dev, ret,
				     "za malo CMA ponizej 4 GB na 4 bufory ekranu (cma=256M@0-4G?)\n");

	ret = drmm_mode_config_init(drm);
	if (ret)
		return ret;
	drm->mode_config.min_width = SZER;
	drm->mode_config.max_width = SZER;
	drm->mode_config.min_height = WYS;
	drm->mode_config.max_height = WYS;
	drm->mode_config.preferred_depth = 24;
	drm->mode_config.funcs = &decon9820_mode_config_funcs;

	ret = drm_universal_plane_init(drm, &d->plane, 0, &decon9820_plane_funcs,
				       decon9820_formaty, ARRAY_SIZE(decon9820_formaty),
				       decon9820_modyfikatory, DRM_PLANE_TYPE_PRIMARY, NULL);
	if (ret)
		return ret;
	drm_plane_helper_add(&d->plane, &decon9820_plane_helper);

	ret = drm_crtc_init_with_planes(drm, &d->crtc, &d->plane, NULL,
					&decon9820_crtc_funcs, NULL);
	if (ret)
		return ret;
	drm_crtc_helper_add(&d->crtc, &decon9820_crtc_helper);

	ret = drm_simple_encoder_init(drm, &d->encoder, DRM_MODE_ENCODER_DSI);
	if (ret)
		return ret;
	d->encoder.possible_crtcs = drm_crtc_mask(&d->crtc);

	ret = drm_connector_init(drm, &d->connector, &decon9820_connector_funcs,
				 DRM_MODE_CONNECTOR_DSI);
	if (ret)
		return ret;
	drm_connector_helper_add(&d->connector, &decon9820_connector_helper);
	ret = drm_connector_attach_encoder(&d->connector, &d->encoder);
	if (ret)
		return ret;
	drm_mode_config_reset(drm);

	/*
	 * simpledrm trzyma ten sam framebuffer; od teraz ekran jest nasz.
	 * Funkcja zawsze zwraca 0, wiec wszystko, co moze zawiesc, jest wyzej.
	 */
	aperture_remove_conflicting_devices(FB_BOOT, FB_BOOT_ROZMIAR,
					    decon9820_driver.name);

	platform_set_drvdata(pdev, drm);
	ret = drm_dev_register(drm, 0);
	if (ret)
		return ret;
	drm_client_setup(drm, NULL);
	drm_info(drm, "DECON 9820 na potoku S-Boota, okno %d, %dx%d, flip na TE%s\n",
		 OKNO, SZER, WYS, d->odpytuj ? " (odpytywanie)" : " (przerwanie)");
	return 0;
}

static void decon9820_shutdown(struct platform_device *pdev)
{
	struct drm_device *drm = platform_get_drvdata(pdev);

	if (!drm)
		return;
	drm_atomic_helper_shutdown(drm);
	/* Zabezpieczenie: ekran na framebufferze S-Boota. */
	decon9820_parkuj(to_d(drm));
}

static struct platform_driver decon9820_platform = {
	.driver = {
		.name = "decon9820",
		.suppress_bind_attrs = true,
	},
	.probe = decon9820_probe,
	.shutdown = decon9820_shutdown,
};

static int __init decon9820_init(void)
{
	struct platform_device *pdev;
	int ret = platform_driver_register(&decon9820_platform);

	if (ret)
		return ret;
	pdev = platform_device_register_simple("decon9820", -1, NULL, 0);
	if (IS_ERR(pdev)) {
		platform_driver_unregister(&decon9820_platform);
		return PTR_ERR(pdev);
	}
	return 0;
}
module_init(decon9820_init);

MODULE_DESCRIPTION("Eksperymentalny KMS dla DECON Exynos9820 na potoku S-Boota");
MODULE_LICENSE("GPL");
