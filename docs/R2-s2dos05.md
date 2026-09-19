# PMIC wyświetlacza S2DOS05

**Odpowiedź: sterownika nie trzeba pisać — mainline już go ma.** Są `drivers/mfd/sec-i2c.c`
(compatible `samsung,s2dos05`), `drivers/regulator/s2dos05-regulator.c` i binding
`Documentation/devicetree/bindings/mfd/samsung,s2dos05.yaml`. Brakowało **magistrali, na której ten
układ siedzi** — a to pociągnęło za sobą blok zegarów CMU_CMGP.

Artefakty: `patches/0011` (ID zegarów + compatible CMU_CMGP), `patches/0040` (węzły DT: CMU_CMGP,
I2C, PMIC, przepięcie zasilania panelu), `patches-oot/0001` (blok CMU_CMGP w driverze zegarów,
razem z CMU_DPU).

## 1. Znalezienie magistrali

Downstreamowy `s2dos05_pmic@60` wisi na `hsi2c@15D50000` (`beyond2lte_eur_open_26.dts:8271`
mapuje `fragment@85` → `hsi2c_44`). To **nie** jest zwykłe PERIC I2C, tylko kontroler w bloku
**CMGP** (niskiego poboru).

Który to instancja? Ustalone z danych, nie z założenia — porównanie wszystkich siedmiu
kontrolerów CMGP w `exynos9820.dts`:

| adres | piny | zegar bramkowany |
|---|---|---|
| 15D10000 | gpm2/gpm3 | id 0x72 |
| 15D30000 | gpm6/gpm7 | id 0x73 |
| **15D50000** | **gpm10/gpm11** | **id 0x74** |
| 15D70000 | gpm14/gpm15 | id 0x75 |
| 15D20000 / 15D40000 / 15D60000 | gpm4/5, gpm8/9, gpm12/13 | id 0x7b-0x7d (rodzina USI) |

Cztery kolejne identyfikatory 0x72-0x75 to bramki `I2C_CMGP0..3_IPCLKPORT_PCLK`, więc
`15D50000` = **I2C_CMGP2**. Zgadza się to z tablicą zegarów: `DIV_CLK_I2C_CMGP2` @0x1810
i bramki `I2C_CMGP2_IPCLKPORT_{IPCLK,PCLK}` @0x2024/0x2028.

## 2. CMU_CMGP (dopisany blok zegarów)

Baza **0x15c00000** (`cmucal-sfr.c:19`). Drzewo — każdy element z cytatem, rodzice z `CLK_GATE()`
w `cmucal-node.c`:

```
mout_cmgp_bus_user  (PLL_CON0 @0x100, bit 4)   <- oscclk | dout_cmu_cmgp_bus (z CMU_APM)
 ├ dout_cmgp_bus    (@0x1804, bity 0..2)
 │   ├ gout_cmgp_cmu_cmgp_pclk  @0x2000  (krytyczny)
 │   ├ gout_cmgp_bus_clk        @0x2038  (krytyczny)
 │   ├ gout_cmgp_gpio_pclk      @0x2010  (krytyczny)
 │   ├ gout_cmgp_sysreg_pclk    @0x206c
 │   └ gout_cmgp_i2c2_pclk      @0x2028
 └ mout_cmgp_i2c2   (@0x100c, bit 0)      <- oscclk | mout_cmgp_bus_user
     └ dout_cmgp_i2c2 (@0x1810, bity 0..3)
         └ gout_cmgp_i2c2_ipclk @0x2024
```

**Uczciwie:** pierwszym rodzicem obu muxów jest oscylator **RCO bloku CMGP**, nie główny 26 MHz.
Jego częstotliwości nie ma w żadnym dostępnym źródle (mainline dla exynos850 zakłada 49,152 MHz,
ale to inny SoC), a muxy zostają na ścieżce z CMU_APM — więc jest modelowany jako `oscclk`
z komentarzem w kodzie. Gdyby ktoś kiedyś przełączył mux na RCO, wyliczona częstotliwość będzie zła.

## 3. Węzły DT

```
cmu_cmgp@15c00000   (samsung,exynos9820-cmu-cmgp, wejście z cmu_apm CLK_DOUT_CMU_CMGP_BUS)
i2c@15d50000        (samsung,exynos9820-hsi2c, IRQ 81, piny gpm10-0/gpm11-0, zegary z CMU_CMGP)
  └ pmic@60         (samsung,s2dos05)
       regulators: buck  -> panel_vddr (1,5-1,6 V)
                   ldo1  -> panel_vdd3 (1,8 V)
                   ldo4  -> panel_vci  (3,0 V)
```

Panel dostaje teraz **prawdziwe regulatory** zamiast trzech `regulator-fixed`, które zniknęły
z DT płyty. Napięcia i przypisanie rail-i pochodzą z downstreamowego węzła
`s2dos05_pmic@60` (`beyond2lte_eur_open_26.dts:6529-6552`) i zgadzają się z tym, co binding panelu
nazywa `vdd3`/`vci`/`vddr` (te same role co w S6E3HA8 z Galaxy S9).

Grupa pinów `hsi2c2_bus` (gpm10-0, gpm11-0, funkcja 3) dopisana do `exynos9820-pinctrl.dtsi`
na podstawie downstreamowego `hsi2c44-bus`.

## 4. Bramki

| bramka | wynik | log |
|---|---|---|
| kompilacja drivera zegarów z CMU_CMGP | **EXIT=0**, 0 uwag z pliku | `build-logs/36-s2dos05-check.log` |
| `CHECK_DTBS` całego dtb | **EXIT=0**, zero uwag | tamże |
| `dt_binding_check` (zegary + s2dos05) | **EXIT=0** | tamże |
| `checkpatch --strict` (0020, 0021) | 0 błędów | — |
| 21 patchy na czystej bazie + `CHECK_DTBS` | **EXIT=0** | `build-logs/37-clean-worktree-21patches.log` |
| patch OOT na czysty plik chiffy | `patch --dry-run` OK | — |

## 5. Co zostaje

Z listy blokerów obrazu znika zasilanie panelu. Zostaje:

1. **Odczyty DSI** (BTA + RXFIFO) — potrzebne do AID dimming, nie do zapalenia.
2. **Pierwsze uruchomienie na sprzęcie** — nic z tego łańcucha (zegary → domena → SYSMMU →
   DECON+DSC → D-PHY → PMIC → panel) nie było testowane.
3. Drobiazgi: RCO CMGP, `simple-framebuffer` do zdjęcia przy starcie DRM-a, PMIC-owe ELVDD/ELVSS
   (mainline binding opisuje tylko buck i ldo1-4).
