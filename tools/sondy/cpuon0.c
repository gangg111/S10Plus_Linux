// SPDX-License-Identifier: GPL-2.0
/*
 * Pytanie rozstrzygajace: CPU_ON na PRAWDZIWY rdzen 1, ale z adresem startu 0,
 * ktory nie jest poprawnym punktem wejscia.  Zgodne z PSCI firmware ma na to
 * odpowiedziec INVALID_ADDRESS (-6) albo INVALID_PARAMS (-2) i niczego nie
 * uruchomic.  Jesli zamiast tego telefon padnie, procedura CPU_ON tego
 * firmware jest nie do uzycia w stanie, w jakim ja zastajemy, i to jest
 * odpowiedz na caly dzisiejszy dzien.
 *
 * Komunikaty ida priorytetem, ktory trafia na panel, bo dziennik zginie razem
 * z telefonem.
 */
#include <linux/arm-smccc.h>
#include <linux/kernel.h>
#include <linux/module.h>

#define PSCI_CPU_ON_FN	0xc4000003

static int __init sonda_init(void)
{
	struct arm_smccc_res res;

	pr_emerg("cpuon0: PRZED CPU_ON rdzen 1, adres startu 0\n");

	arm_smccc_smc(PSCI_CPU_ON_FN, 1, 0, 0, 0, 0, 0, 0, &res);

	pr_emerg("cpuon0: PO, odpowiedz 0x%08lx (%ld)\n", res.a0, (long)res.a0);

	return -EAGAIN;
}
module_init(sonda_init);

MODULE_DESCRIPTION("CPU_ON z bezsensownym adresem startu");
MODULE_LICENSE("GPL");
