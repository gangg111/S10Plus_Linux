# R4 — istniejące porty

**Odpowiedź:** Stan opisany w briefie §3 jest **nieaktualny o rok**: 31.07.2026 do pmaports wszedł
**generyczny port mainline dla Exynos 9820** (`device-samsung-exynos9820`, kernel 7.2.0 z drzewa
`chiffathefox/exynos-9820-mainline-linux`, boot przez własny fork U-Boota po EFI), który *provides*
`device-samsung-beyond2lte`, a stare porty downstreamowe (4.14) zostały **zarchiwizowane** z adnotacją
„Downstream port, only for testing. Use mainline port!". Udokumentowana przyczyna braku ekranu w
starym porcie beyond2lte-downstream to nie „nieznany bug", tylko `deviceinfo_no_framebuffer="true"`
i brak działającego przekazania framebuffera — w porcie mainline ekran działa jako **simple-framebuffer**
(status `P`), bo DRM/KMS dla 9820 nie istnieje.

---

## 1. Co dokładnie jest w pmaports (`pmaports@78958726e3f1a277bc3c568a7ba21b70ae642c9a`, 2026-08-18)

### a) Port mainline (aktualny, `device/testing/`)

| pakiet | co mówi |
|---|---|
| `device/testing/device-samsung-exynos9820/APKBUILD:4` | `pkgdesc="Samsung Exynos 9820 Generic Device"` |
| `…/APKBUILD:10-15` | zależy od `linux-postmarketos-exynos9820`, `systemd-boot`, `reboot-mode` |
| `…/APKBUILD:25-28` | `provides="device-samsung-beyond1lte=… device-samsung-beyond2lte=…"` |
| `…/deviceinfo:14` | `deviceinfo_drm="true"` |
| `…/deviceinfo:19-20` | `# Heimdall fails mid-transfer when flashing rootfs. Use TWRP instead` → `deviceinfo_flash_method="none"` |
| `device/testing/linux-postmarketos-exynos9820/APKBUILD:4-8` | `pkgver=7.2.0`, `_commit="0aeca03f7acddd3aacdf25b01fede0ee3c724d48"`, `url="https://github.com/chiffathefox/exynos-9820-mainline-linux"` |

**Źródło jądra: nie mainline vanilla, tylko fork „close-to-mainline"** (`pkgdesc` :7, konfiguracja wg `…-beyond1lte_defconfig`, :1).
Konfiguracja (`config-postmarketos-exynos9820.aarch64`) mówi o realnym zakresie portu:

| linia | opcja | znaczenie |
|---|---|---|
| 4426 | `CONFIG_DRM_SIMPLEDRM=y` | ekran = framebuffer po bootloaderze |
| 4359 | `# CONFIG_DRM_EXYNOS is not set` | brak DECON/DSI |
| 4410 | `# CONFIG_DRM_PANFROST is not set` | brak GPU |
| 2562 | `CONFIG_TOUCHSCREEN_S6SY761=y` | dotyk mainline’owym driverem |
| 1713 | `CONFIG_EFI_ARMSTUB_DTB_LOADER=y`, 573-574 `CONFIG_EFI_STUB/EFI` | boot przez EFI (U-Boot) |
| 5921 | `CONFIG_EXYNOS_ARM64_COMMON_CLK=y` | driver zegarów 9820 (out-of-tree, patrz R1) |
| 1733 | `CONFIG_EXYNOS_ACPM_PROTOCOL=y` | ACPM (PMIC) |

**Uwaga:** DT **nie ma w drzewie jądra** — w commicie `0aeca03f7acd` nie istnieje żaden plik z
„beyond" ani `exynos9820*.dts*` (sprawdzone przez GitHub contents API na
`arch/arm64/boot/dts/exynos/`, 50 pozycji, log `build-logs/10-r4-chiffa-dts.log`).
DT żyje w forku U-Boota i jest podawany jądru przez EFI:
`chiffathefox/u-boot@c5afa30840d9:dts/upstream/src/arm64/exynos/{exynos9820.dtsi, exynos9820-common.dtsi,
exynos9820-pinctrl.dtsi, exynos9820-beyond1lte.dts, exynos9820-beyond2lte.dts}`.

### b) Porty downstream (zarchiwizowane)

| pakiet | stan |
|---|---|
| `device/archived/device-samsung-beyond2lte-downstream/APKBUILD:1` | `# Archived: Downstream port, only for testing. Use mainline port!` |
| `device/archived/linux-samsung-beyond2lte-downstream/APKBUILD:7` | `pkgver=4.14.316` |
| `…/APKBUILD:31-32` | źródło: `LineageOS/android_kernel_samsung_exynos9820`, commit `7d08ec364a0659edcf90a8dae4453b21e4542311` |
| `…/APKBUILD:3` | konfiguracja bazuje na `arch/arm64/configs/exynos9820-beyond2lte_defconfig` |
| `device/archived/device-samsung-beyond1lte-downstream/` | to samo dla S10 |

Historia (git log, `pmaports@78958726`):

```
c43f2078e 2025-03-03 samsung-beyond2lte: new device (MR 6161)
3235ae4f9 2026-07-31 samsung-beyond1lte: archive downstream port
352ab64e7 2026-07-31 samsung-beyond2lte: rename downstream port
b530ce6db 2026-07-31 device-samsung-exynos9820: add a generic mainline port for Exynos 9820 devices
```

