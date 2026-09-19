# CMU_DPU — blok zegarów dla pipeline’u wyświetlacza

**Odpowiedź:** dopisany. `CMU_DPU` ma bazę **0x19000000**, jeden mux użytkownika, jeden dzielnik
i 22 bramki (w tym `ACLK_DECON`, `ACLK_DPP`, `ACLK_DMA`, APB dla DECON0/DPP/DMA/**DSIM0**, trzy
SYSMMU i infrastruktura magistrali). Wszystkie offsety, szerokości pól i **rodzic każdej bramki**
pochodzą z tablic zegarowych downstreamu — nic nie jest zgadnięte.

Artefakty:
- `patches/0011` — nasza część w serii mainline
  (compatible `samsung,exynos9820-cmu-dpu` + 25 ID zegarów w `samsung,exynos9820.h`).
- `patches-oot/0001-clk-samsung-exynos9820-add-CMU_DPU.patch` — sam blok w kodzie, **przeciw
  drzewu, w którym ten driver żyje**: `chiffathefox/exynos-9820-mainline-linux@0aeca03f7acd`.

## 1. Dlaczego dwa patche zamiast jednego

Driver `clk-exynos9820.c` **nie jest w mainline** (R1) i nie da się go tam wstawić bez dwóch
brakujących typów PLL: `pll_0817x` i `pll_1018x` (mainline `drivers/clk/samsung/clk-pll.h` ma
tylko `pll_0818x` i `pll_0822x`). Import całego drivera do naszej serii byłby podaniem cudzej
pracy jako naszej i tak czy tak wymagałby wcześniejszego upstreamu PLL-i. Dlatego:

| co | gdzie trafia | czyja praca |
|---|---|---|
| compatible + ID zegarów | nasza seria mainline (patch 0007) | nasza |
| blok CMU_DPU w kodzie | drzewo chiffy (patch OOT) | nasza |
| reszta drivera (2516 linii) | drzewo chiffy | chiffathefox |
| `pll_0817x`, `pll_1018x` | do upstreamu **przed** driverem | do zrobienia |

## 2. Skąd liczby

`LineageOS/android_kernel_samsung_exynos9820@7d08ec36:drivers/soc/samsung/cal-if/exynos9820/`

| co | wartość | cytat |
|---|---|---|
| baza bloku | `0x19000000`, rozmiar `0x8000` | `cmucal-sfr.c:24` — `SFR_BLOCK(CMU_DPU, 0x19000000, 0x8000)` |
| mux użytkownika | `PLL_CON0_MUX_CLKCMU_DPU_BUS_USER` @ `0x100`, `MUX_SEL` bit 4, szerokość 1 | `cmucal-sfr.c:209`, `:3163` |
| rodzice muxa | `{ OSCCLK_DPU, CLKCMU_DPU_BUS }` → `{ "oscclk", "dout_cmu_dpu_bus" }` | `cmucal-node.c:696-698` |
| dzielnik | `CLK_CON_DIV_DIV_CLK_DPU_BUSP` @ `0x1800`, bity 0..2 | `cmucal-sfr.c:450`, `:3677` |
| bramki | bit **21** (`CG_VAL`) | `cmucal-sfr.c:5347` (przykład dla `ACLK_DECON`) |
| rodzic każdej bramki | z `CLK_GATE(<node>, <parent>, …)` | `cmucal-node.c:1845-…` |

Przykład, że rodzic nie jest zgadywany: `ACLK_DECON` → `MUX_CLKCMU_DPU_BUS_USER`, a `PCLK`-i
(np. `SYSREG_DPU`, `AD_APB_MIPI_DSIM0_PCLKS`) → `DIV_CLK_DPU_BUSP` — dokładnie tak, jak deklaruje
`cmucal-node.c`.

## 3. Co jest w bloku

```
mux    mout_dpu_bus_user   (oscclk | dout_cmu_dpu_bus)
 └ div dout_dpu_busp       (÷1..8)
bramki krytyczne : cmu_dpu_pclk, busd_clk, busp_clk, lhm_axi_p_clk,
                   lhs_axi_d0/1/2_clk, d_tzpc_pclk
bramki funkcyjne : aclk_decon, aclk_dma, aclk_dpp,
                   decon0_pclkm/pclks, dpp_pclkm/pclks, dma_pclkm/pclks,
                   dsim0_pclks, sysreg_pclk, sysmmu_d0/1/2_clk
```

Bramki magistrali i CMU są `CLK_IS_CRITICAL` (jak analogiczne w innych blokach tego drivera,
np. `gout_fsys0a_rstnsync_clk_fsys0a_bus`), reszta `CLK_SET_RATE_PARENT`.

## 4. Bramki weryfikacyjne

| bramka | wynik | log |
|---|---|---|
| patch OOT stosuje się na czysty plik chiffy | OK (`patch --dry-run`) | `build-logs/26-cmu-dpu-verify.log` |
| kompilacja drivera z blokiem | **EXIT=0**, 0 uwag z pliku, 78 984 B | tamże |
| `dt_binding_check` (`samsung,exynos9820-clock.yaml`) | **EXIT=0** | `build-logs/25-cmu-dpu-binding-check.log` |
| `checkpatch --strict` (0007 i OOT) | 0 błędów | `build-logs/05-checkpatch.log`, log 26 |

**Uczciwie o kompilacji:** żeby w ogóle skompilować cudzy driver w drzewie mainline, użyłem
lokalnego shimu na dwa brakujące typy PLL (`#define pll_0817x pll_0818x`, `#define pll_1018x
pll_0822x`). Shim **nie jest częścią żadnego patcha** i nie wpływa na blok CMU_DPU (żadna z jego
stałych nie dotyczy PLL-i). Dowodzi to poprawności typów i makr naszego bloku, nie tego, że
zegary faktycznie wystartują — to zweryfikuje dopiero `clk_summary` na sprzęcie.

## 5. Co to odblokowuje, a co dalej blokuje

**Odblokowane:** węzły DT dla DECON i DSIM mogą już mieć `clocks = <&cmu_dpu CLK_GOUT_DPU_…>`.

**Nadal brakuje**, zanim ekran ruszy:
1. ~~**Domena zasilania `pd-dpu`**~~ — **zrobiona**, patrz §6.
2. **SYSMMU/IOMMU** — DPP czyta framebuffer przez SYSMMU_DPUD0/1/2 (bramki są, sterownika nie ma).
3. Bramki, których świadomie nie dopisałem (BTM, PPMU, WB_MUX, MCD, DECON1/2, DSIM1) — do dodania,
   gdy będą potrzebne, tą samą metodą.
4. `pll_0817x`/`pll_1018x` + upstream całego drivera zegarów — warunek wejścia do mainline.

## 6. Domena zasilania DPU (dopisana)

Okazało się prostsze, niż zakładałem w §5: **Exynos9820 używa tego samego bloku power-domain co
starsze Exynosy**, który mainline już obsługuje (`drivers/pmdomain/samsung/exynos-pm-domains.c`) —
rejestr `CONFIGURATION` z żądaniem zasilania i `STATUS` 4 bajty wyżej. Różnica jest jedna: maska.

| co | wartość | cytat |
|---|---|---|
| `DPU_CONFIGURATION` | `0x15860000 + 0x1e00`, bit 0 | `…/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h:287` (`dpu_on[]`) |
| `DPU_STATUS` | `0x15860000 + 0x1e04`, bit 0 | `…:288` (czekanie na bit 0) |
| wyłączenie | zapis 0 do bitu 0 i czekanie na 0 | `…:354-355` (`dpu_off[]`) |
| maska (`local_pwr_cfg`) | **0x1** (Exynos4210 ma 0x7, Exynos5433 0xf) | jw. — sekwencja operuje wyłącznie na bicie 0 |

Sekwencje `dpu_on[]`/`dpu_off[]` downstreamu to **dokładnie** to, co robi mainline’owy
`exynos_pd_power()`: zapis do bazy i odpytywanie `base + 0x4`. Nic więcej (żadnych SMC, żadnych
dodatkowych rejestrów) — inaczej niż przy GPU, gdzie brief podejrzewał ścieżkę przez EL3.

Patche (rozdzielone zgodnie z regułami checkpatcha):

| patch | co |
|---|---|
| `patches/0020` | compatible `samsung,exynos9820-pd` |
| `patches/0021` | `exynos9820_cfg = { .local_pwr_cfg = 0x1 }` + wpis w `of_match` |
| `patches/0038` | węzeł `pd_dpu: power-domain@15861e00` w `exynos9820.dtsi` |

Bramki: kompilacja `exynos-pm-domains.c` **EXIT=0** (0 uwag z pliku), `dt_binding_check`
(`pd-samsung.yaml`) **EXIT=0**, `CHECK_DTBS` całego dtb **EXIT=0**, `checkpatch --strict` 0 błędów
(`build-logs/27-pd-dpu-check.log`). Cała seria **10 patchy stosuje się sekwencyjnie na czystą bazę**
`1200d84f4c0a` i dtb się buduje — `build-logs/28-clean-worktree-10patches.log`.

**Czego to nie dowodzi:** że domena faktycznie się włączy. Sprawdzalne dopiero na sprzęcie —
`/sys/kernel/debug/pm_genpd/pm_genpd_summary` powinien pokazać `DPU` w stanie `on`.

Kolejny blocker w łańcuchu: **SYSMMU** (DPP czyta framebuffer przez SYSMMU_DPUD0/1/2) i bindingi
dla samych węzłów DECON/DSIM.
