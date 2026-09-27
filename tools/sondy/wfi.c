// SPDX-License-Identifier: GPL-2.0
/*
 * Czy WFI na rdzeniu wtornym kladzie ten uklad.
 *
 * Rdzen 1 jest juz zasilony i kreci sie na smieciach spod adresu zero, i to
 * telefonowi nie przeszkadza.  Tu startujemy go na wlasnym, dwuinstrukcyjnym
 * kawalku kodu: wfi, a potem skok wstecz na to wfi.  Rdzen nie robi wiec nic
 * poza zasypianiem.
 *
 * Jesli telefon na tym padnie, przyczyna calego dnia jest znaleziona: to nie
 * PSCI, nie zasilanie i nie nasz sterownik, tylko brak podpowiedzi, ktorej
 * firmware oczekuje przy usypianiu rdzenia.  Mainline mowi o tym wprost w
 * drivers/soc/samsung/exynos-pmu.c, przy CPU_INFORM.
 */
#include <linux/arm-smccc.h>
#include <linux/cacheflush.h>
#include <linux/delay.h>
#include <linux/gfp.h>
#include <linux/kernel.h>
#include <linux/module.h>

#define PSCI_CPU_ON_FN	0xc4000003
#define RDZEN		1

#define INSTR_WFI	0xd503207fu	/* wfi          */
#define INSTR_B_WSTECZ	0x17ffffffu	/* b .-4        */

static int __init sonda_init(void)
{
	struct arm_smccc_res res;
	unsigned long strona;
	phys_addr_t fiz;
	u32 *kod;

	strona = __get_free_page(GFP_KERNEL);
	if (!strona)
		return -ENOMEM;

	kod = (u32 *)strona;
	kod[0] = INSTR_WFI;
	kod[1] = INSTR_B_WSTECZ;
	flush_icache_range(strona, strona + 2 * sizeof(u32));

	fiz = virt_to_phys((void *)strona);
	pr_emerg("wfi: kod pod adresem fizycznym 0x%llx\n", (u64)fiz);
	pr_emerg("wfi: PRZED CPU_ON rdzenia %d na petle wfi\n", RDZEN);

	arm_smccc_smc(PSCI_CPU_ON_FN, RDZEN, fiz, 0, 0, 0, 0, 0, &res);

	pr_emerg("wfi: PO, odpowiedz 0x%08lx (%ld)\n", res.a0, (long)res.a0);

	mdelay(500);

	pr_emerg("wfi: pol sekundy pozniej telefon nadal zyje\n");

	return -EAGAIN;
}
module_init(sonda_init);

MODULE_DESCRIPTION("Czy WFI na rdzeniu wtornym kladzie uklad");
MODULE_LICENSE("GPL");
