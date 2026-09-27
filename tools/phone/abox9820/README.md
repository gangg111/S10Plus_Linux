# abox9820: prototyp dźwięku przez ABOX bez firmware DSP

Moduł spoza drzewa. Rejestruje kartę ALSA `S10Plus` z jednym łączem UAIF1
(master I2S 48 kHz, 2x16 bit) do obu wzmacniaczy CS35L40:

- odtwarzanie: RDMA0 -> SPUS -> SIFS1 -> UAIF1 -> wzmacniacze (lewy kanał
  słuchawka 0x41, prawy dolny głośnik 0x40);
- nagrywanie: linia SDOUT wzmacniaczy -> UAIF1 -> NSRC0 -> SIFM0 -> WDMA1;
  wzmacniacze oddają VMON/IMON w slocie swojego kanału.

Wymaga domeny AUD i PLL_AUD0 w stanie po bootloaderze (sprawdzane
w probe). Dzielnik BCLK w CMU_AUD i piny UAIF1 pisze wprost; przy usunięciu
przywraca wszystkie ruszane rejestry. Opis i pomiary: docs/R19-dzwiek.md,
measurements/2026-09-25-dzwiek.

## Budowa i ładowanie

W WSL, na drzewie jądra z `~/linux` (to samo, z którego jest jądro telefonu):

    make -C ~/linux ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M=$PWD W=1 modules

Na telefonie:

    sudo insmod abox9820.ko
    # usuniecie: WirePlumber trzyma karte, wiec najpierw
    systemctl --user stop wireplumber
    sudo rmmod abox9820

## Ustawienia wzmacniaczy

    amixer -c 0 cset name='Bottom Analog PCM Volume' 9   # tak samo Top
    amixer -c 0 cset name='Bottom ASP TX2 Source' Zero   # tak samo Top

Wzmocnienie 9 zamiast androidowego 17, dopóki nie działa firmware ochrony
głośników. ASP TX2 Source musi być Zero przy dwóch slotach I2S: po resecie
jest IMON w slocie 1 u obu wzmacniaczy i kilka nadajników kłóci się o linię.
Do pomiaru `ASP TX1 Source` = VMON albo IMON.

## Test bez ucha

`measurements/2026-09-25-dzwiek/vi.sh`: gra 1 kHz w lewym i 500 Hz w prawym
kanale, nagrywa VMON i IMON, `analiza.py` podaje amplitudę każdej
częstotliwości w każdym kanale. Poprawny wynik: w lewym tylko 1 kHz,
w prawym tylko 500 Hz, po kilkaset LSB.
