# R2 — wyświetlacz

**Odpowiedź:** Mainline **nie ma** ani DECON-a, ani DSI-hosta pokrywającego generację z 9820
(sterowniki DECON kończą się na exynos7870, a `samsung-dsim` ma zupełnie inną mapę rejestrów niż
9820), panel w SM-G975F to **S6E3HA9 / AMB644WQ01 (SDC)** ze **skompresowanym strumieniem DSC**,
a jasność **nie jest** robiona przez DCS 0x51 — teza z briefu §5 jest **obalona**: downstream steruje
jasnością przez AID dimming (gamma 0xCA + AOR 0xB1 + ELVSS/TSET + VINT + ACL + IRC) pod kluczem
poziomu 2.

---

## a) DECON w `drm/exynos` — warianty i compatible

Wszystko, co jest w mainline (`linux@1200d84f4c0a`):

| plik | compatible | linia |
|---|---|---|
| `drivers/gpu/drm/exynos/exynos5433_drm_decon.c` | `samsung,exynos5433-decon` | 751 |
| `drivers/gpu/drm/exynos/exynos5433_drm_decon.c` | `samsung,exynos5433-decon-tv` | 755 |
| `drivers/gpu/drm/exynos/exynos7_drm_decon.c` | `samsung,exynos7-decon` | 82 |
| `drivers/gpu/drm/exynos/exynos7_drm_decon.c` | `samsung,exynos7870-decon` | 86 |

Nic z tego nie pokrywa 9820. Downstream deklaruje **`samsung,exynos9-decon`**
(`LineageOS/android_kernel_samsung_exynos9820@7d08ec36:arch/arm64/boot/dts/exynos/exynos9820.dts:6769-6770`,
`reg = <0x19030000 0x10000>`, drugi kontroler `decon_t@0x19050000` w linii 6813).

