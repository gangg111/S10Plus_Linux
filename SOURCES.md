# Źródła — przypięte commity

Nic w tym repo nie jest skopiowanym drzewem. Każde źródło pobiera się skryptem
`scripts/fetch-sources.sh` do `sources/` (katalog ignorowany przez git).

| rola | URL | commit | data |
|---|---|---|---|
| mainline (baza patchy) | https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git | `1200d84f4c0a929a0780180d25063d93773be79c` (v7.2.0) | 2026-08-18 |
| pmaports | https://gitlab.postmarketos.org/postmarketOS/pmaports | `78958726e3f1a277bc3c568a7ba21b70ae642c9a` | 2026-08-18 |
| kernel portu mainline 9820 | https://github.com/chiffathefox/exynos-9820-mainline-linux | `0aeca03f7acddd3aacdf25b01fede0ee3c724d48` (branch `exynos9820-7.2-rc2`) | — |
| **U-Boot upstream (baza NASZEGO bootloadera)** | https://source.denx.de/u-boot/u-boot.git | `211de43d0f954a00a490220c1aac9db298287c40` | 2026-09-17 |
| U-Boot forka 9820 (punkt odniesienia, NIE do przepisania) | https://github.com/chiffathefox/u-boot | `c5afa30840d92471b5fea4421b10b0a8d83b449b` (branch `exynos9820`) | 2026-07-22 |
| downstream Samsung/LineageOS | https://github.com/LineageOS/android_kernel_samsung_exynos9820 | `7d08ec364a0659edcf90a8dae4453b21e4542311` (4.14.316, lineage-20) | 2023-06-08 |
| uniLoader | https://github.com/ivoszbg/uniLoader | `2fb7820aaf3b20db7b9d2e72ce45f42eb52f1d10` | 2026-08-17 |
| wiki pmOS (zrzuty `action=raw`) | https://wiki.postmarketos.org | `Samsung_Exynos_9820_(samsung-exynos9820)`, `Samsung_Galaxy_S10+_(samsung-beyond2lte)` | pobrane 2026-08-18 |
| MR-y pmaports | https://gitlab.postmarketos.org/postmarketOS/pmaports/-/merge_requests/{6161,8999} | — | 2025-03-03 / 2026-07-31 |

## Pliki downstreamu użyte jako dowód (pobierane pojedynczo, nie całe drzewo)

`arch/arm64/boot/dts/exynos/exynos9820.dts`, `arch/arm64/configs/exynos9820-beyond2lte_defconfig`,
`drivers/video/fbdev/exynos/panel/s6e3ha9/{s6e3ha9.c,s6e3ha9.h,s6e3ha9_beyond2_a3_s0_panel.h,
s6e3ha9_davinci2_a3_s0_panel.h}` (ten ostatni ma tablicę FFC dla 4 zegarów — punkty referencyjne modelu FFC),
`drivers/video/fbdev/exynos/dpu20/cal_9820/{regs-decon.h,regs-dsim.h}`,
`drivers/input/touchscreen/sec_ts/y771/*`,
`drivers/video/fbdev/exynos/dpu20/panels/{s6e3ha9_param.h,s6e3ha9_lcd_ctrl.c,decon_lcd.h}`,
`drivers/video/fbdev/exynos/dpu20/{dsim_drv.c,dsim.h}`,
`drivers/video/fbdev/exynos/dpu20/cal_9820/dsim_reg.c` (tablica timingów D-PHY),
`arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_26.dts` (zdekompilowany overlay płyty —
tu żyją timingi panelu).

Dopisane po audycie cytowan (Krytyk A). Bez nich patche cytowaly pliki, ktorych
nikt odtwarzajacy prace nie mogl otworzyc, wiec kilkadziesiat stalych bylo
formalnie nieweryfikowalnych mimo poprawnego cytatu:

`drivers/soc/samsung/cal-if/exynos9820/{cmucal-sfr.c,cmucal-sfr.h,cmucal-node.c}`
(tablica SFR bloków CMU: bazy, offsety, pozycje i szerokosci pol; `SFR_BLOCK` daje
baze i rozmiar okna, `SFR` offset rejestru, `SFR_ACCESS` pole),
`drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h` (sekwencje
PMUCAL domen zasilania: adres, offset i maska `DPU_CONFIGURATION`/`DPU_STATUS`),
`drivers/video/fbdev/exynos/dpu20/cal_9820/{decon_reg.c,decon_cal.h}` (pola enkodera
DSC i wyliczenia `decon_win_func`/`decon_data_path`),
`drivers/video/fbdev/exynos/dpu20/cal_9820/{regs-dpp.h,dpp_reg.c}` (blok DPP/IDMA).

