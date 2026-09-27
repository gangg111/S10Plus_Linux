// SPDX-License-Identifier: GPL-2.0
/*
 * Diagnostyka: czy mmap buforow GEM (shmem) w danym procesie wskazuje te
 * same strony fizyczne, co tablica stron bufora (ta, z ktorej jadro buduje
 * mapowanie GPU).  Dla kazdego VMA z drm_gem_shmem_vm_ops porownuje PFN
 * z tablicy stron CPU z page_to_pfn(shmem->pages[i]).  Tylko odczyt.
 * Modul nie zostaje w pamieci (init zwraca -EAGAIN).
 *
 * Uzycie: insmod strony_bo.ko pid=<PID>
 */
#include <drm/drm_gem.h>
#include <drm/drm_gem_shmem_helper.h>
#include <drm/drm_vma_manager.h>
#include <linux/dma-resv.h>
#include <linux/mm.h>
#include <linux/module.h>
#include <linux/pid.h>
#include <linux/sched/mm.h>

static int pid;
module_param(pid, int, 0444);

static int __init strony_bo_init(void)
{
	struct task_struct *t;
	struct mm_struct *mm;
	struct vm_area_struct *vma;
	unsigned long vmy = 0, obecne = 0, zgodne = 0, rozne = 0, bez_stron = 0;
	int zgloszone = 0;

	t = get_pid_task(find_get_pid(pid), PIDTYPE_PID);
	if (!t)
		return -ESRCH;
	mm = get_task_mm(t);
	put_task_struct(t);
	if (!mm)
		return -EINVAL;

	mmap_read_lock(mm);
	{
		VMA_ITERATOR(vmi, mm, 0);

		for_each_vma(vmi, vma) {
			struct drm_gem_object *obj;
			struct drm_gem_shmem_object *shmem;
			unsigned long adr, start_obj;

			if (vma->vm_ops != &drm_gem_shmem_vm_ops)
				continue;
			obj = vma->vm_private_data;
			if (!obj)
				continue;
			shmem = to_drm_gem_shmem_obj(obj);
			vmy++;

			if (dma_resv_lock_interruptible(obj->resv, NULL))
				continue;
			if (!shmem->pages) {
				bez_stron++;
				dma_resv_unlock(obj->resv);
				continue;
			}
			start_obj = drm_vma_node_start(&obj->vma_node);

			for (adr = vma->vm_start; adr < vma->vm_end; adr += PAGE_SIZE) {
				struct follow_pfnmap_args a = { .vma = vma, .address = adr };
				unsigned long idx = vma->vm_pgoff - start_obj +
						    ((adr - vma->vm_start) >> PAGE_SHIFT);
				unsigned long oczek;

				if (idx >= obj->size >> PAGE_SHIFT)
					break;
				if (follow_pfnmap_start(&a))
					continue;	/* strona jeszcze nie zmapowana */
				obecne++;
				oczek = page_to_pfn(shmem->pages[idx]);
				if (a.pfn == oczek) {
					zgodne++;
				} else {
					rozne++;
					if (zgloszone++ < 8)
						pr_info("strony-bo: pid %d obj %p rozmiar %zu va 0x%lx strona %lu: mmap pfn 0x%lx, bufor pfn 0x%lx\n",
							pid, obj, obj->size, adr, idx, a.pfn, oczek);
				}
				follow_pfnmap_end(&a);
			}
			dma_resv_unlock(obj->resv);
		}
	}
	mmap_read_unlock(mm);
	mmput(mm);

	pr_info("strony-bo: pid %d: vma GEM %lu (bez stron %lu), stron zmapowanych %lu, zgodnych %lu, ROZNYCH %lu\n",
		pid, vmy, bez_stron, obecne, zgodne, rozne);
	return -EAGAIN;
}
module_init(strony_bo_init);

MODULE_DESCRIPTION("Porownanie stron mmap i stron buforow GEM shmem");
MODULE_LICENSE("GPL");
