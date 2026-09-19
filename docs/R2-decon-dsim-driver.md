# Szkic sterownika DECON/DSIM dla Exynos 9820

**Stan:** szkielet — **kompiluje się (EXIT=0, zero ostrzeżeń z naszych plików)**, przechodzi
`checkpatch --strict` bez błędów, **nie zapala jeszcze panelu** i nie ma węzłów DT, bo te wymagają
bloku CMU_DPU w driverze zegarów, którego nie ma ani w mainline, ani w drzewie out-of-tree.
Artefakt: `patches/0037` (783 linie sterownika plus 347 linii naglowka rejestrow, w tym wpis MAINTAINERS).

## 1. Dlaczego nowy sterownik, a nie rozszerzenie istniejących

| kandydat | werdykt | dowód |
|---|---|---|
| `drivers/gpu/drm/exynos` (DECON) | **nie** — kończy się na `samsung,exynos7870-decon`, 9820 to `samsung,exynos9-decon` z inną mapą (trigger `0x70` vs `DECON_TRIGCON 0x2040`) | `docs/R2-display.md` §a |
| `drivers/gpu/drm/bridge/samsung-dsim.c` | **nie** — inne offsety (`SWRST` 0x04 vs 0x0C, `RESOL` 0x3c vs `MDRESOL` 0x20) i rejestry, których ten model nie zna; zero obsługi DSC | `docs/R2-display.md` §b |

Stąd `drivers/gpu/drm/exynos9820/` jako osobny, mały sterownik DRM (jeden moduł, dwa
`platform_driver`).

## 2. Co jest w szkielecie

```
drivers/gpu/drm/exynos9820/
├── exynos9820_regs.h        235 linii — offsety i pola bitowe (DECON, DPP/IDMA, DSIM link + D-PHY)
├── exynos9820_drm_decon.c   538 linii — urządzenie DRM, CRTC+plane (simple pipe), DPP0, IRQ/vblank
├── exynos9820_drm_dsim.c    545 linii — host MIPI DSI + drm_bridge, PLL i D-PHY, transfer komend
├── exynos9820_drm.h, Kconfig, Makefile
```

**DECON** (`samsung,exynos9820-decon`, `0x19030000`):
tryb komend (`GLOBAL_CONTROL.OPERATION_MODE_CMD`), rozmiar blendera z trybu, ścieżka danych
`DSCC + DSC_ENC0/1 → OUTFIFO0/1 → DSIM_IF0` (`0x0b1`), okno 0 mapowane na kanał DPP0,
trigger sprzętowy z TE (`HW_SW_TRIG_CONTROL`, `HW_TRIG_SEL_FROM_DDI0`), `SHADOW_REG_UPDATE_REQ`
przy każdym flipie, przerwanie `FRAME_DONE` → `drm_crtc_handle_vblank()`, start/stop z odczekaniem
na `RUN_STATUS`/`IDLE_STATUS` (kolejność jak w `decon_reg_start`/`decon_reg_stop`).

**DPP0/IDMA** (drugi zakres `reg`, `0x19071000`): reset, format XRGB8888, `SRC_SIZE`/`IMG_SIZE`,
adres bufora (`IDMA_IN_BASE_ADDR_Y`).

**DSIM** (`samsung,exynos9820-dsim`, `0x19080000` + PHY `0x19161000`):
`mipi_dsi_host` (attach/detach/transfer przez `PKTHDR`/`PAYLOAD` z czekaniem na
`SFR_PH_FIFO_EMPTY`), `drm_bridge` z `atomic_pre_enable`/`atomic_post_disable`, konfiguracja linku
(`CONFIG`: 4 linie, RGB24, EOTP, **`CPRS_EN` gdy panel zgłasza DSC**), `RESOL`, liczniki TE
(`CMD_TE_CTRL0/1` — te same 86 / 8867 / 10102 co w `docs/R2-panel-timings.md` §10.2, liczone
w kodzie z `hs_clk`), dzielnik escape liczony **tą samą arytmetyką całkowitoliczbową co downstream**
(20 MHz → faktycznie 18 MHz), timingi D-PHY z wiersza „900" tablicy oraz PLL P/M/S = 2/138/2.

## 3. Czego brakuje, żeby to zapaliło ekran

Wypisane wprost, bo szkielet bez tej listy jest mylący:

1. ~~**Inicjalizacja enkoderów DSC w DECON**~~ — **zrobiona**, patrz §6.
2. ~~**Bloki stałych analogowych D-PHY**~~ — **zrobione**, patrz §7 (przy okazji znaleziony
   i naprawiony błąd adresów PLL).
