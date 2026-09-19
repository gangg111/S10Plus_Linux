# Etap 0a: odczyty ze stockowego Androida, 11 wrzesnia 2026

Pierwsza sesja przy sprzecie. Wszystko ponizej jest odczytem z tego egzemplarza telefonu,
nie z zadnego drzewa zrodel. Procedura: `docs/UART-BRINGUP.md`, sekcja "Etap 0a".

## Egzemplarz

| co | wartosc | skad |
|---|---|---|
| model | SM-G975F | `getprop ro.product.model` |
| plyta | beyond2 / beyond2ltexx | `getprop ro.product.device`, `ro.product.name` |
| platforma | universal9820 / exynos9820 | `getprop ro.board.platform`, `ro.hardware` |
| Android | 12 (SDK 31), SP1A.210812.016.G975FXXSGHWC1 | `getprop ro.build.display.id` |
| bootloader | G975FXXSGHWC1 | `getprop ro.bootloader` |
| root | Magisk, `uid=0(root) context=u:r:magisk:s0` | `su -c id` |
| numer seryjny | XXXXXXXXXXX | `adb devices -l` |

Numer seryjny jest tu po to, zeby dalo sie sprawdzic, czy kolejna sesja jest na tym samym
egzemplarzu; mapa RAM-u i dane panelu sa specyficzne dla sztuki, nie dla modelu.

## Pliki

| plik | skad | po co |
|---|---|---|
| `stock-fdt.dtb` | `/sys/firmware/fdt` | DTB, ktore bootloader podal stockowemu jadru: zrodlo rozstrzygajace dla HW-31 i HW-34 |
| `stock-fdt.dts` | `dtc -I dtb -O dts` z powyzszego | ta sama tresc czytelnie, do przeszukiwania |
| `cmdline.txt` | `/proc/cmdline` | `s3cfb.bootloaderfb=0xca000000` (HW-19), `lcdtype=10555411` |
| `iomem.txt` | `/proc/iomem` jako root | granice bankow widziane przez jadro, kontrola dla HW-31 |
| `meminfo.txt` | `/proc/meminfo` | `MemTotal` jako druga kontrola sumy |
| `interrupts.txt` | `/proc/interrupts` | numery przerwan w dzialajacym systemie |
| `pm_genpd_summary.txt` | `/sys/kernel/debug/pm_genpd/pm_genpd_summary` | stan domen zasilania |
| `pd-dpu.txt` | `/sys/kernel/debug/pm_genpd/pd-dpu/` | domena DPU: `on`, trzy sysmmu podpiete |

Blob jest caly i nieuszkodzony: pole `totalsize` z naglowka (371894) rowna sie rozmiarowi pliku,
magic `d00dfeed`, `sha256 877a949f886622c3359ee60e85f098b061943a5ffc5ff7cbac9ee87800cd6910`.

## Jak brac binaria z telefonu

`adb exec-out` na tej maszynie **psuje** dane binarne: przy blobie 371894 B plik wyszedl
372365 B, czyli o 471 bajtow za duzy (zamiana koncow linii). Dziala:

```sh
adb shell "su -c 'base64 /sys/firmware/fdt'" | tr -d '\r\n' > fdt.b64
```

i dekodowanie na PC, zawsze z kontrola `totalsize` wzgledem rozmiaru pliku.

## Czego tu nie ma i dlaczego

**Zrzuty debugfs producenta.** Proba odczytu `/sys/kernel/debug/vclk/VCLK_BLK_DPU/*`
**wywrocila jadro i zresetowala telefon**. Slad z `/sys/fs/pstore/dmesg-ramoops-0` po restarcie:

```
ra_get_div_mux+0x8/0x40
vclk_recalc_rate.part.0+0x74/0xf0
vclk_table_dump+0x3c/0x180
seq_read -> full_proxy_read -> vfs_read   [proces: cat]
Code: f9400c01 b40001a1 (b9400021)
```

Handler `read` tych wezlow chodzi po tablicach i rejestrach blokow, wiec debugfs producenta
**nie jest kanalem tylko do odczytu**. Nie wracac do `vclk/*`, `decon/dump0`, `decon/event0`,
`exynos-ss/*`, `exynos-rgt/*`. Bezpieczne sa `/proc/*`, `/sys/firmware/fdt`,
`/sys/firmware/devicetree`, pojedyncze atrybuty `/sys/class/*` i `/sys/fs/pstore/*`.

To nie jest strata dla etapu 0a: mapa RAM-u wyszla z `/sys/firmware/fdt`, czyli z zrodla
pewniejszego niz cokolwiek w debugfs.

## HW-20 zostaje otwarte

Odstepow czasowych miedzy narastaniem szyn panelu nie da sie odczytac przez adb. To pomiar
sonda na zlaczu panelu i nadal czeka, zgodnie z `docs/HW-BLOCKED.md`.