Dopisane pozniej, bo bez nich nie da sie odtworzyc bramek:

`drivers/video/fbdev/exynos/panel/{dimming.c,dimming.h,dimming_gamma.h,panel_dimming.h}`
oraz `drivers/video/fbdev/exynos/panel/s6e3ha9/{s6e3ha9_dimming.h,
s6e3ha9_beyond2_a3_s0_panel_dimming.h,s6e3ha9_davinci2_a3_s0_panel_dimming.h}`
(silnik dimmingu producenta, bramka `scripts/check-dimming-engine.sh`; dwa ostatnie
pobierane pod skroconymi nazwami `beyond2_dimming.h` i `davinci2_dimming.h`, bo tak
odwoluje sie do nich harness),
`drivers/soc/samsung/cal-if/{pll_spec.c,cmucal.h}` (specyfikacje typow PLL: dowod, ze
PLL_0817X dzieli spec z PLL_0822X, a PLL_1018X z PLL_0818X, `pll_spec.c:293-301`).

Dopisane w rundzie krytyka kompletnosci, bo lezaly w `sources/ds` i byly cytowane,
a ta lista ich nie wymieniala. Siedem plikow, dwa zrodla:

Z drzewa producenta (`LineageOS/android_kernel_samsung_exynos9820`, ten sam commit
co wyzej):
`drivers/pinctrl/samsung/{pinctrl-exynos-arm64.c,pinctrl-exynos.h}` (tablice bankow
pinow producenta: offsety bankow, liczby pinow, offsety EINT, punkt odniesienia dla
`patches/0007`),
`drivers/video/fbdev/exynos/panel/{panel_drv.c,panel_drv.h}` (sterownik panelu:
sekwencje wlaczania, odczyt MTP komenda 0xC8, mapowanie jasnosci na tablice AID),
`drivers/muic/{max77705-muic.c,max77705-muic-ccic.c}` (MUIC tego telefonu: tablica, ktora
przypisuje rezystancji na CC tryb pracy, w tym 619 kOhm na `JIG UART ON` z przelaczeniem
magistrali na UART, oraz most, ktorym blok CC zglasza rozpoznane RID; to jest cala przeslanka
jiga UART z `hardware/uart-jig/`),
`drivers/ccic/max77705_pd.c` (blok PD tego samego ukladu: to on realnie mierzy rezystancje
fabryczna na CC, pole `BIT_FCT_ID` rejestru `REG_PD_STATUS1`, i przerwaniem zglasza wynik
jako RID; bez tego pliku nie widac, ze sciezka RID jest zywa, bo w `max77705_usbc.c` pole
`cur_rid` dostaje wartosc tylko przy starcie; rozstrzyga pomiar z `measurements/2026-09-17-etap0/`),
`drivers/ccic/max77705_usbc.c` (glowny sterownik USB-C: wystawia `cur_rid` przez sysfs
i inicjalizuje je na `RID_OPEN`, przez co sam czytany bez `max77705_pd.c` sugeruje falszywie,
ze sciezka RID jest martwa),
`drivers/video/fbdev/exynos/panel/{panel.c,panel.h}` (wybor wariantu panelu: `find_panel_lut`
dopasowuje identyfikator przez tablice `panel-lut` z drzewa urzadzen, z maska na wpis,
a `struct panel_lut` podaje format tego wpisu; potrzebne, zeby rozstrzygnac HW-40),
`drivers/video/fbdev/exynos/panel/s6e3ha9/davinci2_df_tbl.h` (tablica dynamicznej
zmiany czestotliwosci drugiego panelu tej rodziny, uzywana jako kontrola krzyzowa
przy modelu FFC).

Z drzewa portu chiffathefoxa (`chiffathefox/exynos-9820-mainline-linux`, commit
z tabeli wyzej), do porownania, a nie do przepisania:
`drivers/clk/samsung/clk-exynos9820.c` i `include/dt-bindings/clock/exynos9820.h`
(poprzednia realizacja warstwy zegarow: 441 zegarow wobec naszych 533; sluzy za
punkt odniesienia w `docs/R1-clocks.md` i przy patchach out-of-tree).

