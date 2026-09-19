#!/usr/bin/env python3
"""Dekoduje tablice PPS (DSC Picture Parameter Set) z nagłówków downstreamu Samsunga.

Użycie:  scripts/decode-pps.py <plik.h> [--start N] [--end N]
Wypisuje pola PPS wg DSC 1.x (offsety bajtów w nawiasach) dla każdej znalezionej
128-bajtowej tablicy. Czysta transformacja bajtów — zero zgadywania.
"""
import re, sys, json

def blocks(text):
    """Zwraca listę (etykieta, [128 bajtów]) — tylko tablice, których nazwa zawiera PPS."""
    out = []
    # tnij plik na deklaracje tablic:  <typ> NAZWA[...] = { ... };
    for m in re.finditer(r'\b(?:static\s+)?(?:const\s+)?u(?:nsigned\s+char|8)\s+'
                         r'(\w*[Pp][Pp][Ss]\w*)\s*(\[[^=]*)=\s*\{(.*?)\n\};',
                         text, re.S):
        name, body = m.group(1), m.group(3)
        label = None
        cur = []
        for line in body.splitlines():
            c = re.search(r'(?://|/\*)\s*(.*?)(?:\*/)?\s*$', line)
            if c and c.group(1).strip():
                pending = c.group(1).strip()
                if not cur:
                    label = pending
                else:
                    label = label or pending
            # UWAGA: komentarze typu "Slice Info : 720x40" zawierają ciąg "0x40" —
            # bajty wyciągamy dopiero PO usunięciu komentarzy.
            code = re.sub(r'/\*.*?\*/', ' ', line)
            code = re.sub(r'(//|/\*).*$', ' ', code)
            vals = re.findall(r'0x([0-9A-Fa-f]{2})\b', code)
            if vals:
                if not cur and c is None:
                    pass
                cur.extend(int(v, 16) for v in vals)
                while len(cur) >= 128:
                    out.append((f"{name}: {label or ''}".strip(), cur[:128]))
                    cur = cur[128:]
                    label = None
    return out

def u16(b, i):
    return (b[i] << 8) | b[i + 1]

def decode(b):
    bpp = ((b[4] & 0x03) << 8) | b[5]
    d = {
        "dsc_version_major (PPS0[7:4])": b[0] >> 4,
        "dsc_version_minor (PPS0[3:0])": b[0] & 0xF,
        "pps_identifier (PPS1)": b[1],
        "bits_per_component (PPS3[7:4])": b[3] >> 4,
        "linebuf_depth (PPS3[3:0])": b[3] & 0xF,
        "block_pred_enable (PPS4[5])": (b[4] >> 5) & 1,
        "convert_rgb (PPS4[4])": (b[4] >> 4) & 1,
        "simple_422 (PPS4[3])": (b[4] >> 3) & 1,
        "vbr_enable (PPS4[2])": (b[4] >> 2) & 1,
        "bits_per_pixel /16 (PPS4-5)": f"{bpp} -> {bpp/16:g} bpp",
        "pic_height (PPS6-7)": u16(b, 6),
        "pic_width (PPS8-9)": u16(b, 8),
        "slice_height (PPS10-11)": u16(b, 10),
        "slice_width (PPS12-13)": u16(b, 12),
        "chunk_size (PPS14-15)": u16(b, 14),
        "initial_xmit_delay (PPS16-17)": u16(b, 16) & 0x3FF,
        "initial_dec_delay (PPS18-19)": u16(b, 18),
        "initial_scale_value (PPS21)": b[21],
        "scale_increment_interval (PPS22-23)": u16(b, 22),
        "scale_decrement_interval (PPS24-25)": u16(b, 24) & 0xFFF,
        "first_line_bpg_offset (PPS27)": b[27] & 0x1F,
        "nfl_bpg_offset (PPS28-29)": u16(b, 28),
        "slice_bpg_offset (PPS30-31)": u16(b, 30),
        "initial_offset (PPS32-33)": u16(b, 32),
        "final_offset (PPS34-35)": u16(b, 34),
        "flatness_min_qp (PPS36)": b[36],
        "flatness_max_qp (PPS37)": b[37],
        "rc_model_size (PPS38-39)": u16(b, 38),
        "rc_edge_factor (PPS40)": b[40] & 0xF,
        "rc_quant_incr_limit0 (PPS41)": b[41] & 0x1F,
        "rc_quant_incr_limit1 (PPS42)": b[42] & 0x1F,
        "rc_tgt_offset_high (PPS43[7:4])": b[43] >> 4,
        "rc_tgt_offset_low (PPS43[3:0])": b[43] & 0xF,
        "rc_buf_thresh (PPS44-57)": [b[44 + i] for i in range(14)],
    }
    rng = []
    for i in range(15):
        w = u16(b, 58 + 2 * i)
        rng.append({"min_qp": w >> 11, "max_qp": (w >> 6) & 0x1F,
                    "bpg_offset": (w & 0x3F) - 64 if (w & 0x20) else (w & 0x3F)})
    d["rc_range_parameters (PPS58-87)"] = rng
    return d

def main():
    path = sys.argv[1]
    text = open(path, encoding="utf8", errors="replace").read()
    if "--start" in sys.argv:
        i = sys.argv.index("--start"); j = sys.argv.index("--end")
        lines = text.splitlines()
        text = "\n".join(lines[int(sys.argv[i + 1]) - 1:int(sys.argv[j + 1])])
    for n, (label, b) in enumerate(blocks(text)):
        print(f"===== blok {n} — {label or '(bez komentarza)'}")
        for k, v in decode(b).items():
            if k.startswith("rc_range"):
                print(f"  {k}:")
                for m, r in enumerate(v):
                    print(f"    [{m:2d}] min_qp={r['min_qp']:2d} max_qp={r['max_qp']:2d} bpg_offset={r['bpg_offset']:+d}")
            else:
                print(f"  {k}: {v}")
        print()

if __name__ == "__main__":
    main()
