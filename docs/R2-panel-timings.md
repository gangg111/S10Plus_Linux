# R2 (uzupełnienie) — timingi panelu S6E3HA9 i parametry DSC dla beyond2lte

**Odpowiedź:** Panel pracuje w **trybie komend MIPI**, 1440×3040 @ 60 Hz, 4 linie danych,
**HS clock 898 Mbps** (PLL P=2 M=138 S=2 z 26 MHz), escape clock 20 MHz, porch
hbp/hfp/hsa = 2/2/2 i vbp/vfp/vsa = 15/3/1, a kompresja to **DSC 1.1, 8 bpp (3:1), 8 bpc,
2 slice’y 720×40, 2 enkodery**. Wszystkie liczby pochodzą z węzła DT `s6e3ha9_beyond2`
i z bajtów PPS — te same bajty PPS występują niezależnie w trzech miejscach downstreamu i są
**identyczne co do bajtu**, co jest ich wzajemną weryfikacją.

---

## 1. Łańcuch źródła prawdy

`dsim_0` → `lcd_info = <0x38>` → węzeł `s6e3ha9_beyond2` (phandle 0x38):

- `LineageOS/android_kernel_samsung_exynos9820@7d08ec36:arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_26.dts:8235`
  (`dsim_0 = "/fragment@44:target:0"`)
- `…:exynos9820-beyond2lte_eur_open_26.dts:5074` (`lcd_info = <0x38>`)
- `…:exynos9820-beyond2lte_eur_open_26.dts:690-725` (węzeł `s6e3ha9_beyond2`, `phandle = <0x38>`)

Kolejność pól w triadach porch wzięta z parsera, nie zgadnięta:
`…@7d08ec36:drivers/video/fbdev/exynos/dpu20/dsim_drv.c:1731-1742` —
`h-porch = <hbp hfp hsa>`, `v-porch = <vbp vfp vsa>`.
Znaczenie `mode`: `…:drivers/video/fbdev/exynos/dpu20/panels/decon_lcd.h:12-16`
(`DECON_VIDEO_MODE=0`, `DECON_DP_PSR_MODE=1`, `DECON_MIPI_COMMAND_MODE=2`).

Pełny zrzut węzła i parsera: `build-logs/16-r2-panel-dt-node.log`.

**Uwaga:** stary plik `dpu20/panels/s6e3ha9_lcd_ctrl.c:40-71` też zawiera `struct decon_lcd`
(hs_clk 1100, width/height 70/121, vbp 15), ale jest w `#ifdef FW_TEST` z komentarzem
„This information is moved to DT" (`:37`) — **to nie jest źródło prawdy**, wartości się różnią.

## 2. Timingi (wartości z DT, hex → dec)

| pole DT | hex | dec | znaczenie |
|---|---|---|---|
| `mode` | `0x2` | 2 | MIPI **command mode** (zgodne z `psr_mode = <0x2>` w węźle `decon_f`, `exynos9820.dts:6780`) |
| `resolution` | `0x5a0 0xbe0` | 1440 × 3040 | aktywne piksele |
| `size` | `0x46 0x94` | 70 × 148 mm | fizyczny rozmiar (u-boot DT ma 70 × 147 — drobna rozbieżność, patrz §6) |
| `timing,refresh` | `0x3c` | 60 Hz | |
| `timing,h-porch` | `0x2 0x2 0x2` | hbp=2, hfp=2, hsa=2 | |
| `timing,v-porch` | `0xf 0x3 0x1` | vbp=15, vfp=3, vsa=1 | |
| `timing,dsi-hs-clk` | `0x382` | **898** Mbps/linię | |
| `timing,pmsk` | `0x2 0x8a 0x2 0x0 0xd 0x3 0…` | P=2, M=138, S=2, K=0, mfr=13, mrr=3, reszta 0 | dzielniki PLL D-PHY (+ dither) |
| `timing,dsi-escape-clk` | `0x14` | 20 MHz | |
| `data_lane` | `0x4` | 4 | |
| `mic_en` | `0x0` | 0 | MIC wyłączony (kompresja to DSC, nie MIC) |
| `cmd_underrun_lp_ref` | `0xb3d 0x149e 0x1b52` | 2877 / 5278 / 6994 | per tryb rozdzielczości |
| `type_of_ddi` | `0x0` | 0 | |

