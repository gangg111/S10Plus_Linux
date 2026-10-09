// SPDX-License-Identifier: GPL-2.0-only
/*
 * Wspolny start modulu teegris.ko.  W jadrze producenta tzdev byl wbudowany
 * i startowal trzema initcallami: pula watkow (early_initcall), rdzen
 * (module_init) i czas REE (module_init).  Modul ma jeden init, wiec tu sa
 * wywolane w tej samej kolejnosci.  Wyladowania nie ma, jak w jadrze
 * producenta: bezpieczny swiat trzyma pamiec i watki normalnego swiata.
 */
#include <linux/init.h>
#include <linux/irq.h>
#include <linux/irqdomain.h>
#include <linux/module.h>
#include <linux/of.h>
#include <dt-bindings/interrupt-controller/arm-gic.h>

/* Linia SPI kontrolera GIC-400 jako numer IRQ jadra (0 przy bledzie). */
unsigned int teegris_irq_gic(unsigned int spi)
{
	struct irq_fwspec f = {
		.param_count = 3,
		.param = { GIC_SPI, spi, IRQ_TYPE_LEVEL_HIGH },
	};
	unsigned int irq;

	f.fwnode = of_fwnode_handle(of_find_compatible_node(NULL, NULL, "arm,gic-400"));
	if (!f.fwnode)
		return 0;
	irq = irq_create_fwspec_mapping(&f);
	of_node_put(to_of_node(f.fwnode));
	return irq;
}

int tz_kthread_pool_init(void);
int init_tzdev(void);
int tz_ree_time_init(void);

static int __init teegris_init(void)
{
	int ret;

	ret = tz_kthread_pool_init();
	if (ret)
		return ret;
	ret = init_tzdev();
	if (ret)
		return ret;
	return tz_ree_time_init();
}
module_init(teegris_init);

MODULE_DESCRIPTION("TEEgris (Samsung Trusted OS) normal world driver, tzdev port");
MODULE_LICENSE("GPL");
