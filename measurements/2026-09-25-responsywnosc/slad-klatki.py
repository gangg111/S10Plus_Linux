#!/usr/bin/env python3
"""Klatka po klatce: commit KWin -> zadanie GPU KWin gotowe -> flip w DECON -> zatrzask."""
import bisect, re, sys
L = re.compile(r'^\s*(?P<comm>.+?)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+\S+\s+(?P<ts>\d+\.\d+):\s+(?P<ev>\w+):\s*(?P<rest>.*)$')
zd = []
for l in open(sys.argv[1], encoding='utf-8', errors='replace'):
    m = L.match(l)
    if m:
        zd.append((float(m['ts']), m['ev'], m['comm'].strip(), m['rest']))
zd.sort()
commit = [t for t, e, c, r in zd if e == 'commit' and c in ('DSI-1', 'kwin_wayland')]
flip = [(t, c) for t, e, c, r in zd if e == 'flip']
zatrz = [t for t, e, c, r in zd if e == 'zatrzask']
que, done, kl = {}, {}, {}
for t, e, c, r in zd:
    f = re.search(r'fence=(\d+:\d+)', r)
    if not f:
        continue
    f = f.group(1)
    if e == 'drm_sched_job_queue':
        que[f] = t; m = re.search(r'client_id:(\d+)', r); kl[f] = m.group(1) if m else '?'
    elif e == 'drm_sched_job_done':
        done[f] = t
kwin_done = sorted(done[f] for f in done if kl.get(f) in ('3', '7'))
def q(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(len(v) * p))] if v else float('nan')
def op(v):
    return f'n={len(v)} med {q(v,.5):.2f} p90 {q(v,.9):.2f} p99 {q(v,.99):.2f} max {max(v) if v else 0:.2f} ms'
c_f, g_f, f_z, kto = [], [], [], {}
for t, c in flip:
    i = bisect.bisect_right(commit, t) - 1
    if i >= 0:
        c_f.append((t - commit[i]) * 1000)
    j = bisect.bisect_right(kwin_done, t) - 1
    if j >= 0:
        g_f.append((t - kwin_done[j]) * 1000)
    k = bisect.bisect_left(zatrz, t)
    if k < len(zatrz):
        f_z.append((zatrz[k] - t) * 1000)
    kto[c.split('/')[0]] = kto.get(c.split('/')[0], 0) + 1
print('flip wykonuje:', kto)
print('ostatni commit KWin -> flip:', op(c_f))
print('ostatnie zadanie GPU KWin gotowe -> flip:', op(g_f))
print('flip -> zatrzask:', op(f_z))
odst = [(b - a) * 1000 for a, b in zip(commit, commit[1:])]
print('odstep miedzy commitami KWin:', op([x for x in odst if x < 200]))
print('commity w parach < 2 ms (test + prawdziwy?):', sum(1 for x in odst if x < 2))
