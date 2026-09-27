// SPDX-License-Identifier: GPL-2.0
/*
 * Galaxy S10+ (SM-G975F): hub czujnikow i GNSS BCM47752 za SPI17.
 * Punkt wejscia modulu brcm_sensorhub.ko oraz zamienniki infrastruktury
 * Samsunga z drivers/sensorhub/brcm (LineageOS @7d08ec3).
 *
 * Kolejnosc startu odtwarza jadro producenta:
 *   subsys_initcall(sensors_class_init)      -> sensors_class_init()
 *   module_init(bcm_spi_init)                -> bcm_spi_init()
 *     bcm_spi_probe() -> bbd_init() -> ssp_probe()
 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/of.h>
#include <linux/string.h>
#include <linux/err.h>

#include "ssp_port.h"

/* Samsung: drivers/staging/samsung/sec_class.c ("sec") */
static struct class *ssp_sec_class;

struct device *ssp_sec_device_create(void *drvdata, const char *name)
{
	struct device *dev;

	if (!ssp_sec_class)
		return ERR_PTR(-ENODEV);

	dev = device_create(ssp_sec_class, NULL, 0, drvdata, "%s", name);
	if (IS_ERR(dev))
		pr_err("[SSP] %s: device_create(%s) failed %ld\n",
		       __func__, name, PTR_ERR(dev));
	return dev;
}

void ssp_sec_device_destroy(struct device *dev)
{
	if (!IS_ERR_OR_NULL(dev))
		device_unregister(dev);
}

int ssp_port_cmdline_int(const char *key, int *val)
{
	struct device_node *np;
	const char *args, *p;
	size_t klen = strlen(key);
	int ret = -ENOENT;

	np = of_find_node_by_path("/chosen");
	if (!np)
		return -ENODEV;

	if (of_property_read_string(np, "bootargs", &args))
		goto out;

	for (p = args; (p = strstr(p, key)) != NULL; p += klen) {
		if (p != args && p[-1] != ' ')
			continue;
		if (p[klen] != '=')
			continue;
		if (sscanf(p + klen + 1, "%d", val) == 1) {
			ret = 0;
			break;
		}
	}
out:
	of_node_put(np);
	return ret;
}

static int __init brcm_sensorhub_init(void)
{
	int ret;

	ssp_sec_class = class_create("sec");
	if (IS_ERR(ssp_sec_class)) {
		ret = PTR_ERR(ssp_sec_class);
		ssp_sec_class = NULL;
		return ret;
	}

	ret = sensors_class_init();
	if (ret)
		goto err_sec;

	ret = bcm_spi_init();
	if (ret)
		goto err_sensors;

#ifdef CONFIG_BCM_GPS_HOSTWAKE_DRIVER
	ret = gps_hostwake_init();
	if (ret)
		goto err_spi;
#endif
	return 0;

#ifdef CONFIG_BCM_GPS_HOSTWAKE_DRIVER
err_spi:
	bcm_spi_exit();
#endif
err_sensors:
	sensors_class_exit();
err_sec:
	class_destroy(ssp_sec_class);
	ssp_sec_class = NULL;
	return ret;
}

static void __exit brcm_sensorhub_exit(void)
{
#ifdef CONFIG_BCM_GPS_HOSTWAKE_DRIVER
	gps_hostwake_exit();
#endif
	bcm_spi_exit();
	sensors_class_exit();
	class_destroy(ssp_sec_class);
	ssp_sec_class = NULL;
}

module_init(brcm_sensorhub_init);
module_exit(brcm_sensorhub_exit);


MODULE_DESCRIPTION("Samsung SSP + Broadcom BBD sensor hub (BCM47752) for Galaxy S10+");
MODULE_AUTHOR("Samsung Electronics, Broadcom; port: Artur");
MODULE_LICENSE("GPL");
