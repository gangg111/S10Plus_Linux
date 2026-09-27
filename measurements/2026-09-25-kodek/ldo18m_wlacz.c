// SPDX-License-Identifier: GPL-2.0
/*
 * Krok przed kodekiem: wlacza wylacznie LDO18M (vdd_codec_1p2, DCVDD
 * i CPVDD2 kodeka CS47L93) przez framework regulatorow, czyli przez
 * sterownik S2MPS19 i firmware APM.  Szyna jest wlaczona, dopoki modul jest
 * zaladowany; rmmod ja wylacza.  Niczego poza ta szyna nie dotyka.
 */
#include <linux/delay.h>
#include <linux/module.h>
#include <linux/regulator/consumer.h>

static struct regulator *ldo;

static int __init ldo18m_init(void)
{
	int ret;

	ldo = regulator_get(NULL, "vdd_codec_1p2");
	if (IS_ERR(ldo)) {
		pr_err("ldo18m: brak regulatora: %ld\n", PTR_ERR(ldo));
		return PTR_ERR(ldo);
	}
	pr_info("ldo18m: przed: wlaczony=%d napiecie=%d uV\n",
		regulator_is_enabled(ldo), regulator_get_voltage(ldo));
	ret = regulator_enable(ldo);
	if (ret) {
		pr_err("ldo18m: enable zwrocil %d\n", ret);
		regulator_put(ldo);
		return ret;
	}
	msleep(20);
	pr_info("ldo18m: po: wlaczony=%d napiecie=%d uV\n",
		regulator_is_enabled(ldo), regulator_get_voltage(ldo));
	return 0;
}

static void __exit ldo18m_exit(void)
{
	regulator_disable(ldo);
	pr_info("ldo18m: wylaczony, wlaczony=%d\n", regulator_is_enabled(ldo));
	regulator_put(ldo);
}

module_init(ldo18m_init);
module_exit(ldo18m_exit);
MODULE_LICENSE("GPL");