3. ~~**Odczyty DSI**~~ — **zrobione**, patrz §8.
4. **Węzły DT** — DECON/DSIM potrzebują zegarów z **CMU_DPU**, a driver zegarów ma tylko
   źródła w CMU_TOP (`CLK_GOUT_CMU_DPU`, `CLK_DOUT_CMU_DPU_BUS`) i **żadnego bloku CMU_DPU**
   (sprawdzone: brak `samsung,exynos9820-cmu-dpu` w `clk-exynos9820.c`). Do tego dochodzą domena
   zasilania i IOMMU. Dlatego świadomie **nie** dopisałem bindingów ani węzłów — byłyby opisem
   sprzętu, którego jądro i tak nie potrafi włączyć. To ta sama zależność co przy GPU (R1).
5. **Rozdzielenie DPP na własny sterownik** — tu DPP0 jest drugim `reg` węzła DECON-a. Upstream
   będzie chciał osobnego drivera per DPP (jak downstream) albo jawnego opisu w DT.
6. Partial update, PLL sleep, self-refresh, tryby DSU, więcej niż jedno okno.

## 4. Bramki

| bramka | wynik | log |
|---|---|---|
| kompilacja `exynos9820_drm_dsim.o` | **EXIT=0**, 0 ostrzeżeń z pliku, 12 416 B | `build-logs/24-decon-dsim-build.log` |
| kompilacja `exynos9820_drm_decon.o` | **EXIT=0**, 0 ostrzeżeń z pliku, 14 672 B | `build-logs/24-decon-dsim-build.log` |
| `checkpatch --strict` | 0 błędów, 4 ostrzeżenia | `build-logs/05-checkpatch.log` |

Ostrzeżenia checkpatcha i co z nimi: „Unknown commit id" (commit z innego repo w opisie),
„MAINTAINERS?" (fałszywy alarm), oraz **dwa razy „DT compatible string … appears un-documented"** —
to jest prawdziwe i **zamierzone**: binding pojawi się razem z CMU_DPU, patrz §3.4.

Uwaga do środowiska: te pliki, w odróżnieniu od sterownika panelu, **nie kompilują się bez `-O2`**
(inline asm z ograniczeniem `i` w `alternative-macros.h` wymaga zwijania stałych). `scripts/kcc-termux.sh`
ma już `-O2`.

## 5. Kolejność dalszej pracy

1. CMU_DPU w driverze zegarów (bez tego nic nie ruszy) → 2. węzły DT + bindingi →
3. `dsc_reg_init()` i OUTFIFO → 4. bloki analogowe PHY → 5. pierwszy `modetest` na sprzęcie →
6. odczyty DSI i AID dimming w sterowniku panelu.

## 6. DSC w DECON (dopisane, `patches/0037`)

Enkodery DSC dostają **własny PPS**, inny niż panel: przy dwóch enkoderach każdy kompresuje połowę
obrazu, więc jego `pic_width` to **720**, a nie 1440. OUTFIFO niosą już piksele skompresowane —
dla tego panelu **240 na enkoder**.

Co program robi (kolejność jak w downstreamowym `dsc_reg_init` → `dsc_reg_set_encoder`):

1. `DSC_CONTROL0`: wyłączone bramkowanie zegara, swap `(bit, byte, word) = (0, 1, 0)`, próg
   płaskości 2 (stały dla 8 bpc), `dual_slice` i `slice_mode_change` z liczby slice’ów.
2. `DSC_CONTROL3`: `remainder` i `grpcntline` z szerokości slice’a.
3. PPS04-35 i PPS58-59 w rejestrach `DSC_PPSxx_yy` + trzy słowa PPS79..87 zapisywane dosłownie
   (producent robi to samo, `decon_reg.c:1100-1102`).
4. `OUTFIFO_SIZE_CONTROL_0/1/2` — rozmiar na enkoder i rozmiar skompresowanego slice’a.

**Skąd parametry:** ze sterownika panelu, przez hosta DSI — DECON pyta mostek o
`drm_dsc_config` (`exynos9820_dsim_get_dsc()`), więc po stronie DECON-a nie ma żadnej wiedzy
o konkretnym panelu.

**Wartości, które producent zaszywa na sztywno i my też** (z komentarzem w kodzie):
`initial_dec_delay = 0x1b4` (bo `VESA_SCR_V4` nie jest zdefiniowane w ich buildzie — sprawdzone,
w całym drzewie są tylko dwa `#ifndef`) oraz trzy słowa PPS79..87.

### Weryfikacja liczbowa

`scripts/check-decon-dsc.py` **wycina funkcje liczące prosto ze źródła sterownika**, kompiluje je
jako program użytkownika i porównuje wynik dla beyond2lte z wartościami ze wzoru producenta:

```
pic_width 720   slice 720x40   chunk 720   final_offset 4336   nfl_bpg 631
slice_bpg 489   scale_inc 1132  scale_dec 10   width_per_enc 240
dual_slice 0    slice_mode_change 1   initial_dec_delay 0x1b4
```

**18/18 pól zgodnych** — `build-logs/33-decon-dsc-check.log`. To nie jest test na sprzęcie, tylko
dowód, że przepisana arytmetyka daje dokładnie te liczby co oryginał.

### Co zostaje

Do zapalenia obrazu nadal brakuje bloków analogowych D-PHY (§3.2), a do sensownego działania —
odczytów DSI (§3.3) i PMIC-a `s2dos05`. Pozycja „DSC" znika z listy blokerów.

## 7. Bloki analogowe D-PHY (dopisane, `patches/0025`-`0021`)

### 7.1 Błąd, który to ujawniło

Przy przepisywaniu bloków wyszło, że **szkic miał złe adresy PLL-a**: użyłem `PLL_CON` = `0x0300`,
podczas gdy prawdziwe `PLL_CON(i)` to `0x0100 + 4·i`
(`…/cal_9820/regs-dsim.h:433`), a `0x0300` to `MC_GNR_CON` (`:508`). Wartości P/M/S leciały więc
do bloku ogólnego linii zegarowej. Do tego pola były źle rozmieszczone — poprawnie:

| pole | rejestr | bity | cytat |
|---|---|---|---|
| `PLL_EN` | `PLL_CON0` (0x100) | 12 | `regs-dsim.h:455` |
| `PMS_S` | `PLL_CON0` | 10:8 | `:457` |
| `PMS_P` | `PLL_CON0` | 5:0 | `:459` |
| `PMS_K` | `PLL_CON1` (0x104) | 15:0 | `:463` |
| `PMS_M` | `PLL_CON2` (0x108) | 9:0 | `:467` |

Kolejność zapisu też jest teraz jak u producenta (K → M → P/S, `dsim_reg.c:358-381`).

### 7.2 Co zostało dopisane

| blok | rejestry | wartości | cytat |
|---|---|---|---|
| BIAS | `BIAS_CON0..4` @ **M4S4** (`0x19160000`) | `0x10, 0x110, 0x3223, 0, 0` | `dsim_reg.c:45-51` |
| PLL | `PLL_CON0..8` @ M4S0 | `0×5, 0x500, 0x8E, 0x1450, 0xA28` | `:53-65` |
| MC GNR | `MC_GNR_CON0..1` | `0, 0x1450` | `:67-70` |
| MC ANA | `MC_ANA_CON0..2` | `0x7033, 0, 2` (EDGE_CON = D-PHY) | `:71-78` |
| MD GNR | `MD_GNR_CON0..1` × 4 linie | `0, 0x1450` | `:81-84` |
| MD ANA | `MD_ANA_CON0..3` × 4 linie | `0x7033, 0, 0, 0` | `:85-90` |

Kolejność wywołań (bias i PLL przed timingami, GNR/ANA po) odwzorowuje `dsim_reg.c:1847-1893`.

Dodatkowo włączony **dithering PLL-a** (`MFR = 13`, `MRR = 3`, `DITHER_EN` w `PLL_CON4`) — bo
producent go dla tego panelu włącza (`CONFIG_EXYNOS_DSIM_DITHER=y` w defconfigu beyond2lte),
a parametry pochodzą z tej samej właściwości DT co PMS (`timing,pmsk`, patrz
`docs/R2-panel-timings.md` §2).

**Uczciwie:** znaczenia pól w tych blokach nie znam — producent wpisuje surowe słowa bez
dokumentacji i my robimy tak samo. To jest przepisanie, nie zrozumienie.

### 7.3 Blok bias jako osobny węzeł

