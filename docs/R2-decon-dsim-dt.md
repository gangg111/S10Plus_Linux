# Bindingi i węzły DT dla DECON i DSIM

**Stan:** dopisane i zweryfikowane — `CHECK_DTBS` bez uwag, `dt_binding_check` OK, cała seria
**15 patchy** stosuje się na czystą bazę i dtb się buduje. Pipeline wyświetlacza jest opisany
w DT od zegara do panelu; nadal **nie zapala obrazu** z powodów wypisanych w §5.

Artefakty: `patches/0037` (bindingi), `patches/0037` (przerwanie po nazwie w sterowniku),
`patches/0040` (węzły DT + panel na beyond2lte).

## 1. Bindingi

`Documentation/devicetree/bindings/display/samsung/samsung,exynos9820-decon.yaml`
i `…-dsim.yaml`.

DSIM dostał własny binding zamiast wpisu w `samsung,mipi-dsim.yaml`, bo to inna generacja IP
(uzasadnienie z dowodami rejestrowymi: `docs/R2-display.md` §b).

W bindingu DECON-a **rejestry DMA kanału DPP0 są częścią węzła DECON-a** — dokładnie tak, jak
działa dziś sterownik. To jest świadome uproszczenie szkicu i jest napisane wprost w opisie
bindingu: przy wielu oknach trzeba będzie osobnego bindingu DPP.

## 2. Węzły w `exynos9820.dtsi`

| węzeł | adresy | przerwania | zegary |
|---|---|---|---|
| `decon0` (`display-controller@19030000`) | `0x19030000` (DECON_F) + `0x19071000` (DMA DPP0) | 183 frame-start, 184 frame-done, 189 extra | `ACLK_DECON`, `ACLK_DMA`, `ACLK_DPP` z CMU_DPU |
| `dsim0` (`dsi@19080000`) | `0x19080000` (link) + `0x19161000` (D-PHY M4S0) | 190 | `DSIM0_PCLKS` z CMU_DPU |

Oba mają `power-domains = <&pd_dpu>`, DECON dodatkowo `iommus = <&sysmmu_dpud0/1/2>`.
Graf: `decon0 → dsim0 → panel`. Oba są `status = "disabled"` w DTSI i włączane na płycie.

**Skąd numery przerwań i który jest który:** downstreamowy `decon_f` ma cztery wpisy
(`0xb7 0xb8 0xbd 0x197`), a kolejność rozstrzyga kod, nie zgadywanie —
`…/dpu20/decon_dsi.c:121-141` bierze je jako *1: FRAME START*, *2: FRAME DONE*,
*3: EXTRA (resource conflict, timeout, error)*. Czwartego (SPI 407) **nie zidentyfikowałem**:
komentarz w tym samym pliku numeruje dopiero indeksy 4-7 jako DIMMING/DQE, więc nie opisuję go.

**Skąd baza DMA dla DPP0:** węzeł `dpp@0x19071000` ma trzy zakresy `reg`, a sterownik downstreamu
mapuje zasób 0 jako `dma_regs` (`…/dpu20/dpp_drv.c:1023-1034`) — czyli `0x19071000`. To jedyny
węzeł DPP z trzecim zakresem („DPP0 channel can only access common area of DPU_DMA"), co potwierdza,
że to kanał 0.

Przy okazji sterownik bierze teraz przerwanie **po nazwie** (`platform_get_irq_byname("frame-done")`,
`patches/0037`) — wcześniej brał indeks 0, czyli frame-start.

## 3. Panel na płycie (`exynos9820-beyond2lte.dts`)

`panel@0` pod `dsim0`: `samsung,s6e3ha9`, `reset-gpios = <&gpa3 4 GPIO_ACTIVE_LOW>`
(downstreamowy `disp-reset`), endpoint do `dsim0_out`.

Zasilanie to na razie **trzy `regulator-fixed`** (1,8 V / 3,0 V / 1,5-1,6 V) z komentarzem TODO —
prawdziwe rail-e są w PMIC-u `s2dos05`, którego mainline nie obsługuje. Ta sama konwencja, co przy
zasilaniu panelu dotykowego.

Uwaga: `simple-framebuffer` z S-Boota **zostaje** w `chosen`. Do czasu, aż DECON faktycznie ruszy,
to jedyne źródło obrazu; przy uruchamianiu DRM-a trzeba będzie je zdjąć (albo pozwolić
`drm_aperture`/sysfb przejąć pamięć), inaczej dwa sterowniki będą pisać po tym samym buforze.

## 4. Bramki

| bramka | wynik | log |
|---|---|---|
| `dt_binding_check` (DECON + DSIM) | **EXIT=0** | `build-logs/30-decon-dsim-binding.log` |
| `CHECK_DTBS` całego dtb | **EXIT=0**, zero uwag | `build-logs/31-decon-dsim-dt-check.log` |
| kompilacja obu sterowników po zmianie IRQ | **EXIT=0**, 0 uwag z plików | — |
| `checkpatch --strict` (0013-0015) | 0 błędów | — |
| 15 patchy na czystej bazie + `CHECK_DTBS` | **EXIT=0** | `build-logs/32-clean-worktree-15patches.log` |

## 5. Czego nadal brakuje do obrazu

1. **`dsc_reg_init()` w DECON** — bez konfiguracji enkoderów DSC i rozmiarów OUTFIFO ścieżka
   `DSCC+ENC0/1` nie wypuści danych (`docs/R2-decon-dsim-driver.md` §3.1).
2. **Bloki analogowe D-PHY** (BIAS/PLL/MC/MD_ANA_CON) — drugi zakres PHY (`0x19160000`), którego
   węzeł nawet nie opisuje, bo sterownik go jeszcze nie używa.
3. **PMIC `s2dos05`** — dopóki go nie ma, panel jest zasilany atrapami, więc sekwencja włączania
   nie jest realna.
4. Odczyty DSI (BTA/RXFIFO) — potrzebne do AID dimming, nie do zapalenia.
