# Kodek CS47L93 na SPI2, 25.09.2026 (przy właścicielu)

Jądro #64, łatki 0122-0124 (wiązanie SPI 9820, USI01 z SPI2, kodek i jego
szyny w PMIC), `CONFIG_SPI_S3C64XX=y`, stos Madera jako moduły ładowane ręcznie
z `/tmp/kodek`, żeby włączenie szyny i start kodeka były osobnymi krokami.
Skrypty: `krok0-stan.sh`, `krok1-ldo18m.sh`, `krok2-kodek.sh`, `zdrowie.sh`;
moduł `ldo18m_wlacz.c` włącza wyłącznie LDO18M przez framework regulatorów.

## Krok 0: stan po rozruchu, bez zapisów

    szyna vdd_pmic_codec_1p8: enabled 1800000 uV, użytkowników 1
    szyna vdd_codec_1p2: disabled 1200000 uV, użytkowników 0
    spi0.0 modalias=spi:cs47l93 sterownik=
    exynos-usi 104700c0.usi: sw_conf offset=0x100c zapisano=0x2 odczyt=0x00000002

Brak komunikatu `Bringing ... uV` w dmesg: opis szyn w DT nie spowodował
zapisu napięcia (LDO18M ma już 1,2 V, LDO17M 1,8 V).

## Krok 1: samo LDO18M (jeden zapis do PMIC przez ACPM)

    ldo18m: przed: wlaczony=0 napiecie=1200000 uV
    ldo18m: po: wlaczony=1 napiecie=1200000 uV

Po kroku: usługi aktywne, panel 420 nitów, szyny dotyku bez zmian, telefon
odpowiada 5 s później. `rmmod` wyłącza szynę (`wlaczony=0`).

## Krok 2, pierwsza próba: CS sterowany przez kontroler

    madera spi0.0: Missing MCLK2, requires 32kHz clock
    madera spi0.0: Unknown device ID: ffff
    statystyki spi0.0: messages=2 transfers=4 bytes_tx=12 bytes_rx=4 errors=0

MISO czyta same jedynki. Odczyt rejestru przez regmap to jedna wiadomość
z dwoma transferami (adres z wypełnieniem, potem dane), a dla bloków USI
sterownik `spi-s3c64xx` ustawia `QUIRK_CS_AUTO`: sprzęt zwalnia CS po każdym
transferze, więc kodek widzi dwie osobne transakcje. Nawet oczekiwanie na
BOOT_DONE przeszło tylko dlatego, że 0xffff ma każdy bit ustawiony.

## Krok 2, CS jako GPIO (`cs-gpios = <&gpp0 7 GPIO_ACTIVE_LOW>`)

    madera spi0.0: Missing MCLK2, requires 32kHz clock
    madera spi0.0: CS47L93 silicon revision 1
    spi0.0 -> madera, errors=0, messages=145, bytes=1272
    madera-irq -> madera-irq, madera-pinctrl -> madera-pinctrl
    129: gpa2 2 Level madera IRQ (zero wyzwoleń w spoczynku)
    runtime_status: suspended (DCVDD wyłączone po probe, zgodnie ze sterownikiem)

Zegar SPI: `dout_peric0_usi01_usi` 20 MHz = 5 MHz · clk_div 4. 25 MHz
producenta wyjdzie dokładnie (200 MHz / 2 = 100 MHz).
