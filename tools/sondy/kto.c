// SPDX-License-Identifier: GPL-2.0
/*
 * Kto nam odpowiada na SMC: prawdziwy monitor czy cos, co odrzuca wszystko.
 * Same bezpieczne pytania: zadne nie rusza rdzenia ani stanu zasilania.
 */
#include <linux/arm-smccc.h>
#include <linux/kernel.h>
#include <linux/module.h>

struct pyt {
	const char *nazwa;
	unsigned long fn;
	unsigned long a1;
};

static const struct pyt pytania[] = {
	{ "SMCCC_VERSION",        0x80000000, 0 },
	{ "SMCCC_ARCH_FEATURES",  0x80000001, 0x80000000 },
	{ "PSCI_VERSION",         0x84000000, 0 },
	{ "PSCI_FEATURES CPU_ON", 0x8400000a, 0xc4000003 },
	{ "MIGRATE_INFO_TYPE",    0x84000006, 0 },
	{ "SIP_call 0x82000000",  0x82000000, 0 },
};

static int __init sonda_init(void)
{
	struct arm_smccc_res res;
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(pytania); i++) {
		pr_emerg("kto: pytam %s\n", pytania[i].nazwa);
		arm_smccc_smc(pytania[i].fn, pytania[i].a1, 0, 0, 0, 0, 0, 0,
			      &res);
		pr_emerg("kto: %-22s -> 0x%08lx (%ld)\n", pytania[i].nazwa,
			 res.a0, (long)res.a0);
	}

	return -EAGAIN;
}
module_init(sonda_init);

MODULE_DESCRIPTION("Kto odpowiada na SMC");
MODULE_LICENSE("GPL");
