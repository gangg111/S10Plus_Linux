// SPDX-License-Identifier: GPL-2.0-only
/*
 * modem_sonda2 - sonda blokow, ktorych uzywa sciezka rozruchu modemu na TEJ plycie.
 *
 * Ustalenie z plikow producenta (modem_ctrl_s5000ap.c, s5000ap_on):
 * na tej plycie rozruch idzie sciezka "ap2cp_cfg_ioaddr", czyli zapisem 1 pod
 * 0x15020000, a NIE przez sekwencje PMU (cal_cp_status/cal_cp_init sa w galezi
 * else). Dlatego mierzymy dokladnie te dwa bloki:
 *
 *   0x15020000  ap2cp_cfg_addr   (wyzwalacz rozruchu, z drzewa plyty)
 *   0x15920000  MCU_IPC          (skrzynka, dlugosc 0x180, ISSR0 od +0x80)
 *
 * Sonda jest TYLKO DO ODCZYTU. Zaden zapis nie jest wykonywany, bo zapis pod
 * 0x15020000 uruchamia modem, a to ma byc swiadoma decyzja, nie skutek testu.
 */
#include <linux/debugfs.h>
#include <linux/io.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/seq_file.h>

#define AP2CP_CFG_PA	0x15020000UL
#define AP2CP_CFG_LEN	0x100
#define MCU_IPC_PA	0x15920000UL
#define MCU_IPC_LEN	0x400

static void __iomem *cfg;
static void __iomem *ipc;
static struct dentry *katalog;

struct ipc_reg {
	u32 off;
	const char *name;
};

static const struct ipc_reg ipc_regs[] = {
	{ 0x00, "MCUCTLR" },
	{ 0x08, "INTGR0" },
	{ 0x0c, "INTCR0" },
	{ 0x10, "INTMR0" },
	{ 0x14, "INTSR0" },
	{ 0x18, "INTMSR0" },
	{ 0x1c, "INTGR1" },
	{ 0x20, "INTCR1" },
	{ 0x24, "INTMR1" },
	{ 0x28, "INTSR1" },
	{ 0x2c, "INTMSR1" },
	{ 0x80, "ISSR0 (ap2cp_msg)" },
	{ 0x84, "ISSR1 (cp2ap_msg)" },
	{ 0x88, "ISSR2 (ap2cp_united)" },
	{ 0x8c, "ISSR3 (cp2ap_united)" },
};

static int rejestry_show(struct seq_file *s, void *unused)
{
	int i;
	u32 v;

	seq_puts(s, "== blok wyzwalacza rozruchu, 0x15020000 ==\n");
	if (cfg) {
		v = readl(cfg);
		seq_printf(s, "  0x15020000 = 0x%08x   (ap2cp_cfg: 1 = modem wystartuj)\n", v);
	} else {
		seq_puts(s, "  BRAK MAPOWANIA\n");
	}

	seq_puts(s, "\n== skrzynka MCU_IPC, 0x15920000 ==\n");
	if (ipc) {
		for (i = 0; i < ARRAY_SIZE(ipc_regs); i++)
			seq_printf(s, "  +0x%03x %-22s = 0x%08x\n", ipc_regs[i].off,
				   ipc_regs[i].name, readl(ipc + ipc_regs[i].off));
	} else {
		seq_puts(s, "  BRAK MAPOWANIA\n");
	}

	seq_puts(s, "\nZapis do 0x15020000 uruchamia modem i NIE jest tu wykonywany.\n");
	return 0;
}
static int rejestry_open(struct inode *inode, struct file *file)
{
	return single_open(file, rejestry_show, NULL);
}
static const struct file_operations rejestry_fops = {
	.owner = THIS_MODULE,
	.open = rejestry_open,
	.read = seq_read,
	.llseek = seq_lseek,
	.release = single_release,
};

static int __init modem_sonda2_init(void)
{
	katalog = debugfs_create_dir("modem_sonda2", NULL);
	if (IS_ERR(katalog))
		return PTR_ERR(katalog);

	/* mapujemy osobno, zeby brak jednego bloku nie zabil drugiego */
	cfg = ioremap(AP2CP_CFG_PA, AP2CP_CFG_LEN);
	ipc = ioremap(MCU_IPC_PA, MCU_IPC_LEN);

	pr_info("modem_sonda2: mapy cfg=%p ipc=%p\n", cfg, ipc);

	debugfs_create_file("rejestry", 0444, katalog, NULL, &rejestry_fops);
	return 0;
}

static void __exit modem_sonda2_exit(void)
{
	debugfs_remove_recursive(katalog);
	katalog = NULL;
	if (cfg)
		iounmap(cfg);
	if (ipc)
		iounmap(ipc);
	cfg = NULL;
	ipc = NULL;
	pr_info("modem_sonda2: zdjete\n");
}

module_init(modem_sonda2_init);
module_exit(modem_sonda2_exit);

MODULE_DESCRIPTION("Sonda blokow rozruchu modemu: ap2cp_cfg + MCU_IPC (tylko odczyt)");
MODULE_LICENSE("GPL");
