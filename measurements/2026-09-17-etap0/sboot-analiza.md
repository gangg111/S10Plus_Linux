# Etap 0, przelom: mamy log S-Boota telefonu, i to on rozstrzyga

Data: 17 wrzesnia 2026, druga runda przy telefonie. Telefon podpiety kablem, adb z rootem.
Zrodlo: `/proc/last_kmsg` telefonu, czyli log poprzedniego startu, zdjety przez base64.
Pelny wycinek bootloadera: `sboot-log-z-last_kmsg.txt` (736 wierszy).

Ten start (uptime w chwili odczytu 2420 s, znacznik 04:03) to **dokladnie ten start z wpietym
jigiem 619 kOhm**, ktory badalismy. Nie musimy juz sluchac UART-a, zeby wiedziec, co robi
S-Boot: on sam zapisal swoje decyzje do bufora, ktory przezyl restart.

## Co S-Boot naprawde zrobil, wiersz po wierszu

```
[0: 0.137] Samsung S-Boot 4.0 for SM-G975F (Mar  2 2023 - 10:36:42 62768724)
[0: 0.390]  FW:1a.10 ST:07 31 00 CC:00 00 PD:00 07 IM:00 00 00 TOPCTRL:81
[0: 0.562] board_ccic_check_uart: jig_adc=1f, cc_adc=07
[0: 0.603] ifconn_is_ccic_jig_device: rid=07
[0: 0.703] ifconn_com_to_open:
[0: 0.761] max77705_set_muic_uart_early: MUIC: SWITCH_COMMAND: 0x3f
[0: 1.216] init_cmdline: default: console=ram loglevel=4
[0: 14.519] ifconn_show_switch_sel: SWITCH_SEL(3)
```

Rozbior:

1. **`CC:00 00`** przy inicjalizacji MUIC-a: blok CC nie widzi na zlaczu zadnej znaczacej
   rezystancji. To odczyt z samego ukladu, nie z sysfs, i pochodzi z warstwy przed Androidem.
2. **`board_ccic_check_uart: jig_adc=1f, cc_adc=07`**: to jest funkcja S-Boota, ktora decyduje
   o UART. `cc_adc=07` to `RID_OPEN`. Dzialajacy jig dalby tu `cc_adc=06`. Czyli **sam
   bootloader, niezaleznie od jadra, tez widzi otwarte**. To zamyka furtke, ktora zostawilismy
   w pierwszej rundzie ("moze S-Boot ma wlasna obsluge MUIC-a i cos jednak nadaje"). Ma wlasna,
   i ta wlasna widzi to samo: brak jiga.
3. **`ifconn_com_to_open`** a potem **`max77705_set_muic_uart_early: SWITCH_COMMAND: 0x3f`**:
   S-Boot, nie rozpoznawszy jiga, ustawil przelacznik magistrali na **0x3f = COM_OPEN**, czyli
   fizycznie ROZLACZYL linie danych. Dekodowanie 0x3f z naglowka producenta
   (`include/linux/muic/max77705-muic.h`, `COMN1SW_SHIFT=0`, `COMP2SW_SHIFT=3`, `COM_OPEN=0x07`):
   (7<<3)|7 = 0x3F. Dla porownania `COM_UART` = (1<<7)|(3<<3)|3 = 0x9B. Cisza na DP w pierwszej
   rundzie nie byla wiec brakiem transmisji, tylko odlaczona magistrala.
4. **`init_cmdline: default: console=ram loglevel=4`**: nawet gdyby magistrala byla na UART,
   jadro producenta i tak nie pisze na port szeregowy, tylko do bufora w RAM. To osobny powod,
   dla ktorego kernel byl niemy, i on jest po stronie oprogramowania, nie sprzetu.

## Wniosek: pasywny rezystor na CC nie wystarcza na tym telefonie

Trzy niezalezne warstwy zgadzaja sie co do jednego, ze na zlaczu nie ma rozpoznawalnego jiga:
odczyt jadra przez adb (`rid 7`, `attached_dev No VPS`), odczyt S-Boota (`cc_adc=07`), rejestr
CC przy starcie (`CC:00 00`). Rezystancja 618,4 kOhm zmierzona na gniezdzie jiga do ukladu nie
dociera jako rozpoznana wartosc.

To nie jest wada naszego egzemplarza ani bledu montazu. Potwierdzaja to zrodla zewnetrzne:
uzytkownicy probowali 300k, 523k i 619k miedzy CC a GND na telefonach USB-C i **nikomu nie
zadzialalo** (watek "HARDWARE UART Cable time" na XDA). Jednoczesnie w cudzych logach S-Boota
ta sama funkcja pokazuje `cc_adc=06`, wiec mechanizm dziala tam, gdzie rezystancja jest podana
tak, jak trzeba.

## Dlaczego tak jest: USB-C nie ma pinu ID

Na micro-USB rezystor szedl na pin ID, ktory uklad mierzyl wprost. To dziala do dzis: przewodnik
dla Galaxy S7 (MAX77854) opisuje jig micro-USB z rezystorem 619 kOhm na ID i realnym logiem
S-Boota. Referencyjny projekt `Otus9051/uart-usb-jig`, od ktorego wyszlismy, tez jest micro-USB,
z rezystorem na ID.

