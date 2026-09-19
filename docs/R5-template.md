# R5 — szablon minimalnego portu (z serii Ivaylo Ivanova dla exynos8895 i exynos2200)

**Odpowiedź:** Minimalny port SoC-a Samsunga do mainline to konsekwentnie **cztery kroki i sześć
typów plików**: (1) DT SoC-a + pinctrl DTSI, (2) DT płyty (framebuffer + gpio-keys + pstore),
(3) driver zegarów jako jeden plik `clk-exynosNNNN.c` + jedna linia w `Makefile` + nagłówek
`dt-bindings`, (4) po jednej linii `enum` w istniejących bindingach na każdy blok IP, który
recyklujesz. Szablon odtworzony dla 9820 znajduje się w `patches/` i **kompiluje się oraz przechodzi
`CHECK_DTBS` i `dt_binding_check`** (logi w `build-logs/`).

---

## 1. Seria exynos8895 (Galaxy S8, `dreamlte`) — commity w `torvalds/linux`

| commit | data | autor | co robi | pliki |
|---|---|---|---|---|
| `dcabaa8ae457` | 2024-09-20 | Ivaylo Ivanov | `arm64: dts: exynos: Add initial support for exynos8895 SoC` | **+** `exynos8895-pinctrl.dtsi` (+1094), **+** `exynos8895.dtsi` (+251) |
| `296621bfa3dd` | 2024-09-20 | Ivaylo Ivanov | `arm64: dts: exynos: Add initial support for Samsung Galaxy S8` | **+** `exynos8895-dreamlte.dts` (+126), **M** `dts/exynos/Makefile` (+1) |
| `9174fac3b302` | 2024-10-23 | Ivaylo Ivanov | `clk: samsung: Introduce Exynos8895 clock driver` | **+** `drivers/clk/samsung/clk-exynos8895.c` (+2803), **M** `drivers/clk/samsung/Makefile` (+1) |
| `a81dca057273` | 2024-10-23 | Ivaylo Ivanov | `dt-bindings: clock: samsung: Add Exynos8895 SoC` | **+** `Documentation/devicetree/bindings/clock/samsung,exynos8895-clock.yaml` |
| `fa986d107380` | 2024-10-23 | Ivaylo Ivanov | `arm64: dts: exynos8895: Add clock management unit nodes` | **M** `exynos8895.dtsi` |
| `9ad6c3bd1bcb` | 2024-10-23 | Ivaylo Ivanov | `arm64: dts: exynos8895: Add Multi Core Timer (MCT) node` | **M** `exynos8895.dtsi` |

Kolejność jest istotna: **najpierw DT z pinctrl i simple-framebufferem (shell w initramfs), dopiero
potem zegary i MCT.** Ten sam wzorzec w exynos2200:

| commit | data | co robi | pliki |
|---|---|---|---|
| `11715fcf1cca` | 2025-05-04 | initial SoC | **+** `exynos2200-pinctrl.dtsi` (+1765), **+** `exynos2200.dtsi` (+561) |
| `5430fd9e0794` | 2025-05-04 | initial board (Galaxy S22+) | **+** `exynos2200-g0s.dts` (+169), **M** `Makefile` (+1) |
| `11fd259b7a9c` | 2025-02-23 | clock driver | **+** `clk-exynos2200.c` (+3928), **M** `Makefile` (+1) |
| `6662c09c0ddf` | 2025-02-23 | binding zegarów | **+** `samsung,exynos2200-cmu.yaml` |

Zawartość minimalnego DT płyty (`torvalds/linux@296621bfa3dd:arch/arm64/boot/dts/exynos/exynos8895-dreamlte.dts`):
`compatible` płyty (:16), `chosen` (:19) z `simple-framebuffer` (:24-25), `memory@80000000` (:34),
`ramoops`/pstore (:47), rezerwacja framebuffera (:53), `gpio-keys` (:59-60). **To wszystko.**

## 2. Pełna lista plików, które trzeba dotknąć (stan mainline `linux@1200d84f4c0a`)

Wyprodukowana z drzewa, nie z pamięci — `git grep -l exynos8895` / `exynos2200`:

| kategoria | pliki | typ zmiany |
|---|---|---|
| DT SoC | `arch/arm64/boot/dts/exynos/exynosNNNN.dtsi`, `…-pinctrl.dtsi` | nowe |
| DT płyty | `arch/arm64/boot/dts/exynos/exynosNNNN-<board>.dts` | nowy |
| build DT | `arch/arm64/boot/dts/exynos/Makefile` | +1 linia |
| zegary | `drivers/clk/samsung/clk-exynosNNNN.c`, `drivers/clk/samsung/Makefile` | nowy + 1 linia |
| ID zegarów | `include/dt-bindings/clock/samsung,exynosNNNN.h` | nowy |
| binding zegarów | `Documentation/devicetree/bindings/clock/samsung,exynosNNNN-*.yaml` | nowy |
| płyty | `Documentation/devicetree/bindings/arm/samsung/samsung-boards.yaml` | +enum |
| CPU | `Documentation/devicetree/bindings/arm/cpus.yaml` | +enum (rdzeń Samsunga) |
| chipid | `Documentation/devicetree/bindings/hwinfo/samsung,exynos-chipid.yaml` | +enum |
| pinctrl | `Documentation/devicetree/bindings/pinctrl/samsung,pinctrl.yaml`, `…-wakeup-interrupt.yaml` | +enum |
| PMU | `Documentation/devicetree/bindings/soc/samsung/exynos-pmu.yaml` | +enum |
| sysreg | `Documentation/devicetree/bindings/soc/samsung/samsung,exynos-sysreg.yaml` | +enum |
| USI | `Documentation/devicetree/bindings/soc/samsung/exynos-usi.yaml` | +enum |
| UART | `Documentation/devicetree/bindings/serial/samsung_uart.yaml` | +enum |
| HSI2C | `Documentation/devicetree/bindings/i2c/i2c-exynos5.yaml` | +enum |
| MCT | `Documentation/devicetree/bindings/timer/samsung,exynos4210-mct.yaml` | +enum |
| drivery, które tylko dostają compatible | `drivers/pinctrl/samsung/pinctrl-exynos-arm64.c`, `pinctrl-samsung.{c,h}`, `drivers/tty/serial/samsung_tty.c`, `drivers/i2c/busses/i2c-exynos5.c`, `drivers/soc/samsung/exynos-usi.c` | +wpis w tablicy |
| (2200 dodatkowo) | `drivers/phy/samsung/phy-exynos5-usbdrd.c`, `drivers/usb/dwc3/dwc3-exynos.c`, `MAINTAINERS` | +wpis |

