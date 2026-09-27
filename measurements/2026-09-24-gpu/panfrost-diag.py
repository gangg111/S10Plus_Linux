#!/usr/bin/env python3
# Diagnostyczna kopia panfrosta: do komunikatu "js fault" dopisuje proces,
# ktory zglosil zadanie, oraz adres lancucha z ioctl.  Tylko do pomiaru.
import io
import sys

d = sys.argv[1]


def podmien(plik, stary, nowy):
    p = d + "/" + plik
    t = io.open(p, encoding="utf-8").read()
    if t.count(stary) != 1:
        sys.exit("%s: wzorzec %r wystepuje %d razy" % (plik, stary[:40], t.count(stary)))
    io.open(p, "w", encoding="utf-8", newline="\n").write(t.replace(stary, nowy))


podmien("panfrost_job.h",
        "struct panfrost_job {\n\tstruct drm_sched_job base;\n",
        "struct panfrost_job {\n\tstruct drm_sched_job base;\n"
        "\tchar diag_comm[16];\n\tpid_t diag_tgid;\n")
podmien("panfrost_drv.c",
        "\tjob->jc = args->jc;\n",
        "\tjob->jc = args->jc;\n"
        "\tget_task_comm(job->diag_comm, current->group_leader);\n"
        "\tjob->diag_tgid = current->tgid;\n")
podmien("panfrost_job.c",
        '\t\tdev_err(pfdev->base.dev, "js fault, js=%d, status=%s, head=0x%x, tail=0x%x",\n'
        "\t\t\tjs, exception_name,\n"
        "\t\t\tjob_read(pfdev, JS_HEAD_LO(js)),\n"
        "\t\t\tjob_read(pfdev, JS_TAIL_LO(js)));\n",
        '\t\tdev_err(pfdev->base.dev, "js fault, js=%d, status=%s, head=0x%x, tail=0x%x, od %s/%d jc=0x%llx as=%d",\n'
        "\t\t\tjs, exception_name,\n"
        "\t\t\tjob_read(pfdev, JS_HEAD_LO(js)),\n"
        "\t\t\tjob_read(pfdev, JS_TAIL_LO(js)),\n"
        "\t\t\tjob->diag_comm, job->diag_tgid, (unsigned long long)job->jc,\n"
        "\t\t\tjob->mmu->as);\n")
if "--jeden-na-slot" in sys.argv:
    podmien("panfrost_job.c",
            "\tif (!panfrost_has_hw_feature(pfdev, HW_FEATURE_JOBCHAIN_DISAMBIGUATION))\n"
            "\t\targs.credit_limit = 1;\n",
            "\t/* DIAG: zawsze jedno zadanie na slot */\n"
            "\targs.credit_limit = 1;\n")
    print("wariant: jedno zadanie na slot")
if "--przedwczesne" in sys.argv:
    # Czy panfrost uznaje zadanie za skonczone, gdy GPU wciaz je wykonuje
    # (JS_STATUS ACTIVE i JS_HEAD = jc) albo gdy czeka ono jeszcze w _NEXT.
    podmien("panfrost_job.c",
            "static void panfrost_jm_handle_done(struct panfrost_device *pfdev,\n"
            "\t\t\t\t    struct panfrost_job *job)\n{\n",
            "static atomic_t diag_done_n = ATOMIC_INIT(0);\n"
            "static atomic_t diag_przed_n = ATOMIC_INIT(0);\n\n"
            "static void panfrost_jm_handle_done(struct panfrost_device *pfdev,\n"
            "\t\t\t\t    struct panfrost_job *job)\n{\n"
            "\t{\n"
            "\t\tint js = panfrost_job_get_slot(job);\n"
            "\t\tu32 st = job_read(pfdev, JS_STATUS(js));\n"
            "\t\tu32 head = job_read(pfdev, JS_HEAD_LO(js));\n"
            "\t\tu32 hnext = job_read(pfdev, JS_HEAD_NEXT_LO(js));\n"
            "\t\tu32 cnext = job_read(pfdev, JS_COMMAND_NEXT(js));\n"
            "\t\tint n = atomic_inc_return(&diag_done_n);\n\n"
            "\t\tif ((st == 0x08 && head == lower_32_bits(job->jc)) ||\n"
            "\t\t    (cnext && hnext == lower_32_bits(job->jc))) {\n"
            "\t\t\tif (atomic_inc_return(&diag_przed_n) <= 20)\n"
            "\t\t\t\tdev_err(pfdev->base.dev, \"diag-przedwczesne: js=%d jc=0x%llx od %s/%d status=0x%x head=0x%x head_next=0x%x cmd_next=0x%x\\n\",\n"
            "\t\t\t\t\tjs, job->jc, job->diag_comm, job->diag_tgid, st, head, hnext, cnext);\n"
            "\t\t}\n"
            "\t\tif (!(n % 5000))\n"
            "\t\t\tdev_info(pfdev->base.dev, \"diag-przedwczesne: zakonczonych %d, przedwczesnych %d\\n\",\n"
            "\t\t\t\t n, atomic_read(&diag_przed_n));\n"
            "\t}\n")
    print("wariant: detektor przedwczesnego zakonczenia")
