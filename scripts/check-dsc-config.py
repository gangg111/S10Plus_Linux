#!/usr/bin/env python3
"""Sprawdza, że konfiguracja DSC z panel-samsung-s6e3ha9-main.c daje dokładnie ten
PPS, który wysyła downstream.

Odtwarza algorytm z drivers/gpu/drm/display/drm_dsc_helper.c
(drm_dsc_set_const_params + drm_dsc_set_rc_buf_thresh + drm_dsc_setup_rc_params
+ drm_dsc_initial_scale_value + drm_dsc_compute_rc_parameters) dla parametrów
wpisanych w sterowniku i porównuje wynik z bajtami PPS z nagłówka panelu.

Użycie: scripts/check-dsc-config.py [panel_header.h]
"""
import importlib.util, math, os, sys

HDR = sys.argv[1] if len(sys.argv) > 1 else 'sources/ds/s6e3ha9_beyond2_a3_s0_panel.h'
DRV = os.environ.get('S6E3HA9_DRV',
                     'sources/linux/drivers/gpu/drm/panel/panel-samsung-s6e3ha9-main.c')
BLOCK = 3   # beyond2_a3_s0_pps_table[1][0] = 1440x3040, DSU mode 1

# --- to, co sterownik ustawia jawnie -----------------------------------------
cfg = dict(pic_width=1440, pic_height=3040, slice_width=720, slice_height=40,
           slice_count=2, bits_per_component=8, bits_per_pixel=8 << 4,
           line_buf_depth=9, block_pred_enable=True, convert_rgb=True,
           simple_422=False, vbr_enable=False,
           dsc_version_major=1, dsc_version_minor=1)

# --- kontrola: czy sterownik NAPRAWDE ustawia to, co zaklada ten skrypt ------
# Bez tego skrypt sprawdzalby sam siebie: parametry bylyby tylko slownikiem
# obok sterownika, a zmiana w sterowniku przeszlaby niezauwazona.
def _driver_fields(path):
    import re
    src = open(path, encoding='utf-8', errors='replace').read()
    i = src.index('s6e3ha9_init_dsc(')
    body = src[i:src.index('static int s6e3ha9_probe', i)]
    out = {}
    for name, expr in re.findall(r'dsc->(\w+)\s*=\s*([^;]+);', body):
        e = expr.split('/*')[0].strip()
        if e in ('true', 'false'):
            out[name] = (e == 'true')
            continue
        try:
            out[name] = int(eval(e, {'__builtins__': {}}, {}))
        except Exception:
            pass                      # wywolania helperow pomijamy
    if 'DRM_DSC_1_1_PRE_SCR' not in body:
        raise SystemExit('sterownik nie uzywa DRM_DSC_1_1_PRE_SCR, skrypt zaklada inaczej')
    return out

if os.path.exists(DRV):
    drv = _driver_fields(DRV)
    bad_drv = [(k, cfg[k], drv[k]) for k in cfg if k in drv and cfg[k] != drv[k]]
    missing = [k for k in ('pic_width', 'pic_height', 'slice_width', 'slice_height',
                           'slice_count', 'bits_per_component', 'bits_per_pixel',
                           'line_buf_depth') if k not in drv]
    if missing:
        raise SystemExit('sterownik nie ustawia jawnie pol: ' + ', '.join(missing))
    if bad_drv:
        for k, a, b in bad_drv:
            print('ROZJAZD  %-24s skrypt=%s sterownik=%s' % (k, a, b))
        raise SystemExit('konfiguracja DSC w sterowniku rozjechala sie z tym skryptem')
    print('# sterownik %s: %d pol zgodnych z zalozeniami skryptu'
          % (os.path.basename(DRV), len([k for k in cfg if k in drv])))
else:
    raise SystemExit('nie ma %s: bez sterownika ten skrypt sprawdzalby sam siebie' % DRV)

# --- drm_dsc_set_const_params ------------------------------------------------
cfg.update(rc_model_size=8192, rc_edge_factor=6,
           rc_tgt_offset_high=3, rc_tgt_offset_low=3, mux_word_size=48)

# --- drm_dsc_set_rc_buf_thresh (DSC 1.1, wartości w jednostkach PPS) ---------
RC_BUF_THRESH = [t >> 6 for t in (896, 1792, 2688, 3584, 4480, 5376, 6272,
                                  6720, 7168, 7616, 7744, 7872, 8000, 8064)]

# --- drm_dsc_setup_rc_params(DRM_DSC_1_1_PRE_SCR), wpis bpp=8 bpc=8 ---------
cfg.update(initial_xmit_delay=512, first_line_bpg_offset=12, initial_offset=6144,
           flatness_min_qp=3, flatness_max_qp=12,
           rc_quant_incr_limit0=11, rc_quant_incr_limit1=11)
RC_RANGE = [(0, 4, 2), (0, 4, 0), (1, 5, 0), (1, 6, -2), (3, 7, -4), (3, 7, -6),
            (3, 7, -8), (3, 8, -8), (3, 9, -8), (3, 10, -10), (5, 11, -10),
            (5, 12, -12), (5, 13, -12), (7, 13, -12), (13, 15, -12)]

# --- drm_dsc_initial_scale_value --------------------------------------------
cfg['initial_scale_value'] = 8 * cfg['rc_model_size'] // (cfg['rc_model_size'] - cfg['initial_offset'])