**Kontrola spójności PLL** (nie przepisana, policzona): `Fout = M·Fin / (P·2^S) = 138·26 / (2·4)
= 448,5 MHz`, więc DDR → `2·448,5 = 897 Mbps` przy deklarowanych 898 Mbps.
Zgadza się z oscylatorem 26 MHz z `u-boot@c5afa30840d9:…/exynos9820-common.dtsi:168-170`.

**Kontrola przepustowości:** 4 linie × 898 Mbps = 3592 Mbps; przy DSC 8 bpp daje to sufit
449 Mpix/s, a tryb natywny potrzebuje ~265 Mpix/s (patrz §4) — mieści się z zapasem, co jest
typowe dla trybu komend.

## 3. DSC — parametry z DT i zdekodowane PPS

Z DT (`…_26.dts:704-707`): `dsc_en = 1`, `dsc_cnt = 2` (dwa enkodery), `dsc_slice_num = 2`,
`dsc_slice_h = 0x28` = 40.

Tryby wielorozdzielczościowe (`…_26.dts:710-716`): `mres_number = 3`,
`mres_width = 1440/1080/720`, `mres_height = 3040/2280/1520`,
`mres_dsc_width = 720/540/360`, `mres_dsc_height = 40/40/76`, `mres_dsc_en = 1/1/1`.

Zdekodowane PPS trybu natywnego (`scripts/decode-pps.py`, pełny zrzut:
`build-logs/14-pps-decoded-beyond2.txt`, blok 3):

| pole PPS | offset | wartość |
|---|---|---|
| `dsc_version_major/minor` | PPS0 | **1 / 1** (DSC 1.1) |
| `bits_per_component` | PPS3[7:4] | 8 |
| `linebuf_depth` | PPS3[3:0] | 9 |
| `block_pred_enable` | PPS4[5] | 1 |
| `convert_rgb` | PPS4[4] | 1 |
| `simple_422` / `vbr_enable` | PPS4[3]/[2] | 0 / 0 |
| `bits_per_pixel` | PPS4-5 | 128/16 = **8,0 bpp** (kompresja 3:1 z 24 bpp) |
| `pic_width × pic_height` | PPS6-9 | 1440 × 3040 |
| `slice_width × slice_height` | PPS10-13 | **720 × 40** |
| `chunk_size` | PPS14-15 | 720 B ( = slice_width × bpp/8 ✔) |
| `initial_xmit_delay` | PPS16-17 | 512 |
| `initial_dec_delay` | PPS18-19 | 616 |
| `initial_scale_value` | PPS21 | 32 |
| `scale_increment_interval` | PPS22-23 | 1132 |
| `scale_decrement_interval` | PPS24-25 | 10 |
| `first_line_bpg_offset` | PPS27 | 12 |
| `nfl_bpg_offset` | PPS28-29 | 631 |
| `slice_bpg_offset` | PPS30-31 | 489 |
| `initial_offset` | PPS32-33 | 6144 |
| `final_offset` | PPS34-35 | 4336 |
| `flatness_min_qp` / `max_qp` | PPS36-37 | 3 / 12 |
| `rc_model_size` | PPS38-39 | 8192 |
| `rc_edge_factor` | PPS40 | 6 |
| `rc_quant_incr_limit0/1` | PPS41-42 | 11 / 11 |
| `rc_tgt_offset_high/low` | PPS43 | 3 / 3 |
| `rc_buf_thresh[14]` | PPS44-57 | 14, 28, 42, 56, 70, 84, 98, 105, 112, 119, 121, 123, 125, 126 |
| `rc_range_parameters[15]` | PPS58-87 | w logu `build-logs/14-pps-decoded-beyond2.txt` (min_qp/max_qp/bpg_offset dla 15 zakresów) |

Uwaga: `rc_buf_thresh` w PPS jest w jednostkach 1/64 `rc_model_size` — mainline’owe
`drm_dsc_config.rc_buf_thresh[]` trzyma tę samą postać (patrz `drm_dsc_pps_payload_pack()`),
więc bajty przenoszą się 1:1.

