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
 * vblank z timera DRM (60 Hz), a flush czeka, az DECON zatrzasnie nowy
 * adres, zeby stary bufor nie wrocil do KWin, zanim przestanie byc czytany.
 * Przy zdjeciu modulu adres wraca na framebuffer S-Boota (0xca000000).
 */
#include <linux/aperture.h>
#include <linux/clk.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_clk.h>
#include <linux/platform_device.h>

#include <drm/clients/drm_client_setup.h>
#include <drm/drm_atomic.h>
#include <drm/drm_atomic_helper.h>
#include <drm/drm_crtc_helper.h>
#include <drm/drm_drv.h>
#include <drm/drm_fb_dma_helper.h>
#include <drm/drm_fbdev_dma.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_framebuffer.h>
#include <drm/drm_gem_atomic_helper.h>
#include <drm/drm_gem_dma_helper.h>
#include <drm/drm_gem_framebuffer_helper.h>
#include <drm/drm_managed.h>
#include <drm/drm_modeset_helper_vtables.h>
#include <drm/drm_print.h>
#include <drm/drm_probe_helper.h>
#include <drm/drm_simple_kms_helper.h>
#include <drm/drm_vblank.h>
#include <drm/drm_vblank_helper.h>

#define SZER		1440
#define WYS		3040
#define FB_BOOT		0xca000000u
#define FB_BOOT_ROZMIAR	(SZER * WYS * 4)

#define DECON_BAZA		0x19030000
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
	struct drm_plane plane;
	struct drm_crtc crtc;
	struct drm_encoder encoder;
	struct drm_connector connector;
};

static struct decon9820 *to_d(struct drm_device *drm)
{
	return container_of(drm, struct decon9820, drm);
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
	writel(readl(d->decon + DECON_SHADOW_REQ) | BIT(OKNO),
	       d->decon + DECON_SHADOW_REQ);
	/* Zatrzask na najblizszej ramce TE: 60 Hz, wiec do ok. 17 ms. */
	ret = readl_poll_timeout(d->decon + DECON_SHADOW_REQ, v,
				 !(v & BIT(OKNO)), 200, 50000);
	if (ret)
		drm_warn_once(&d->drm, "aktualizacja okna nie zatrzasnieta (0x060=0x%08x)\n", v);
	return ret;
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
	    ps->src_x || ps->src_y || ps->crtc_x || ps->crtc_y)
		return -EINVAL;
	return 0;
}

static void decon9820_plane_atomic_update(struct drm_plane *plane,
					  struct drm_atomic_commit *state)
{
	struct drm_plane_state *ps = drm_atomic_get_new_plane_state(state, plane);
	struct decon9820 *d = to_d(plane->dev);
	dma_addr_t adres;
	u32 fmt;

	if (!ps->fb || !ps->visible)
		return;
	adres = drm_fb_dma_get_gem_addr(ps->fb, ps, 0);
	if (upper_32_bits(adres)) {
		drm_err_once(plane->dev, "bufor powyzej 4 GB (%pad), pomijam\n", &adres);
		return;
	}
	fmt = ps->fb->format->format == DRM_FORMAT_ARGB8888 ?
	      IDMA_FMT_ARGB8888 : IDMA_FMT_XRGB8888;
	decon9820_pokaz(d, lower_32_bits(adres), fmt);
}