## 2. Udokumentowana przyczyna, dla której na beyond2lte nie działał ekran

Trzy niezależne, cytowalne ślady — i wszystkie mówią to samo: **downstreamowy port nigdy nie miał
działającego wyjścia obrazu, bo nie umiał przejąć framebuffera DECON-a**:

1. **Deklaracja w porcie**: `deviceinfo_no_framebuffer="true"`
   (`pmaports@78958726:device/archived/device-samsung-beyond2lte-downstream/deviceinfo:33`).
   Dla porównania port beyond1lte-downstream działał (wiki: `status_screen` = działa) — czyli
   różnica nie jest „w Exynosie", tylko w konkretnym porcie.
2. **Próba obejścia w initfs**: hook wpisuje `16` do
   `/sys/devices/platform/19030000.decon_f/graphics/fb0/bits_per_pixel`
   (`…/device-samsung-beyond2lte-downstream/initfs-hook.sh:3`) — czyli walka o to, żeby fbdev
   downstreamowego DECON-a (adres `0x19030000`, ten sam co w DT: `exynos9820.dts:6769`) w ogóle
   pokazał cokolwiek.
3. **Opis pierwszego MR-a**: „Device boots and is accessible via ssh through USB / **No screen** /
   Wifi works" (`pmaports!6161`, opis MR, 2025-02-06). Wiki `Samsung Galaxy S10+ (samsung-beyond2lte)`:
   `status_screen = N`, `status_touch = N`, `status_wifi = Y`, `status_battery = Y`.

**Czego w tym nie ma:** nikt nie opublikował analizy typu „DECON nie odświeża, bo trigger control
nie ustawiony". Tę przyczynę zna projekt uniLoader dla **mainline**
(`ivoszbg/uniLoader@2fb7820aaf3b:board/samsung/board-beyond1lte.c:17-22` — wpis `0x1281` do
`0x19030000 + 0x70`), ale to dotyczy ścieżki simple-framebuffer, nie downstreamowego DPU20.

## 3. Realny status funkcji w porcie mainline (wiki pmOS, `Samsung Exynos 9820 (samsung-exynos9820)`)

`booting = yes`, `pmoskernel = 7.2.0`, `category = testing`, `whet_dhry = 6044.6`

| funkcja | status |
|---|---|
| ekran | **P** (simple-framebuffer, bez DPMS/jasności) |
| dotyk | **P** (działa na oryginalnym panelu) |
| USB net | Y |
| pamięć wewnętrzna (UFS) | Y |
| U-Boot (secondary) | Y, w tym obraz i przyciski |
| 3D, audio, Wi-Fi, BT, bateria, kamery, GPS, modem, OTG, czujniki | **N** |
| flashowanie pmbootstrap | **N** (instalacja przez TWRP + `dd`) |

Znane ograniczenia z opisu `pmaports!8999` (cytaty):

- CPU: „no cpuidle, cpufreq or cpuhp support… Stressing all 8 cores… bakes the SoC very quickly and
  it goes into thermal protection (hard power cutoff)… Hence the `maxcpus=6` bootarg".
- U-Boot: „Not easily mainlineable since this SoC uses non-standard PRDT entry size which is, at the
  moment, hardcoded in core UFS implementation."
- Pinctrl: „Fully working driver… Seems easily mainlineable." UFS: „Fully working driver, seems
  easily mainlineable."
- PMIC: zaimplementowany `s2mps19` (z trzech: `s2mpb02`, `s2dos05`, `s2mps19`), „close to gs101's
  S2MPG10", zasila TSP.
- ACPM: „WIP. Protocol format matches gs101, but has a different peripheral address and doorbell
  offsets."
- USB host nie działa; gadget działa (driver z exynos990 „worked out of the box").

## 4. Pozostałe porty z briefu — weryfikacja

- **Ubuntu Touch / Halium / Droidian** — nie weryfikowane w tej fazie (poza zakresem R1–R5 i
  sprzeczne z celem projektu, §13 briefu).
- **beyond1lte downstream** — zarchiwizowany tym samym MR-em (`3235ae4f9`).

## Czego nie udało się ustalić

- **Dokładna wersja firmware’u G975F, z której pochodzą źródła downstreamu** (§7.8 briefu).
  Ustalono tylko łańcuch: pmaports → LineageOS `7d08ec364a06` (merge 4.14.316 do `lineage-20`,
  2023-06-08). Szukane w: commitach LineageOS (GitHub commits API, `search/commits` dla „G975F",
  „Import", „opensource" — brak commitu importu w widocznej historii), `opensource.samsung.com`
  (POST `/uploadSearch` → **HTTP 403**, log `build-logs/11-r4-samsung-oss.log`). Pobranie
  pierwotnego archiwum Samsunga wymaga interaktywnej sesji na stronie — **DO ZROBIENIA RĘCZNIE**.
- Czy port mainline był testowany na **beyond2lte** (S10+), czy tylko na beyond1lte (S10) — zdjęcia
  w MR pokazują oba egzemplarze, ale `pmaports!8999` nie zawiera per-model matrycy testów.
