# Wi-Fi BCM4375 na PCIe: pierwsze uruchomienie (23.09.2026)

## Co bylo do sprawdzenia

Czy kontroler PCIe pod `0x13ed0000` (latki 0084-0087, nigdy wczesniej
nieuruchomione na sprzecie) wytrenuje lacze z ukladem Wi-Fi, czy `brcmfmac`
uruchomi na BCM4375 obraz producenta z `bcmdhd`, i czy powstanie `wlan0`.

## Co trzeba bylo dolozyc (latki 0101-0103)

Zwiad po zrodlach producenta pokazal trzy blokady, kazda wystarczajaca,
zeby nic nie ruszylo:

1. **Uklad nie mial zasilania.** Polowa Wi-Fi wstaje linia WL_REG_ON
   (`gpg0-5`, aktywna wysokim), ktora u producenta podnosi sterownik
   `bcmdhd` i czeka 100 ms przed treningiem lacza. Teraz: regulator stały
   z ta linia i `startup-delay-us = <100000>`, podany kontrolerowi jako
   `vpcie3v3-supply`, wlaczany w probe przy wcisnietym PERST#.
2. **Kolejnosc.** Producent (`exynos_pcie_establish_link`) zwalnia PERST#
   przed konfiguracja PHY; nasz sterownik robil to po. Teraz jak producent.
3. **MSI nigdy by nie przyszly.** Rdzen DesignWare przy wlaczonym PCI_MSI
   sam buduje domene iMSI-RX, a plyta nie ma podpietego przerwania MSI
   (producent: `use-msi = "false"`). Teraz pusta `msi_init` i
   `bridge->msi_domain = true`: szyna dostaje NO_MSI, brcmfmac jedzie na
   INTx przez `interrupt-map`.

Do tego NVRAM od wlasciwej rewizji: obraz jest tylko `_b1`, a na telefonie
lezal wariant b0 (skrypt bral pierwszy z brzegu). Teraz
`nvram.txt_CS01_semco_b1`.

## Jak zmierzone

Najpierw bezpiecznie: sterownik PCIe jako modul, jadro z nowym drzewem
wstalo bez niego, kontroler ruszyl dopiero po `insmod` (`test-wifi.sh`,
wynik w `pierwsze-insmod.txt`). Zawieszenie oznaczaloby restart, a nie
petle rozruchowa, bo modul nie laduje sie sam.

## Wynik

- `PCIe Gen.1 x1 link up` przy pierwszej probie, ok. 0,1 s po probe.
- Na szynie 1 `14e4:4475`, BAR 0 (64 KiB) i BAR 2 (4 MiB) przydzielone
  w oknie `0x14000000`.
- `brcmfmac: ... chip BCM4375/5`, firmware
  `version 18.41.117 (B1 Network/rsdb)`: obraz `bcmdhd_sta.bin_b1`
  dziala pod brcmfmac (hipoteza z R14 potwierdzona).
- Przerwania INTx: `brcmf_pcie_intr` na wspolnej linii kontrolera, 224
  przerwania w 20 s.
- `wlan0` z prawdziwym adresem z OTP ukladu (`permaddr a8:db:03:...`,
  prefiks Samsunga).
- Skan NetworkManagera: 6 sieci, na 2,4 GHz (kanaly 1, 5, 6, 13) i na
  5 GHz (kanaly 40 i 120), najsilniejsza 80 %. Nazwy sieci usuniete.

Potem docelowo: sterownik wbudowany, firmware w initramfs
(`tools/phone/wszyj-firmware-wifi-w-initramfs.sh`). Po restarcie lacze
o 0,34 s, firmware wczytane o 0,54 s, `wlan0` pod NetworkManagerem bez
recznego kroku, caly rozruch 26,2 s.

## Drugi etap tego samego wieczoru: dane nie szly (latka 0104)

Skan i asocjacja z punktem dostepu dzialaly, ale polaczenie WPA2 padalo
z `reason=15`. Pomiary, jeden po drugim:

- szczegolowy log `wpa_supplicant`: po asocjacji ani jednej ramki EAPOL,
- licznik RX na `wlan0`: 0 pakietow,
- jadro z `CONFIG_BRCMDBG`, `ieee80211/phy0/msgbuf_stats`:
  `h2d_rx_submit: rp 0, wp 511` (firmware nie wzial ani jednego bufora
  odbiorczego), a pierscien polecen chodzil,
- flagi pamieci wspoldzielonej `0x30040007`, slowo `host_cap` (+84) = 0.

Obalone pomiarem: supplicant w firmware (zmiennej `sup_wpa` firmware nie
ma, `-52`), odstep indeksow pierscieni w TCM (flaga 2B nieustawiona),
brak sygnalu host ready. Przyczyna z porownania z `bcmdhd`: brcmfmac nie
zapisywal `host_cap`. Z zapisem `0x1407` przy starcie (latka 0104):
pierscien odbioru ruszyl, 4-way handshake przeszedl, polaczenie 5 GHz
270 Mbit/s, ping do internetu bez strat, pobieranie okolo 90 Mbit/s.
Zapis tego slowa dopiero w trakcie pracy (narzedziem `pcibar`) NIE
wystarczal, firmware czyta je przy starcie.

## 6 GHz: nie ma i nie bedzie

NetworkManager zglasza `2GHZ: yes`, `5GHZ: yes`, `6GHZ: no`, ale
brcmfmac w 7.2 w ogole nie obsluguje 6 GHz, wiec to nie jest dowod.
Dowod niezalezny od sterownika: kalibracja radia modulu (NVRAM B1 Semco)
ma 45 parametrow dla 2,4 GHz, 125 dla 5 GHz i **zero** dla 6 GHz. Modul
nie ma toru radiowego na 6 GHz; firmware tego nie doda.

## Otwarte

- `link_history` w debugfs pokazuje same zera: bufor historii LTSSM
  prawdopodobnie trzeba wlaczyc tak jak producent, zanim zacznie zapisywac.
- `WLC_SET_ROAM_TRIGGER error (-52)`: firmware nie przyjmuje progu
  roamingu i zostaje przy swoim. Niegrozne; na ekran wychodzil przez
  plymouth, stad `loglevel=2`.
- `brcmf_p2p_create_p2pdev: timeout`: interfejs P2P nie powstaje, zwykle
  polaczenie tego nie potrzebuje.
- Modul radiowy (Semco albo Murata) wybrany bez odczytu OTP; wariant
  Murata `nvram.txt_1rh_es43_b1` do sprawdzenia, gdyby zasieg byl slaby.
