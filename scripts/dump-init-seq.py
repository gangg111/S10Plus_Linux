#!/usr/bin/env python3
"""Rozwija tablicę sekwencji panelu Samsunga (panel framework) do listy realnych
komend DCS, opóźnień i kluczy.

Użycie:  scripts/dump-init-seq.py <panel_header.h> <nazwa_cmdtbl>
Przykład: scripts/dump-init-seq.py sources/ds/s6e3ha9_beyond2_a3_s0_panel.h \\
              beyond2_a3_s0_init_cmdtbl

Rozwiązywane makra: DEFINE_STATIC_PACKET, DEFINE_VARIABLE_PACKET + DEFINE_PKTUI,
DEFINE_PANEL_MDELAY/UDELAY, DEFINE_PANEL_KEY.  Pakiety zmienne (sterowane maptbl)
są oznaczane, bo ich bajty zależą od poziomu jasności/temperatury.
"""
import os, re, sys


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    return re.sub(r'//[^\n]*', ' ', text)


def parse(path):
    raw = open(path, encoding='utf8', errors='replace').read()
    src = strip_comments(raw)

    arrays = {}
    # skanowanie z licznikiem nawiasów: tablice bywają jednolinijkowe i wielowymiarowe
    for m in re.finditer(r'\bstatic\s+u8\s+([A-Z0-9_]+)\s*\[[^=]*=\s*\{', src):
        i = m.end() - 1
        depth, j = 0, i
        while j < len(src):
            if src[j] == '{':
                depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        vals = re.findall(r'0x[0-9A-Fa-f]{2}\b', src[i:j])
        if vals:
            arrays[m.group(1)] = vals

    packets, variable, delays, keys = {}, set(), {}, {}
    for m in re.finditer(r'DEFINE_STATIC_PACKET\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*([\w0-9xX]+)\s*\)', src):
        packets[m.group(1)] = (m.group(3), m.group(4), m.group(2))
    for m in re.finditer(r'DEFINE_VARIABLE_PACKET\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*([\w0-9xX]+)\s*\)', src):
        packets[m.group(1)] = (m.group(3), m.group(4), m.group(2))
        variable.add(m.group(1))
    for m in re.finditer(r'DEFINE_PKTUI\(\s*(\w+)\s*,\s*&(\w+)\[(\w+)\]', src):
        variable.add(m.group(1))
        packets.setdefault(m.group(1), (None, '0', None))
    for m in re.finditer(r'DEFINE_PANEL_(M|U)DELAY\(\s*(\w+)\s*,\s*(\d+)\s*\)', src):
        delays[m.group(2)] = (int(m.group(3)), 'ms' if m.group(1) == 'M' else 'us')
    for m in re.finditer(r'DEFINE_PANEL_KEY\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*&PKTINFO\(\s*(\w+)\s*\)', src):
        keys[m.group(1)] = (m.group(2), m.group(3), m.group(4))

    return raw, arrays, packets, variable, delays, keys


def cmdtbl_entries(raw, name):
    """Zwraca [(wpis, gating_ifdef|None)] w kolejności źródłowej."""
    m = re.search(r'static\s+void\s+\*' + re.escape(name) + r'\[\]\s*=\s*\{(.*?)\n\};', raw, re.S)
    if not m:
        sys.exit(f"nie znaleziono tablicy {name}")
    out, stack = [], []
    for line in m.group(1).splitlines():
        t = line.strip()
        if t.startswith('#if'):
            stack.append(t[1:].strip())
            continue
        if t.startswith('#endif'):
            stack and stack.pop()
            continue
        if t.startswith('#else'):
            stack and stack.append('!' + stack.pop())
            continue
        e = re.match(r'&(\w+)\(\s*([\w\[\]]+)\s*\)', t)
        if e:
            out.append((e.group(1), e.group(2), stack[-1] if stack else None))
        elif t.startswith('&'):
            out.append(('RAW', t.rstrip(','), stack[-1] if stack else None))
    return out


def main():
    path, table = sys.argv[1], sys.argv[2]
    raw, arrays, packets, variable, delays, keys = parse(path)

    # W naglowku drukujemy sama nazwe pliku, nie podana sciezke: wynik jest
    # plikiem wzorcowym bramki, a absolutna sciezka przywiazalaby go do jednej
    # maszyny i wywalalaby verify.sh po sklonowaniu repo gdzie indziej.
    print(f"# {table}  ({os.path.basename(path)})\n")
    n = 0
    for kind, arg, gate in cmdtbl_entries(raw, table):
        n += 1
        gate_s = f"   [tylko gdy {gate}]" if gate else ""
        if kind == 'DLYINFO':
            v, unit = delays.get(arg, ('?', ''))
            print(f"{n:3d}. czekaj {v} {unit}{gate_s}")
        elif kind == 'KEYINFO':
            lvl, act, pkt = keys.get(arg, ('?', '?', None))
            b = arrays.get(packets.get(pkt, (None,))[0], [])
            print(f"{n:3d}. klucz {lvl} {act}: {' '.join(b)}{gate_s}")
        elif kind == 'PKTINFO':
            up, off, typ = packets.get(arg, (None, '?', None))
            b = arrays.get(up, [])
            off_s = '' if str(off) in ('0', '0x0') else f"  @gpara {off}"
            var = '  <-- ZMIENNY (maptbl)' if arg in variable else ''
            body = ' '.join(b) if b else '(bajty z maptbl)'
            print(f"{n:3d}. DCS {body}{off_s}{var}{gate_s}")
        else:
            print(f"{n:3d}. {kind} {arg}{gate_s}")


if __name__ == "__main__":
    main()
