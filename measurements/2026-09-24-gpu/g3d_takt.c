// SPDX-License-Identifier: GPL-2.0
/*
 * Jednorazowa zmiana zegara GPU (domena DVFS G3D w firmware APM) przez
 * zwykle clk_set_rate na zegarze urzadzenia 18500000.gpu, czyli przez
 * sterownik clk-acpm i jego blokade kanalu, a nie z pominieciem jadra.
 * Przyjmuje tylko poziomy z tablicy fvmap tego egzemplarza (100-702 MHz)
 * i nie wyzej niz sufit.  Modul nie zostaje w pamieci: po zmianie init
 * zwraca -EAGAIN.
 *
 * Uzycie: insmod g3d_takt.ko khz=325000
 */
#include <linux/clk.h>
#include <linux/device.h>
#include <linux/module.h>
#include <linux/platform_device.h>

static unsigned int khz;
static unsigned int sufit = 325000;
module_param(khz, uint, 0444);
module_param(sufit, uint, 0444);

static const unsigned int poziomy[] = {
	702000, 676000, 650000, 598000, 572000, 433000,
	377000, 325000, 260000, 200000, 156000, 100000,
};

static int __init g3d_takt_init(void)
{
	struct device *dev;
	struct clk *clk;
	bool znany = false;
	int i, ret;

	for (i = 0; i < ARRAY_SIZE(poziomy); i++)
		znany |= poziomy[i] == khz;
	if (!znany || khz > sufit) {
		pr_err("g3d-takt: %u kHz poza poziomami fvmap albo ponad sufit %u\n", khz, sufit);
		return -EINVAL;
	}

	dev = bus_find_device_by_name(&platform_bus_type, NULL, "18500000.gpu");
	if (!dev)
		return -ENODEV;
	clk = clk_get(dev, NULL);
	if (IS_ERR(clk)) {
		put_device(dev);
		return PTR_ERR(clk);
	}
	pr_info("g3d-takt: przed %lu Hz\n", clk_get_rate(clk));
	ret = clk_set_rate(clk, khz * 1000UL);
	pr_info("g3d-takt: clk_set_rate(%u kHz) = %d, teraz %lu Hz\n",
		khz, ret, clk_get_rate(clk));
	clk_put(clk);
	put_device(dev);
	return ret ? ret : -EAGAIN;
}
module_init(g3d_takt_init);

MODULE_DESCRIPTION("Jednorazowa zmiana zegara G3D przez clk-acpm");
MODULE_LICENSE("GPL");