if "--flush-przed-zadaniem" in sys.argv:
    # Pelne FLUSH_MEM (L2 + TLB) dla AS zadania tuz przed jego startem.
    podmien("panfrost_mmu.c",
            "static void panfrost_mmu_enable(struct panfrost_device *pfdev, struct panfrost_mmu *mmu)\n",
            "void panfrost_mmu_diag_flush(struct panfrost_device *pfdev, struct panfrost_mmu *mmu)\n{\n"
            "\tmmu_hw_do_operation(pfdev, mmu, 0, ~0ULL, AS_COMMAND_FLUSH_MEM);\n}\n\n"
            "static void panfrost_mmu_enable(struct panfrost_device *pfdev, struct panfrost_mmu *mmu)\n")
    podmien("panfrost_mmu.h",
            "int panfrost_mmu_as_get(",
            "void panfrost_mmu_diag_flush(struct panfrost_device *pfdev, struct panfrost_mmu *mmu);\n"
            "int panfrost_mmu_as_get(")
    podmien("panfrost_job.c",
            "\tjob_write(pfdev, JS_HEAD_NEXT_LO(js), lower_32_bits(jc_head));\n",
            "\tpanfrost_mmu_diag_flush(pfdev, job->mmu);\n"
            "\tjob_write(pfdev, JS_HEAD_NEXT_LO(js), lower_32_bits(jc_head));\n")
    print("wariant: FLUSH_MEM przed kazdym zadaniem")
if "--cache" in sys.argv:
    # Przy pierwszych 4 bledach: linia 64 B pod adresem zadania czytana przez
    # cache'owane mapowanie jadra (kmap) i przez mapowanie write-combine
    # (prawda z DRAM).  Rozne tresci = dane utknely w cache CPU.
    podmien("panfrost_job.c",
            "static void panfrost_job_handle_err(struct panfrost_device *pfdev,\n",
            "static atomic_t diag_cache_n = ATOMIC_INIT(0);\n"
            "struct diag_cache {\n\tstruct work_struct w;\n\tstruct panfrost_job *job;\n};\n\n"
            "static void diag_cache_fn(struct work_struct *w)\n{\n"
            "\tstruct diag_cache *z = container_of(w, struct diag_cache, w);\n"
            "\tstruct panfrost_job *job = z->job;\n"
            "\tu64 jc = job->jc_diag;\n"
            "\tu32 i;\n\n"
            "\tfor (i = 0; i < job->bo_count; i++) {\n"
            "\t\tstruct panfrost_gem_mapping *m = job->mappings[i];\n"
            "\t\tu64 start = m->mmnode.start << PAGE_SHIFT;\n"
            "\t\tu64 size = m->mmnode.size << PAGE_SHIFT;\n"
            "\t\tstruct page *pg;\n"
            "\t\tunsigned int off;\n"
            "\t\tu8 a[64], b[64];\n"
            "\t\tvoid *p;\n\n"
            "\t\tif (jc < start || jc >= start + size || !m->obj->base.pages)\n"
            "\t\t\tcontinue;\n"
            "\t\tpg = m->obj->base.pages[(jc - start) >> PAGE_SHIFT];\n"
            "\t\toff = (jc - start) & (PAGE_SIZE - 1) & ~63u;\n"
            "\t\tp = kmap_local_page(pg);\n"
            "\t\tmemcpy(a, p + off, 64);\n"
            "\t\tkunmap_local(p);\n"
            "\t\tp = vmap(&pg, 1, VM_MAP, pgprot_writecombine(PAGE_KERNEL));\n"
            "\t\tif (p) {\n"
            "\t\t\tmemcpy(b, p + off, 64);\n"
            "\t\t\tvunmap(p);\n"
            "\t\t}\n"
            "\t\tpr_err(\"diag-cache: jc=0x%llx map_wc=%d wb_mmap=%d cache: %64phN\\n\",\n"
            "\t\t       jc, m->obj->base.map_wc, m->obj->wb_mmap, a);\n"
            "\t\tpr_err(\"diag-cache: jc=0x%llx               dram:  %64phN\\n\", jc, b);\n"
            "\t\tbreak;\n"
            "\t}\n"
            "\tpanfrost_job_put(job);\n"
            "\tkfree(z);\n}\n\n"
            "static void panfrost_job_handle_err(struct panfrost_device *pfdev,\n")
    podmien("panfrost_job.c",
            "\t\t\tjob->mmu->as);\n",
            "\t\t\tjob->mmu->as);\n"
            "\t\tif (atomic_inc_return(&diag_cache_n) <= 4) {\n"
            "\t\t\tstruct diag_cache *z = kzalloc(sizeof(*z), GFP_ATOMIC);\n\n"
            "\t\t\tif (z) {\n"
            "\t\t\t\tjob->jc_diag = job_read(pfdev, JS_HEAD_LO(js)) |\n"
            "\t\t\t\t\t((u64)job_read(pfdev, JS_HEAD_HI(js)) << 32);\n"
            "\t\t\t\tkref_get(&job->refcount);\n"
            "\t\t\t\tz->job = job;\n"
            "\t\t\t\tINIT_WORK(&z->w, diag_cache_fn);\n"
            "\t\t\t\tschedule_work(&z->w);\n"
            "\t\t\t}\n"
            "\t\t}\n")
    podmien("panfrost_job.h",
            "\tchar diag_comm[16];\n",
            "\tchar diag_comm[16];\n\tu64 jc_diag;\n")
    podmien("panfrost_job.c",
            "#include <linux/delay.h>\n",
            "#include <linux/delay.h>\n#include <linux/highmem.h>\n#include <linux/vmalloc.h>\n")
    print("wariant: porownanie cache i DRAM")
