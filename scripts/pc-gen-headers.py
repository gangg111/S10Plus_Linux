#!/usr/bin/env python3
"""Odtwarza naglowki, ktore kbuild generuje w fazie archprepare:
   - arch/arm64/include/generated/asm/*.h        (wrappery generic-y / mandatory-y)
   - arch/arm64/include/generated/uapi/asm/*.h
   - include/generated/uapi/linux/version.h
   - include/generated/utsrelease.h
Bez make, zeby dalo sie kompilowac pojedyncze pliki jadra na hoscie Windows.
"""
import os, re, sys

K = sys.argv[1] if len(sys.argv) > 1 else "sources/linux"


def read_kbuild(path, key):
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*" + key + r"\s*\+=\s*(\S+)", line)
        if m:
            out.append(m.group(1))
    return out


def make_wrappers(gen_dir, names, present_dir, prefix="asm-generic"):
    os.makedirs(gen_dir, exist_ok=True)
    made = 0
    for n in sorted(set(names)):
        if present_dir and os.path.exists(os.path.join(present_dir, n)):
            continue          # arch ma wlasny naglowek, wrapper sie nie generuje
        with open(os.path.join(gen_dir, n), "w", newline="\n") as f:
            f.write("#include <%s/%s>\n" % (prefix, n))
        made += 1
    return made


def main():
    os.chdir(K)

    # 1. przestrzen jadra
    generic = read_kbuild("arch/arm64/include/asm/Kbuild", "generic-y")
    mandatory = read_kbuild("include/asm-generic/Kbuild", "mandatory-y")
    n1 = make_wrappers("arch/arm64/include/generated/asm",
                       generic + mandatory, "arch/arm64/include/asm")

    # 2. uapi
    ugeneric = read_kbuild("arch/arm64/include/uapi/asm/Kbuild", "generic-y")
    umandatory = read_kbuild("include/uapi/asm-generic/Kbuild", "mandatory-y")
    n2 = make_wrappers("arch/arm64/include/generated/uapi/asm",
                       ugeneric + umandatory, "arch/arm64/include/uapi/asm")

    # 3. wersja jadra z Makefile
    mk = open("Makefile", encoding="utf-8", errors="replace").read(4000)
    ver = dict(re.findall(r"^(VERSION|PATCHLEVEL|SUBLEVEL|EXTRAVERSION)[ 	]*=[ 	]*(\S*)",
                          mk, re.M))
    v = int(ver.get("VERSION", 0) or 0)
    p = int(ver.get("PATCHLEVEL", 0) or 0)
    s = int(ver.get("SUBLEVEL", 0) or 0)
    code = (v << 16) + (p << 8) + min(s, 255)
    os.makedirs("include/generated/uapi/linux", exist_ok=True)
    with open("include/generated/uapi/linux/version.h", "w", newline="\n") as f:
        f.write("#define LINUX_VERSION_CODE %d\n" % code)
        f.write("#define KERNEL_VERSION(a,b,c) (((a) << 16) + ((b) << 8) + "
                "((c) > 255 ? 255 : (c)))\n")
        f.write("#define LINUX_VERSION_MAJOR %d\n" % v)
        f.write("#define LINUX_VERSION_PATCHLEVEL %d\n" % p)
        f.write("#define LINUX_VERSION_SUBLEVEL %d\n" % s)
    rel = "%d.%d.%d%s" % (v, p, s, ver.get("EXTRAVERSION", ""))
    with open("include/generated/utsrelease.h", "w", newline="\n") as f:
        f.write('#define UTS_RELEASE "%s"\n' % rel)

    print("wrappery asm: %d, wrappery uapi/asm: %d, wersja: %s (code %d)"
          % (n1, n2, rel, code))


if __name__ == "__main__":
    main()
