// SPDX-License-Identifier: GPL-2.0-only
/*
 * modem_sonda - diagnostyczna sonda domeny modemu (Exynos 9820, s5000ap).
 *
 * Pytania: HW-46 (czy domena jest zasilona) i HW-47 (czy CP_CTRL_S nalezy do
 * swiata bezpiecznego). Cel: zmierzyc stan domeny i przygotowac grunt pod
 * sekwencje wlaczenia z pmucal_cp_exynos9820.h producenta.
 *
 * Adresy (zrodlo: sources/ds/pmucal_cp_exynos9820.h):
 *   PMU 0x15860000, CP_CONFIGURATION +0x3000 bit0, CP_STATUS +0x3004 bit0,
 *   CP_CTRL_S +0x3014 bit3, CP_IN +0x3024 bit4.
 *
 * Bezpieczenstwo:
 *  - czytamy tylko blok PMU (zawsze zasilony);
 *  - skrzynki 0x15920000 NIE DOTYKAMY, dopoki bramka zegarowa nie jest
 *    potwierdzona jako otwarta (ten odczyt juz raz zawiesil ten telefon);
 *  - zapis tylko przez plik "zapisz" i tylko do znanych offsetow domeny CP.
 *
 * Uzycie (debugfs, montowane przez jadro):
 *   insmod modem_sonda.ko
 *   cat /sys/kernel/debug/modem_sonda/rejestry
 *   echo "0x3000 0x1" > /sys/kernel/debug/modem_sonda/zapisz
 *
 * Uwaga na przyszlosc: pierwsza wersja uzywala sysfs (class_create +
 * device_create). Przy otwartym pliku atrybutu rmmod wchodzil w zakleszczenie,
 * bo device_destroy czeka na zwolnienie referencji, a exit zdazyl juz zrobic
 * iounmap. debugfs nie trzyma referencji do modulu, wiec tego problemu nie ma.
 */
#include <linux/debugfs.h>
#include <linux/io.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>

#define PMU_BASE_PA	0x15860000UL
#define PMU_LEN		0x4000

static void __iomem *pmu;
static struct dentry *katalog;
static struct dentry *plik_rejestry;
static struct dentry *plik_zapisz;

struct cp_reg {
	u32 off;
	const char *name;
};

static const struct cp_reg cp_regs[] = {
	{ 0x3000, "CP_CONFIGURATION" },
	{ 0x3004, "CP_STATUS" },
	{ 0x3008, "CP_CTRL" },
	{ 0x3014, "CP_CTRL_S" },
	{ 0x3018, "CP_RESET" },
	{ 0x3024, "CP_IN" },
	{ 0x3028, "CP_OUT" },
};

static int rejestry_show(struct seq_file *s, void *unused)
{
	int i;

	seq_printf(s, "PMU phys 0x%08lx, okno 0x%x\n\n", (unsigned long)PMU_BASE_PA, PMU_LEN);
	for (i = 0; i < ARRAY_SIZE(cp_regs); i++)
		seq_printf(s, "0x%04x  %-18s = 0x%08x\n", cp_regs[i].off,
			   cp_regs[i].name, readl(pmu + cp_regs[i].off));

	seq_puts(s, "\nznaczenie bitow (pmucal_cp_exynos9820.h):\n"
		    "  CP_CONFIGURATION bit0 = 1 wlacza domeny modemu\n"
		    "  CP_STATUS        bit0 = 1 potwierdza zasilenie\n"
		    "  CP_IN            bit4 = 1 potwierdza wejscie\n"
		    "  CP_CTRL_S        bit3 -> zwolnienie resetu (sekwencja producenta)\n");
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

static ssize_t zapisz_write(struct file *file, const char __user *ubuf,
			    size_t count, loff_t *ppos)
{
	char buf[64];
	unsigned int off, val;
	u32 przed, po;
	int i, znany = 0;

	if (count >= sizeof(buf))
		return -EINVAL;
	if (copy_from_user(buf, ubuf, count))
		return -EFAULT;
	buf[count] = '\0';

	if (sscanf(buf, "0x%x 0x%x", &off, &val) != 2) {
		pr_err("modem_sonda: uzycie: echo \"0x3000 0x1\" > zapisz\n");
		return -EINVAL;
	}

	for (i = 0; i < ARRAY_SIZE(cp_regs); i++)
		if (cp_regs[i].off == off)
			znany = 1;
	if (!znany) {
		pr_err("modem_sonda: offset 0x%x nie nalezy do domeny CP\n", off);
		return -EINVAL;
	}

	przed = readl(pmu + off);
	writel(val, pmu + off);
	wmb();
	po = readl(pmu + off);

	pr_info("modem_sonda: ZAPIS 0x%04x: przed=0x%08x wpisano=0x%08x po=0x%08x%s\n",
		off, przed, val, po, (po == val) ? " ZGADZA SIE" : " NIE ZGADZA SIE");

	return count;
}
static const struct file_operations zapisz_fops = {
	.owner = THIS_MODULE,
	.write = zapisz_write,
};

static int __init modem_sonda_init(void)
{
	pmu = ioremap(PMU_BASE_PA, PMU_LEN);
	if (!pmu) {
		pr_err("modem_sonda: ioremap nieudany\n");
		return -ENOMEM;
	}

	katalog = debugfs_create_dir("modem_sonda", NULL);
	if (IS_ERR(katalog))
		return PTR_ERR(katalog);

	debugfs_create_file("rejestry", 0444, katalog, NULL, &rejestry_fops);
	debugfs_create_file("zapisz", 0200, katalog, NULL, &zapisz_fops);

	pr_info("modem_sonda: gotowe. CP_STATUS=0x%08x CP_CONFIG=0x%08x CP_CTRL_S=0x%08x CP_IN=0x%08x\n",
		readl(pmu + 0x3004), readl(pmu + 0x3000),
		readl(pmu + 0x3014), readl(pmu + 0x3024));

	return 0;
}

static void __exit modem_sonda_exit(void)
{
	/* kolejnosc ma znaczenie: najpierw pliki i katalog, na koncu mapowanie */
	debugfs_remove_recursive(katalog);
	katalog = NULL;
	iounmap(pmu);
	pmu = NULL;
	pr_info("modem_sonda: zdjete\n");
}

module_init(modem_sonda_init);
module_exit(modem_sonda_exit);

MODULE_DESCRIPTION("Sonda domeny modemu Exynos 9820 (HW-46, HW-47)");
MODULE_LICENSE("GPL");
