# decon9820: sterownik KMS na potoku wyswietlania S-Boota

Modul spoza drzewa jadra. Przejmuje potok, ktory zostawia S-Boot (DECON w trybie
polecen DSI z TE, okno 5, IDMA GF0, DSC, SYSMMU w bypassie) bez modesetu: flip to
zapis adresu bufora GEM DMA (CMA ponizej 4 GB) do IDMA i zadanie aktualizacji
cienia okna; na zatrzask czeka do przerwania poczatku ramki (SPI 183, zbocze),
a zdarzenie flipa DRM wysyla zaraz potem. Pomiary: measurements/2026-09-24-decon-m0-m1a,
measurements/2026-09-24-decon-m1b, measurements/2026-09-25-responsywnosc.

## Dlaczego modul, a nie latka w serii

Decyzja 25.09.2026 po red-teamie (agy): sterownik opisuje stan bootloadera, a nie
sprzet, i dubluje sterownik exynos DRM, wiec do serii kierowanej na upstream sie
nie nadaje (wiazanie DT opisujace stan S-Boota zostaloby odrzucone). Docelowa
droga to pelny modeset w exynos DRM (plan M4: blokada PLL z PLL_STAT0 D-PHY,
HW-26; inicjalizacja panelu z MTP; cykl domeny przez SMC). Do tego czasu ten
modul daje 60 kl/s bez kopii CPU.

## Wymagania

- `cma=256M@0-4G` w wierszu polecen jadra (wpis loadera 00-s10.conf).
- `CONFIG_DRM_GEM_DMA_HELPER=m` i `drm_dma_helper.ko` w extra/.
- Latka 0100 (klasa LCD) dla DPMS: sterownik wola lcd_notify_blank_all z
  urzadzeniem posrednim o wezle simple-framebuffer.

## Budowanie i wgrywanie

Po kazdej przebudowie jadra (ta sama wersja, inne ABI):

    wsl: sh tools/pc/buduj-moduly-extra.sh
    pc:  KLUCZ=<klucz> sh tools/pc/wgraj-moduly-extra.sh <adres>

Ladowanie przy starcie: decon9820.service do /etc/systemd/system, potem
`systemctl enable decon9820`. Modulu nie da sie wyladowac (brak module_exit):
odwrot przez `systemctl disable decon9820` i restart.
