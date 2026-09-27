// SPDX-License-Identifier: GPL-2.0
/*
 * Jedno jedyne wywolanie SMC: PSCI_VERSION, ktore nie ma argumentow i nie
 * dotyka zadnego rdzenia.  Komunikaty ida priorytetem, ktory trafia na panel,
 * bo jesli telefon na tym padnie, dziennik przepadnie razem z nim, a na
 * ekranie zostanie widac, ze doszlo do "PRZED", a nie doszlo do "PO".
 */
#include <linux/arm-smccc.h>
#include <linux/kernel.h>
#include <linux/module.h>

#define PSCI_AFFINITY_INFO_FN	0xc4000004

static int __init sonda_init(void)
{
	struct arm_smccc_res res;

	pr_emerg("aff: PRZED wywolaniem SMC AFFINITY_INFO dla rdzenia 1\n");

	arm_smccc_smc(PSCI_AFFINITY_INFO_FN, 1, 0, 0, 0, 0, 0, 0, &res);

	pr_emerg("aff: PO wywolaniu, odpowiedz 0x%08lx (%lu.%lu)\n",
		 res.a0, (res.a0 >> 16) & 0xffff, res.a0 & 0xffff);

	return -EAGAIN;
}
module_init(sonda_init);

MODULE_DESCRIPTION("Jedno wywolanie SMC, z komunikatami na panel");
MODULE_LICENSE("GPL");
