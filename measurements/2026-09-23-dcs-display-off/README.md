# Display off przez lacze DSIM po bootloaderze (23.09.2026)

## Co bylo do sprawdzenia

Czy krotka komenda DCS 0x28 (display off) i 0x29 (display on), wpisana do
kolejki naglowkow DSIM0 zostawionego przez bootloader, gasi i zapala panel
S6E3HA9, bez przejmowania DSIM ani DECON. Dzis wygaszenie konsoli tylko
maluje czern w buforze simpledrm, a panel dalej pracuje.

## Jak zmierzone

1. Modul probny `s10_dcs.c` (kopia w tym katalogu) zbudowany spoza drzewa
   pod dzialajace jadro `7.2.0-01001-ga9d566a524be-dirty #46`, W=1 bez uwag.
   Nie wiaze urzadzenia z wezlem dsi (zwiazanie odblokowaloby sync_state
   domeny pd_dpu), wlacza zegary APB `dsim0_pclks`, `decon0_pclks`
   i `decon0_pclkm`, mapuje rejestry i robi zrzut tylko do odczytu
   (bez 0x58, 0x5c i 0x60, bo to porty kolejek, a 0x60 zdejmuje dane).
2. Przed zaladowaniem: CMU_DPU mial runtime PM `suspended`, obie bramki
   mostka APB DECON0 i bramka DSIM0 mialy `hardware_enable=Y`.
   Po zaladowaniu CMU_DPU `active`, obraz bez zmian.
3. `test-dcs.sh`: czeka, az uzytkownik obudzi ekran, po 3 s wysyla 0x28,
   dwa zrzuty w odstepie 4 s, potem 0x29 i zrzut.

## Wynik

Stan zastany (przy `insmod`, ekran wygaszony przez klawiature):

```
DSIM version=02030000 clk_ctrl=06131f03 escmode=01400000 config=04887cff
     intsrc=01000000 intmsk=8e7b4447 fifoctrl=00009507 cmd_status=00000000
DECON global=00000113 trig=00001001 trig_aktywny=00001001 te_cnt=73c373c3
licznik TE po 1 s: 74017401
```

- EVT1 (0x02030000). Lacze uruchomione przez bootloader (CLOCK_SEL b26),
  zegar HS zadany (b20), zegar linii nieciagly (b25), tryb komend
  (CONFIG b18 = 0), kompresja wlaczona (b19), PLL_SLEEP wylaczony (b29 = 0),
  komendy w HS (ESCMODE b7 = 0), bez ULPS.
- DECON w trybie komend (b8), pracuje (b4), wyzwalacz sprzetowy od TE
  wlaczony i niezamaskowany (0x1001). Licznik TE rosnie o 62 na sekunde.

Wysylka (pelny log w `proba-0x28-0x29.txt`):

- 0x28 i 0x29: kolejka naglowkow oprozniona, INTSRC b28 ustawiony po
  wczesniejszym skasowaniu (pakiet wyszedl), zadnych bitow bledu
  (b27, b23, b22), `cmd_status=0`.
- **TE nie ustaje przy wylaczonym obrazie**: 0x9d93 do 0x9e83 w 4 s,
  czyli 240 impulsow, 60 Hz. DECON dalej wysyla ramki.
- **Uzytkownik potwierdzil okiem**: ekran zgasl na okolo 5 s i wrocil
  z tym samym obrazem.

## Wniosek

Samo 0x28 i 0x29 bez klucza 9F A5 A5 dziala na tym panelu i daje sie
w pelni cofnac. Na tym opiera sie sterownik
`drivers/video/backlight/exynos9820-dsim-lcd.c` (latka 0100), ktory
podpina te komendy pod wygaszanie framebuffera przez klase LCD.

## Sterownik wbudowany (jadro #48, ten sam wieczor)

Latka 0100 zbudowana w jadrze (`CONFIG_LCD_CLASS_DEVICE=y`,
`CONFIG_LCD_EXYNOS9820_DSIM=y`) i wgrana po sieci. Po starcie:
`/sys/class/lcd/exynos9820-dsim` istnieje, bramka `dsim0_pclks` ma
wlasciciela (`dsi@19080000 bus`, licznik 1), CMU_DPU `active`, zero
komunikatow sterownika w dmesg.

`sledz-ekran.sh` przez 150 s zapisywal kazda zmiane `dpms` i `lcd_power`,
a uzytkownik w tym czasie budzil przyciskiem i dwuklikiem, gasil
przyciskiem i czekal na 30 s ciszy (`sterownik-wbudowany-przejscia.txt`):
kazde przejscie DPMS przestawilo `lcd_power` (0 wlaczony, 4 wylaczony)
najpozniej w nastepnej probce, czyli w ciagu 200 ms; ostatnie zgaszenie
przyszlo dokladnie 30 s po obudzeniu (13:35:29, 13:35:59). Uzytkownik
potwierdzil, ze obraz wracal za kazdym razem.