W USB-C pinu ID nie ma. Zeby uklad zmierzyl rezystancje "fabryczna", musi ja odczytac blok CC
w polu `BIT_FCT_ID` (`sources/ds/max77705_pd.c:1386-1387`). Na tym egzemplarzu ten pomiar zwraca
otwarte mimo rezystora na CC. Najprostsze wytlumaczenie, spojne ze wszystkimi zrodlami, jest
takie, ze na USB-C sam rezystor miedzy CC a GND nie jest tym, czego uklad szuka, i wlasciwym
kanalem jest nie rezystancja, tylko komunikat.

## Wlasciwy kanal na USB-C: VDM po CC (to robi AnyWay)

Praca naukowa "Exploiting Vendor-Defined Messages in the USB Power Delivery Protocol"
(Alendal, Axelsson, Dyrkolbotn, Advances in Digital Forensics XV, 2019) rozklada to na czesci,
i to na **Galaxy S9 G960F**, czyli bracie naszego telefonu z tej samej rodziny:

- Konsola bootloadera, ktora na starych telefonach micro-USB wychodzila po rezystorze, na USB-C
  wlaczana jest przez **komunikaty Vendor Defined Message (VDM)** protokolu USB Power Delivery,
  slane po linii CC. Nie przez rezystancje.
- Autorzy przechwycili ruch prawdziwego **Samsung Anyway S103** (Tabela 7) i zrobili **slepy
  replay** z zapisanych ramek. Zadzialalo: telefon wlaczyl te sama konsole bez AnyWaya.
- Uzyta jest SVID Samsunga **0x04E8**. Sekwencja: DiscoverIdentity, potem VDM unstructured
  z vendor use `0x0001`, `0x0002` (cztery slowa danych, pseudolosowe, wyglada na inicjalizacje
  szyfru albo IV), potem seria `0x0003`. Odpowiedzi maja ustawiony bit 6 (0x0040) jako ACK.
  Komunikacja NIE wymaga negocjacji jawnego kontraktu PD, ida od razu VDM-y.

To jest dokladnie ta "druga droga", ktora user planowal (AnyWay S103 + kabel GH81-11962W),
i ktora ma niezalezne, techniczne poparcie w tej pracy. Zwykly rezystor jej nie zastapi.

## Firmware'owe znaleziska z telefonu (przy okazji)

Zdjete z zywej linii polecen jadra (`cat /proc/cmdline` przez su):
```
console=ram  pmic_info=43  sec_debug.level=0  androidboot.debug_level=0x4f4c
```
- `console=ram` potwierdza, ze kernel producenta nie pisze na UART, tylko do RAM. To ustawia
  S-Boot w `init_cmdline`. Nasze jadro tego nie dziedziczy (my podamy `stdout-path`).
- `pmic_info=43` to `switch_sel` (`__setup("pmic_info=", set_switch_sel)`,
  scratchpad `muic-core.c:377-386`). Maski w `muic_init_gpio_cb` (`:466-489`): bit UART wybiera
  tylko sciezke AP kontra CP, **nie ma bitu wymuszajacego sam UART**. 0x43: bit USB (0x40) i
  bit UART (0x02, MUIC_PATH_UART_AP) ustawione, wiec sciezka szeregowa jest kierowana na AP,
  ale to i tak nie pomaga, dopoki magistrala jest COM_OPEN.
- `set_switch_sel` istnieje jako symbol w jadrze (`/proc/kallsyms`), ale to parametr startowy,
  nie da sie nim przelaczyc magistrali w locie.
- `debug_level=0x4f4c` to ASCII "LO", czyli poziom debugowania LOW. Nie odblokowuje UART-a
  na USB-C sam z siebie.
- Programowe wymuszenie przez sysfs odpada: `uart_en`/`uart_sel` tylko ustawiaja flagi kierunku,
  a `debug_opcode` wysyla wylacznie opcode 0x74 do odczytu (`sources/ds/max77705_usbc.c:309-320`).

## Co to znaczy dla portu

Nasze jadro mainline **nie zalezy** od tego, czy jig zadziala: my podajemy wlasny `stdout-path`
zamiast `console=ram`, wiec gdy juz uruchomimy port przez EFI (`dtb=`), nasze jadro bedzie pisac
na `serial0` niezaleznie od S-Boota. Problem jiga dotyczy wylacznie **podgladu S-Boota i kernela
producenta przed nasza seria**, czyli etapu 0 jako narzedzia diagnostycznego, nie samego portu.

Do zdobycia logu S-Boota tej plyty pozostaja trzy drogi, w kolejnosci trudnosci:
1. **`/proc/last_kmsg` i pstore, tak jak tutaj.** Log S-Boota i tak trafia do bufora RAM
   i da sie go zdjac przez adb po kazdym starcie. Dla wielu zadan diagnostycznych to wystarcza
   i nie wymaga zadnego sprzetu. To jest realny, dzialajacy kanal, ktory wlasnie zdobylismy.
2. **VDM po CC, emulacja AnyWaya.** Wymaga kontrolera USB-C PD, ktory umie nadawac surowe VDM
   (np. z ukladem FUSB302), i odtworzenia sekwencji SVID 0x04E8 z pracy. To odpowiednik tego,
   co robi AnyWay S103.
3. **AnyWay S103 + kabel GH81-11962W**, droga serwisowa, ktora user juz zamowil.
