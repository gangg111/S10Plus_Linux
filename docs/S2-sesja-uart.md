### S2: druga sesja przy telefonie, 17 wrzesnia 2026, kanal UART

Etap 0 z `docs/UART-BRINGUP.md`: zbudowanie jiga UART i sprawdzenie, czy telefon przelacza
magistrale danych na UART. Material: `measurements/2026-09-17-etap0/`. Sprzet i schemat
polaczen: `hardware/uart-jig/README.md`, wariant B.

**Wynik: nie przelacza.** Wynik jest negatywny, ale rozstrzygniety, a nie zagadkowy.

#### Co zbudowano

Wariant B, z czesci kupnych, bez zamawiania PCB: gniazdo USB-C 16 pin na plytce z goldpinami,
dwa rezystory 619 kOhm na CC1 i CC2 do masy, modul USB-UART na CH343P z pinem VIO,
stabilizator AMS1117-1.8 zasilajacy VIO z pinu 5V modulu. Konwerter poziomow okazal sie
zbedny, bo CH343P pracuje wprost na logice 1,8 V.

Plytke gniazda user przerobil z posiadanego testera kabli USB: wylutowanie diod odcina
niepotrzebne gniazda i zostawia dolne z parami zwartymi po stronie danych.

#### Dlaczego zero bajtow jest tu pomiarem, a nie brakiem pomiaru

Na tym wieczor mogl sie skonczyc falszywym wnioskiem, bo pierwsze trzy proby dawaly cisze
z trzech roznych powodow, z ktorych zaden nie byl wina telefonu:

| objaw | przyczyna | jak wyszla |
|---|---|---|
| PuTTY nie tworzy pliku logu | ustawienia logowania nadpisane przez zaladowanie zapisanej sesji | zastapiony wlasnym nasluchem `scratchpad/nasluch.ps1`, ktory pisze surowe bajty i drukuje licznik |
| petla zwrotna daje 0 bajtow | zworka zalozona RX do masy zamiast TX do RX | znalazl user; po poprawieniu petla zwrocila `ABC123.`, 7 bajtow |
| 380 bajtow smieci w logu PuTTY | zapis w oknie, gdy RX byl zwarty z masa przy podpietym telefonie | korelacja czasu zapisu pliku ze znacznikami czasu rozmowy |

Dopiero po tych trzech rzeczach zero bajtow zaczelo cokolwiek znaczyc. Tor byl przed
pomiarem potwierdzony petla zwrotna, napieciami (VIO 1,7982 V, TX w spoczynku 1,7983 V)
i przedzwonieniem polaczen. Kolejnosc jest cala trescia lekcji: **zapis zera bajtow jest
wart tyle, ile dowod, ze ten sam tor przed chwila zapisal bajty niezerowe.**

Plik `void-0355-rx-zwarty-z-gnd.log` zostaje w katalogu pomiarow pod nazwa, ktora sama
mowi, ze jest niewazny. Jego zawartosc to sygnatura stanu break, nie znakow: 47 procent
bajtow to 0x00, reszta niemal wylacznie pojedyncze ciagi jedynek.

#### Co rozstrzyga wynik

Nie cisza na linii, tylko stan sterownika odczytany przy wpietym jigu:
`rid` rowne 7 (`RID_OPEN`), gdzie dzialajacy jig dalby 6 (`RID_619K`), oraz `attached_dev`
rowne "No VPS".

Sciezka rozpoznawania rezystancji jest przy tym w jadrze producenta **zywa i niczym nie
obwarowana**: blok PD mierzy sprzetowo pole `BIT_FCT_ID` rejestru `REG_PD_STATUS1`
(`sources/ds/max77705_pd.c:1386-1387`), robi to z przerwania (`:1397`), mapuje
`FCT_619Kohm` na `RID_619K` (`:1138-1144`) i wysyla do MUIC-a (`:1161-1167`), a MUIC
podstawia te wartosc w miejsce ADC przy dopasowywaniu akcesorium
(`sources/ds/max77705-muic.c:1525-1561`). Jedyny warunek wpisu `JIG UART ON` poza
rezystancja to brak napiecia na VBUS, a `vbus_value` wynosil 0.

Po drodze poleglo moje wlasne wczesniejsze uzasadnienie, dwa razy:

- twierdzilem, ze `adc: 0x1f` dowodzi, ze uklad nie widzi rezystancji. Nie dowodzi:
  to surowy pin UID, a w USB-C do dopasowania podstawiana jest wartosc z RID.
- twierdzilem, ze odczyt `rid` jest bezwartosciowy, bo `cur_rid` dostaje wartosc tylko przy
  starcie (`sources/ds/max77705_usbc.c:3451`). Bylo tak dlatego, ze mialem trzy pliki z katalogu
  `drivers/ccic`, a nie wszystkie: pole jest aktualizowane w `max77705_pd.c:1167` przy kazdym
  przerwaniu FCT. Dopiero wyliczenie zawartosci calego katalogu przez API GitHuba pokazalo
  brakujacy plik. **Wniosek na przyszlosc: zanim orzeknie sie "martwy kod", trzeba miec
  komplet plikow katalogu, a nie te, ktore akurat sciagnieto.**

