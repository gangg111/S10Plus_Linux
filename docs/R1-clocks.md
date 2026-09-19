# R1 — zegary: czy mainline ma driver zegarów dla Exynos 9820 i czy wystawia CMU_G3D?

**Odpowiedź:** NIE — w mainline (v7.2.0, `linux@1200d84f4c0a`) **nie ma żadnego** drivera zegarów dla
exynos9820 (zero plików, zero wystąpień stringa „9820"); poza mainline istnieje kompletny
out-of-tree driver (`clk-exynos9820.c`, 2516 linii), ale **on też nie ma bloku CMU_G3D** — ma tylko
źródła GPU w CMU_TOP (PLL_G3D + CLKCMU_G3D_SWITCH). GPU to zatem liga „napisz brakujący blok
drivera zegarów + power domain", nie „dopisz węzeł DT".

## Dowody

### Mainline: nic

Przeszukane (drzewo `linux@1200d84f4c0a929a0780180d25063d93773be79c`, v7.2.0):

```
grep -ril "9820" drivers/clk/samsung/ include/dt-bindings/clock/ \
                 Documentation/devicetree/bindings/clock/     -> 0 trafień
grep -ril "exynos9820|exynos-9820" . (całe drzewo, bez .git)  -> 0 trafień
```

Log: `build-logs/06-r1-grep-mainline.log`.

Dostępne w mainline drivery Exynos ARM64 (`linux@1200d84f4c0a:drivers/clk/samsung/Makefile:18-30`):
exynos5433, exynos7, exynos7870, exynos7885, exynos850, **exynos8895**, exynos990,
**exynos2200**, exynosautov9/v920, gs101, fsd. Wszystkie pod jednym symbolem
`CONFIG_EXYNOS_ARM64_COMMON_CLK` (`…:drivers/clk/samsung/Kconfig:75-77`) — dodanie 9820 to jedna
linia w Makefile, bez nowego Kconfiga.

### Out-of-tree: jest driver, nie ma CMU_G3D

Repo: `chiffathefox/exynos-9820-mainline-linux@0aeca03f7acddd3aacdf25b01fede0ee3c724d48`
(branch `exynos9820-7.2-rc2`, to dokładnie ten commit, który pinuje pmaports —
`pmaports@78958726:device/testing/linux-postmarketos-exynos9820/APKBUILD:6`).

Zarejestrowane bloki CMU (`…:drivers/clk/samsung/clk-exynos9820.c`):

| blok | compatible | linia |
|---|---|---|
| CMU_PERIS | `samsung,exynos9820-cmu-peris` | 206 (`CLK_OF_DECLARE`) |
| CMU_TOP   | `samsung,exynos9820-cmu-top`   | 2472 (`CLK_OF_DECLARE`) |
| CMU_FSYS1 | `samsung,exynos9820-cmu-fsys1` | 2488 |
| CMU_PERIC0| `samsung,exynos9820-cmu-peric0`| 2491 |
| CMU_FSYS0A| `samsung,exynos9820-cmu-fsys0a`| 2494 |
| CMU_APM   | `samsung,exynos9820-cmu-apm`   | 2497 |

**Brak `samsung,exynos9820-cmu-g3d`.** Autor portu potwierdza to wprost:
„Clock driver only covers clock banks that have clock sources important to mainline DT nodes.
I am adding new blocks on as needed basis." (`pmaports!8999`, sekcja *Clock Driver*).

Co dla GPU **jest** (wszystko w CMU_TOP, czyli źródła, nie leaf-clocki bloku G3D):

```
clk-exynos9820.c:1520  #define PLL_LOCKTIME_PLL_G3D           0x0008
clk-exynos9820.c:1528  #define PLL_CON0_PLL_G3D               0x0140
clk-exynos9820.c:1616  #define CLK_CON_DIV_CLKCMU_G3D_SWITCH  0x1870
clk-exynos9820.c:1682  #define CLK_CON_GAT_GATE_CLKCMU_G3D_SWITCH 0x208c
clk-exynos9820.c:1893  PLL(pll_0818x, CLK_FOUT_PLL_G3D, "fout_pll_g3d", "oscclk", …)
clk-exynos9820.c:2242  DIV(CLK_DOUT_CMU_G3D_SWITCH, "dout_cmu_g3d_switch", "gout_cmu_g3d_switch", …)
clk-exynos9820.c:2395  GATE(CLK_GOUT_CMU_G3D_SWITCH, "gout_cmu_g3d_switch", "fout_pll_shared2", …)
```

Adres bazowy CMU_TOP: `0x1a240000` (`clk-exynos9820.c:1518` — komentarz nagłówkowy bloku;
węzeł DT: `chiffathefox/u-boot@c5afa30840d9:dts/upstream/src/arm64/exynos/exynos9820.dtsi:619-627`).

### Co to znaczy dla B0 (bramka „czy mainline ma zegary GPU")

Bramka **zaliczona negatywnie, ale nie na czerwono**: praca do wykonania to dopisanie bloku
CMU_G3D (mux `mout_g3d_switch/mout_g3d_pll`, div, gate’y IP Mali) do istniejącego drivera —
plik i infrastruktura (`samsung_cmu_info`, `exynos_arm64_register_cmu`) już są. Osobnym,
niepoliczonym ryzykiem pozostaje domena zasilania G3D (SMC/EL3), której ten raport nie dotyka.

## Czego nie udało się ustalić

- **Offsety rejestrów CMU_G3D** (adres bazowy bloku, mux/div/gate). Szukane w:
  `clk-exynos9820.c` (jest tylko strona TOP), `u-boot@c5afa30840d9:…/exynos9820.dtsi` (brak węzła),
  `LineageOS/android_kernel_samsung_exynos9820@7d08ec36:arch/arm64/boot/dts/exynos/exynos9820.dts`
  (to DT SoC-a bez sekcji G3D). Downstreamowe źródło prawdy to `drivers/gpu/arm/…` (Mali DDK)
  + `drivers/soc/samsung/cal-if/…` w downstreamie Samsunga — **nie sprawdzone w tej fazie**.
- Czy włączenie domeny G3D idzie przez SMC do EL3 na 9820 — **NIE ZNALEZIONO** dowodu w otwartych
  drzewach; teza z briefu (§3) pozostaje niepotwierdzona i niezaprzeczona.