Dopisane przy pracy nad PHY pamieci UFS dla naszego bootloadera (`patches-uboot/`).
Cztery pliki z drzewa producenta, ten sam commit co wyzej:

`drivers/scsi/ufs/{ufs-cal-9820.c,ufs-cal-9820.h}` (warstwa kalibracyjna tego SoC:
tablice zapisow do bloku PMA rozbite na punkty kalibracji i warianty rewizji krzemu,
`init_cfg_evt0` kontra `init_cfg_evt1`, warianty `_g3`/`_g4` wedlug maksymalnego biegu,
osobne tablice `_card` dla karty UFS, ktorej ten telefon nie ma, oraz sekwencje czekania
`PHY_EMB_CAL_WAIT` i `PHY_EMB_CDR_WAIT` z rejestrami, maskami i limitami czasu; wybor
tablicy dla naszej plyty rozstrzygaja wpisy `evt-ver = [01]`, `brd-for-cal = [01]`,
`ufs,pmd-attr-gear = [03]` i `ufs,pmd-attr-lane = [02]` z wezla `ufs@0x13D60000`
w `exynos9820.dts`),
`drivers/scsi/ufs/{ufs-exynos.c,ufs-exynos.h}` (sterownik hosta UFS producenta: to on
wola warstwe kalibracyjna, steruje izolacja PHY w bloku PMU i dzieli prace miedzy
warstwe PMA, ktora u nas trafia do sterownika PHY, a warstwy PCS i UniPro, ktore
naleza do sterownika hosta).

`drivers/misc/mcu_ipc/{regs-mcu_ipc.h,mcu_ipc.c,shm_ipc.c}` (skrzynka pocztowa
miedzy procesorem aplikacyjnym a modemem: mapa rejestrow bloku MCU_IPC, kierunki
przerwan w obie strony, rejestry wiadomosci ISSR, a w `shm_ipc.c` podzial
zarezerwowanej pamieci modemu na obszary i wyliczanie parametrow wywolania do
firmware bezpieczenstwa),
`drivers/misc/modem_v1/{modem_ctrl_s5000ap.c,link_device_shmem.c,link_device_memory.h,modem_prj.h,modem_v1.h}`
(sterownik modemu producenta w czesci dotyczacej NASZEGO wariantu `s5000ap`:
kolejnosc rozruchu procesora komunikacyjnego, zerowanie i pola startowe rejestrow
skrzynki, wywolania do swiata bezpiecznego sprawdzajace podpis obrazu modemu wraz
z ich trybami i petla ponowien, stary uklad pamieci uzywany przy rozruchu i zrzucie
razem z wartosciami rozpoznawczymi, komendy protokolu sterujacego oraz lista operacji
dla przestrzeni uzytkownika, z ktorych korzysta demon rozruchu modemu),
`drivers/misc/modem_v1/include/{sbd.h,sipc5.h}` (opis kolejek pierscieniowych,
ktorymi biegnie ruch do modemu, oraz ramkowania warstwy lacza),
`drivers/soc/samsung/cal-if/exynos9820/pmucal_cp_exynos9820.h` (sekwencje jednostki
zarzadzania zasilaniem dla domeny modemu: wlaczenie, potwierdzenie, zatrzymanie
i zwolnienie resetu, kazda jako tablica zapisow i oczekiwan na konkretne bity),

