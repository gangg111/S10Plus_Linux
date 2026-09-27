# R19: dźwięk

Runda dziewiętnasta. Cel: dźwięk jak w Androidzie, czyli głośniki, słuchawka
rozmowowa, gniazdo słuchawkowe z mikrofonem, trzy mikrofony wbudowane
i Bluetooth. Stan na 25.09.2026: Bluetooth działa od strony systemu,
wzmacniacze głośników odpowiadają na magistrali, a cała ścieżka wewnętrzna
stoi na bloku audio SoC, którego mainline nie ma.

## Jak płynie dźwięk w tym telefonie

Wszystko wewnętrzne idzie przez **ABOX**, blok audio Samsunga z własnym
procesorem DSP. Węzeł `abox@18c50000` w `sources/ds/exynos9820.dts:5978`,
karta dźwiękowa producenta `samsung,beyond-madera` łączy go z układami tak:

| interfejs ABOX | układ | magistrala sterowania | co obsługuje |
| --- | --- | --- | --- |
| UAIF0 | kodek CS47L93 (Madera) | SPI2 | gniazdo 3,5 mm, mikrofony, DSP kodeka |
| UAIF1 | 2 x CS35L40 | hsi2c38, adresy 0x40 i 0x41 | głośnik dolny i słuchawka rozmowowa (drugi głośnik) |

Źródło: `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:2015` (UAIF0 do
kodeka), `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:2027` (UAIF1 do obu wzmacniaczy), `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6110`
(kodek), `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6355` i `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6394` (wzmacniacze).

Bluetooth jest niezależny: układ BCM4375 wysyła mowę rozmów na piny PCM,
które idą do ABOX, ale da się ją przełączyć na UART (niżej).

## Co działa

**Bluetooth: muzyka (A2DP) i rozmowy (HFP/HSP).** Łatki 0117 (SCO po UART),
0118 (port 3 Mbaud), `CONFIG_BT_RFCOMM=m`, łatka firmware BT w initramfs
(`tools/phone/51-bt-bcm4375.files`), w systemie `pipewire-spa-bluez`
i `pipewire-pulse`. Sprawdzone na telefonie:

- `hcitool cmd 0x3f 0x001d` (odczyt parametrów PCM): `00 02 00 01 01` przed
  łatką 0117, `01 02 00 01 01` po niej, czyli SCO po UART;
- firmware BT ładuje się w 1,4 s (było 18,6 s przy 115200 bodach, a samo
  łącze niosło ok. 92 kbit/s, mniej niż jeden strumień A2DP);
- `bluetoothctl show`: Audio Source, Audio Sink, Handsfree, Handsfree Audio
  Gateway; `pactl info`: PulseAudio (on PipeWire 1.6.8).

Nie sprawdzone: odtwarzanie i rozmowa z prawdziwymi słuchawkami (parowanie
wymaga potwierdzenia na obu urządzeniach). Rozmowy idą w CVSD 8 kHz, bo
`hci_bcm` nie zgłasza mowy szerokopasmowej (mSBC).

**Wzmacniacze głośników.** Łatki 0119 (USI17_I2C i hsi2c38), 0120 (włączenie
magistrali), 0121 (oba CS35L40). Magistrala wstała jako `i2c-1`, rejestr trybu
USI w PERIC1 pod 0x1050 zapisany i odczytany (`0x4`). Po zwolnieniu resetu
(gph1-1, gph1-2) oba układy odpowiadają: DEVID `0x035A40`, REVID `0xA0`,
OTPID `3`; mainline `cs35l41` zna rewizję A0 i mapę OTP 3. Po łatce 0121 oba
przejmuje sterownik (`Cirrus Logic CS35L41 (35a40), Revision: A0`), a regmap
pokazuje stan z Androida: `0x3808` = `0x42` (4100 mA), `0x3810` = `0x2424`,
`0x3814` = `0x7500`, `0x242c` = `0x02000000` (GPIO2 w otwartym drenie).
Wspólne przerwanie gpm24-0: zero wyzwoleń w spoczynku.

Dwa ustalenia z pomiaru, oba w łatce 0121:

- **Boost jak w Androidzie.** Po resecie współczynniki to K1 0x24, K2 0x24,
  nachylenie 0x75, LBST 0, czyli wiersz 1,0 uH / poniżej 20 uF tabeli
  sterownika mainline. Sterownik producenta ich nie zmienia, ustawia tylko
  prąd szczytowy 4100 mA (`sources/ds/cs35l41.c:1579`,
  `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6371`). Opis w DT tym
  wierszem i tym prądem daje dokładnie stan z Androida.
