// SPDX-License-Identifier: GPL-2.0-only
/*
 * Modul probny: wysyla krotkie komendy DCS 0x28 i 0x29 do panelu przez lacze
 * DSIM0 zostawione przez bootloader, bez przejmowania DSIM ani DECON.
 *
 * Nie tworzy urzadzenia na wezle dsi, bo zwiazanie go odblokowaloby
 * sync_state domeny pd_dpu (dmesg: "sync_state() pending due to
 * 19080000.dsi"), a ta moglaby zgasic caly blok wyswietlania.
 *
 * Uzycie:
 *   insmod s10_dcs.ko                 zrzut rejestrow do dmesg
 *   echo 28 > /sys/module/s10_dcs/parameters/dcs    display off
 *   echo 29 > /sys/module/s10_dcs/parameters/dcs    display on
 *   echo 1 > /sys/module/s10_dcs/parameters/zrzut   ponowny zrzut
 *
 * Zegary APB wlaczamy i przy rmmod ich NIE wylaczamy: przed zaladowaniem
 * bramki byly fizycznie otwarte (clk_summary, kolumna hardware_enable = Y),
 * a wylaczenie zamknelo by je naprawde, czego nikt wczesniej nie robil.
 */
#include <linux/bits.h>
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/of_clk.h>

#define DSIM_MIPI_STATUS	0x18
#define DSIM_DPHY_STATUS	0x1c
#define DSIM_CLK_CTRL		0x20
#define DSIM_CLK_CTRL_CLOCK_SEL		BIT(26)
#define DSIM_CLK_CTRL_NONCONT		BIT(25)
#define DSIM_CLK_CTRL_TX_REQ_HSCLK	BIT(20)
#define DSIM_ESCMODE		0x2c
#define DSIM_CONFIG		0x4c
#define DSIM_INTSRC		0x50
#define DSIM_INTSRC_PH_FIFO_EMPTY	BIT(28)
#define DSIM_INTSRC_PH_FIFO_OVERFLOW	BIT(27)
#define DSIM_INTSRC_INVALID_SFR		BIT(23)
#define DSIM_INTSRC_ABNORMAL_CMD	BIT(22)
#define DSIM_INTSRC_BLEDY	(DSIM_INTSRC_PH_FIFO_OVERFLOW | \
				 DSIM_INTSRC_INVALID_SFR | \
				 DSIM_INTSRC_ABNORMAL_CMD)
#define DSIM_INTMSK		0x54
#define DSIM_PKTHDR		0x58
#define DSIM_PKTHDR_MASKA	GENMASK(24, 0)
#define DSIM_FIFOCTRL		0x68
#define DSIM_FIFOCTRL_EMPTY_PH		BIT(10)
#define DSIM_FIFOCTRL_NUM_PH		GENMASK(21, 16)
#define DSIM_CMD_STATUS		0x8c

#define MIPI_DSI_DCS_SHORT_WRITE	0x05
#define DSIM_TIMEOUT_US		50000

#define DECON_GLOBAL_CONTROL	0x0000
#define DECON_SHADOW_UPDATE_REQ	0x0060
#define DECON_HW_SW_TRIG_CONTROL	0x0070
#define DECON_HW_TE_CNT		0x0078
#define DECON_SHADOW_OFFSET	0x7000

/* Identyfikator zegara APB DECON0 w CMU_DPU (dt-bindings, latka 0011). */
#define CLK_GOUT_DPU_AD_APB_DECON0_PCLKM	5
#define CLK_GOUT_DPU_AD_APB_DECON0_PCLKS	6

static void __iomem *dsim;
static void __iomem *decon;
static DEFINE_MUTEX(dcs_lock);
static bool zablokowany;

