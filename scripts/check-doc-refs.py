#!/usr/bin/env python3
"""Sprawdza odsylacze do patchy w dokumentacji.

Numery patchy zmieniaja sie przy kazdym przestawieniu serii, wiec odsylacz
"patches/0016" po jednej przebudowie zaczyna wskazywac zupelnie inny patch.
Ten skrypt wylapuje takie rozjazdy zanim zrobi to recenzent.

Sprawdza dwie rzeczy:
1. Kazda pelna nazwa pliku patcha cytowana w dokumentach naprawde istnieje.
2. Kazdy odsylacz "patches/NNNN" wskazuje ten sam patch co poprzednio. Sluzy do
   tego migawka scripts/golden/doc-refs.txt: para "dokument:linia -> temat patcha".
   Po przenumerowaniu serii odsylacze zaczynaja wskazywac inne patche i bramka
   to lapie, nie zgadujac przy tym po slowach kluczowych (dokumentacja jest po
   polsku, tematy patchy po angielsku, wiec dopasowanie slow dawalo falszywe alarmy).

Tryb --list wypisuje wszystkie odsylacze, --update zapisuje nowa migawke
(wolno tylko wtedy, gdy zmiana numeracji jest zamierzona).

Uzycie: scripts/check-doc-refs.py [--list|--update]
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = sorted(glob.glob(os.path.join(ROOT, 'docs', '*.md'))) + \
    [os.path.join(ROOT, 'README.md')]

REF_FILE = re.compile(r'patches/(\d{4}-[A-Za-z0-9._+-]*\.patch)')
REF_NUM = re.compile(r'patches/(\d{4})(?!-)(?:[^\n)]{0,4}?\(([^)]{3,60})\))?')


def patch_subjects():
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'patches', '*.patch'))):
        num = os.path.basename(p)[:4]
        subj = ''
        with open(p, encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('Subject:'):
                    subj = re.sub(r'^Subject:\s*(\[[^]]*\]\s*)?', '', line).strip()
                    break
        out[num] = (os.path.basename(p), subj)
    return out


def main():
    listing = '--list' in sys.argv
    update = '--update' in sys.argv
    subs = patch_subjects()
    snap_path = os.path.join(ROOT, 'scripts', 'golden', 'doc-refs.txt')
    old = {}
    if os.path.exists(snap_path):
        for line in open(snap_path, encoding='utf-8'):
            if '->' in line:
                k, v = line.rstrip(chr(10)).split(' -> ', 1)
                old[k] = v

    cur = {}
    bad = 0
    for doc in DOCS:
        if not os.path.exists(doc):
            continue
        rel = os.path.relpath(doc, ROOT).replace(os.sep, '/')
        for i, line in enumerate(open(doc, encoding='utf-8', errors='replace'), 1):
            for m in REF_FILE.finditer(line):
                name = m.group(1)
                key = '%s:%d:%s' % (rel, i, name)
                if not os.path.exists(os.path.join(ROOT, 'patches', name)):
                    print('BRAK PLIKU  %s:%d  patches/%s' % (rel, i, name))
                    bad += 1
                    continue
                cur[key] = subs.get(name[:4], ('', ''))[1]
            for m in REF_NUM.finditer(line):
                num = m.group(1)
                key = '%s:%d:%s' % (rel, i, num)
                if num not in subs:
                    print('BRAK NUMERU %s:%d  patches/%s' % (rel, i, num))
                    bad += 1
                    continue
                cur[key] = subs[num][1]

    if listing:
        for k in sorted(cur):
            print('%s -> %s' % (k, cur[k]))

    if update:
        with open(snap_path, 'w', encoding='utf-8', newline=chr(10)) as f:
            for k in sorted(cur):
                f.write('%s -> %s' % (k, cur[k]) + chr(10))
        print('# migawka zapisana: %d odsylaczy' % len(cur))
        return 1 if bad else 0

    if not old:
        print('# brak migawki scripts/golden/doc-refs.txt, uruchom --update')
        return 1

    for k in sorted(cur):
        if k in old and old[k] != cur[k]:
            print('DRYF        %s' % k)
            print('            bylo: %s' % old[k])
            print('            jest: %s' % cur[k])
            bad += 1
    znikly = [k for k in old if k not in cur]
    if znikly:
        print('# odsylaczy, ktorych juz nie ma w dokumentach: %d (to nie blad)' % len(znikly))

    print()
    print('# sprawdzonych odsylaczy: %d, problemow: %d' % (len(cur), bad))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