- **Przerwanie w otwartym drenie, nie push-pull.** Oba wzmacniacze dzielą
  linię gpm24-0. Z wyłączonymi wyjściami GPIO2 obu układów linia czyta 1 nawet
  przy podciąganiu SoC w dół, więc płyta ma własne podciągnięcie w górę.
  Producent ustawia push-pull (`sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6384`, `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6422`), przy którym jeden układ
  może ciągnąć linię przeciw drugiemu.

**Kodek CS47L93.** Łatki 0122-0124: wiązanie SPI dla 9820 (fallback
exynos850, FIFO 64), USI01 z kontrolerem SPI2 (sysreg `0x100c`), kodek na
`spi_2` z szynami LDO17M/LDO18M. Kodek odpowiada: `CS47L93 silicon revision 1`
(measurements/2026-09-25-kodek). Dwie rzeczy, które wyszły na sprzęcie:
pierwsze włączenie LDO18M przez ACPM poszło bez skutków ubocznych, a CS musi
być GPIO, bo sprzętowy CS bloków USI puszcza po każdym transferze i odczyt
rejestru kodeka dawał `0xffff`. Stos Madera jest na razie modułem ładowanym
ręcznie; brakuje MCLK (26 MHz dla FLL) i ścieżki danych przez ABOX.

**Ścieżka danych ABOX bez firmware DSP.** RDMA0, SPUS, SIFS i UAIF1 jako
master I2S, wszystko programowane z AP, pobiera próbki w tempie 48 kHz
(measurements/2026-09-25-dzwiek, eksperyment E3): 193 B/ms wobec 192 B/ms
wymaganych dla 16 bit stereo. Dane ciągnie UAIF: samo RDMA, także z licznikiem
SIFS, stoi.

**Głośniki grają (prototyp ALSA `tools/phone/abox9820`).** Moduł spoza
drzewa rejestruje kartę `S10Plus` z jednym łączem: UAIF1 jako master I2S
48 kHz 2x16 bit do obu CS35L40, odtwarzanie przez RDMA0, nagrywanie z linii
SDOUT wzmacniaczy przez NSRC0, SIFM0 i WDMA1. Dowód bez ucha, bo wzmacniacze
same mierzą napięcie (VMON) i prąd (IMON) na głośniku i oddają je w slocie
swojego kanału. Grany jednocześnie ton 1 kHz w lewym kanale i 500 Hz
w prawym, -30 dBFS (measurements/2026-09-25-dzwiek, `vi.sh`):

| pomiar | lewy slot (słuchawka, 0x41) | prawy slot (dolny, 0x40) |
| --- | --- | --- |
| VMON | 1 kHz, 763 LSB, 500 Hz 0,0 | 500 Hz, 791 LSB, 1 kHz 0,0 |
| IMON | 1 kHz, 711 LSB, 500 Hz 0,2 | 500 Hz, 731 LSB, 1 kHz 1,2 |

Prąd płynie przez cewki obu głośników, każdy dostaje swój kanał, przesłuch
na poziomie szumu. PipeWire od razu wystawia kartę jako „Wbudowany dźwięk
Stereo” (wyjście i wejście). Trzy ustalenia z uruchomienia:

- **NSRC0 zasila WDMA1, nie WDMA0.** W grafie producenta WDMA0 bierze ścieżkę
  RECP, a SIFMn idzie do WDMA(n+1) (`sources/ds/abox_cmpnt_v20.c:5007`).
  Z WDMA0 status stał na zerze, z WDMA1 ruszył od razu.
- **Dwa wzmacniacze na jednej linii SDOUT kolidują przez ASPTX2.** Źródło
  ASPTX2 jest po resecie IMON, slot 1 u obu, więc przy nagrywaniu w slocie 1
  nadawały naraz trzy nadajniki. Przy dwóch slotach I2S ASP TX2 Source musi
  być Zero; pełne V/I obu wzmacniaczy wymaga TDM 4x32 jak w Androidzie
  (DSP_A, sloty 0-3).
- **Karta i komponent w jednym module blokują `rmmod`.** Komponent bierze
  referencję na własny moduł przy sondowaniu karty; `module_get_upon_open`
  przenosi ją na otwarcie strumienia.

Bez firmware ochrony głośników wzmocnienie analogowe zostaje na 9 (Android
z ochroną: 17).