static void zrzut_rejestrow(const char *kiedy)
{
	pr_info("s10_dcs: %s: DSIM version=%08x link1=%08x link3=%08x sfr_ctrl=%08x cmd_config=%08x te_ctrl0=%08x te_ctrl1=%08x\n",
		kiedy, readl(dsim + 0x00), readl(dsim + 0x0c), readl(dsim + 0x14),
		readl(dsim + 0x64), readl(dsim + 0x80), readl(dsim + 0x84),
		readl(dsim + 0x88));
	pr_info("s10_dcs: %s: DSIM clk_ctrl=%08x escmode=%08x config=%08x mipi_status=%08x dphy_status=%08x\n",
		kiedy, readl(dsim + DSIM_CLK_CTRL), readl(dsim + DSIM_ESCMODE),
		readl(dsim + DSIM_CONFIG), readl(dsim + DSIM_MIPI_STATUS),
		readl(dsim + DSIM_DPHY_STATUS));
	pr_info("s10_dcs: %s: DSIM intsrc=%08x intmsk=%08x fifoctrl=%08x cmd_status=%08x\n",
		kiedy, readl(dsim + DSIM_INTSRC), readl(dsim + DSIM_INTMSK),
		readl(dsim + DSIM_FIFOCTRL), readl(dsim + DSIM_CMD_STATUS));
	if (!decon)
		return;
	pr_info("s10_dcs: %s: DECON global=%08x shadow_req=%08x trig=%08x trig_aktywny=%08x te_cnt=%08x\n",
		kiedy, readl(decon + DECON_GLOBAL_CONTROL),
		readl(decon + DECON_SHADOW_UPDATE_REQ),
		readl(decon + DECON_HW_SW_TRIG_CONTROL),
		readl(decon + DECON_SHADOW_OFFSET + DECON_HW_SW_TRIG_CONTROL),
		readl(decon + DECON_HW_TE_CNT));
}

static int wyslij_krotka(u8 komenda)
{
	u32 v, bledy;
	int ret;

	if (zablokowany)
		return -EIO;

	v = readl(dsim + DSIM_CLK_CTRL);
	if (!(v & DSIM_CLK_CTRL_CLOCK_SEL)) {
		pr_err("s10_dcs: lacze nie jest uruchomione (clk_ctrl=%08x)\n", v);
		return -ENODEV;
	}

	/* Naglowek wpisujemy tylko do pustej kolejki: zawieszonej nie da sie
	 * zresetowac bez pelnej reinicjalizacji DSIM. */
	ret = readl_poll_timeout(dsim + DSIM_FIFOCTRL, v,
				 (v & DSIM_FIFOCTRL_EMPTY_PH) &&
				 !(v & DSIM_FIFOCTRL_NUM_PH), 100, DSIM_TIMEOUT_US);
	if (ret) {
		pr_err("s10_dcs: kolejka nie jest pusta (fifoctrl=%08x), nic nie wysylam\n", v);
		return ret;
	}

	writel(DSIM_INTSRC_PH_FIFO_EMPTY | DSIM_INTSRC_BLEDY,
	       dsim + DSIM_INTSRC);
	/* Jak dsim_write_mask producenta: bity [31:25] zostaja, jakie byly. */
	v = readl(dsim + DSIM_PKTHDR) & ~DSIM_PKTHDR_MASKA;
	writel(v | MIPI_DSI_DCS_SHORT_WRITE | (u32)komenda << 8,
	       dsim + DSIM_PKTHDR);

	/* Producent czeka na przerwanie SFR_PH_FIFO_EMPTY, a po czasie
	 * rozstrzyga FIFOCTRL; nie wiemy, czy zamaskowane zrodlo w ogole
	 * zatrzaskuje sie w INTSRC, wiec odpytujemy od razu kolejke. */
	ret = readl_poll_timeout(dsim + DSIM_FIFOCTRL, v,
				 (v & DSIM_FIFOCTRL_EMPTY_PH) &&
				 !(v & DSIM_FIFOCTRL_NUM_PH), 100,
				 DSIM_TIMEOUT_US);
	if (ret) {
		zablokowany = true;
		pr_err("s10_dcs: 0x%02x utknelo w kolejce (fifoctrl=%08x), blokuje dalsze wysylki\n",
		       komenda, v);
		zrzut_rejestrow("po zawieszeniu");
		return -ETIMEDOUT;
	}

	v = readl(dsim + DSIM_INTSRC);
	bledy = v & DSIM_INTSRC_BLEDY;
	pr_info("s10_dcs: intsrc po wysylce %08x (b28 %s)\n", v,
		v & DSIM_INTSRC_PH_FIFO_EMPTY ? "ustawiony" : "pusty");
	v = readl(dsim + DSIM_CMD_STATUS);
	if (bledy)
		writel(bledy, dsim + DSIM_INTSRC);
	pr_info("s10_dcs: wyslano 0x%02x, bledy intsrc=%08x cmd_status=%08x\n",
		komenda, bledy, v);
	return bledy ? -EIO : 0;
}