if "--zrzut" in sys.argv:
    # Jeden zrzut devcoredump przy pierwszym bledzie zadania.  Obsluga bledu
    # dziala pod spinlockiem, a zrzut spi, wiec idzie przez kolejke robocza
    # z referencja na zadanie.
    podmien("panfrost_job.c",
            "static void panfrost_job_handle_err(struct panfrost_device *pfdev,\n",
            "static atomic_t diag_zrzuty = ATOMIC_INIT(0);\n"
            "struct diag_zrzut {\n\tstruct work_struct w;\n\tstruct panfrost_job *job;\n};\n\n"
            "static void diag_zrzut_fn(struct work_struct *w)\n{\n"
            "\tstruct diag_zrzut *z = container_of(w, struct diag_zrzut, w);\n\n"
            "\tpanfrost_core_dump(z->job);\n"
            "\tpanfrost_job_put(z->job);\n"
            "\tkfree(z);\n}\n\n"
            "static void panfrost_job_handle_err(struct panfrost_device *pfdev,\n")
    podmien("panfrost_job.c",
            "\t\t\tjob->mmu->as);\n",
            "\t\t\tjob->mmu->as);\n"
            "\t\tif (atomic_inc_return(&diag_zrzuty) == 1) {\n"
            "\t\t\tstruct diag_zrzut *z = kzalloc(sizeof(*z), GFP_ATOMIC);\n\n"
            "\t\t\tif (z) {\n"
            "\t\t\t\tkref_get(&job->refcount);\n"
            "\t\t\t\tz->job = job;\n"
            "\t\t\t\tINIT_WORK(&z->w, diag_zrzut_fn);\n"
            "\t\t\t\tschedule_work(&z->w);\n"
            "\t\t\t}\n"
            "\t\t}\n")
    print("wariant: zrzut przy pierwszym bledzie")
if "--bez-flush-reduction" in sys.argv:
    podmien("panfrost_job.c",
            "\tif (panfrost_has_hw_feature(pfdev, HW_FEATURE_FLUSH_REDUCTION))\n"
            "\t\tcfg |= JS_CONFIG_ENABLE_FLUSH_REDUCTION;\n",
            "\t/* DIAG: bez flush reduction, zawsze czyszczenie na starcie */\n")
    podmien("panfrost_job.c",
            "\tif (panfrost_has_hw_feature(pfdev, HW_FEATURE_FLUSH_REDUCTION))\n"
            "\t\tjob_write(pfdev, JS_FLUSH_ID_NEXT(js), job->flush_id);\n",
            "")
    print("wariant: bez flush reduction")
if "--bez-wb-mmap" in sys.argv:
    podmien("panfrost_gem.c",
            "\tif (bo->wb_mmap)\n\t\treturn false;\n",
            "\t/* DIAG: WB_MMAP ignorowane, zawsze write-combine */\n")
    print("wariant: bez WB_MMAP")
print("latka diagnostyczna nalozona")
