#!/usr/bin/env python3
"""Analiza sladu trace-cmd (report) z telefonu: gdzie ucieka czas od dotyku do obrazu.

Uzycie: slad-analiza.py <slad.txt> [pid_kwin] [pid_plasmashell]
"""
import bisect
import collections
import re
import statistics
import sys

LINIA = re.compile(r'^\s*(?P<comm>.+?)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+\S+\s+(?P<ts>\d+\.\d+):\s+(?P<ev>\w+):\s*(?P<rest>.*)$')
SWITCH = re.compile(r'(?P<pc>.+?):(?P<pp>\d+) \[(?P<ppr>-?\d+)\] (?P<ps>\S+) ==> (?P<nc>.+?):(?P<np>\d+) \[(?P<npr>-?\d+)\]')
WAKING = re.compile(r'comm=(?P<c>.+?) pid=(?P<p>\d+) prio=(?P<pr>-?\d+) target_cpu=(?P<t>\d+)')
FREQ = re.compile(r'state=(?P<f>\d+) cpu_id=(?P<c>\d+)')
JOB = re.compile(r'fence=(?P<f>\d+:\d+).*?(?:ring=(?P<r>[\w-]+))?.*?(?:client_id:(?P<cl>\d+))?$')
KLASTER = {0: 'maly', 1: 'maly', 2: 'maly', 3: 'maly', 4: 'sredni', 5: 'sredni', 6: 'duzy', 7: 'duzy'}


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * p))] if v else float('nan')


def opis(v, jedn='ms'):
    if not v:
        return 'brak'
    return f'n={len(v)} med {q(v, 0.5):.2f} p90 {q(v, 0.9):.2f} p99 {q(v, 0.99):.2f} max {max(v):.2f} {jedn}'