static const struct drm_plane_helper_funcs decon9820_plane_helper = {
	.atomic_check = decon9820_plane_atomic_check,
	.atomic_update = decon9820_plane_atomic_update,
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

static void decon9820_crtc_atomic_enable(struct drm_crtc *crtc,
					 struct drm_atomic_commit *state)
{
	drm_crtc_vblank_on(crtc);
}

static void decon9820_crtc_atomic_disable(struct drm_crtc *crtc,
					  struct drm_atomic_commit *state)
{
	/* Potok zostaje wlaczony; wygaszanie panelu robi klasa LCD (0100). */
	drm_crtc_vblank_off(crtc);
}

static const struct drm_crtc_helper_funcs decon9820_crtc_helper = {
	.atomic_check = decon9820_crtc_atomic_check,
	.atomic_flush = drm_crtc_vblank_atomic_flush,
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
	DRM_CRTC_VBLANK_TIMER_FUNCS,
};

static int decon9820_get_modes(struct drm_connector *connector)
{
	static const struct drm_display_mode tryb = {
		DRM_MODE_INIT(60, SZER, WYS, 69, 147),
	};

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

DEFINE_DRM_GEM_DMA_FOPS(decon9820_fops);

static const struct drm_driver decon9820_driver = {
	.driver_features = DRIVER_GEM | DRIVER_MODESET | DRIVER_ATOMIC,
	.fops = &decon9820_fops,
	.name = "decon9820",
	.desc = "Exynos9820 DECON na potoku S-Boota",
	.major = 0,
	.minor = 1,
	DRM_GEM_DMA_DRIVER_OPS,
	DRM_FBDEV_DMA_DRIVER_OPS,
};

static int decon9820_zegary(struct device *dev)
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
		if (IS_ERR(c))
			ret = PTR_ERR(c);
		else
			ret = clk_prepare_enable(c);
	}
	of_node_put(a.np);
	return ret;
}

static int decon9820_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct decon9820 *d;
	struct drm_device *drm;
	int ret;

	ret = dma_coerce_mask_and_coherent(dev, DMA_BIT_MASK(32));
	if (ret)
		return ret;
	ret = decon9820_zegary(dev);
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

	ret = drm_vblank_init(drm, 1);
	if (ret)
		return ret;
	drm_mode_config_reset(drm);

	/* simpledrm trzyma ten sam framebuffer; od teraz ekran jest nasz. */
	ret = aperture_remove_conflicting_devices(FB_BOOT, FB_BOOT_ROZMIAR,
						  decon9820_driver.name);
	if (ret)
		return dev_err_probe(dev, ret, "nie przejalem framebuffera S-Boota\n");

	platform_set_drvdata(pdev, drm);
	ret = drm_dev_register(drm, 0);
	if (ret)
		return ret;
	drm_client_setup(drm, NULL);
	drm_info(drm, "DECON 9820 na potoku S-Boota, okno %d, %dx%d\n", OKNO, SZER, WYS);
	return 0;
}

static void decon9820_remove(struct platform_device *pdev)
{
	struct drm_device *drm = platform_get_drvdata(pdev);
	struct decon9820 *d = to_d(drm);

	drm_dev_unplug(drm);
	drm_atomic_helper_shutdown(drm);
	/* Zanim zwolnimy bufory: ekran z powrotem na framebuffer S-Boota. */
	decon9820_pokaz(d, FB_BOOT, (d->in_con_boot & IDMA_IMG_FORMAT_MASK) >> 11);
}

static void decon9820_shutdown(struct platform_device *pdev)
{
	drm_atomic_helper_shutdown(platform_get_drvdata(pdev));
}

static struct platform_driver decon9820_platform = {
	.driver = { .name = "decon9820" },
	.probe = decon9820_probe,
	.remove = decon9820_remove,
	.shutdown = decon9820_shutdown,
};

static struct platform_device *decon9820_pdev;

static int __init decon9820_init(void)
{
	int ret = platform_driver_register(&decon9820_platform);

	if (ret)
		return ret;
	decon9820_pdev = platform_device_register_simple("decon9820", -1, NULL, 0);
	if (IS_ERR(decon9820_pdev)) {
		platform_driver_unregister(&decon9820_platform);
		return PTR_ERR(decon9820_pdev);
	}
	return 0;
}

static void __exit decon9820_exit(void)
{
	platform_device_unregister(decon9820_pdev);
	platform_driver_unregister(&decon9820_platform);
}

module_init(decon9820_init);
module_exit(decon9820_exit);

MODULE_DESCRIPTION("Eksperymentalny KMS dla DECON Exynos9820 na potoku S-Boota");
MODULE_LICENSE("GPL");
