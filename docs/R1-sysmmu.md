# SYSMMU dla Exynos 9820

**Odpowiedź: sterownika nie trzeba pisać — mainline już go ma.** SYSMMU w 9820 to **wersja 7**,
a `drivers/iommu/exynos-iommu.c` obsługuje v7 od dawna, z tym samym stringiem `compatible`
(`samsung,exynos-sysmmu`), którego używa downstream. Brakowało **opisu w DT** — i to zostało dopisane
(`patches/0039`), razem z węzłem CMU_DPU, na którym te SYSMMU wiszą.

## 1. Dowód, że to jest v7 obsługiwane przez mainline

Porównanie mapy rejestrów: mainline `sysmmu_v7_variant`
(`linux@1200d84f4c0a:drivers/iommu/exynos-iommu.c:392-405`) kontra downstream 9820
(`LineageOS/android_kernel_samsung_exynos9820@7d08ec36:drivers/iommu/exynos-iommu.h`):

| pole | mainline v7 | downstream 9820 | cytat downstreamu |
|---|---|---|---|
| `pt_base` | 0x0c | `REG_PT_BASE_PPN` 0x00C | `:131` |
| `flush_all` | 0x10 | `REG_MMU_FLUSH` 0x010 | `:132` |
| `flush_entry` | 0x14 | `REG_MMU_FLUSH_ENTRY` 0x014 | `:133` |
| `flush_range` | 0x18 | `REG_MMU_FLUSH_RANGE` 0x018 | `:134` |
| `flush_start` | 0x20 | `REG_FLUSH_RANGE_START` 0x020 | `:135` |
| `flush_end` | 0x24 | `REG_FLUSH_RANGE_END` 0x024 | `:136` |
| `int_status` | 0x60 | `REG_INT_STATUS` 0x060 | `:139` |
| `int_clear` | 0x64 | `REG_INT_CLEAR` 0x064 | `:140` |
| `fault_va` | 0x70 | `REG_FAULT_ADDR` 0x070 | `:157` |
| `fault_info` | 0x78 | `REG_FAULT_TRANS_INFO` 0x078 | `:158` |

**Dziesięć na dziesięć.** Do tego `REG_MMU_CAPA0_V7` 0x870 i `REG_MMU_CAPA1_V7` 0x874 w downstreamie
(`:150-151`) to dokładnie mainline’owe `REG_V7_CAPA0`/`REG_V7_CAPA1` (`exynos-iommu.c:170-171`),
używane do wykrycia wariantu z VM.

Dekodowanie wersji też się zgadza, mimo innego zapisu makr: mainline bierze `reg[31:21]` i dzieli na
major `reg[31:28]` / minor `reg[27:21]`; downstream bierze `reg[31:17]`, major `reg[31:28]`,
minor `reg[27:21]` i dodatkowo rewizję `reg[20:17]`, której mainline nie czyta. Major i minor
wychodzą **identycznie** — różnica dotyczy tylko ignorowanego pola rewizji.

Poszlaka strukturalna: okno `reg` ma w downstreamowym DT rozmiar **0x9000**, czyli obejmuje blok
VM pod 0x8000 — mainline sam wybierze `sysmmu_v7_vm_variant`, jeśli `CAPA1` zgłosi VCR.

**Czego to nie przesądza:** faktycznej wartości `REG_MMU_VERSION` na krzemie. Sterownik wypisuje ją
przy probe (`dev_dbg "hardware version: %d.%d"`), więc pierwszy boot z UART-em to rozstrzygnie.
Gdyby okazało się, że major < 7, wystarczyłby inny wariant — nie nowy sterownik.

## 2. Co zostało dopisane w DT

`patches/0039`

| węzeł | adres | IRQ (nie-bezpieczne) | zegar |
|---|---|---|---|
| `sysmmu_dpud0` | `0x190a0000` | SPI 212 | `CLK_GOUT_DPU_SYSMMU_D0_CLK` |
| `sysmmu_dpud1` | `0x190b0000` | SPI 214 | `CLK_GOUT_DPU_SYSMMU_D1_CLK` |
| `sysmmu_dpud2` | `0x190c0000` | SPI 216 | `CLK_GOUT_DPU_SYSMMU_D2_CLK` |
| `cmu_dpu` | `0x19000000` | — | `oscclk` + `CLK_DOUT_CMU_DPU_BUS` z CMU_TOP |

Wszystkie trzy dostają `power-domains = <&pd_dpu>` i `#iommu-cells = <0>`.

Skąd numery przerwań: downstreamowy DT podaje parami, np. `interrupts = <0x0 0xd4 0x0 0x0 0xd3 0x0>`
dla `sysmmu@190A0000` (`exynos9820.dts:2986-3002`). Że **pierwsze jest nie-bezpieczne**, wynika
z kodu: zwykłe przerwanie to `platform_get_irq(pdev, 0)`
(`…/drivers/iommu/exynos-iommu.c:509`), a bezpieczne `platform_get_irq(pdev, 1)` (`:225`,
używane tylko gdy jest `sysmmu,secure-irq`). Mainline nie używa bezpiecznego, więc opisujemy jedno.

Przypisanie zegarów D0/D1/D2 do adresów wynika z kolejności: downstream ma kolejne indeksy zegarów
(206, 207, 208) dla węzłów 190a/190b/190c. Nazwy portów to `"VGRFS, GF0"`, `"VGF, GF1"`,
`"VGS, VG, WB"` — **grup DPP nie mapowałem na numery SYSMMU**, więc gdyby na sprzęcie okazało się,
że kolejność jest inna, poprawka to zamiana trzech identyfikatorów zegarów.

Przy okazji: `patches/0017` pozwala węzłom CMU mieć `power-domains` — CMU_DPU leży w domenie DPU
i traci stan przy jej wyłączeniu (downstreamowe `dpu_save[]` zapisuje i odtwarza właśnie rejestry
CMU_DPU: `flexpmu_cal_local_exynos9820.h:292-293`).

## 3. Bramki

| bramka | wynik | log |
|---|---|---|
| `CHECK_DTBS` całego dtb | **EXIT=0**, zero uwag | `build-logs/29-sysmmu-check.log` |
| `dt_binding_check` (clock + sysmmu) | **EXIT=0** | tamże |
| `checkpatch --strict` (0011, 0012) | **0 błędów, 0 ostrzeżeń** | — |

## 4. Co dalej blokuje obraz

1. **Bindingi i węzły DECON/DSIM** — teraz mają już wszystko, czego potrzebowały (zegary z CMU_DPU,
   domena zasilania, SYSMMU do `iommus = <…>`).
2. `dsc_reg_init()` i rozmiary OUTFIFO w sterowniku DECON (`docs/R2-decon-dsim-driver.md` §3).
3. Bloki analogowe D-PHY.