#### Czego nie zmierzono

- **Linii DN.** Rundy sprzed naprawy zworki sa niewazne, a po naprawie zmierzono tylko DP.
- **Czy rezystancja dociera do pinu ukladu.** Miedzy zmierzonymi 618,4 kOhm na gniezdzie
  jiga a telefonem sa dwa metry kabla USB-C. Rozroznienie "uklad zmierzyl i zobaczyl
  otwarte" od "uklad nigdy nie mierzyl" daje podglad logu jadra w chwili wpinania:
  `max77705_check_rid` wypisuje `rid : N, fct_id : M` (`sources/ds/max77705_pd.c:1393`).
- **Zachowania S-Boota.** To osobny program z wlasna obsluga MUIC-a, a odczyty sysfs
  pochodza z dzialajacego Androida. Przeciw tej furtce stoi jedno: okno pomiaru DP
  obejmowalo caly start telefonu.

#### Przelom: mamy log S-Boota z telefonu, bez kabla UART

Po tym, jak pasywny kanal okazal sie martwy, cel przesunal sie z "zbuduj jig" na "zdobadz log
S-Boota kazdym mozliwym sposobem". Okazalo sie, ze najprostsza droga w ogole nie potrzebuje
UART-a: **S-Boot zapisuje swoj log do bufora RAM, ktory przezywa restart**, a Android wystawia
go jako `/proc/last_kmsg`. Uptime telefonu w chwili odczytu (2420 s, start 04:03) potwierdza,
ze to log dokladnie tego startu z wpietym jigiem. Zdjety przez base64 (adb, root).

Log rozstrzyga dwie rzeczy, ktorych sysfs nie mogl:

1. **S-Boot ma wlasna obsluge MUIC-a i ona tez widzi otwarte.** `board_ccic_check_uart:
   jig_adc=1f, cc_adc=07`, gdzie `07` to `RID_OPEN`. To zamyka furtke z pierwszej rundy
   ("moze bootloader jednak cos nadaje"): nie nadaje, bo nie widzi jiga.
2. **Cisza na DP nie byla brakiem transmisji, tylko odlaczona magistrala.** S-Boot, nie
   rozpoznawszy jiga, wykonal `ifconn_com_to_open` i zapisal `SWITCH_COMMAND: 0x3f`, czyli
   `COM_OPEN`. Linie danych byly rozlaczone.

Trzeci wiersz, `init_cmdline: default: console=ram loglevel=4`, tlumaczy niezaleznie, czemu
jadro producenta nie pisze na UART: bootloader kieruje konsole do RAM, nie na port.

Pelna analiza, dekodowanie 0x3f i kontekst VDM: `measurements/2026-09-17-etap0/sboot-analiza.md`.
Log: `measurements/2026-09-17-etap0/sboot-log-z-last_kmsg.txt`.

#### Dlaczego pasywny rezystor nie moze zadzialac na USB-C

USB-C nie ma pinu ID. Na micro-USB rezystor "fabryczny" szedl na ID i uklad mierzyl go wprost,
i to dziala do dzis (przewodnik Galaxy S7, MAX77854). Referencyjny `Otus9051/uart-usb-jig`, od
ktorego wyszlismy, tez jest micro-USB. Na USB-C rezystancje "fabryczna" musi odczytac blok CC
w polu `BIT_FCT_ID`, a na tym egzemplarzu ten pomiar zwraca otwarte mimo rezystora na CC.
Zrodla zewnetrzne potwierdzaja regule: nikomu 300k/523k/619k miedzy CC a GND nie zadzialalo na
telefonach USB-C.

Wlasciwym kanalem na USB-C jest **VDM protokolu USB Power Delivery po linii CC**, SVID Samsunga
0x04E8. Praca Alendal, Axelsson, Dyrkolbotn (Advances in Digital Forensics XV, 2019) rozklada to
na Galaxy S9 G960F (ta sama rodzina) i pokazuje slepy replay ramek prawdziwego AnyWaya S103.
To dokladnie ta druga droga, ktora user zamowil (AnyWay S103 + kabel GH81-11962W).

#### Nastepny krok

Pasywna droga jest zamknieta z dowodem, wiec nie ma po co powtarzac pomiaru z jigiem.
Do podgladu S-Boota tej plyty mamy juz dzialajacy, bezsprzetowy kanal: `/proc/last_kmsg`
przez adb po kazdym starcie. Do logu naszego jadra po uruchomieniu portu wystarczy `stdout-path`
na `serial0`, bez jiga.

Realne zapalenie UART-a przed Androidem, gdyby bylo potrzebne, wymaga odtworzenia sekwencji VDM
AnyWaya (SVID 0x04E8) kontrolerem USB-C PD, ktory umie nadawac surowe VDM (np. FUSB302), albo
uzycia zamowionego AnyWaya S103 z kablem GH81-11962W. Materialy: `measurements/2026-09-17-etap0/`.
