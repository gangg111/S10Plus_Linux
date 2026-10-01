// SPDX-License-Identifier: GPL-2.0-only
/*
 * modem_sonda3 - test hipotezy "zamkniete bramki zegarowe APM".
 *
 * Ustalenie: odczyt rejestrow pod 0x15020000 i 0x15920000 konczy sie
 * "synchronous external abort". Producent pod 0x15020000 PISZE, wiec blok musi
 * byc osiagalny - podejrzenie pada na zamkniete bramki zegarowe APM, ktore
 * w naszym drzewie nie maja zadnego konsumenta (clk_summary: enable count = 0,
 * deviceless, no_connection_id).
 *
 * Ten modul:
 *  1) wypisuje, ktore bramki APM uda sie znalezc i w jakim sa stanie,
 *  2) probuje je otworzyc (clk_prepare_enable),
 *  3) ponawia odczyt 0x15020000 i wybrane rejestry skrzynki,
 *  4) na wyjsciu oddaje bramki (clk_disable_unprepare).
 *
 * Kazdy etap raportuje wynik osobno, zeby bylo widac, co przechodzi, a co nie.
 */
#include <linux/clk.h>
#include <linux/clk-provider.h>
#include <linux/debugfs.h>
#include <linux/io.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/seq_file.h>

#define AP2CP_CFG_PA	0x15020000UL
#define MCU_IPC_PA	0x15920000UL

/* bramki APM z mainline: nazwy z clk-exynos9820.c */
static const char *bramki[] = {
	"gout_apm_lhs_axi_d_apm_i_clk",
	"gout_apm_lhs_axi_p_apm_i_clk",
	"gout_apm_lhs_axi_g_dbgcore_i_clk",
	"gout_apm_lhm_axi_p_apm_i_clk",
	"gout_apm_lhm_axi_c_modem_i_clk",
	"gout_apm_xiu_dp_apm_aclk",
	"gout_apm_mailbox_apm_ap_pclk",
	"gout_apm_mailbox_ap_ap_pclk",
	"gout_apm_mailbox_ap_cp_pclk",
	"gout_apm_mailbox_ap_cp_s_pclk",
	"gout_apm_sysreg_apm_pclk",
	"gout_apm_pmu_intr_gen_pclk",
	"gout_apm_intmem_pclk",
	"gout_apm_intmem_aclk",
	"gout_apm_speedy_apm_pclk",
	"gout_apm_wdt_apm_pclk",
};

#define ILE_BRAMEK ARRAY_SIZE(bramki)

static struct clk *uchwyty[ILE_BRAMEK];
static int zalaczone[ILE_BRAMEK];
static void __iomem *cfg, *ipc;
static struct dentry *kat;

static int test_show(struct seq_file *s, void *unused)
{
	int i, ok = 0;
	u32 v;

	seq_puts(s, "== ETAP 1: znalezienie bramek APM ==\n");
	for (i = 0; i < ILE_BRAMEK; i++) {
		uchwyty[i] = clk_get(NULL, bramki[i]);
		if (IS_ERR(uchwyty[i])) {
			seq_printf(s, "  %-42s BRAK\n", bramki[i]);
			uchwyty[i] = NULL;
		} else {
			seq_printf(s, "  %-42s jest, wlaczona=%d\n", bramki[i],
				   __clk_is_enabled(uchwyty[i]));
		}
	}

	seq_puts(s, "\n== ETAP 2: otwarcie bramek ==\n");
	for (i = 0; i < ILE_BRAMEK; i++) {
		if (!uchwyty[i])
			continue;
		if (clk_prepare_enable(uchwyty[i]) == 0) {
			zalaczone[i] = 1;
			ok++;
		} else {
			seq_printf(s, "  %-42s nie udalo sie otworzyc\n", bramki[i]);
		}
	}
	seq_printf(s, "  otwartych bramek: %d\n", ok);

	seq_puts(s, "\n== ETAP 3: odczyt bloku wyzwalacza 0x15020000 ==\n");
	seq_puts(s, "  (uwaga: tu moze byc wyjatek zewnetrzny; jesli tak, telefon\n"
		    "   przezyje, a ja dostane powod w dmesg)\n");
	if (cfg) {
		v = readl(cfg);
		seq_printf(s, "  0x15020000 = 0x%08x  <-- ODCZYT PRZESZEDL\n", v);
	} else {
		seq_puts(s, "  brak mapowania\n");
	}

	seq_puts(s, "\n== ETAP 4: odczyt skrzynki 0x15920000 ==\n");
	if (ipc) {
		v = readl(ipc);
		seq_printf(s, "  MCUCTLR(+0x00) = 0x%08x  <-- ODCZYT PRZESZEDL\n", v);
		v = readl(ipc + 0x14);
		seq_printf(s, "  INTSR0(+0x14)  = 0x%08x\n", v);
	} else {
		seq_puts(s, "  brak mapowania\n");
	}

	return 0;
}
static int test_open(struct inode *i, struct file *f) { return single_open(f, test_show, NULL); }
static const struct file_operations test_fops = {
	.owner = THIS_MODULE, .open = test_open, .read = seq_read,
	.llseek = seq_lseek, .release = single_release,
};

static int __init sonda3_init(void)
{
	kat = debugfs_create_dir("modem_sonda3", NULL);
	cfg = ioremap(AP2CP_CFG_PA, 0x100);
	ipc = ioremap(MCU_IPC_PA, 0x400);
	debugfs_create_file("test", 0444, kat, NULL, &test_fops);
	pr_info("modem_sonda3: gotowe, cfg=%p ipc=%p\n", cfg, ipc);
	return 0;
}

static void __exit sonda3_exit(void)
{
	int i;

	debugfs_remove_recursive(kat);
	for (i = 0; i < ILE_BRAMEK; i++)
		if (zalaczone[i] && uchwyty[i])
			clk_disable_unprepare(uchwyty[i]);
	for (i = 0; i < ILE_BRAMEK; i++)
		if (uchwyty[i])
			clk_put(uchwyty[i]);
	if (cfg) iounmap(cfg);
	if (ipc) iounmap(ipc);
	pr_info("modem_sonda3: zdjete\n");
}

module_init(sonda3_init);
module_exit(sonda3_exit);
MODULE_DESCRIPTION("Test bramek zegarowych APM dla dostepu do blokow modemu");
MODULE_LICENSE("GPL");