`drivers/pci/dwc/{pcie-exynos-host-v0.c,pcie-exynos-host-v0.h,pci-exynos9820_cal.c}`
(sterownik kontrolera PCIe producenta i jego warstwa kalibracji warstwy
fizycznej: sekwencja startu lacza, uklad rejestrow okien elbi, pcs i ia oraz
tablice strojenia; uklad Wi-Fi tego telefonu wisi wlasnie na tym kontrolerze,
a mainline nie ma dla niego niczego, patrz HW-44),
`drivers/soc/samsung/cal-if/exynos9820/{flexpmu_cal_cpu_exynos9820.h,flexpmu_cal_powermode_exynos9820.h}`
(sekwencje jednostki zasilania dla rdzeni: trzy kroki, ktorymi producent wlacza
kazdy z osmiu rdzeni, oraz lista rejestrow podpowiedzi CPU_INFORM; stad adres
bloku generatora przerwan 0x15870000, offsety GRP1/GRP2 i wniosek, ze samo
wywolanie PSCI na tym ukladzie nie wystarcza, opisany w docs/R13-rdzenie.md),
`drivers/soc/samsung/acpm/{acpm.c,acpm_ipc.c,acpm.h,acpm_ipc.h,acpm_common.h,acpm_framework.h,acpm_ipc_ctrl.h}`
(firmware Active Power Manager i jego protokol: uklad pamieci wspoldzielonej,
naglowek ramki, numery kanalow i to, ze konfiguracja kanalow lezy pod offsetem
wewnatrz tej pamieci; stad liczby w `patches/0066` oraz w wezlach `sram@2039000`
i `firmware/power-management`),
`drivers/soc/samsung/acpm/{acpm_mfd.c,acpm_mfd.h}` (czesc tego samego firmware,
ktora obsluguje uklady zasilania: dowod, ze glowny PMIC odpowiada wylacznie przez
kanal APM, a nie na zadnej magistrali procesora, co zamyka HW-42),
`drivers/mfd/s2mps19_core.c`, `drivers/regulator/s2mps19_regulator.c`,
`include/linux/mfd/samsung/{s2mps19.h,s2mps19-regulator.h}` (glowny uklad
zasilania tego telefonu: lista szyn, ich zakresy i numery kanalow, czyli to, co
trzeba znac, zanim ktokolwiek siegnie po szyny przez APM),
`drivers/mfd/s2mps19_irq.c` (tablica przerwan tego ukladu: numer rejestru
i BIT dla kazdego zdarzenia.  Potrzebna wprost, bo kolejnosc w wyliczeniu
naglowka NIE odpowiada kolejnosci bitow: rejestr INT3 pomija bit 4, wiec
odtworzenie masek z samej listy nazw dalo by zle przypisanie siedmiu przerwan),
`drivers/input/touchscreen/sec_ts/y771/{sec_ts.h,sec_ts_fn.c}` (naglowek i warstwa
polecen sterownika dotyku producenta: uklad osmiobajtowego zdarzenia pole po polu,
w tym podzial bajtu 7 na piciobitowy licznik pozostalych zdarzen, znacznik
`max_energy_flag` i dwa bity typu kontaktu, ktory rozstrzygnal maske w latce 0093;
do tego stale gestow, tryby niskiego poboru i opcody silnika SPONGE, czyli to, na
czym stanie gest wybudzania),
`drivers/i2c/busses/i2c-exynos5.c` jako `i2c-exynos5-vendor.c` (sterownik
magistrali producenta: to z niego wzieta jest kolejnosc resetu kontrolera
i odczyt wyniku transferu z `TRANS_STATUS`, ktory w mainline czytany jest
z innego rejestru; rozstrzygnal objaw "tx timeout" na zywej magistrali),
`sound/soc/samsung/abox/{abox_soc.h,abox_rdma.c,abox_wdma.c}` (mapa rejestrow
bloku audio ABOX i sterowniki jego DMA odtwarzania i nagrywania: dowod, ze RDMA
i WDMA programuje firmware DSP przez IPC, a AP czyta tylko wskaznik bufora;
docs/R19-dzwiek.md),
`sound/soc/samsung/abox/{abox.c,abox.h,abox_soc.c,abox_if.c,abox_cmpnt_v20.c}`
(strona AP bloku ABOX: zadanie DRAM przez SYSPOWER, regmapa, konfiguracja UAIF,
kontrolki trasy SPUS/SIFS i licznik SIFS; z nich skladana jest sciezka
odtwarzania bez firmware DSP),
`sound/soc/samsung/beyond_madera.c` (sterownik karty tego telefonu: formaty
i sloty UAIF dla kodeka i wzmacniaczy),
`drivers/mfd/cirrus-cal.c` (kalibracja glosnikow producenta: odczyt
`/efs/cirrus/rdc_cal`, `rdc_cal_r`, `temp_cal` i wpis do pol CAL_R,
CAL_AMBIENT, CAL_STATUS, CAL_CHECKSUM firmware ochrony; docs/R19-dzwiek.md),
`sound/soc/codecs/cs35l41.c` (sterownik wzmacniaczy producenta: z wartosci
przetwornicy boost ustawia tylko prad szczytowy, wspolczynniki zostaja po
resecie, co wyznaczylo opis wzmacniaczy w latce 0121),
`drivers/extcon/extcon-madera.c` (wykrywanie akcesoriow kodeka producenta:
tryb zacisku MICD, pomiar mikrofonu przez ADC, progi i klawisze pilota,
na ktorych oparta jest latka 0138 i przyciski zestawu; docs/R19-dzwiek.md),
`drivers/mmc/host/dw_mmc-exynos.c` i `drivers/mmc/host/dw_mmc-exynos.h`
(kontroler kart producenta: czyta
`samsung,dw-mshc-sdr-timing` jako czterech liczb `div, f_drv, drv, sample`,
podczas gdy mainline czyta dwie `sample, drive`; stad przelozenie taktowania
gniazda microSD w wezle plyty).

