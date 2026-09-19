# R3 — dotyk

**Odpowiedź:** Kontroler to Samsung **Y771** (rodzina S6SY76x), a mainline **ma** dla niego sterownik —
`drivers/input/touchscreen/s6sy761.c` (544 linie, I2C, compatible `samsung,s6sy761`) — i jest on
**empirycznie potwierdzony na tym SoC**: port pmOS dla exynos9820 włącza `CONFIG_TOUCHSCREEN_S6SY761=y`
i opisuje panel dotykowy pod adresem 0x48 na `hsi2c10`, a autor portu raportuje działający dotyk na
oryginalnym panelu. Downstreamowy odpowiednik ma 12 552 linie — czyli mainline’owy driver jest ~23×
mniejszy i wystarcza.

## Dowody

### Co jest w telefonie (downstream)

- `CONFIG_TOUCHSCREEN_SEC_TS_Y771=y`
  (`LineageOS/android_kernel_samsung_exynos9820@7d08ec36:arch/arm64/configs/exynos9820-beyond2lte_defconfig:2286`).
- Sterownik: katalog `drivers/input/touchscreen/sec_ts/y771/` (jest też wariant `y771_d`).
  Interfejs: **I2C** — `static struct i2c_driver sec_ts_driver` (`…/y771/sec_ts.c:3210`),
  tablica id `{ SEC_TS_I2C_NAME, 0 }` (`:3190`).
- Rozmiar (wc -l, pobrane pliki — log `build-logs/09-r3-y771-wc.log`):

| plik | linie |
|---|---|
| `sec_ts.c` | 3251 |
| `sec_ts.h` | 965 |
| `sec_ts_fn.c` | 6666 |
| `sec_ts_fw.c` | 1013 |
| `sec_ts_ioctl.c` | 333 |
| `sec_ts_only_vendor.c` | 296 |
| Kconfig + Makefile | 28 |
| **razem** | **12 552** |

### Co jest w mainline

- `linux@1200d84f4c0a:drivers/input/touchscreen/s6sy761.c` — 544 linie,
  `{ .compatible = "samsung,s6sy761" }` (`:516`), rejestry protokołu w `:19-57`
  (`S6SY761_DEVICE_ID 0x52`, `S6SY761_READ_ONE_EVENT 0x60`, …), zasilanie przez
  `regulator_bulk` (avdd + vdd).
- Binding: `linux@1200d84f4c0a:Documentation/devicetree/bindings/input/touchscreen/samsung,s6sy761.yaml:17`
  (`const: samsung,s6sy761`), przykład w `:45`.

### Most między Y771 a s6sy761 — dowód, nie analogia

Port mainline dla exynos9820 opisuje ten sam układ przez mainline’owy compatible:

```
chiffathefox/u-boot@c5afa30840d9:dts/upstream/src/arm64/exynos/exynos9820-common.dtsi:151-165
  &hsi2c10 {
      clock-frequency = <400000>;
      touchscreen@48 {
          compatible = "samsung,s6sy761";
          reg = <0x48>;
          avdd-supply = <&ldo27m>;      /* tsp_avdd 3.0 V, s2mps19 */
          vdd-supply  = <&ldo19m>;      /* tsp_io   1.8 V, s2mps19 */
          interrupts-extended = <&gpa1 0 IRQ_TYPE_LEVEL_LOW>;
          pinctrl-0 = <&ts_int>;        /* gpa1-0, EINT */
      };
  };
```

Regulatory: `…/exynos9820-common.dtsi:131-146` (`ldo19m` = `tsp_io` 1.8 V, `ldo27m` = `tsp_avdd` 3.0 V,
PMIC `samsung,s2mps19-pmic` na ACPM).

Konfiguracja jądra pmOS: `CONFIG_TOUCHSCREEN_S6SY761=y`
(`pmaports@78958726:device/testing/linux-postmarketos-exynos9820/config-postmarketos-exynos9820.aarch64:2562`).

Status empiryczny (autor portu, `pmaports!8999`, sekcja *Touchscreen*):
„Works with an original panel. With an aftermarket panels the driver probes and communicates with
the IC, but there are no touch events available. IC seems to report a hardcoded state."
Wiki pmOS dla `samsung-exynos9820`: `status_touch = P`.

### Co to znaczy dla bramki B4

B4 **przestaje być otwartym pytaniem**: nie trzeba pisać drivera. Zakres pracy to (1) węzeł
`hsi2c10` + `touchscreen@48` w DT (już zrobione w artefakcie tej fazy —
`patches/0012-arm64-dts-exynos-*.patch`), (2) zasilanie TSP: docelowo s2mps19/ACPM, tymczasowo
`regulator-fixed`, (3) sprawdzenie, czy nasz egzemplarz ma **oryginalny** panel — bo aftermarket
nie generuje zdarzeń mimo poprawnego probe’a.

## Czego nie udało się ustalić

- Czy Y771 i S6SY761 to ten sam krzem, czy tylko zgodny protokół — w `sec_ts.c` nie ma stringa
  „S6SY" (grep: `build-logs/09-r3-y771-wc.log`). Ustalono to **funkcjonalnie** (driver działa), nie
  z dokumentacji.
- Czy oryginalny panel w naszym SM-G975F jest oryginalny — **do sprawdzenia na sprzęcie** (B4).
- Wariant `y771_d` (drugi katalog w downstreamie) — nie ustalono, dla której płyty jest przeznaczony.
