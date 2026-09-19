# Etap 0: czy pasywny jig 619 kOhm przelacza SM-G975F na UART

Data: 17 wrzesnia 2026. Telefon: SM-G975F, stockowy Android 12 z rootem Magiska.
Procedura: `docs/UART-BRINGUP.md`, etap 0. Sprzet: `hardware/uart-jig/README.md`, wariant B.

**Wynik: nie przelacza.** Blok CC ukladu MAX77705 nie rozpoznaje naszej rezystancji, wiec
magistrala danych nie idzie na UART, a na linii DP przez caly start telefonu nie ma ani
jednego bajtu.

## Tor pomiarowy i jak zostal sprawdzony

| element | czym potwierdzony |
|---|---|
| gniazdo USB-C z rezystorami | CC1 do GND 618,4 kOhm, CC2 do GND 621 kOhm, CC1 do CC2 1,23 MOhm (dwa rezystory szeregowo przez mase) |
| zworki linii danych | DP1 do DP2 zwarte, DN1 do DN2 zwarte |
| stabilizator 1,8 V | na pinie VIO modulu 1,7982 V |
| poziom logiki modulu | TX do GND w spoczynku 1,7983 V, czyli stan wysoki na 1,8 V, nie 3,3 V |
| sam modul CH343P | petla TX do RX, wpisane znaki wracaja |
| nasluch i zapis do pliku | ta sama petla przez `scratchpad/nasluch.ps1`: `bajtow odebranych: 7`, tresc `ABC123.` |
| okablowanie przed pomiarem | RX do GND rozwarte, pozostale polaczenia zwarte |

Kolejnosc ma znaczenie: zapis zera bajtow jest wart tyle, ile dowod, ze ten sam tor
przed chwila zapisal bajty niezerowe.

## Co zmierzono

**`sboot-dp.log`, 0 bajtow.** Nasluch 120 s na COM7, 115200 8N1, przewod na linii DP
gniazda wpiety w RX modulu, w oknie pomiaru pelny start telefonu. Zero bajtow.

**`muic-jig-wpiety.txt`.** Stan sterownika przy wpietym jigu, odczytany przez adb po WiFi.
Rozstrzygaja dwie pozycje: `rid` rowne 7, czyli `RID_OPEN`, gdzie dzialajacy jig dalby 6
(`RID_619K`), oraz `attached_dev` rowne "No VPS", czyli zadne akcesorium nie zostalo
dopasowane.

**Linia DN: nie zmierzona w warunkach dowodowych.** Rundy sprzed naprawy zworki sa
niewazne (patrz nizej), a po naprawie zmierzono tylko DP.

## Dlaczego wynik jest wnioskiem o ukladzie, a nie o okablowaniu

Sciezka rozpoznawania rezystancji fabrycznej w jadrze producenta jest zywa i niczym
nie obwarowana:

1. Blok PD mierzy rezystancje sam, sprzetowo: `sources/ds/max77705_pd.c:1386-1387` czyta
   `REG_PD_STATUS1` i wyluskuje pole `BIT_FCT_ID`.
2. Odczyt odpala przerwanie `max77705_fctid_irq` (`sources/ds/max77705_pd.c:1397-1403`),
   wiec dzieje sie przy kazdej zmianie, bez pytania kogokolwiek.
3. `max77705_pd_rid` (`sources/ds/max77705_pd.c:1093`) mapuje `FCT_619Kohm` na `RID_619K`
   (`:1138-1144`), wysyla to do MUIC-a i ustawia `cur_rid` (`:1161-1167`).
4. MUIC podstawia te wartosc w miejsce ADC przy dopasowywaniu akcesorium
   (`sources/ds/max77705-muic.c:1525-1561`), wiec wpis `JIG UART ON`
   (`sources/ds/max77705-muic.c:144-149`) zapala sie wlasnie z RID, a nie z pinu UID.
5. Jedyny warunek tego wpisu poza rezystancja to brak napiecia na VBUS, a `vbus_value`
   przy pomiarze wynosil 0.

Mechanizm istnieje, jest przerwaniowy i byl w tym momencie zasilony. Zglosil `RID_OPEN`.
Nie ma tu pola na "sterownik tego nie obsluguje".

## Czego ten pomiar NIE dowodzi

- **Nie dowodzi, ze S-Boot zachowuje sie tak samo.** S-Boot to osobny program z wlasna
  obsluga MUIC-a. Odczyty sysfs pochodza z dzialajacego Androida. Przeciw tej furtce stoi
  tylko jedno: okno pomiaru `sboot-dp.log` obejmowalo caly start, wiec gdyby S-Boot
  przelaczyl magistrale i cokolwiek wypisal, bajty bylyby w pliku.
- **Nie dowodzi, ze rezystancja dociera do pinu ukladu.** Zmierzone 618,4 kOhm jest na
  gniezdzie jiga, a miedzy nim a telefonem sa dwa metry kabla USB-C. Rozroznienie
  "uklad zmierzyl i zobaczyl otwarte" od "uklad nigdy nie mierzyl" wymaga podgladu logu
  jadra w chwili wpinania: `max77705_check_rid` wypisuje `rid : N, fct_id : M`
  (`sources/ds/max77705_pd.c:1393`) przy kazdym przerwaniu FCT.
- **Nie dowodzi niczego o linii DN**, bo jej nie zmierzono w warunkach dowodowych.

## Material niewazny, zostawiony swiadomie

`void-0355-rx-zwarty-z-gnd.log`, 493 bajty, z tego 380 bajtow tresci zapisanych przez PuTTY
miedzy 03:55:24 a 03:55:33 czasu lokalnego. **To nie jest log telefonu.** Okno zapisu lezy
w srodku okresu, w ktorym zworka byla zalozona blednie, RX do masy, przy wciaz podpietym
telefonie. Zawartosc to sygnatura stanu break, nie znakow: 47 procent bajtow to 0x00,
a prawie cala reszta to pojedyncze ciagi jedynek (0xc0, 0xf8, 0x1e, 0x3f).

Plik zostaje z ta nazwa, zeby nikt go pozniej nie wzial za zrzut S-Boota. Z tego samego
powodu niewazne sa dwie wczesniejsze proby restartu z tego wieczoru: tor nie byl wtedy
niczym potwierdzony.
