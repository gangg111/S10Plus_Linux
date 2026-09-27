// SPDX-License-Identifier: GPL-2.0
/*
 * Test rozdzielajacy: modul, ktory NIE robi nic poza wypisaniem linii.
 * Jesli przejdzie, ladowanie modulow na tym telefonie jest zdrowe i winne
 * jest to, co robil poprzedni modul, czyli wywolanie SMC.
 */
#include <linux/kernel.h>
#include <linux/module.h>

static int __init sonda_init(void)
{
	pr_info("nic: modul zaladowany i nic nie zrobil\n");

	return -EAGAIN;
}
module_init(sonda_init);

MODULE_DESCRIPTION("Test kontrolny ladowania modulow");
MODULE_LICENSE("GPL");