Blok BIAS leży w osobnym oknie (`0x19160000`, „M4S4 top"). Nie należy do żadnego łącza,
a SoC ma miejsce na drugi kontroler DSI, więc w DT jest węzłem `syscon`, na który węzeł PHY
wskazuje właściwością `samsung,dphy-top-syscon` (`patches/0024`, `0021`). Gdyby stał jako
drugi zakres `reg` każdej instancji, drugi węzeł dostałby `-EBUSY` na tym samym oknie.

### 7.4 Bramki

| bramka | wynik | log |
|---|---|---|
| kompilacja DSIM i DECON | **EXIT=0**, 0 uwag z plików | `build-logs/34-dphy-analog-check.log` |
| `dt_binding_check` (dsim) | **EXIT=0** | tamże |
| `CHECK_DTBS` | **EXIT=0** | tamże |
| `checkpatch --strict` (0017-0019) | 0 błędów | — |
| 19 patchy na czystej bazie + `CHECK_DTBS` | **EXIT=0** | `build-logs/35-clean-worktree-19patches.log` |

## 8. Odczyty DSI (dopisane, `patches/0034`)

Odczyt to krótki pakiet z ustawionym bitem **bus turnaround** w nagłówku
(`DSIM_PKTHDR_BTA_TYPE`, `regs-dsim.h:228`), poprzedzony poinformowaniem panelu, ile bajtów może
zwrócić (`MIPI_DSI_SET_MAXIMUM_RETURN_PACKET_SIZE`). Odpowiedź wychodzi z `DSIM_RXFIFO` (0x60):
pierwsze słowo to nagłówek pakietu, a przy długiej odpowiedzi kolejne słowa niosą ładunek
po 4 bajty.

Obsługiwane typy odpowiedzi (jak w `dsim_drv.c:330-386`): błąd (`ACKNOWLEDGE_AND_ERROR_REPORT`
→ `-EPROTO` z wypisaniem kodu), `END_OF_TRANSMISSION`, krótkie 1- i 2-bajtowe (DCS i generic)
oraz długie DCS/generic. Pętla kończy się, gdy `FIFOCTRL.EMPTY_RX` się ustawi, z twardym limitem
64 iteracji — inaczej przy złych timingach D-PHY czytałaby w nieskończoność (dokładnie ten sam
zabezpieczający licznik ma producent).

**Różnica względem downstreamu:** on czeka na przerwanie `RX_DATA_DONE` przez completion, my
odpytujemy `DSIM_INTSRC` (timeout 100 ms). Prostsze i wystarczające dla ścieżki komend, która
i tak jest synchroniczna.

Po co to: panel raportuje tak swoje dane **MTP**, z których biorą się tablice gamma do AID
dimming (`docs/R2-panel-driver.md` §4).

Bramki: kompilacja EXIT=0, 0 uwag z pliku (`build-logs/39-dsi-read-check.log`),
`checkpatch --strict` 0 błędów, 22 patche na czystej bazie + `CHECK_DTBS` EXIT=0.

### Poprawki z fazy drugiej

**Trzy zegary DECON zamiast jednego.** Binding wymaga `aclk`, `aclk-dma` i `aclk-dpp`
(`patches/0036`), DT podaje wszystkie trzy (`patches/0040`), a sterownik pobieral i wlaczal
wylacznie `aclk`. Rownoczesnie `decon_dpp_setup()` pisze do drugiego zakresu `reg`, czyli do
rejestrow IDMA kanalu DPP0, bramkowanych przez `ACLK_DMA` i `ACLK_DPP`. Zapis do bloku
z martwym zegarem na tym SoC nie konczy sie czytelnym bledem, tylko zawisem na dostepie do
SFR, wiec byla to najgorsza mozliwa klasa bledu: niemy.

Po poprawce sterownik trzyma `struct clk_bulk_data clks[3]`, pobiera je jednym
`devm_clk_bulk_get()` i wlacza w `runtime_resume` przez `clk_bulk_prepare_enable()`.

**Zegary w ogole istnieja.** Do tej pory caly rozdzial zakladal blok CMU_DPU "w driverze
zegarow, ktorego nie ma ani w mainline, ani w drzewie out-of-tree". To juz nieaktualne:
`patches/0013` wnosi sterownik zegarow do mainline, a `patches/0022` dokłada do niego bloki
CMU_DPU i CMU_CMGP. Kolejnosc serii jest tak ulozona, ze sterownik stoi **przed** DT, ktore
sie na niego powoluje, a blok DPU/CMGP **po** bindingach, ktore wnosza jego identyfikatory.

**Liczniki D-PHY oznaczone jako niezweryfikowane.** Wiersz tablicy dla 898 Mbps jest
przepisany poprawnie, ale jednostka licznikow nie jest udokumentowana i kontrola wobec
minimow MIPI nie wychodzi. W kodzie stoi teraz komentarz `UNVERIFIED: HW-01` z zakazem
przeskalowywania wiersza na inny zegar lacza przed pomiarem.

**Bramki.** Kompilacja tych plikow dla arm64 jest teraz bramka w `scripts/verify.sh`,
w dwoch wariantach: zwyklym i `W=1`. Oba wymagaja **zera** uwag. Do tego dochodzi
`dt-validate` na zbudowanym DTB (odpowiednik `CHECK_DTBS`, 0 naruszen wobec wszystkich
schematow jadra) oraz porownanie sha256 DTB z plikiem wzorcowym.