def main():
    plik = sys.argv[1]
    pid_kwin = int(sys.argv[2]) if len(sys.argv) > 2 else 781
    pid_shell = int(sys.argv[3]) if len(sys.argv) > 3 else 923
    zd = []
    for l in open(plik, encoding='utf-8', errors='replace'):
        m = LINIA.match(l)
        if m:
            zd.append((float(m['ts']), m['ev'], m['comm'].strip(), int(m['pid']), int(m['cpu']), m['rest']))
    zd.sort(key=lambda z: z[0])
    t_start, t_end = zd[0][0], zd[-1][0]
    print(f'zdarzen {len(zd)}, okno {t_end - t_start:.1f} s')

    # Takt kazdego rdzenia w czasie (cpu_frequency) i nazwy watkow.
    takt = {c: [(t_start, 0)] for c in range(8)}
    nazwa = {}
    for ts, ev, comm, pid, cpu, rest in zd:
        if ev == 'cpu_frequency':
            m = FREQ.search(rest)
            takt[int(m['c'])].append((ts, int(m['f']) // 1000))
        elif ev == 'sched_switch':
            m = SWITCH.search(rest)
            if m:
                nazwa[int(m['np'])] = m['nc']
                nazwa[int(m['pp'])] = m['pc']
    takt_ts = {c: [t for t, _ in takt[c]] for c in takt}

    def mhz(cpu, ts):
        i = bisect.bisect_right(takt_ts[cpu], ts) - 1
        return takt[cpu][max(i, 0)][1]

    # Watki kluczowe: po nazwie i przynaleznosci (pid glowny podany).
    klucz = {}
    for pid, n in nazwa.items():
        if pid == pid_kwin:
            klucz[pid] = 'kwin: glowny'
        elif pid == pid_shell:
            klucz[pid] = 'plasmashell: glowny'
        elif n.startswith('QSGRenderThread'):
            klucz[pid] = 'plasmashell: QSGRenderThread'
        elif n in ('DSI-1', 'libinput-connec'):
            klucz[pid] = f'kwin: {n}'
        elif n.startswith('irq/') and 's6sy' in n:
            klucz[pid] = 'dotyk: watek przerwania'
        elif n.startswith('irq/') and 'panfros' in n:
            klucz[pid] = 'gpu: watek przerwania'

    # Opoznienie planisty: waking -> switch-in, z rdzeniem i taktem startu.
    czeka = {}
    lat = collections.defaultdict(list)
    gdzie = collections.defaultdict(collections.Counter)
    takty = collections.defaultdict(list)
    bieg = collections.defaultdict(list)
    wszedl = {}
    for ts, ev, comm, pid, cpu, rest in zd:
        if ev == 'sched_waking':
            m = WAKING.search(rest)
            p = int(m['p'])
            if p in klucz and p not in czeka:
                czeka[p] = ts
        elif ev == 'sched_switch':
            m = SWITCH.search(rest)
            if not m:
                continue
            nx, pv = int(m['np']), int(m['pp'])
            if pv in wszedl:
                bieg[pv].append((ts - wszedl.pop(pv)) * 1000)
            if nx in klucz:
                wszedl[nx] = ts
                gdzie[nx][KLASTER[cpu]] += 1
                takty[nx].append(mhz(cpu, ts))
                if nx in czeka:
                    lat[nx].append((ts - czeka.pop(nx)) * 1000)

    print('\n== planista: czekanie od wybudzenia do startu, rdzen, takt, dlugosc biegu')
    grupy = collections.defaultdict(list)
    for pid, k in klucz.items():
        grupy[k].append(pid)
    for k in sorted(grupy):
        L, G, T, B = [], collections.Counter(), [], []
        for pid in grupy[k]:
            L += lat[pid]; G += gdzie[pid]; T += takty[pid]; B += bieg[pid]
        suma = sum(G.values()) or 1
        rozkl = ' '.join(f'{c} {100 * G[c] / suma:.0f}%' for c in ('maly', 'sredni', 'duzy'))
        print(f'{k:32s} czekanie {opis(L)}')
        print(f'{"":32s} rdzenie: {rozkl}; takt przy starcie med {q(T, 0.5) if T else 0:.0f} MHz; bieg {opis(B)}')

    # Klatki: commit KWin -> flip -> zatrzask -> vblank.
    commit = [z for z in zd if z[1] == 'commit' and z[2] in ('DSI-1', 'kwin_wayland')]
    flip = [z[0] for z in zd if z[1] == 'flip']
    zatrz = [z for z in zd if z[1] == 'zatrzask']
    vbl = [z[0] for z in zd if z[1] == 'vblank']
    zt = [z[0] for z in zatrz]
    print(f'\n== klatki: commitow KWin {len(commit)}, flipow {len(flip)}, zatrzaskow {len(zt)}, bledow zatrzasku '
          f'{sum(1 for z in zatrz if "ret=0" not in z[5])}')
    fz = [(zt[bisect.bisect_left(zt, f)] - f) * 1000 for f in flip if bisect.bisect_left(zt, f) < len(zt)]
    print('flip -> zatrzask (czekanie na TE):', opis(fz))
    zv = [(vbl[bisect.bisect_left(vbl, z)] - z) * 1000 for z in zt if bisect.bisect_left(vbl, z) < len(vbl)]
    print('zatrzask -> zdarzenie flipa do KWin:', opis(zv))
    odst = [(b - a) * 1000 for a, b in zip(zt, zt[1:]) if b - a < 0.2]
    print('odstep zatrzaskow w ruchu:', opis(odst))

    # GPU: kolejka -> start -> koniec, per klient.
    run, done, que = {}, {}, {}
    klient = {}
    for ts, ev, comm, pid, cpu, rest in zd:
        if ev.startswith('drm_sched_job'):
            m = JOB.search(rest)
            f = m['f'] if m else None
            if not f:
                continue
            if ev == 'drm_sched_job_queue':
                que[f] = ts
                cl = re.search(r'client_id:(\d+)', rest)
                klient[f] = cl.group(1) if cl else '?'
            elif ev == 'drm_sched_job_run':
                run[f] = ts
            elif ev == 'drm_sched_job_done':
                done[f] = ts
    print('\n== GPU (per klient: 3/7 KWin, 14 plasmashell)')
    per = collections.defaultdict(lambda: ([], []))
    for f, t in done.items():
        if f in run and f in que:
            per[klient.get(f, '?')][0].append((run[f] - que[f]) * 1000)
            per[klient.get(f, '?')][1].append((t - run[f]) * 1000)
    for cl, (kol, wyk) in sorted(per.items()):
        print(f'klient {cl}: kolejka {opis(kol)}')
        print(f'{"":10s}wykonanie {opis(wyk)}')

    # Dotyk: kazdy ruch syntetycznego palca (grupy zdarzen z przerwa > 0,3 s).
    dotyk = [z[0] for z in zd if z[1] == 'dotyk']
    ruchy = []
    for t in dotyk:
        if not ruchy or t - ruchy[-1][-1] > 0.3:
            ruchy.append([t])
        else:
            ruchy[-1].append(t)
    zadania_shell = sorted((que[f], done[f]) for f in done if f in que and klient.get(f) == '14')
    kom_t = [c[0] for c in commit]
    wake = collections.defaultdict(list)
    for ts, ev, comm, pid, cpu, rest in zd:
        if ev == 'sched_switch':
            m = SWITCH.search(rest)
            if m:
                wake[int(m['np'])].append(ts)

    def pierwszy(lista, t):
        i = bisect.bisect_left(lista, t)
        return lista[i] if i < len(lista) else None

    print(f'\n== dotyk: ruchow {len(ruchy)}, zdarzen {len(dotyk)}')
    etapy = collections.defaultdict(list)
    for r in ruchy:
        t0 = r[0]
        lib = [p for p, k in klucz.items() if k == 'kwin: libinput-connec']
        t_lib = min((pierwszy(wake[p], t0) or 9e9) for p in lib) if lib else None
        t_kw = pierwszy(wake[pid_kwin], t0)
        t_sh = pierwszy(wake[pid_shell], t0)
        j = bisect.bisect_left([a for a, _ in zadania_shell], t0)
        t_jq, t_jd = zadania_shell[j] if j < len(zadania_shell) else (None, None)
        t_c = pierwszy(kom_t, t_jd) if t_jd else None
        t_z = pierwszy(zt, t_c) if t_c else None
        for nazwa_e, t in (('watek wejscia KWin', t_lib), ('KWin glowny', t_kw), ('plasmashell glowny', t_sh),
                           ('plasmashell zadanie GPU', t_jq), ('GPU gotowe', t_jd), ('commit KWin', t_c),
                           ('zatrzask w DECON', t_z)):
            if t and t < 9e8:
                etapy[nazwa_e].append((t - t0) * 1000)
    for nazwa_e in ('watek wejscia KWin', 'KWin glowny', 'plasmashell glowny', 'plasmashell zadanie GPU',
                    'GPU gotowe', 'commit KWin', 'zatrzask w DECON'):
        print(f'od dotyku do: {nazwa_e:26s} {opis(etapy[nazwa_e])}')

    print('\n== takty klastrow w oknie (czas w MHz)')
    for c in (0, 4, 6):
        czas = collections.Counter()
        pts = takt[c] + [(t_end, 0)]
        for (a, f), (b, _) in zip(pts, pts[1:]):
            czas[f] += b - a
        tot = sum(czas.values()) or 1
        print(f'cpu{c} ({KLASTER[c]}): ' + ', '.join(f'{f}: {100 * s / tot:.0f}%' for f, s in sorted(czas.items()) if s / tot > 0.02))


if __name__ == '__main__':
    main()
