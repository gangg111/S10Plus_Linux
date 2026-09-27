"""Kto wola settery pol RDMA0 w firmware Calliope i z jakimi argumentami."""
import re
import collections
SETTERY = {
    0xfaad0: 'ENABLE', 0xfab08: 'BUF_TYPE', 0xfab40: 'BUF_UPDATE', 0xfab78: 'FORMAT',
    0xfabac: 'EXPEND', 0xfabe4: 'AUTO_FADE_IN', 0xfac1c: 'FUNC', 0xfac50: 'BURST_LEN',
    0xfac84: 'BIT23', 0xfacbc: 'CTRL1', 0xfacd4: 'BUF_STR', 0xfad08: 'BUF_END',
    0xfad3c: 'BUF_OFFSET', 0xfad74: 'STR_POINT', 0xfada8: 'VOL_FACTOR',
    0xfaddc: 'VOL_CHANGE', 0xfb5b0: 'SBANK_LIMIT',
}
ins = []
for l in open('cd.s'):
    m = re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)', l)
    if m:
        ins.append((int(m.group(1), 16), m.group(3), m.group(4).split(';')[0].split('@')[0].strip()))
idx = {a: i for i, (a, _, _) in enumerate(ins)}
# poczatki funkcji: push {...lr} lub stmdb sp!
starty = [a for a, op, arg in ins if (op == 'push' and 'lr' in arg) or (op.startswith('stmdb') and 'lr' in arg)]
import bisect
def funkcja(a):
    i = bisect.bisect_right(starty, a) - 1
    return starty[i] if i >= 0 else 0
wywolania = collections.defaultdict(list)
for a, op, arg in ins:
    if op in ('bl', 'b', 'blx', 'bleq', 'blne', 'beq', 'bne'):
        m = re.match(r'0x([0-9a-f]+)', arg)
        if m and int(m.group(1), 16) in SETTERY:
            t = int(m.group(1), 16)
            # argumenty: ostatnie mov/movw do r0, r1, r2 przed wywolaniem
            argi = {}
            i = idx[a] - 1
            while i >= 0 and idx[a] - i < 8:
                _, o, x = ins[i]
                mm = re.match(r'(r[0-3]),\s*(.*)', x)
                if o in ('mov', 'movw', 'mvn', 'ldr', 'add', 'sub', 'lsl', 'and', 'orr') and mm and mm.group(1) not in argi:
                    argi[mm.group(1)] = o + ' ' + mm.group(2)
                if o.startswith('b') and o not in ('bic', 'bics', 'bfi'):
                    break
                i -= 1
            wywolania[funkcja(a)].append((a, SETTERY[t], argi.get('r1', '?'), argi.get('r0', '?')))
for f in sorted(wywolania):
    print('funkcja 0x%x:' % f)
    for a, n, r1, r0 in wywolania[f]:
        print('   %x %-12s r0=%-22s r1=%s' % (a, n, r0[:22], r1[:40]))