**Firmware ochrony głośników: pierwsza próba (25.09.2026, nieudana).**
Plik `.wmfw` producenta (CSPL, WMFW rev 3, rdzeń Halo) jest wspólny dla
obu głośników, strojenie `.bin` różne (bot, rcv); mainline szuka ich jako
`cirrus/cs35l41-dsp1-spk-prot-samsung-beyond2lte-{bottom,top}.{wmfw,bin}`,
gdy wzmacniacz ma nazwę systemu (w prototypie ustawianą z modułu karty,
docelowo `cirrus,subsystem-id` z wiązania DT). Kalibracja fabryczna leży
w `sec_efs/cirrus`: `rdc_cal_r` 8523 (dolny, `right-channel-amp`),
`rdc_cal` 8173 (słuchawka), `temp_cal` 29; producent wpisuje ją po
załadowaniu firmware do CAL_R, CAL_AMBIENT, CAL_STATUS = 1 i CAL_CHECKSUM
= 1 + RDC (`sources/ds/cirrus-cal.c:774`). Wynik:

- oba pliki znalezione, ale pierwszy zapis danych (XM_PACKED, 840 B pod
  0x02000000) kończy się NACK na I2C (`-ENXIO`). To pierwszy transfer
  dłuższy niż FIFO na tej magistrali; sterownik HDA przed ładowaniem pisze
  `DSP_CLK_CTRL` (0x2C08) = 3, sterownik ASoC nie;
- druga próba (przełącznik Preload na 0 przy `toggle_preload` też ładuje
  firmware, potem odtwarzanie i Preload 1) zawiesiła telefon, zanim skrypt
  wypisał pierwszą linię; brak logu.

Następna próba tylko przy właścicielu: `dmesg -w` przesyłany na PC przez
cały czas, odczyt `DSP_CLK_CTRL` i `PLL_CLK_CTRL` bez strumienia i w trakcie,
ładowanie przy działającym BCLK, jeden krok naraz.

## Co blokuje dźwięk wewnętrzny

1. **ABOX nie ma sterownika w mainline.** U producenta DMA odtwarzania
   i nagrywania (RDMA/WDMA) programuje firmware DSP przez IPC
   (`PCM_SET_BUFFER`, `PCM_PLTDAI_TRIGGER`: `sources/ds/abox_rdma.c:1455`,
   `sources/ds/abox_rdma.c:1571`). AP pisze sam tylko routing, UAIF i głośność, a wskaźnik bufora
   czyta z `ABOX_RDMA_STATUS` (`sources/ds/abox_rdma.c:1616`). Nagłówek rejestrów opisuje
   w `ABOX_RDMA_CTRL0` tylko bit włączenia i długość paczki
   (`sources/ds/abox_soc.h:410`, `sources/ds/abox_soc.h:425`,
   `sources/ds/abox_soc.h:428`); format próbki i liczbę kanałów
   zna wyłącznie firmware. Dwie drogi:
   - uruchomić firmware Calliope tak jak Android (ładowanie do SRAM i DRAM
     ABOX, SYSMMU ABOX, rdzeń DSP przez PMU, protokół IPC z nagłówków
     producenta). Pliki leżą na partycji vendor telefonu (`calliope_sram.bin`,
     `calliope_dram.bin` i wersje `_2`), kopia z sumami:
     `D:\S10Plus-backup\vendor-audio-2026-09-25`;
   - sterować RDMA z AP bez firmware. Ta droga jest już rozpoznana: układ pól
     `RDMA_CTRL0` (FORMAT, EXPEND, FUNC, BUF_TYPE, BUF_UPDATE, BURST_LEN),
     jednostki adresów i kolejność zapisów odczytane z funkcji dostępowych
     firmware, a SMMU bloku audio jest po starcie wyłączona, więc DMA widzi
     adresy fizyczne (measurements/2026-09-25-dzwiek). Brakuje jeszcze
     konfiguracji SPUS/SIFS, którą firmware robi w `pcm_prepare`, i drogi
     przerwań (GIC wewnątrz ABOX albo timer).