# --- drm_dsc_compute_rc_parameters ------------------------------------------
def ceil_div(a, b):
    return -(-a // b)

gpl = ceil_div(cfg['slice_width'], 3)                       # groups_per_line
cfg['slice_chunk_size'] = ceil_div(cfg['slice_width'] * cfg['bits_per_pixel'], 8 * 16)
extra = 3 * (cfg['mux_word_size'] + (4 * cfg['bits_per_component'] + 4) - 2)
slice_bits = 8 * cfg['slice_chunk_size'] * cfg['slice_height']
while extra > 0 and (slice_bits - extra) % cfg['mux_word_size']:
    extra -= 1
if gpl < cfg['initial_scale_value'] - 8:
    cfg['initial_scale_value'] = gpl + 8
cfg['scale_decrement_interval'] = gpl // (cfg['initial_scale_value'] - 8)
cfg['final_offset'] = (cfg['rc_model_size']
                       - (cfg['initial_xmit_delay'] * cfg['bits_per_pixel'] + 8) // 16
                       + extra)
final_scale = (cfg['rc_model_size'] * 8) // (cfg['rc_model_size'] - cfg['final_offset'])
cfg['nfl_bpg_offset'] = ceil_div(cfg['first_line_bpg_offset'] << 11, cfg['slice_height'] - 1)
groups_total = gpl * cfg['slice_height']
cfg['slice_bpg_offset'] = ceil_div((cfg['rc_model_size'] - cfg['initial_offset'] + extra) << 11,
                                   groups_total)
cfg['scale_increment_interval'] = ((cfg['final_offset'] << 11) //
                                   ((cfg['nfl_bpg_offset'] + cfg['slice_bpg_offset']) *
                                    (final_scale - 9))) if final_scale > 9 else 0
rbs_min = (cfg['rc_model_size'] - cfg['initial_offset']
           + ceil_div(cfg['initial_xmit_delay'] * cfg['bits_per_pixel'], 16)
           + gpl * cfg['first_line_bpg_offset'])
hrd_delay = ceil_div(rbs_min * 16, cfg['bits_per_pixel'])
cfg['initial_dec_delay'] = hrd_delay - cfg['initial_xmit_delay']

# --- firmowy PPS -------------------------------------------------------------
spec = importlib.util.spec_from_file_location(
    "dec", os.path.join(os.path.dirname(os.path.abspath(__file__)), "decode-pps.py"))
dec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dec)
label, raw = dec.blocks(open(HDR, encoding='utf8', errors='replace').read())[BLOCK]
v = dec.decode(raw)

def vint(key):
    for k, val in v.items():
        if k.startswith(key + ' '):
            return val
    raise KeyError(key)

CHECKS = [
    ('dsc_version_major', 'dsc_version_major'), ('dsc_version_minor', 'dsc_version_minor'),
    ('pic_width', 'pic_width'), ('pic_height', 'pic_height'),
    ('slice_width', 'slice_width'), ('slice_height', 'slice_height'),
    ('slice_chunk_size', 'chunk_size'),
    ('bits_per_component', 'bits_per_component'), ('line_buf_depth', 'linebuf_depth'),
    ('initial_xmit_delay', 'initial_xmit_delay'), ('initial_dec_delay', 'initial_dec_delay'),
    ('initial_scale_value', 'initial_scale_value'),
    ('scale_increment_interval', 'scale_increment_interval'),
    ('scale_decrement_interval', 'scale_decrement_interval'),
    ('first_line_bpg_offset', 'first_line_bpg_offset'),
    ('nfl_bpg_offset', 'nfl_bpg_offset'), ('slice_bpg_offset', 'slice_bpg_offset'),
    ('initial_offset', 'initial_offset'), ('final_offset', 'final_offset'),
    ('flatness_min_qp', 'flatness_min_qp'), ('flatness_max_qp', 'flatness_max_qp'),
    ('rc_model_size', 'rc_model_size'), ('rc_edge_factor', 'rc_edge_factor'),
    ('rc_quant_incr_limit0', 'rc_quant_incr_limit0'),
    ('rc_quant_incr_limit1', 'rc_quant_incr_limit1'),
    ('rc_tgt_offset_high', 'rc_tgt_offset_high'), ('rc_tgt_offset_low', 'rc_tgt_offset_low'),
]

print(f"# porownanie: sterownik (helpery DRM) vs firmowy PPS\n# {label}\n")
bad = 0
for ours, theirs in CHECKS:
    a, b = cfg[ours], vint(theirs)
    ok = a == b
    bad += not ok
    print(f"  {'OK ' if ok else 'ZLE'} {ours:26s} sterownik={a:<6} PPS={b}")

a, b = RC_BUF_THRESH, vint('rc_buf_thresh')
print(f"  {'OK ' if a == b else 'ZLE'} rc_buf_thresh              {a}")
bad += a != b

a = [(r['min_qp'], r['max_qp'], r['bpg_offset']) for r in vint('rc_range_parameters')]
print(f"  {'OK ' if a == RC_RANGE else 'ZLE'} rc_range_parameters[15]")
bad += a != RC_RANGE

# bpp: PPS trzyma 1/16, sterownik tak samo
a = cfg['bits_per_pixel']
b = int(vint('bits_per_pixel /16').split()[0])
print(f"  {'OK ' if a == b else 'ZLE'} bits_per_pixel             sterownik={a} PPS={b}")
bad += a != b

print(f"\n{'WSZYSTKO ZGODNE' if not bad else str(bad) + ' ROZBIEZNOSCI'}")
sys.exit(1 if bad else 0)
