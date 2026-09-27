import re, sys, bisect
L = re.compile(r'^\s*(?P<comm>.+?)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+\S+\s+(?P<ts>\d+\.\d+):\s+(?P<ev>\w+):')
dot, zat = [], []
for l in open(sys.argv[1], encoding='utf-8', errors='replace'):
    m = L.match(l)
    if not m: continue
    if m['ev'] == 'dotyk': dot.append(float(m['ts']))
    elif m['ev'] == 'zatrzask': zat.append(float(m['ts']))
dot.sort(); zat.sort()
starty = [t for i, t in enumerate(dot) if i == 0 or t - dot[i-1] > 0.3]
for a, b in zip(zat, zat[1:]):
    d = (b - a) * 1000
    if 20 < d < 200:
        i = bisect.bisect_right(starty, b) - 1
        od = (b - starty[i]) * 1000 if i >= 0 else -1
        j = bisect.bisect_right(dot, b) - 1
        ost = (b - dot[j]) * 1000 if j >= 0 else -1
        print(f'podwojna klatka {d:.1f} ms: {od:.0f} ms od poczatku gestu, {ost:.0f} ms od ostatniego zdarzenia dotyku')