2. **Brak zegarów CMU_AUD w serii.** Blok `0x18C00000` (PLL_AUD0/1, dzielniki
   UAIF0-3, MCLK, DSIF) nie jest w sterowniku zegarów. Domena zasilania AUD jest
   prosta (PMU `0x1900`/`0x1904`, `sources/ds/flexpmu_cal_local_exynos9820.h:3`),
   a sterownik domen `samsung,exynos9820-pd` już działa dla DPU. Sondy tylko do
   odczytu (measurements/2026-09-25-dzwiek) pokazały, że bootloader zostawia
   domenę AUD włączoną, PLL_AUD0 zablokowany na 1179,648 MHz (24576 · 48 kHz),
   wszystkie bramki ABOX otwarte, a ABOX odpowiada z AP (`VERSION` 2.0.1,
   RDMA0_CTRL0 po resecie `0x00400000`). Pułapka dla sterownika: mainline
   `pll0831x` czyta ułamek K spod `con_reg + 8`, a na 9820 leży on pod
   `con_reg + 0xc`; bez poprawki w `clk-pll.c` PLL wyjdzie 1170 MHz. Odczyt
   PLL_CON5_AUD0 (`+0x134`) daje zewnętrzne przerwanie magistrali.
3. **Kodek potrzebował ACPM (rozwiązane).** CS47L93 bierze DCVDD i CPVDD2 z LDO18M
   głównego PMIC (`vdd_codec_1p2`, `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:5694`), które nie jest always-on ani
   boot-on. Główny PMIC jest za firmware APM, więc włączenie to komunikat
   ACPM, dozwolony tylko przy właścicielu. LDO17M (`vdd_pmic_codec_1p8`,
   `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:5683`) jest always-on.

## Następne kroki

1. Zrobione 25.09.2026: LDO18M przez ACPM, SPI2, kodek odczytany. Dalej:
   stos Madera wbudowany, SPI 25 MHz, MCLK1 26 MHz dla FLL (u producenta
   `fll1-refclk` 26 MHz; bramka `AUD_CODEC_MCLK` w CMU_AUD jest otwarta).
2. Sterownik CMU_AUD z tablic producenta (generator zegarów), węzeł domeny AUD.
3. Zrobione 25.09.2026 jako prototyp: ABOX sterowany z AP, odtwarzanie
   i nagrywanie, oba głośniki potwierdzone pomiarem VMON/IMON. Przeniesione
   do serii tego samego dnia, jeszcze bez wgrania na telefon: zegary CMU_AUD
   (0126-0128, PLL_AUD0 jako stała, wszystkie bramki `CLK_IGNORE_UNUSED`,
   blok bez domeny zasilania), sterownik `exynos9820-abox` (0130-0131),
   sterownik karty `beyond-audio` (0132-0133) z wyłączeniem ASPTX2 przy
   starcie, węzły DT (0134-0135). Dalej: pierwsze uruchomienie tego jądra
   (karta ma powstać sama przy starcie), TDM 4x32 (DSP_A) jak w Androidzie,
   format S32, profil UCM dla PipeWire.
4. Firmware ochrony głośników CS35L40 (`cs35l40-bot/rcv-dsp1-spk-prot*`,
   w tej samej kopii) dla pełnej głośności; bez niego tylko ostrożne poziomy.
5. `mfc_fw.bin` z tej samej partycji to firmware sprzętowego dekodera wideo
   (MFC), potrzebny do 4K60 HDR (measurements/2026-09-25-hdr).

## Kodek CS47L93 na UAIF0: mikrofony dzialaja (26.09.2026, jadro #75)

W serii (latki 0130-0135, generatory etap 22 SoC i 17 plyty):

- ABOX ma dwa porty z tabeli: UAIF1 (RDMA0, WDMA1, SIFS1, NSRC0) i UAIF0
  (RDMA1 -> wejscie SPUS 1 -> SIFS2 -> UAIF0, UAIF0 -> NSRC1 -> SIFM1 -> WDMA2).
  Wartosci pol z nazw kontrolek mieszalnika producenta (abox_cmpnt_v20.c:
  spus_outx_texts, sifsx_texts, uaif_spkx_texts, nsrcx_texts); banki RDMA1
  od 0x80 i NSRC1 od 0x600, bo producent ustawia tylko rozmiary.
- Karta ma drugie polaczenie `codec-link`: AIF1 kodeka jako odbiorca zegarow.
  MCLK1 26 MHz producenta pochodzi z wyjscia zegara PMU, ktorego sterownika
  nie ma, wiec FLL1 bierze odniesienie z BCLK portu (MADERA_FLL_SRC_AIF1BCLK),
  SYSCLK 98,304 MHz; FLL wlaczany przy wejsciu kodeka w bias PREPARE (ABOX
  startuje BCLK w prepare, przed DAPM).