## 3. Szablon odtworzony dla 9820 — co jest w `patches/`

| patch | zawartość | dowód |
|---|---|---|
| `0001-dt-bindings-Add-Exynos9820-SoC-compatibles.patch` | +enum w 10 bindingach (cpus: `samsung,mongoose-m4`; boards: `samsung,beyond2lte`; pinctrl + wakeup-eint; uart; usi; hsi2c; pmu; sysreg; mct) | `dt_binding_check` OK |
| `0002-dt-bindings-clock-Add-Exynos9820-SoC-clock-controller.patch` | nowy `samsung,exynos9820-clock.yaml` (CMU_TOP/APM/PERIS/PERIC0) + `include/dt-bindings/clock/samsung,exynos9820.h` (413 ID, z `chiffathefox/exynos-9820-mainline-linux@0aeca03f7acd`) | przykład z bindingu kompiluje się |
| `0003-arm64-dts-exynos-Add-minimal-Exynos9820-SoC-and-Galaxy-S10+.patch` | `exynos9820.dtsi` (411 linii), `exynos9820-pinctrl.dtsi` (647 linii, z `chiffathefox/u-boot@c5afa30840d9`), `exynos9820-beyond2lte.dts` (165 linii), +1 linia w `Makefile` | `dtbs` + `CHECK_DTBS` OK |

Zawartość `exynos9820-beyond2lte.dts` odwzorowuje szablon dreamlte: `simple-framebuffer` @0xca000000,
`gpio-keys` (vol±, Bixby/„wink", power), `reserved-memory` na framebuffer, `hsi2c10` +
`touchscreen@48` (`samsung,s6sy761`), `serial0` jako `stdout-path`.

**Świadome odstępstwa od u-boot DT (i dlaczego):**

- brak `memory@…` i `ramoops` — banki RAM i region pstore nie zostały zweryfikowane na sprzęcie
  (brief §7.2: nie zgadujemy);
- brak węzłów UFS / USB / ACPM / PMIC `s2mps19` — nie mają bindingów w mainline; TSP dostaje
  tymczasowe `regulator-fixed` z komentarzem TODO;
- brak `idle-states` — w u-boot DT są `status = "disabled"`, a `arm,psci-suspend-param` nie jest
  zweryfikowany (autor portu: „if I let more cores enter C2 they hang", `pmaports!8999`);
- `wakeup-interrupt-controller` dostaje `samsung,exynos9820-wakeup-eint` + fallbacki 850/7 —
  wariant bez `interrupts`, zgodnie ze schematem mainline (jak exynos9810).

## 4. Bramki weryfikacyjne — wyniki

```
make LLVM=1 ARCH=arm64 defconfig                                   EXIT=0   build-logs/01-defconfig.log
make LLVM=1 ARCH=arm64 exynos/exynos9820-beyond2lte.dtb            EXIT=0   build-logs/02-dtb.log
make LLVM=1 ARCH=arm64 CHECK_DTBS=y exynos/exynos9820-beyond2lte.dtb  EXIT=0, 0 warnings  build-logs/03-check-dtbs.log
make LLVM=1 ARCH=arm64 dt_binding_check DT_SCHEMA_FILES=<11 plików>   EXIT=0  build-logs/04-dt-binding-check.log
scripts/checkpatch.pl --strict (3 patche)                          0 errors build-logs/05-checkpatch.log
```

Weryfikacja na **czystym drzewie** (git worktree z bazy + tylko te 3 patche):
`git apply --check` OK, `CHECK_DTBS` OK, identyczna suma sha256 dtb —
`build-logs/13-clean-worktree-verify.log`.

checkpatch zgłasza tylko dwa ostrzeżenia klasy „false positive": „Unknown commit id" (commity z
innych repozytoriów, cytowane w opisach) oraz „does MAINTAINERS need updating?" (pliki wpadają pod
istniejący wildcard `ARM/SAMSUNG EXYNOS ARM ARCHITECTURES`).

Artefakt: `arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dtb`, 16 KB,
sha256 `4fcba6b623d07f8e6549c6c64661155944d3b3e3242896ea87e67cf80ab7fdb3`
(baza: `linux@1200d84f4c0a929a0780180d25063d93773be79c`, v7.2.0).

## Czego nie udało się ustalić

- **Oryginalne serie patchy na lore.kernel.org** — `lore.kernel.org/all/?q=exynos8895&x=A` zwraca
  403 / stronę anty-botową (log `build-logs/12-r5-lore.log`). Zamiast message-id cytowane są
  commity w `torvalds/linux` (hash + data + autor + lista plików z GitHub API) — informacja
  równoważna, inny nośnik.
- Czy driver zegarów 9820 z drzewa chiffa jest w takim stanie, żeby go wysłać upstream (styl,
  podział na CMU) — **nie oceniano**; ten raport nie dotyka `clk-exynos9820.c` poza R1.