### Pozostałe tryby DSU (kompresja włączona w każdym)

| tryb | rozdz. | slice | `initial_dec_delay` | `scale_incr` | `nfl_bpg` | `slice_bpg` |
|---|---|---|---|---|---|---|
| 1 (natywny) | 1440×3040 | 720×40 | 616 | 1132 | 631 | 489 |
| 2 | 1080×2280 | 540×40 | 526 | 989 | 631 | 651 |
| 3 | 720×1520 | 360×76 | 436 | 1506 | 328 | 514 |

## 4. Gotowe wartości do `drm_display_mode` (tryb natywny)

Z porch DT, wg konwencji DRM (`hsync_start = hdisplay + hfp` itd.):

```
hdisplay 1440   hsync_start 1442   hsync_end 1444   htotal 1446
vdisplay 3040   vsync_start 3043   vsync_end 3044   vtotal 3059
clock = 1446 * 3059 * 60 / 1000 = 265399 kHz   (~265,4 MHz)
width_mm 70   height_mm 148   flags: MIPI command mode (DSI_MODE_VIDEO nie ustawiać)
```

## 5. Weryfikacja: te same bajty PPS w trzech miejscach

`scripts/decode-pps.py` + porównanie bajt-po-bajcie (log `build-logs/17-pps-crosscheck.log`):