- W DT kodeka: `cirrus,dmic-ref = <0 0 1 1>`, `inmode`, `out-mono`, `micvdd`
  3,0 V i `pin-settings` z grupa `aif1` -> funkcja `aif1`. Bez tej grupy piny
  AIF1 kodeka sa po resecie wolne i nagranie przez UAIF0 dawalo same zera.
  MICVDD wymaga `CONFIG_REGULATOR_ARIZONA_MICSUPP` (inaczej atrapa).

Dowod (ton 1 kHz na sluchawce gornej, 500 Hz na dolnym glosniku, -30 dBFS):

    hw:0,1 (AIF1TX1 = IN3L, AIF1TX2 = IN4L), jadro #75:
      kanal 0 (DMIC1, IN3): 500 Hz 36,1  1 kHz 1,4
      kanal 1 (DMIC2, IN4): 500 Hz 1,3   1 kHz 23,6
    przez PipeWire (UCM, paplay + parecord, glosnosc 100%):
      kanal 0: 500 Hz 29,8  1 kHz 1,2
      kanal 1: 500 Hz 1,0   1 kHz 19,4

Kazdy mikrofon slyszy najmocniej glosnik obok siebie: DMIC1 jest na dole,
DMIC2 na gorze.

UCM2: `tools/phone/ucm` (instalacja `sh zainstaluj.sh` na telefonie). Urzadzenia
Speaker (hw,0, priorytet 300), Headphones (hw,1, 100), Mic (hw,1, 200),
Headset (hw,1, 100). PipeWire: domyslne wyjscie Speakers, wejscie Internal
Microphones.

Nie sprawdzone: sluchawki i mikrofon zestawu (trzeba podlaczyc), wykrywanie
gniazda (mainline madera go nie ma; u producenta madera-extcon).

## Firmware ochrony glosnikow: laduje sie i dziala (26.09.2026, jadro #77)

Przyczyna NACK z 25.09 byla po stronie jadra, nie wzmacniacza. Jadra do #75 budowalem
z drzewa WSL, w ktorym `i2c-exynos5.c` byl stara wersja diagnostyczna: odpytywala
`TRANS_STATUS` co 2 ms i stan maszyny nadawczej 0x6 (dolne bity to na 9820 stan, nie bledy)
brala za NACK. Kazdy zapis dluzszy niz ok. 2 ms byl przerywany, a przerwany zapis zawieszal
interfejs I2C wzmacniacza (potem nawet odczyt ID dawal NACK, pomagal dopiero reset).
Dlugie odczyty przechodzily. Z wersja z serii zapisy 260, 844, 2052 i 4004 B wracaja
bajt w bajt. Drugi limit: blok 6144 B pamieci YM trwa na 400 kHz ok. 140 ms, dluzej niz
sztywne 100 ms na wiadomosc, stad `tx timeout`; latka 0136 skaluje limit z dlugoscia
(producent ma plaskie 1 s).

Z obiema poprawkami (dolny wzmacniacz, pliki podlozone pod nazwe bez systemu):

    DSP1: Firmware: 400a4 vendor: 0x2 v0.0.1, 1 algorithms
    DSP1: cirrus/cs35l41-dsp1-spk-prot.bin (v1): v0.0.1
    przy PCM Source = DSP: HALO_STATE 2, HALO_HEARTBEAT 0x5e4 -> 0xa22 w 1 s,
    CSPL_STATE 0 (= RUNNING wg calibration.h producenta), VMON dolnego 55,4

Otwarte:

- kalibracja: mainline (cs35l41_hda) wpisuje CAL_AMBIENT, CAL_R, CAL_STATUS = 1 i
  CAL_CHECKSUM = CAL_R + 1 po zaladowaniu, przed startem DSP. Po starcie CAL_R, STATUS,
  CHECKSUM czytaja sie jako 0 (takze po zapisie wprost pod 0x02800224 jednym transferem),
  CAL_SET_STATUS = 1, a CSPL_TEMPERATURE stoi na 0x05C000 (23,0 w Q14) mimo otoczenia 29.
  Przyjecia kalibracji nie umiem potwierdzic, wiec wzmocnienia (9) nie podnosze;
- DSP bierze RX1 i RX2, a RX2 dolnego to lewy kanal: w VMON dolnego oba tony po ok. 55;
- docelowo `cirrus,subsystem-id = "samsung-beyond2lte"` w wezlach wzmacniaczy (wiazanie
  mainline je zna), wtedy kazdy laduje swoje strojenie (bottom/top) bez dowiazan.