`drivers/soc/samsung/cal-if/{pmucal_cpu.c,pmucal_cpu.h,pmucal_rae.c,
pmucal_powermode.c,pmucal_powermode.h,pmucal_common.h,cal-if.c}` oraz
`drivers/soc/samsung/exynos-cpupm.c` to warstwa, ktora WYKONUJE tablice
`flexpmu_cal_*` przy budzeniu i usypianiu rdzeni. Tablice same mowia, jakie
rejestry, a dopiero ten kod mowi, w jakiej kolejnosci, na co sie czeka i co
robi sie na poziomie klastra. Sciagniete przy rundzie R13, zeby ustalic, czy
producent robi przy starcie rdzenia cos, czego nasz port nie robi.
Odpowiedz brzmi: nie robi, jego `cal_cpu_enable()` wisi na
`CPUHP_AP_EXYNOS_CPU_UP_POWER_CONTROL`, czyli biegnie na rdzeniu JUZ
wystartowanym, wiec w kwestii samego rozruchu rdzenia polega na firmware
tak samo jak my.


## Instrukcja serwisowa SM-G975F

Sześć plików PDF (service guide producenta) dostarczonych przez właściciela urządzenia,
archiwum `SAMSUNG GALAXY S10 PLUS SM-G975F.zip`. Wykorzystane fragmenty:

- sekcja `Tshoo` (Level 3 Repair, 8-4-16 Display, str. 33): szyny panelu z napięciami
  i punktami pomiarowymi — `VDD_DDI_3P0` 3,0 V (C12027), `VDD_DDI_1P8` 1,8 V (C12028),
  `VDD_DDR_1P6` 1,6 V (C12037), `ELVDD` 4,6 V (C12039), `ELVSS` −5,4…−1,4 V (C12029),
  `ELAVDD` 7,6 V (C12036). Zamyka przypisanie ról szyn S2DOS05 (HW-20).
- sekcja `Tshoo` (8-4-20 TSP): szyny panelu dotykowego `VDD_TSP_1.8V` (C12024)
  i `VDD_TSP_3.0V` (C12023).
- diagram blokowy płyty (`Beyond2_EUR`, sekcja `Tshoo` str. 3): niezależne potwierdzenie
  topologii, którą wyprowadziliśmy ze źródeł producenta — łącze **MIPI 4 lane** z AP do
  DDI, **Display PMIC na I2C**, panel dotykowy na osobnym `TSP_I2C`, plus `COPR_SPI`
  do DDI, którego nie modelujemy.
- specyfikacja produktu: `Display 6.4", WQHD+, 1440x3040`. Z przekątnej i proporcji
  wychodzi aktywny obszar 69,6 × 146,9 mm, co rozstrzyga HW-22.

Dokumenty są oznaczone jako poufne i **nie są redystrybuowane w tym repozytorium**:
cytowane są wyłącznie pojedyncze wartości potrzebne do uzasadnienia wpisów w kodzie,
tak jak w przypadku pozostałych źródeł. Patche wysyłane na listę nie odwołują się do
nich ścieżką ani adresem.

## Niedostępne w tej fazie

- `opensource.samsung.com` — `POST /uploadSearch` zwraca HTTP 403 bez interaktywnej sesji;
  **dokładna wersja firmware’u SM-G975F, z której pochodzą źródła, pozostaje nieustalona** (§7.8 briefu).
- `lore.kernel.org` — zapytania `?q=…` zwracają 403 / stronę anty-botową; serie patchy Ivanova
  cytowane przez commity w `torvalds/linux`.
