// SPDX-License-Identifier: GPL-2.0
/*
 * Diagnostyka: czy tablice stron MMU GPU (panfrost, io-pgtable) wskazuja te
 * strony, ktore naleza do buforow zmapowanych pod danym adresem, i czy w
 * dziurach miedzy buforami nie zostaly nieaktualne wpisy.  Dla kazdej
 * przestrzeni adresowej z przydzielonym AS przechodzi wezly drm_mm i dla
 * kazdej strony porownuje iova_to_phys() z page_to_phys(pages[i]).
 * Tylko odczyt.  Init zwraca -EAGAIN.
 */
#include <linux/io-pgtable.h>
#include <linux/module.h>
#include <linux/platform_device.h>

#include "panfrost_device.h"
#include "panfrost_gem.h"

#define DZIURA_MAX	(64ULL << 20)

static int __init gpu_strony_init(void)
{
	struct panfrost_device *pfdev;
	struct panfrost_mmu *mmu;
	struct device *dev;
	unsigned long flags;

	dev = bus_find_device_by_name(&platform_bus_type, NULL, "18500000.gpu");
	if (!dev)
		return -ENODEV;
	pfdev = dev_get_drvdata(dev);
	if (!pfdev) {
		put_device(dev);
		return -ENODEV;
	}

	spin_lock_irqsave(&pfdev->as_lock, flags);
	list_for_each_entry(mmu, &pfdev->as_lru_list, list) {
		struct io_pgtable_ops *ops = mmu->pgtbl_ops;
		struct drm_mm_node *node;
		unsigned long map = 0, zgodne = 0, rozne = 0, puste = 0, bez = 0;
		unsigned long dziury_str = 0, dziury_wpisy = 0;
		u64 hole_start, hole_end;
		int zgl = 0;

		spin_lock(&mmu->mm_lock);
		drm_mm_for_each_node(node, &mmu->mm) {
			struct panfrost_gem_mapping *m =
				container_of(node, struct panfrost_gem_mapping, mmnode);
			struct panfrost_gem_object *bo = m->obj;
			u64 va = node->start << PAGE_SHIFT;
			u64 i, n = node->size;

			map++;
			if (!bo->base.pages || bo->is_heap) {
				bez++;
				continue;
			}
			for (i = 0; i < n && i < (bo->base.base.size >> PAGE_SHIFT); i++) {
				phys_addr_t pa = ops->iova_to_phys(ops, va + (i << PAGE_SHIFT));
				phys_addr_t oczek = page_to_phys(bo->base.pages[i]);

				if (!pa)
					puste++;
				else if (pa == oczek)
					zgodne++;
				else {
					rozne++;
					if (zgl++ < 6)
						pr_info("gpu-strony: AS%d va 0x%llx: MMU 0x%llx, bufor 0x%llx (bo %zu B)\n",
							mmu->as, va + (i << PAGE_SHIFT), (u64)pa, (u64)oczek,
							bo->base.base.size);
				}
			}
		}
		drm_mm_for_each_hole(node, &mmu->mm, hole_start, hole_end) {
			u64 a, s = hole_start << PAGE_SHIFT, e = hole_end << PAGE_SHIFT;

			if (e - s > DZIURA_MAX)
				e = s + DZIURA_MAX;
			for (a = s; a < e; a += PAGE_SIZE) {
				dziury_str++;
				if (ops->iova_to_phys(ops, a)) {
					dziury_wpisy++;
					if (zgl++ < 12)
						pr_info("gpu-strony: AS%d dziura va 0x%llx ma wpis -> 0x%llx\n",
							mmu->as, a, (u64)ops->iova_to_phys(ops, a));
				}
			}
		}
		spin_unlock(&mmu->mm_lock);
		pr_info("gpu-strony: AS%d: mapowan %lu (bez stron/heap %lu), stron zgodnych %lu, ROZNYCH %lu, pustych %lu; dziury: sprawdzone %lu stron, z wpisem %lu\n",
			mmu->as, map, bez, zgodne, rozne, puste, dziury_str, dziury_wpisy);
	}
	spin_unlock_irqrestore(&pfdev->as_lock, flags);
	put_device(dev);
	return -EAGAIN;
}
module_init(gpu_strony_init);

MODULE_DESCRIPTION("Porownanie tablic stron MMU GPU ze stronami buforow");
MODULE_LICENSE("GPL");