## Ochrona glosnikow kompletna: kalibracja przyjeta, wzmocnienie Androida (27.09.2026, jadro #79)

Trzy rzeczy zamknely otwarte punkty z 26.09:

- **Firmware startuje wstrzymany.** CSPL po zaladowaniu melduje w skrzynce PAUSED, a mainline
  wysylal RESUME tylko przy kolejnych strumieniach. Firmware ignoruje polecenie przez chwile
  po zgloszeniu pauzy (RESUME po 20 ms ginie, po 50 ms przechodzi). Latka 0137 wysyla RESUME
  takze przy pierwszym starcie, 100 ms po nim.
- **Kalibracja trafia przed start DSP.** cs_dsp odrzuca zapis ulotnych kontrolek (EPERM), dopoki
  DSP stoi, a firmware czyta kalibracje wlasnie przy starcie i potem zeruje pola. Narzedzie
  `tools/phone/ochrona-glosnikow` przeladowuje firmware i wpisuje CAL_R, AMBIENT, STATUS,
  CHECKSUM jednym transferem I2C pod 0x02800224. Przyjecie: CAL_SET_STATUS = 2 na obu
  wzmacniaczach (bez kalibracji 1), CSPL_STATE 0.
- **subsystem-id w DT** (`samsung-beyond2lte`, latka wzmacniaczy): kazdy wzmacniacz laduje
  wlasne strojenie `cs35l41-dsp1-spk-prot-samsung-beyond2lte-{bottom,top}`.

Wzmocnienie jak w Androidzie (`mixer_gains.xml` z partycji vendor, glosniki stereo): DSP RX2
Source = ASPRX1, AMP PCM Gain 17 (u nas Analog PCM Volume, to samo pole rejestru),
Digital PCM Volume 817 (to samo pole, 0 dB). Sluchawka w rozmowie ma 4 i 761, to przyszly
profil UCM. Pomiar VMON przy tym samym sygnale:

    wzmocnienie 0:  gorny 1 kHz 107,1   dolny 500 Hz 110,8   (drugi ton 0,0)
    wzmocnienie 17: gorny 1 kHz 756,2   dolny 500 Hz 783,4   (drugi ton 0,0-0,1)

czyli +17 dB, kanaly rozdzielone, CSPL_STATE 0. Model cewki zyje: temperatura rosnie
z glosnoscia (23,0 na starcie, 33-38 po serii testow na 17).

Usluga `ochrona-glosnikow.service` robi to przy kazdym starcie. Dowod po zimnym restarcie:
usluga przeszla sama, odtwarzanie przez PipeWire (`pw-play`), w trakcie
CAL_SET_STATUS=2 i CSPL_STATE=0 na obu, Analog PCM Volume 17.

