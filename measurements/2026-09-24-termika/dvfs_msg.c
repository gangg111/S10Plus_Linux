// SPDX-License-Identifier: GPL-2.0
/*
 * JEDNA wiadomosc do firmware DVFS na APM: typ 0 FREQ_REQ, 1 FREQ_GET, 4 POLICY_REQ.
 * Czestotliwosc (kHz) musi byc poziomem z tablicy fvmap tej domeny i nie wieksza
 * niz sufit; inaczej modul nic nie wysyla.
 *
 * Kanal 1 (u producenta menedzer DVFS exynos-dm) to kolejka odpytywana
 * o 3 miejscach po 16 B, ktorej jadro nie uzywa.  Format jak u producenta
 * (acpm_dvfs.c exynos_acpm_get_rate): cmd[0] = id domeny | numer sekwencji
 * w bitach 21:16, cmd[1] = 0, cmd[2] = FREQ_GET (1), cmd[3] = 0.
 *
 * Kolejki opisane sa z punktu widzenia firmware: jego RX (ch.rx_*) jest
 * nasza kolejka nadawcza, jego TX (ch.tx_*) nasza odbiorcza.  Przesuniecia
 * odczytane z pamieci APM (measurements/2026-09-24-termika/kanaly-acpm.txt).
 * Dzwonek dla 9820: (1 << kanal) << 16 do INTGR0 (0x08) skrzynki.
 */
#include <linux/delay.h>
#include <linux/io.h>
#include <linux/module.h>

#define SRAM_BAZA	0x02039000
#define SRAM_ROZMIAR	0x30000
#define MBOX_BAZA	0x15900000
#define INTGR0		0x08
#define INITDATA	0x7000
#define OPIS_KANALU	72
#define SEQ		0x2a

static unsigned int kanal = 1;
static unsigned int id = 4;
static unsigned int typ = 1;
static unsigned int khz;
static unsigned int sufit = 1560000;
module_param(kanal, uint, 0444);
module_param(id, uint, 0444);
module_param(typ, uint, 0444);
module_param(khz, uint, 0444);
module_param(sufit, uint, 0444);

/* Czy khz jest poziomem fvmap domeny id (plugin DVFS: fvmap pod 0x29000). */
static bool poziom_fvmap(void __iomem *s, u32 d, u32 f)
{
	u32 fv = 0x29000, h = fv + d * 24, lv = readb(s + h + 1), t = fv + readw(s + h + 20), j;

	if (d >= 15 || lv > 40)
		return false;
	for (j = 0; j < lv; j++)
		if (readl(s + t + j * 8) == f)
			return true;
	return false;
}

static int __init dvfs_get_init(void)
{
	void __iomem *s, *mb;
	u32 ch, c, tx_rear_o, tx_front_o, tx_base_o, rx_rear_o, rx_front_o, rx_base_o;
	u32 qlen, esz, front, rear, nast, cmd[4], odp[4];
	int i, ret = 0;

	s = ioremap(SRAM_BAZA, SRAM_ROZMIAR);
	mb = ioremap(MBOX_BAZA, 0x1000);
	if (!s || !mb) {
		ret = -ENOMEM;
		goto koniec;
	}

	ch = readl(s + INITDATA + 8);
	c = ch + kanal * OPIS_KANALU;
	if (readl(s + c) != kanal || readl(s + c + 68) != 1 ||
	    readl(s + c + 12) != 1) {
		pr_err("dvfs-get: kanal %u nie jest odpytywana kolejka, nic nie wysylam\n", kanal);
		ret = -EINVAL;
		goto koniec;
	}
	/* nasza kolejka nadawcza = RX firmware, odbiorcza = TX firmware */
	tx_rear_o = readl(s + c + 16);
	tx_front_o = readl(s + c + 20);
	tx_base_o = readl(s + c + 24);
	rx_rear_o = readl(s + c + 40);
	rx_front_o = readl(s + c + 44);
	rx_base_o = readl(s + c + 48);
	qlen = readl(s + c + 52);
	esz = readl(s + c + 56);
	if (esz != 16 || !qlen || qlen > 16) {
		ret = -EINVAL;
		goto koniec;
	}

	if (typ != 1 && (typ != 0 && typ != 4)) {
		ret = -EINVAL;
		goto koniec;
	}
	if (typ != 1 && (!poziom_fvmap(s, id, khz) || khz > sufit)) {
		pr_err("dvfs-get: %u kHz nie jest poziomem domeny %u albo przekracza sufit %u, nic nie wysylam\n", khz, id, sufit);
		ret = -EINVAL;
		goto koniec;
	}

	front = readl(s + tx_front_o);
	rear = readl(s + tx_rear_o);
	nast = (front + 1) % qlen;
	pr_info("dvfs-get: kanal %u qlen %u nadawcza front %u rear %u, odbiorcza front %u rear %u\n",
		kanal, qlen, front, rear, readl(s + rx_front_o), readl(s + rx_rear_o));
	if (nast == rear) {
		pr_err("dvfs-get: kolejka pelna, nic nie wysylam\n");
		ret = -EBUSY;
		goto koniec;
	}

	cmd[0] = (id & 0xfff) | (SEQ << 16);
	cmd[1] = typ == 1 ? 0 : khz;
	cmd[2] = typ;
	cmd[3] = 0;
	for (i = 0; i < 4; i++)
		writel(cmd[i], s + tx_base_o + front * esz + i * 4);
	writel(nast, s + tx_front_o);
	writel((1U << kanal) << 16, mb + INTGR0);
	pr_info("dvfs-get: wyslane %08x %08x %08x %08x\n", cmd[0], cmd[1], cmd[2], cmd[3]);

	/* Odpowiedz: do 200 ms, co 1 ms */
	for (i = 0; i < 200; i++) {
		u32 rf = readl(s + rx_front_o), rr = readl(s + rx_rear_o);

		if (rf != rr) {
			int k;

			for (k = 0; k < 4; k++)
				odp[k] = readl(s + rx_base_o + rr * esz + k * 4);
			pr_info("dvfs-get: po %d ms odpowiedz %08x %08x %08x %08x (seq %u, cmd[1] = %u)\n",
				i, odp[0], odp[1], odp[2], odp[3],
				(odp[0] >> 16) & 0x3f, odp[1]);
			if (((odp[0] >> 16) & 0x3f) == SEQ)
				writel((rr + 1) % qlen, s + rx_rear_o);
			goto koniec;
		}
		msleep(1);
	}
	pr_err("dvfs-get: brak odpowiedzi w 200 ms (nadawcza front %u rear %u)\n",
	       readl(s + tx_front_o), readl(s + tx_rear_o));
koniec:
	if (mb)
		iounmap(mb);
	if (s)
		iounmap(s);
	return ret;
}

static void __exit dvfs_get_exit(void)
{
}

module_init(dvfs_get_init);
module_exit(dvfs_get_exit);
MODULE_DESCRIPTION("Jedna wiadomosc FREQ_GET do firmware DVFS Exynos 9820");
MODULE_LICENSE("GPL");
