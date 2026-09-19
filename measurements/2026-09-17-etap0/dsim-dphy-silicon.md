# Blok wyswietlacza i rewizja krzemu, zmierzone z logu S-Boota

Data: 17 wrzesnia 2026. Zrodlo: log S-Boota tego egzemplarza z `/proc/last_kmsg`, zdjety przez
adb (base64), zapisany w `sboot-log-z-last_kmsg.txt`. To ten sam start z wpietym jigiem, ktory
badalismy (uptime w chwili odczytu 2420 s). Log obejmuje pelna inicjalizacje DSIM i D-PHY, ktora
zakonczyla sie sukcesem: `dsim_enable_pll: dsim pll is stable`, `dsim_enable_phy_lane: PHY ready
done`, po czym S-Boot narysowal logo (`drawimg`, `LoadJPEG`). Czyli wartosci ponizej NIE sa
martwym zapisem, tylko takimi, przy ktorych panel tego telefonu realnie zaswiecil.

## Rewizja krzemu (HW-11)

```
[0: 0.144] EXYNOS9820 EVT 1.1 (Base on ARM CortexA55)
[0: 1.781] DSIM:INFO:dsim_is_pll_stable:EVT1
```

Firmware telefonu dwukrotnie i niezaleznie melduje **EVT1**, nie EVT0. Baner podaje pelna
rewizje "EVT 1.1", a sterownik DSIM wybiera sciezke EVT1. To rozstrzyga HW-11: zapisy
`PLL_CON8 = 0xA28` i `MC_ANA_CON2 = 0x2`, ktore producent obejmuje
`#if !defined(CONFIG_SOC_EXYNOS9820_EVT0)` (`sources/ds/dsim_reg.c:60-64`, `:75-77`), na tym
egzemplarzu **naleza**, bo to nie jest krzem EVT0. Nasza seria zapisuje je bezwarunkowo, co jest
poprawne dla EVT1. Odczyt rejestru chipid nie byl potrzebny: baner bootloadera to oswiadczenie
firmware'u o wlasnej rewizji krzemu, a jego zadaniem jest te rewizje znac.

## Zegary i czasy D-PHY (HW-01, HW-02, HW-03)

```
[0: 1.781] dsim_set_clocks: word clock is 56 MHz
[0: 1.781] dsim_set_clocks: requested escape clock 20 MHz
[0: 1.781] dsim_set_clocks: escape clock divider is 0x3
[0: 1.781] dsim_set_clocks: escape clock is 18 MHz
[0: 1.781] dsim_get_dphy_timing: bps(898) clk_prepare(35) clk_zero(14) clk_post(3)
[0: 1.781] dsim_get_dphy_timing: clk_trail(56) hs_prepare(36) hs_zero(5) hs_trail(50)
[0: 1.781] dsim_get_dphy_timing: lpx(26) hs_exit(5)
[0: 1.781] dsim_get_dphy_timing: b_dphyctl(450)
[0: 1.781] dsim_set_pll_freq: p : 2, m : 138, s : 2, k : 0
```

Porownanie z wierszem naszej serii
(`sources/linux/drivers/phy/samsung/phy-exynos9820-dsim.c:137-159`, jedyny operacyjny punkt,
etykieta 898 Mbps):

| wielkosc | S-Boot telefonu | nasza seria | zgodne |
|---|---|---|---|
| clk_prepare | 35 | 35 | tak |
| clk_zero | 14 | 14 | tak |
| clk_post | 3 | 3 | tak |
| clk_trail | 56 | 56 | tak |
| hs_prepare | 36 | 36 | tak |
| hs_zero | 5 | 5 | tak |
| hs_trail | 50 | 50 | tak |
| lpx | 26 | 26 | tak |
| hs_exit | 5 | 5 | tak |
| b_dphyctl | 450 (0x1c2) | ulps_exit = 0x1c2 | tak |
| PLL p/m/s/k | 2/138/2/0 | 2/138/2/0 | tak |
| bps | 898 | hs_clk_rate 898000000 | tak |
| escape zadany | 20 MHz | `samsung,esc-clock-frequency` 20 MHz | tak |

Wszystkie trzynascie wielkosci zgadza sie co do wartosci. `b_dphyctl(450)` to `0x1c2`, czyli wpis
tablicy producenta `b_dphyctl[14]` dla escape 18 MHz (`sources/ds/dsim_reg.c:302-305`, wpisy dla
esc 16..20 to `0x190, 0x1a9, 0x1c2, 0x1db, 0x1f4`). Nasze pole `ulps_exit = 0x1c2` bierze wlasnie
ten wpis, co niezaleznie potwierdza, ze escape ma 18 MHz.

### Co to rozstrzyga

- **HW-03 (18 kontra 20 MHz): rozstrzygniete.** S-Boot pokazuje pelny lancuch: zadane 20 MHz,
  dzielnik 0x3, wynik 18 MHz. Nasza wlasciwosc `samsung,esc-clock-frequency = 20MHz` to wartosc
  ZADANA (zgodna z tym, co zadaje bootloader), a sprzet dzieli ja przez 3 do okolo 18,7 MHz
  (S-Boot zaokragla do 18). Dwie liczby z tego sporu to nie dwie prawdy, tylko wejscie i wyjscie
  dzielnika. Nasze DT ma juz jedno zrodlo prawdy (20, zadanie), i jest ono poprawne.
- **HW-01 (liczniki D-PHY): wartosci potwierdzone bit w bit.** Bootloader programuje dokladnie te
  same dziesiec licznikow (35,14,3,56,36,5,50,26,5 i b_dphyctl 0x1c2) i przy nich panel dziala.
  Jednostka fizyczna tych licznikow nadal nie jest udokumentowana, ale to juz nie ma znaczenia dla
  portu: piszemy te same surowe wartosci, co dzialajacy bootloader, i nie przeliczamy ich na inny
  zegar. Sprawdzian na nanosekundy, ktory sie nie domykal, dotyczyl interpretacji, nie poprawnosci.
- **HW-02 (dokladne Mbps lacza): potwierdzony punkt pracy, nie zmierzony drut.** Bootloader
  programuje P/M/S = 2/138/2 (czyli 897,0 Mbps z arytmetyki) i ETYKIETUJE to jako 898, dokladnie
  jak nasze DT. Wszystkie liczniki pochodne wychodza z tej samej etykiety 898 i zgadzaja sie
  z bootloaderem, wiec wybor etykiety jest neutralny dla rejestrow. Czego log NIE daje: pomiaru
  czestotliwosci na drucie czestosciomierzem, wiec spor 897,0 kontra 897,6 kontra 898 jako
  fizyczna wartosc pozostaje formalnie otwarty. Zmienil sie jednak z "trzy sprzeczne wartosci"
  na "jeden punkt pracy z pod-Mbps etykieta, ktora nie zmienia zadnego zapisu".

**Pilnuje:** `scripts/check-dphy-timing.py` parsuje ten log i wiersz serii, i porownuje wszystkie
trzynascie wielkosci oraz rewizje krzemu. Kod 2, gdy brak logu albo pliku serii.