VPBR (ochrona przed spadkiem napiecia baterii, #85, latka 0139): kontrolki jak u producenta
(`VPBR Switch` zamiast jego `VPBR Enable`), usluga ustawia wartosci z mixer_paths.xml: prog
2,687 V, atak 1 dB co 2,5 us, maks. 2 kroki, czekanie 10 ms, zwolnienie 5 ms. Odczyt po I2C na
obu wzmacniaczach: VPBR_CFG = 0x02005206, PWR_CTRL3 = 0x01001010 (bit 12), bez zmian w trakcie
odtwarzania, VPBR_STATUS = 0 przy naladowanej baterii.

Otwarte: kalibracja powinna docelowo wchodzic ze sterownika, nie z przestrzeni uzytkownika.

## Wykrywanie wtyczki sluchawek (27.09.2026, jadro #81, latka 0138)

Mainline nie ma wykrywania akcesoriow dla kodekow madera (u producenta robi to extcon-madera,
3851 linii). Latka 0138 uzbraja je w sterowniku karty tak, jak ustawia to drzewo producenta
(wezel `cirrus,accdet`, acc@1):

- oba piny JD zasilaja zacisk MICD w trybie JD1L/JD2L (0x8), przerwania MICD_CLAMP rise/fall
  sledza wtyczke; wtyczka jest w gniezdzie, gdy zacisk puszcza (RAW_STATUS_7 bit 4 = 0);
- po wlozeniu ADC MICD mierzy styk mikrofonu przez MICBIAS2A (zrodlo 4, masa 1, rate 7,
  debounce 300 ms, tabela progow producenta): mikrofon albo rozwarcie = zestaw z mikrofonem,
  zwarcie = same sluchawki;
- wynik idzie do jacka karty (`Headphone Jack`, `Headset Mic Jack`), UCM ma `JackControl`,
  wiec PipeWire przelacza sam: sluchawki maja priorytet 400 nad glosnikami 300, mikrofon
  zestawu 300 nad wbudowanymi 200.

Dowod przy pustym gniezdzie (#81): rejestry 0x2C6=0x0218, 0x2D3=0x0003, 0x1A06=0x0015,
przerwania JACKDET podpiete, jack zglasza `off`, w PipeWire port Headphones
`not available`, domyslne wyjscie Speakers, ochrona glosnikow nadal aktywna.

Do sprawdzenia z wtyczka (potrzebny czlowiek): `dmesg | grep jack` po wlozeniu ma dac
`jack inserted: headset|headphones` z odczytem MICDET_ADCVAL, a port Headphones ma przejsc
na `available`. Brak MCLK2 (32 kHz) w DT: madera wlacza zegar 32k z MCLK2, a odbicie
debounce JD dziala tylko przy obecnym zegarze; jesli wlozenie nie da przerwania, to jest
pierwszy podejrzany. Przyciski pilota (#84): przy zestawie MICD zostaje wlaczony w trybie poziomow, progi
z `cirrus,micd-ranges` producenta: 116, 173, 321, 752 ohm (indeksy 37, 43, 51, 60,
odczytane z rejestrow 0x2A8/0x2A9 = 0x333c/0x252b) na play/pauza, asystent, glosniej,
ciszej. Piaty zakres producenta (1257 ohm, KEY_SEARCH) nigdy nie daje przycisku, bo nie
jest nizszy od progu mikrofonu. Jack powstaje w late_probe, bo urzadzenie wejsciowe
jacka rejestruje sie tylko razem z karta: w #83 (jack po rejestracji) byly kontrolki,
ale nie bylo urzadzenia. Teraz `Samsung Galaxy S10+ Headset` (event1) ma klawisze
164, 582, 115, 114 i przelaczniki SW_HEADPHONE_INSERT, SW_MICROPHONE_INSERT.
Nie ma jeszcze pomiaru impedancji sluchawek (HPDET) do strojenia wzmocnienia ani
wyciszania mikrofonu na czas nacisku, ktore robi producent.

Przy okazji w logu: `exynos-clkout probe ... failed with error -22`. To wyjscie zegara
PMU, z ktorego producent karmi MCLK1 kodeka (26 MHz); jego naprawa pozwolilaby wziac
SYSCLK z MCLK1 jak w Androidzie zamiast z BCLK.

## Hi-res 96 i 192 kHz na porcie kodeka (27.09.2026, jadro #86, latka 0140)

Tor ABOX nie przelicza czestotliwosci (SPUS prosto do SIFS, UAIF ciagnie probki zegarem
bitowym), wiec port chodzi z czestotliwoscia swojego zegara. PLL_AUD0 1179,648 MHz dzieli sie
na 48, 96 i 192 kHz (dla 16 bit stereo dzielniki 768, 192, 96), a rodzina 44,1 kHz nie. Latka
0140 daje 96 i 192 kHz na UAIF0 (kodek), wzmacniacze zostaja na 48 kHz (firmware ochrony).

Dowod (#86): mikrofony nagrane przy 48/96/192 kHz, gdy glosniki graja 1 kHz: ton w prazku
1000 Hz o tej samej amplitudzie (8647, 8500, 8502), 139200/278400/556800 probek na ~2,9 s.
PipeWire z `tools/phone/hires/hires.conf` (allowed-rates 48/96/192 kHz): plik 96 kHz na
sluchawki idzie do sprzetu jako 96000, na glosniki jako 48000 (przeliczany).
24 bity (#87, latka 0141): S32_LE na porcie kodeka, kod szerokosci 3 w polu formatu DMA
i UAIF (kody producenta z abox.h: 1=16, 2=24, 3=32 bit). Mikrofony nagrane w S32 przy 192 kHz:
ton 1 kHz 558 732 340 / 65536 = 8526 wobec 8707 w S16, bity 8-15 niezerowe w 369 708 z 384 000
probek, bity 0-7 zawsze zero (24 bity danych w ramce 32). Wzmacniacze przyjmuja tylko S16
(format DAI cs35l41), wiec tor glosnikow zostaje 16-bitowy. Odtwarzania S32 na sluchawkach
nie da sie potwierdzic bez wtyczki.

## Tlumienie echa i szumu do rozmow (27.09.2026, tools/phone/redukcja-echa)

PipeWire 1.6.8 + pakiet `pipewire-echo-cancel` (WebRTC: AEC, redukcja szumu, filtr
gornoprzepustowy, AGC), odniesienie z monitora domyslnego wyjscia. Nowe zrodlo "Mikrofon do
rozmow", surowy mikrofon zostaje domyslny. Pomiar wielotonem w pasmie mowy (8 tonow
310-3130 Hz, obwiednia 4 Hz), oba zrodla nagrywane naraz, druga polowa nagrania:

    echo z glosnikow (odniesienie jest):   surowy 55,4  ->  bez echa 3,2   (-24,7 dB)
    ten sam sygnal bez odniesienia (aplay wprost na hw:0,0, jak glos przy telefonie):
                                           surowy 385,2 ->  bez echa 131,2 (-9,3 dB)

czyli modul nie wycisza mikrofonu, tylko odejmuje to, co gra telefon; spadek przy braku
odniesienia to redukcja szumu (staly wieloton wyglada dla niej jak szum, mowa mniej).

Bluetooth audio: PipeWire ma kodeki SBC, AAC, aptX, LDAC (jak Android) oraz LC3, Opus, mSBC,
kontroler wystawia A2DP Sink/Source. Sprawdzone 27.09.2026 ze sluchawkami JBL TUNE FLEX:
sparowane, strumien A2DP 03:24:53-03:32:51 (bluetoothd "sep2/fd0: fd ready"), WirePlumber
zapamietal profil a2dp-sink / headset-output, AVRCP podpiety (mpris-proxy "Player
registered"), grajace potwierdzone przez usera uchem. Wynegocjowanego kodeka ten przebieg
nie zapisal; przy nastepnym polaczeniu odczyt przez wpctl inspect wezla bluez_output.

## Sluchawki przewodowe dzialaja (27.09.2026)

Test z wtyczka: jadro wykrywa ja (`jack inserted: headphones`, `Headphone Jack` = on, przerwania
JACKDET rosna przy kazdym wlozeniu i wyjeciu), user potwierdzil odtwarzanie uchem. Dwie usterki
po drodze, obie w przestrzeni uzytkownika:

- **Dzwiek zostawal w glosnikach.** Glosniki (hw:0,0) i sluchawki (hw:0,1) to osobne urzadzenia
  PCM, wiec priorytety portow z UCM (400 nad 300) nie przechodza na wezly. WirePlumber dawal
  glosnikom priority.session 1000, sluchawkom 728. Regula
  `tools/phone/ucm/wireplumber/51-beyond-jack.conf` daje wezlowi sluchawek 1100; po wlozeniu
  wtyczki domyslnym wyjsciem zostaja sluchawki.
- **Sluchawki milczaly.** `HPOUT2 Digital Switch` jest po resecie wylaczony, a Android wlacza go
  w sciezce dev-headset (mixer_paths.xml). UCM Headphones ustawia go teraz w EnableSequence
  i gasi w DisableSequence. Glosnosc wejscia miksera 32 (0 dB), jak u producenta.

Te sluchawki pomiar ADC MICD ocenil jako zwarcie na styku mikrofonu (ADCVAL 0, 3 ohm), czyli
sluchawki bez mikrofonu; user potwierdzil, ze mikrofonu nie maja, wiec rozpoznanie jest trafne.
Mikrofon zestawu i przyciski pilota czekaja na sluchawki przewodowe z mikrofonem.

Przelaczanie w obie strony potwierdzone przez usera: wlozenie wtyczki przenosi dzwiek na
sluchawki i wycisza glosniki, wyjecie wraca na glosniki (port sluchawek niedostepny, wezel
glosnikow znow domyslny).

Sluchawki Bluetooth, drugie polaczenie (27.09.2026): A2DP gra kodekiem AAC (api.bluez5.codec),
profile rozmow headset-head-unit (mSBC) i headset-head-unit-cvsd dostepne. Mikrofon w mSBC
(16 kHz, SCO po UART): 60 s nagrania, RMS na sekunde 2-90 w przerwach, 1000-6194 przy mowie
(user mowil w trakcie), czyli okolo 70 dB zakresu. Po tescie profil wraca na a2dp-sink.