**Dlaczego to inna generacja (dowód rejestrowy, nie „wygląda inaczej"):**

| rejestr | mainline exynos5433 | downstream 9820 |
|---|---|---|
| główny CON | `DECON_VIDCON0 = 0x0000` (`linux@1200d84f4c0a:drivers/gpu/drm/exynos/regs-decon5433.h:10`) | `GLOBAL_CONTROL = 0x0000` (`…@7d08ec36:drivers/video/fbdev/exynos/dpu20/cal_9820/regs-decon.h:89`) |
| trigger | `DECON_TRIGCON = 0x2040` (`regs-decon5433.h:55`) | `HW_SW_TRIG_CONTROL = 0x0070` (`cal_9820/regs-decon.h:151`) |
| update | `DECON_UPDATE = 0x1410` (`regs-decon5433.h:45`) | brak odpowiednika pod tym offsetem |

`HW_SW_TRIG_CONTROL @ 0x70` to dokładnie ten rejestr, który uniLoader wpisuje, żeby framebuffer
S-Boota się odświeżał: `ivoszbg/uniLoader@2fb7820aaf3b:board/samsung/board-beyond1lte.c:13-22`
(`#define DECON_F_BASE 0x19030000`, `#define HW_SW_TRIG_CONTROL 0x70`, zapis `0x1281`).

Downstreamowy nagłówek `cal_9820/regs-decon.h` ma 448 definicji `#define` — to skala pracy przy
pisaniu nowego wariantu DECON-a od zera.

Tryb pracy panelu (dla przyszłego drivera): `psr_mode = <0x2>`, `trig_mode = <0x0>`, `dsi_mode = <0x0>`
(`exynos9820.dts:6774-6777`) → command mode + HW trigger z TE.

## b) `samsung-dsim` — obsługiwane compatible i czy da się użyć dla 9820

Obsługiwane compatible (`linux@1200d84f4c0a:drivers/gpu/drm/exynos/exynos_drm_dsi.c:164-186`
dla części Samsunga i `…/bridge/samsung-dsim.c:2313-2317` dla i.MX):
`samsung,exynos3250-mipi-dsi`, `exynos4210`, `exynos5410`, `exynos5422`, `exynos5433`,
`exynos7870-mipi-dsi`, `fsl,imx8mm-mipi-dsim`, `fsl,imx8mp-mipi-dsim`
(binding: `Documentation/devicetree/bindings/display/bridge/samsung,mipi-dsim.yaml:22-34`).

**Dla 9820 nie da się użyć „bez zmian".** Mapa rejestrów to inna generacja IP:

| rejestr | mainline exynos5433 (`samsung-dsim.c:306-328`) | mainline exynos7870 (`samsung-dsim.c:330-353`) | downstream 9820 (`cal_9820/regs-dsim.h`) |
|---|---|---|---|
| 0x00 | `DSIM_STATUS` | (LINK_STATUS @0x04) | `DSIM_VERSION` (:18) |
| 0x04 | `DSIM_STATUS`=0x04 | `DSIM_LINK_STATUS`=0x04 | `DSIM_SWRST` (:20) |
| 0x0C | `DSIM_SWRST` | `DSIM_SWRST` | `DSIM_LINK_STATUS1` (:29) |
| rozdzielczość | `DSIM_MDRESOL = 0x20` | `DSIM_MDRESOL = 0x20` | `DSIM_RESOL = 0x3c` (:110) |
| porch | `DSIM_MVPORCH = 0x24` | `0x24` | `DSIM_VPORCH = 0x40` (:120) |

9820 ma dodatkowo rejestry, których model programowania `samsung-dsim` w ogóle nie zna
(`DSIM_NUM_OF_TRANSFER` :96, `DSIM_UNDERRUN_CTRL` :101, `DSIM_THRESHOLD` :105, `DSIM_DESKEW_CTRL` :68).
Realny zakres pracy: nowy `hw_type` + własna tablica `reg_ofs` **i** przepisane ścieżki PLL/DPHY/
transferu komend — czyli praktycznie nowy wariant sterownika, nie „dopisz enum".

**Dodatkowy blocker: DSC.** Panel beyond2 pracuje ze skompresowanym strumieniem (tablica PPS 128 B na
tryb: `…@7d08ec36:drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_beyond2_a3_s0_panel.h:390`
`beyond2_a3_s0_pps_table[][3][128]`, oraz `beyond2_a3_s0_dsc_table` :385).
W `samsung-dsim.c` **nie ma ani jednego wystąpienia „dsc"/„compress"** (grep, log
`build-logs/07-r2-dsc-grep.log`), choć rdzeń DRM ma helper `drivers/gpu/drm/display/drm_dsc_helper.c`.

Węzeł DSI w downstreamie: `exynos9820.dts:6745-6746` — `samsung,exynos9-dsim`,
`reg = <0x19080000 0x300>, <0x19161000 0x800>, <0x19160000 0x100>` (link + dwa D-PHY).

## c) Jaki DDI/panel siedzi w G975F i gdzie jest sekwencja inicjalizacyjna DCS

**DDI: S6E3HA9. Moduł: AMB644WQ01, vendor SDC, panel id 0xA01010 / 0xA01011, rev 2.**

- Wybór w konfiguracji urządzenia: `CONFIG_EXYNOS_DECON_LCD_S6E3HA9=y`
  (`…@7d08ec36:arch/arm64/configs/exynos9820-beyond2lte_defconfig:3565`).
- Nazwa modułu i identyfikatory:
  `…:drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_beyond2_a3_s0_panel.h:2290-2295`
  (`.ldi_name = "s6e3ha9"`, `.model = "AMB644WQ01"`, `.vendor = "SDC"`, `.id = 0xA01011`).

**Lokalizacja sekwencji** (w fazie rekonesansu tylko zlokalizowana i zacytowana; na żądanie przepisana w całości — `docs/R2-panel-timings.md` §9, wraz z TE w §10):

| co | plik | linia |
|---|---|---|
| tablica sekwencji init | `…/s6e3ha9/s6e3ha9_beyond2_a3_s0_panel.h` | 1366 (`beyond2_a3_s0_init_cmdtbl[]`), zarejestrowana jako `PANEL_INIT_SEQ` w :2062 |
| sekwencja „display on" | to samo | 1505 (`…_display_on_cmdtbl`) |
| sekwencja „exit" | to samo | 1517 (`…_exit_cmdtbl`) |
| sekwencja jasności | to samo | 1454 (`…_set_bl_cmdtbl`) |
| klucze dostępu | to samo | 689-694 (`KEY1 0x9F A5 A5`, `KEY2 0xF0 5A 5A`, `KEY3 0xFC 5A 5A`) |
| standardowe DCS | to samo | 695-698 (`SLEEP_OUT 0x11`, `SLEEP_IN 0x10`, `DISPLAY_OFF 0x28`, `DISPLAY_ON 0x29`) |
| PPS/DSC | to samo | 385-512 |
| wspólna logika DDI | `…/s6e3ha9/s6e3ha9.c` (2589 linii), `s6e3ha9.h` (900 linii) | — |

## d) Jak downstream ustawia jasność — teza „DCS 0x51 + tabela ELVSS"

**OBALONA w części „0x51".** W całym `s6e3ha9.c` **nie ma ani jednego `0x51`** jako opkodu
(grep — `build-logs/08-r2-brightness-grep.log`), a sekwencja jasności to AID dimming:

```
s6e3ha9_beyond2_a3_s0_panel.h:1454  beyond2_a3_s0_set_bl_cmdtbl[] = {
        level2_key_enable,            /* 0xF0 0x5A 0x5A  (:690) */
        gamma,                        /* 0xCA, 34 B, tablica GAMMA_MAPTBL (:814, :1164) */
        aor,                          /* 0xB1 0x00 0x14  (:829) */
        tset_mps_elvss,               /* 0xB5 TSET/MPS/ELVSS (:836-841) */
        elvss_temp,                   /* 0xB5 ELVSS TEMP (:842-845) */
        vgh_vint,                     /* 0xF4 VGH+VINT (:846-850) */
        acl_control, acl_onoff,       /* 0xB4 (:866), 0x55 (:865) */
        irc_value, irc_on,
        poc_comp1, poc_comp2,         /* 0xB1 (:830), 0x96 (:835) */
        gamma_update_enable,          /* 0xF7 0x03  (:864) */
        level2_key_disable };
```

Potwierdzone w konfiguracji: `CONFIG_PANEL_AID_DIMMING=y`
(`…:arch/arm64/configs/exynos9820-beyond2lte_defconfig:3579`).

**ELVSS: teza potwierdzona** — są trójwymiarowe tablice ELVSS i ELVSS-temp indeksowane poziomem
jasności i temperaturą (`…_panel.h:120` `beyond2_a3_s0_elvss_table[][…][1]`, `:165`
`beyond2_a3_s0_elvss_temp_table`, maptable `:641-642`).

**Konsekwencja projektowa:** driver panelu w mainline nie może być „jednym zapisem 0x51 z
backlight_ops". Musi wozić tablice gamma/AOR/ELVSS/VINT per poziom jasności — to jest ta sama
klasa pracy co `panel-samsung-s6e3ha2.c` (w mainline istnieje, `drivers/gpu/drm/panel/`), tyle że
z DSC. Wygaszanie (0x28/0x10) i AMOLED-owy brak PWM z briefu §5 — **potwierdzone** (:697, :696).

## Czego nie udało się ustalić

- ~~**Timingi panelu i parametry DSC**~~ — **USTALONE**, patrz `docs/R2-panel-timings.md`:
  command mode, 1440×3040 @60 Hz, 4 linie, HS 898 Mbps (P/M/S = 2/138/2), esc 20 MHz,
  hbp/hfp/hsa = 2/2/2, vbp/vfp/vsa = 15/3/1, DSC 1.1 8 bpp 8 bpc, 2 slice’y 720×40, 2 enkodery.
  Źródło: węzeł DT `s6e3ha9_beyond2` w overlayu płyty + zdekodowane bajty PPS.
- **Adres framebuffera dla beyond2lte** — `0xca000000` jest udokumentowany dla beyond1lte
  (uniLoader `board-beyond1lte.c:30`, `configs/beyond1lte_defconfig:8`) i użyty także w DT beyond2lte
  (`u-boot@c5afa30840d9:…/exynos9820-beyond2lte.dts:16`), ale **nie zweryfikowany pomiarowo na
  naszym egzemplarzu**. To jest do potwierdzenia w B1/B2, nie do przyjęcia na wiarę.
- Czy `samsung,exynos9-decon` z 9820 jest tożsamy z DECON-em z exynos990/gs101 (co pozwoliłoby
  współdzielić przyszły sterownik) — **NIE SPRAWDZONE**.

## Dlaczego nie rozszerzyc samsung-dsim (odpowiedz mierzona, nie deklarowana)

Pierwsze pytanie recenzenta mainline brzmi: `drivers/gpu/drm/bridge/samsung-dsim.c`
ma juz indirekcje offsetow (`exynos_reg_ofs`, `exynos5433_reg_ofs`), wiec czy nie
wystarczy dopisac tam kolejnej tablicy dla 9820.

Odpowiedz generuje `scripts/compare-dsim.py`, ktory czyta offsety z OBU sterownikow
i wypisuje rozjazd. Wynik jest bramka w `verify.sh` i lezy w
`build-logs/45-samsung-dsim-porownanie.log`:

- z 15 rejestrow, ktore `samsung-dsim` programuje i ktore maja odpowiednik na 9820,
  **14 lezy pod innym adresem**. Zgadza sie dokladnie jeden: `SWRST` pod 0x04.
  Przyklady rozjazdu: `STATUS` 0x00 kontra `LINK_STATUS0` 0x08, `CONFIG` 0x10
  kontra 0x4c, `MDRESOL` 0x18 kontra `RESOL` 0x3c, `TIMEOUT` 0x0c kontra 0x28.
- **9 rejestrow nie ma odpowiednika w tym bloku w ogole**: porche i sync trybu wideo
  (9820 pracuje w trybie komend), oraz `PLLCTRL`, `PHYCTRL`, `PHYTIMING*`, bo na 9820
  PLL i D-PHY to **osobne zakresy `reg`** (M4S0 i M4S4), a nie rejestry w oknie DSIM.
- `samsung-dsim` **nie zna kompresji DSC**: w calym pliku nie ma ani jednego wystapienia
  ciagu "dsc" (sprawdzone `grep -ci`). Panel S6E3HA9 nie uruchamia sie bez DSC, a jej
  konfiguracja to 31 rejestrow po stronie DECON plus bit `CPRS_EN` w DSIM.

Wniosek: dopisanie tablicy offsetow nie zalatwia niczego poza jednym rejestrem.
Rozszerzenie `samsung-dsim` o 9820 oznaczaloby dolozenie do niego drugiego, rownoleglego
zestawu sciezek dla trybu komend, osobnego bloku PHY i calej kompresji DSC, czyli
przepisanie sterownika wewnatrz sterownika. Dlatego generacja IP z 9820 dostaje wlasny
plik, tak jak w mainline maja go kolejne generacje DECON-a (`exynos5433`, `exynos7`,
`exynos7870`).

Regeneracja tego porownania: `python3 scripts/compare-dsim.py`.