static int dcs_ustaw(const char *val, const struct kernel_param *kp)
{
	u8 komenda;
	int ret;

	ret = kstrtou8(val, 16, &komenda);
	if (ret)
		return ret;
	if (komenda != 0x28 && komenda != 0x29)
		return -EINVAL;

	mutex_lock(&dcs_lock);
	/* Parametr podany przy insmod przychodzi przed s10_dcs_init. */
	ret = dsim ? wyslij_krotka(komenda) : -ENODEV;
	mutex_unlock(&dcs_lock);
	return ret;
}

static const struct kernel_param_ops dcs_ops = {
	.set = dcs_ustaw,
};
module_param_cb(dcs, &dcs_ops, NULL, 0200);
MODULE_PARM_DESC(dcs, "28 = display off, 29 = display on");

static int zrzut_ustaw(const char *val, const struct kernel_param *kp)
{
	int ret = -ENODEV;

	mutex_lock(&dcs_lock);
	if (dsim) {
		zrzut_rejestrow("na zadanie");
		ret = 0;
	}
	mutex_unlock(&dcs_lock);
	return ret;
}

static const struct kernel_param_ops zrzut_ops = {
	.set = zrzut_ustaw,
};
module_param_cb(zrzut, &zrzut_ops, NULL, 0200);
MODULE_PARM_DESC(zrzut, "dowolny zapis zrzuca rejestry DSIM i DECON do dmesg");

static int wlacz_zegar(struct clk *clk, const char *nazwa)
{
	int ret;

	if (IS_ERR(clk)) {
		pr_err("s10_dcs: brak zegara %s: %ld\n", nazwa, PTR_ERR(clk));
		return PTR_ERR(clk);
	}
	ret = clk_prepare_enable(clk);
	if (ret)
		pr_err("s10_dcs: nie wlaczylem zegara %s: %d\n", nazwa, ret);
	return ret;
}

static int __init s10_dcs_init(void)
{
	struct of_phandle_args zegar = { .args_count = 1,
					 .args = { CLK_GOUT_DPU_AD_APB_DECON0_PCLKS } };
	struct clk *clk, *clk_decon = NULL;
	struct device_node *np;
	int ret;

	np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-mipi-dsi");
	if (!np)
		return -ENODEV;

	clk = of_clk_get_by_name(np, "bus");
	ret = wlacz_zegar(clk, "bus DSIM0");
	if (ret)
		goto out_np;

	zegar.np = of_parse_phandle(np, "clocks", 0);
	if (zegar.np) {
		/* Mostek APB DECON0 ma dwie bramki, PCLKS i PCLKM; obie
		 * musza byc otwarte, zanim przeczytamy jego rejestry. */
		clk_decon = of_clk_get_from_provider(&zegar);
		if (wlacz_zegar(clk_decon, "APB DECON0 PCLKS"))
			clk_decon = NULL;
		zegar.args[0] = CLK_GOUT_DPU_AD_APB_DECON0_PCLKM;
		clk = of_clk_get_from_provider(&zegar);
		if (wlacz_zegar(clk, "APB DECON0 PCLKM"))
			clk_decon = NULL;
		of_node_put(zegar.np);
	}

	dsim = of_iomap(np, 0);
	if (!dsim) {
		ret = -ENOMEM;
		goto out_np;
	}

	/* Bez wlasnego zegara APB rejestrow DECON nie czytamy wcale. */
	if (clk_decon) {
		struct device_node *dn;

		dn = of_find_compatible_node(NULL, NULL,
					     "samsung,exynos9820-decon");
		if (dn) {
			decon = of_iomap(dn, 0);
			of_node_put(dn);
		}
	}

	zrzut_rejestrow("po zaladowaniu");
	msleep(1000);
	if (decon)
		pr_info("s10_dcs: licznik TE po 1 s: %08x\n",
			readl(decon + DECON_HW_TE_CNT));
	ret = 0;
out_np:
	of_node_put(np);
	return ret;
}

static void __exit s10_dcs_exit(void)
{
	void __iomem *d, *c;

	mutex_lock(&dcs_lock);
	d = dsim;
	c = decon;
	dsim = NULL;
	decon = NULL;
	mutex_unlock(&dcs_lock);
	if (c)
		iounmap(c);
	iounmap(d);
}

module_init(s10_dcs_init);
module_exit(s10_dcs_exit);
MODULE_DESCRIPTION("Probne DCS display off/on przez DSIM po bootloaderze");
MODULE_LICENSE("GPL");