| źródło | ścieżka | wynik |
|---|---|---|
| framework panelu (używany przez beyond2) | `drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_beyond2_a3_s0_panel.h:452-454` (`beyond2_a3_s0_pps_table[1][0]`) | ✔ |
| ten sam plik, druga tablica | `…:719` (`BEYOND2_A3_S0_PPS`, „WQHD : 1440x3040") | **identyczne** |
| stary stos dpu20 | `drivers/video/fbdev/exynos/dpu20/panels/s6e3ha9_param.h:31` (`SEQ_PPS_SLICE2`) i `:152-171` (`PPS_TABLE[0]`) | **identyczne** |

**Rozbieżność, o której trzeba wiedzieć:** dla trybów 2 i 3 stary `s6e3ha9_param.h` ma
slice 540×**30** i 360×**74**, a framework panelu (i DT `mres_dsc_height = 40/40/76`) —
540×**40** i 360×**76**. Wiążący jest framework panelu + DT; `s6e3ha9_param.h` to martwa
ścieżka dla tego modelu.

Uwaga metodyczna: dekoder najpierw usuwa komentarze, bo napisy typu `Slice Info : 720x40`
zawierają ciąg `0x40` i naiwny grep po `0x..` przesuwa całą tablicę o bajt (błąd wykryty
i naprawiony w trakcie — `scripts/decode-pps.py`, komentarz przy `re.sub`).

## 6. Czego nadal nie ustalono

- **Wysokość ekranu w mm**: DT downstreamu mówi 148, DT z portu mainline (u-boot) 147.
  Różnica bez znaczenia dla obrazu, ale do rozstrzygnięcia przy pisaniu drivera panelu
  (dane katalogowe modułu AMB644WQ01 — nie sprawdzane).
- ~~**Sekwencja TE / tearing**~~ — **ustalone**, patrz §10: beyond2 wysyła własny pakiet
  `B9 01 B0 E1 09 …` (wariant PLL_SLEEP, `CONFIG_EXYNOS_PLL_SLEEP=y`), TE on = `35 00`.
  Otwarte zostaje, skąd Samsung wziął dokładnie 3041 linii (reguła kodowania jest pewna).
- ~~**FFC**~~ — **rozwiązane**, patrz §8: dla naszego zegara pakiet stockowy jest właściwy, a na
  wypadek zmiany zegara wyprowadzona jest reguła z tablicy dynamicznej tego samego DDI (odtwarza
  4/4 punkty referencyjne co do bitu). Otwarte: skąd bierze się 7 LSB różnicy na wariancie
  5-bajtowym (brak drugiego punktu pomiarowego w tym wariancie).
- ~~Parametry D-PHY poza PMS~~ — **wyciągnięte**, patrz §7. Otwarta zostaje **jednostka**
  liczników czasu D-PHY (patrz ostrzeżenie w §7.2) — do rozstrzygnięcia pomiarem albo dokumentacją
  PHY; nie ma jej w źródłach downstreamu.

## 7. D-PHY — wartości i sposób programowania

Źródło: `LineageOS/android_kernel_samsung_exynos9820@7d08ec36:drivers/video/fbdev/exynos/dpu20/cal_9820/dsim_reg.c`
(mapa rejestrów: `…/cal_9820/regs-dsim.h`). Zrzut dowodowy: `build-logs/18-dphy-9820.log`.

### 7.1 Zegary wyprowadzone przez sterownik (arytmetyka całkowitoliczbowa u32!)

`dsim_reg.c:1826-1846`:

```
word_clk = hs_clk / 16            = 898 / 16 = 56 MHz
esc_div  = word_clk / esc_clk_req = 56 / 20 = 2 -> (56/2 = 28) > 20 -> esc_div = 3
esc_clk  = word_clk / esc_div     = 56 / 3  = 18 MHz
```

**Gotcha:** DT prosi o 20 MHz, ale sprzęt dostaje **18 MHz** — i to ta poprawiona wartość idzie
dalej do wyboru `b_dphyctl`. Sterownik mainline musi powtórzyć tę samą arytmetykę, inaczej wyjdzie
inny ULPS-exit.

`hs_clk = 898 < 1500` → `hsmode = 1` (`dsim_reg.c:1852-1853`) → `HSTX_CLK_SEL = 1`,
kalibracja skew **wyłączona** (`SKEWCAL_EN = 0`, `dsim_reg.c:391-399`).

### 7.2 Wiersz tablicy `dphy_timing` dla naszego łącza

Reguła wyboru (`dsim_reg.c:1608-1631`): iteracja od końca tablicy, wybierany jest **najmniejszy
`bps ≥ hs_clk`**. Tablica ma 201 wierszy, 2500 → 500 Mbps co 10. Dla `hs_clk = 898` → wiersz **900**
(`dsim_reg.c:259`):

| pole (wg komentarza `dsim_reg.c:96-98`) | wartość | rejestr | offset | bity |
|---|---|---|---|---|
| `clk_prepare` | **35** | `DSIM_PHY_MC_TIME_CON1` | 0x0334 | [7:0] |
| `clk_zero` | **14** | `DSIM_PHY_MC_TIME_CON1` | 0x0334 | [15:8] |
| `clk_post` | **3** | `DSIM_PHY_MC_TIME_CON3` | 0x033C | [7:0] |
| `clk_trail` | **56** | `DSIM_PHY_MC_TIME_CON2` | 0x0338 | [7:0] |
| `hs_prepare` | **36** | `DSIM_PHY_MD_TIME_CON1(n)` | 0x0434 + 0x100·n | [7:0] |
| `hs_zero` | **5** | `DSIM_PHY_MD_TIME_CON1(n)` | 0x0434 + 0x100·n | [15:8] |
| `hs_trail` | **50** | `DSIM_PHY_MD_TIME_CON2(n)` | 0x0438 + 0x100·n | [7:0] |
| `lpx` | **26** | `MC_TIME_CON0` 0x0330 / `MD_TIME_CON0(n)` 0x0430+0x100·n | | [11:4] |
| `hs_exit` | **5** | `MC_TIME_CON2` 0x0338 / `MD_TIME_CON2(n)` 0x0438+0x100·n | | [15:8] |
| `b_dphyctl` (ULPS exit) | **0x1C2 = 450** (esc 18 MHz → `b_dphyctl[11]`, `dsim_reg.c:302-306`) | `MC_TIME_CON4` 0x0340 / `MD_TIME_CON4(n)` 0x0440+0x100·n | | [9:0] |

Wiersze sąsiednie dla kontroli, że nie ma pomyłki o jeden:
`{910, 36, 14, 3, 57, 36, 5, 50, 27, 5}` (`:258`), `{890, 35, 14, 3, 56, 36, 5, 49, 26, 5}` (`:260`).

Stałe wpisywane niezależnie od zegara (`dsim_reg.c:463-476`): `TTA_GET = 3`, `TTA_GO = 0`,
`TLP_EXIT_SKEW = 0`, `TLP_ENTRY_SKEW = 0`, dla każdej z 4 linii danych.

**OSTRZEŻENIE — nie przeliczaj tych liczb na nanosekundy.** Jednostka liczników nie jest w źródle
udokumentowana, a próba kontroli się **nie zgadza**: przy założeniu jednostki = 1 UI wiersz 900 daje
`clk_prepare` = 35 × 1,11 ns = 38,9 ns (mieści się w spec 38–95 ns), ale ten sam wiersz daje
`clk_zero` = 15,6 ns przy minimum 262 ns ze specyfikacji MIPI, a wiersz 2500 daje `clk_prepare`
= 4,8 ns. Sam Samsung oznacza tablicę komentarzem „below table have to be changed to meet MK DPHY
spec" (`dsim_reg.c:94`). Wniosek do przeniesienia do mainline: **wziąć wiersz 900 jako liczby
surowe**, a interpretację jednostek rozstrzygnąć pomiarowo albo z dokumentacji PHY — nie z reguły
kciuka.

### 7.3 Bloki stałych PHY wpisywane przy starcie

Adresy: PHY „M4S0" = `phy_regs` = **0x19161000** (0x800) — tu idą `PLL_CON`, `MC_*`, `MD_*`;
PHY „M4S4 top" = `phy_regs_ex` = **0x19160000** (0x100) — tu idzie `BIAS_CON`
(`dsim.h:409-420`, mapowanie zasobów `dsim_drv.c:2371-2395`, węzeł DT `exynos9820.dts:6745-6747`).

| blok | wartości | cytat |
|---|---|---|
| `DSIM_PHY_BIAS_CON[5]` | `0x10, 0x110, 0x3223, 0x0, 0x0` | `dsim_reg.c:45-51` |
| `DSIM_PHY_PLL_CON[9]` | `0x0 ×5, 0x500, 0x8E, 0x1450, 0xA28` | `dsim_reg.c:53-65` |
| `DSIM_PHY_MC_GNR_CON[2]` | `0x0, 0x1450` | `dsim_reg.c:67-70` |
| `DSIM_PHY_MC_ANA_CON[3]` | `0x7033, 0x0, 0x2` (EDGE_CON[14:12] = 3'b111 dla D-PHY) | `dsim_reg.c:71-78` |
| `DSIM_PHY_MD_GNR_CON[2]` | `0x0, 0x1450` | `dsim_reg.c:81-84` |
| `DSIM_PHY_MD_ANA_CON[4]` | `0x7033, 0x0, 0x0, 0x0` | `dsim_reg.c:85-90` |

Liczniki PLL:

- `pll_lock_cnt = PLL_LOCK_CNT_MULT × P = 500 × 2 = **1000**` (`dsim_reg.c:41-43, 1903`)
- `DSIM_PLL_STABLE_TIME = 0x682A` (`dsim_reg.c:24`)
- `wclk_buf_sft_cnt = 3` (`dsim_reg.c:1893`, funkcja `:350`)
- freq-hopping / PLL sleep (tylko command mode): `pll_stable_cnt = PLL_SLEEP_CNT_MULT × P = 450 × 2
  = 900` (`dsim_reg.c:28, 2556-2558`)

## 8. FFC (DCS 0xC5) — czy trzeba przeliczać dla naszego zegara

**Krótka odpowiedź: nie.** Nasz zegar **jest** zegarem stockowym (898 Mbps), więc stockowy pakiet
FFC jest już dostrojony i przenosi się do mainline’a bez zmian:

```
0xC5, 0x0D, 0x10, 0xB4, 0x3E, 0x01
```

(`…@7d08ec36:drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_beyond2_a3_s0_panel.h:804-807`)

Identyczne bajty mają beyond1 (`…_beyond1_a3_s0_panel.h:798-801`) i beyondX
(`…_beyondx_a3_s0_panel.h:819-822`) — wszystkie trzy pracują na 898 Mbps
(`timing,dsi-hs-clk = <0x382>` w węzłach `s6e3ha9_beyond1/beyond2/beyondx`).
FFC leci w sekwencji init **pod kluczem poziomu 3** (`0xFC 0x5A 0x5A`, `…_beyond2_a3_s0_panel.h:691`),
między `level3_key_enable` a `level3_key_disable` (`:1393-1395`).

### 8.1 Reguła na wypadek zmiany zegara (wyprowadzona, nie zgadnięta)

Ten sam DDI w Note10+ (davinci2) ma dynamiczną zmianę częstotliwości MIPI i **cztery** zestawy FFC
z podanymi zegarami — to jest kamień z Rosetty:
`…:drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_davinci2_a3_s0_panel.h:645-670`.

Układ ładunku (indeksy 0-based po opkodzie `0xC5`) jest w obu wariantach ten sam:

| bajt | znaczenie | beyond* | davinci2 |
|---|---|---|---|
| [0] | sterowanie (`0x08` = FFC off w wariancie dynamicznym, `…:1109-1111`) | `0x0D` | `0x0D` |
| [1] | stała | `0x10` | `0x10` |
| [2] | skala | `0xB4` (180) | `0x64` (100) |
| [3][4] | **słowo kompensacji, 16-bit big-endian** | `0x3E01` | `0x21FA` |
| [5…18] | dalsze stałe (tylko wariant 19-bajtowy) | — | niezależne od zegara |

Zależność (`scripts/ffc-calc.py`, log `build-logs/19-ffc-model.log`):

```
word = round(C * skala / f_Mbps),   C = 79 153,7
```

| zegar | słowo w źródle | model | błąd |
|---|---|---|---|
| 897,0 Mbps (davinci2) | 0x2278 | 0x2278 | **0 LSB** |
| 903,5 Mbps (davinci2) | 0x2239 | 0x2239 | **0 LSB** |
| 910,0 Mbps (davinci2, = wartość statyczna `:844-850`) | 0x21FA | 0x21FA | **0 LSB** |
| 929,5 Mbps (davinci2) | 0x2144 | 0x2144 | **0 LSB** |
| 898,0 Mbps (beyond*, skala 0xB4) | 0x3E01 | 0x3DFA | −7 LSB (−0,044 %) |

Cztery punkty davinci2 model odtwarza **co do bitu**. Punkt beyond* rozjeżdża się o 7 LSB:
odwrotność modelu daje dla `0x3E01` częstotliwość **897,6 Mbps**, a nie 898,0 — co jest zgodne
z obserwacją, że fizyczny PLL daje 897,0 Mbps (26 × 138 / (2·2²) × 2), a „898" w DT to zaokrąglenie.
Nie rozstrzygam, czy Samsung liczył z 897,6, czy skala `0xB4` ma nieco inną wagę niż `0x64` —
**do przesądzenia tego brakuje drugiego punktu w wariancie 5-bajtowym.**

Wartości wyliczone dla kilku alternatywnych zegarów (skala `0xB4`) są w
`build-logs/19-ffc-model.log`; przykładowo 950 Mbps → `0xC5, 0x0D, 0x10, 0xB4, 0x3A, 0x96`.
**Nieweryfikowane na sprzęcie** — dopóki nie ma UART-u i obrazu, to są liczby z modelu, nie fakty.

### 8.2 Kiedy to w ogóle będzie potrzebne

Tylko jeśli port zmieni zegar łącza (np. inne PMS przy walce z EMI albo przy trybie DSU o innym
zapotrzebowaniu na pasmo). Przy odtworzeniu stockowych 898 Mbps — pakiet przepisujemy 1:1.

## 9. Sekwencja inicjalizacyjna panelu — przepisana

Rozwinięta ze `beyond2_a3_s0_init_cmdtbl`
(`…@7d08ec36:drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_beyond2_a3_s0_panel.h:1366-1405`)
skryptem `scripts/dump-init-seq.py` (rozwiązuje `PKTINFO`/`KEYINFO`/`DLYINFO` do realnych bajtów).
Pełny zrzut, razem z sekwencjami display-on/exit/set-bl: `build-logs/20-init-seq-beyond2.log`.

Kolumna „typ" to typ pakietu DSI z definicji pakietu, nie zgadywanie:
`DSI_PKT_TYPE_WR` = zwykły zapis DCS, `DSI_PKT_TYPE_COMP` = MIPI *Compression Mode* (DT 0x07,
w mainline `mipi_dsi_compression_mode()`), `DSI_PKT_TYPE_PPS` = *Picture Parameter Set* (DT 0x0A,
w mainline `mipi_dsi_picture_parameter_set()`).

| # | krok | bajty (tryb natywny 1440×3040) | typ | uwagi |
|---|---|---|---|---|
| 1 | opóźnienie | — | — | 5 ms (`:1343`) |
| 2 | klucz L1 on | `9F A5 A5` | WR | |
| 3 | DSC enable | `01` | **COMP** | z `beyond2_a3_s0_dsc_table[1]` (`:385-388`); bazowy bajt w pakiecie to `00` |
| 4 | PPS | 128 B PPS trybu natywnego (§3) | **PPS** | z `beyond2_a3_s0_pps_table[1][0]` (`:452-471`) |
| 5 | klucz L1 off | `9F 5A 5A` | WR | |
| 6 | sleep out | `11` | WR | |
| 7 | opóźnienie | — | — | 10 ms (`:1344`) |
| 8 | klucz L2 on | `F0 5A 5A` | WR | |
| 9 | scaler | `BA 01 26 08 08 F3` | WR | „scaler off" dla 1440×3040 (`:522-523`) |
| 10 | klucz L2 off | `F0 A5 A5` | WR | |
| 11 | CASET | `2A 00 00 05 9F` | WR | kolumny 0…1439 (`:540-541`) |
| 12 | PASET | `2B 00 00 0B DF` | WR | wiersze 0…3039 (`:558-559`) — **uwaga:** bajty bazowe w nagłówku (`:871`) to `09 FF`, prawdziwa wartość przychodzi z maptbl |
| 13 | klucz L1 on | `9F A5 A5` | WR | |
| 14 | set area | `1A 1F 00 00 00 00` | WR | komenda producenta (`:758-760`) |
| 15 | **TE on** | `35 00` | WR | patrz §10 |
| 16 | klucz L1 off | `9F 5A 5A` | WR | |
| 17 | klucz L2 on | `F0 5A 5A` | WR | |
| 18 | err flag | `ED 04 4C` | WR | (`:803`) |
| 19 | klucz L3 on | `FC 5A 5A` | WR | |
| 20 | **FFC** | `C5 0D 10 B4 3E 01` | WR | §8 |
| 21 | klucz L3 off | `FC A5 A5` | WR | |
| 22 | **TSP HSYNC / TE start** | `B9 01 B0 E1 09 00 00 00 11 03` | WR | patrz §10 |
| 23 | ISC | `F6 43` @gpara 4 | WR | (`:886`, offset 4 w `DEFINE_STATIC_PACKET`, `:1268`) |
| 24 | STM enable | `86 01 08 10 21 11 42 01 00 00 00 00 00 00 00 00` | WR | |
| 25 | gamma mode 1 | `B1 00 01 00 01 00 00` @gpara 0x95 | WR | (`:863`, offset 0x95, `:1150`) |
| 26 | klucz L2 off | `F0 A5 A5` | WR | |
| 27 | sekwencja jasności | `PANEL_SET_BL_SEQ` | — | AID dimming, patrz `docs/R2-display.md` §d |

Kroki pominięte powyżej, bo są zależne od konfiguracji downstreamu i nie wnoszą nic do bring-upu:
`DUMP_SELF_DIAG` (`CONFIG_DISPLAY_USE_INFO`), odczyt `RES_POC_CHKSUM` (`CONFIG_SUPPORT_DDI_FLASH`),
`COPR_SET_SEQ` (`CONFIG_EXYNOS_DECON_LCD_COPR`) — wszystkie widoczne w logu.

**gpara** (kroki 23 i 25) to mechanizm globalnego parametru DDI: przed właściwym zapisem leci
`B0 <offset>`, czyli zapis trafia pod przesunięcie w rejestrze. Sterownik w mainline musi to
odtworzyć, inaczej zapisze pod zły adres.

### Pozostałe sekwencje (z tego samego zrzutu)

```
display on:   9F A5 A5 | 29 | 9F 5A 5A
display off:  9F A5 A5 | 28 | 9F 5A 5A
exit (sleep): 9F A5 A5 | 10 | 9F 5A 5A | czekaj 120 ms
```

## 10. TE (tearing effect) — strona panelu i strona SoC

Panel pracuje w trybie komend, więc DECON czeka na TE z panelu. Konfiguracja jest po obu stronach.

### 10.1 Panel

| co | bajty | cytat |
|---|---|---|
| TE on | `35 00` — tryb 0, impuls tylko dla V-blanking | `…_beyond2_a3_s0_panel.h:801` |
| TE off | `34` | `…:802` |
| moment startu TE | `B9 01 B0 E1 09 00 00 00 11 03` | `…:810-813` |

Dekodowanie trzech pierwszych parametrów `0xB9` — reguła wprost z komentarza w downstreamie
(`…:drivers/video/fbdev/exynos/dpu20/panels/s6e3ha9_param.h:72-83`):

```
wartość = ((param2 & 0x0F) << 8) | param3
param1 = 0x01 gdy start TE jest przyspieszony pod PLL_SLEEP, 0x00 gdy nie
```

Komentarz podaje dwa punkty kontrolne dla tej samej reguły: `00 B0 E5` → `0xBE5` = 3045
= „3040 (linie aktywne) + 7 (vbp) − 2", oraz wariant PLL_SLEEP `01 B0 DA` → `0xBDA` = 3034
= 3045 − 11. Nasz pakiet: `01 B0 E1` → **`0xBE1` = 3041 linii, wariant PLL_SLEEP**.
To, że wariant PLL_SLEEP jest tym aktywnym, potwierdza konfiguracja urządzenia:
`CONFIG_EXYNOS_PLL_SLEEP=y` (`…:arch/arm64/configs/exynos9820-beyond2lte_defconfig:3557`).

**Uwaga:** liczba z beyond2 (3041) nie zgadza się z arytmetyką z komentarza dla naszych porch
(3040 + vbp 15 − 2 = 3053, a z odjęciem 11 → 3042). Reguła kodowania jest pewna (dwa punkty
kontrolne), sama wartość 3041 — przepisana z panelu, nie wyprowadzona. Nie zgaduję, skąd dokładnie
Samsung ją wziął.

### 10.2 SoC

| co | wartość | cytat |
|---|---|---|
| pin TE | **gpd0-0**, funkcja `0xF` (EINT) przy TE on, `0x0` przy TE off | `…:arch/arm64/boot/dts/exynos/exynos9820.dts:2037-2049` (`decon_f_te_on` / `decon_f_te_off`) |
| odwołanie z DECON | `gpios = <&gpd0 0 0xf>`, `pinctrl-names = "hw_te_on", "hw_te_off"` | `…:exynos9820.dts:6769-6784` |
| rejestr EINT dla TE | `0x10830a14` = pinctrl_peric1 (`0x10830000`) + `0xA14` | `…:exynos9820.dts`, węzeł `te_eint` w `decon_f` |
| tryb DECON | `psr_mode = <0x2>` (command), `trig_mode = <0x0>` (HW trigger z TE) | `…:exynos9820.dts:6780-6781` |

Liczniki TE po stronie DSIM (`…/dpu20/cal_9820/dsim_reg.c:1254-1267`), policzone dla naszego
zegara 898 Mbps i 1440 px:

```
time_stable_vfp     = xres * 2 * 3 / 100      = 1440*2*3/100 = 86
time_te_protect_on  = hs_clk * 158 / 16       = 898*158/16   = 8867   (15,8 ms)
time_te_tout        = hs_clk * 180 / 16       = 898*180/16   = 10102  (18 ms)
```

Rejestry: `DSIM_CMD_TE_CTRL0` (0x84) — `TIME_STABLE_VFP` [15:0];
`DSIM_CMD_TE_CTRL1` (0x88) — `TIME_TE_PROTECT_ON` [31:16], `TIME_TE_TOUT` [15:0]
(`…/cal_9820/regs-dsim.h:306-315`). Stałe 158 i 180 to dziesiąte części milisekundy
(`TE_PROTECT_ON_TIME`, `TE_TIMEOUT_TIME`, `dsim_reg.c:38-39`).

Do kompletu: `cmd_underrun_lp_ref = <2877 5278 6994>` (per tryb rozdzielczości, §2) trafia do
`DSIM_UNDERRUN_CTRL` — to zabezpieczenie przed niedomiarem danych w trybie komend.
