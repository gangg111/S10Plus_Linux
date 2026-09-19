# Jig UART dla SM-G975F: po co, na czym stoi i jak go zrobić

Bez kanału szeregowego etap 0 z `docs/UART-BRINGUP.md` jest ślepy: błąd w DECON-ie albo w domenie
zasilania nie zostawia śladu na ekranie. Ten katalog trzyma projekt przejściówki, która wyprowadza
UART telefonu na zwykłą przejściówkę USB.

## Na czym to stoi

Telefon nie ma wyprowadzenia UART. Ma za to układ MUIC (MAX77705), który potrafi **przełączyć
magistralę danych USB na UART**, gdy zobaczy określoną rezystancję na linii CC. To nie jest
domysł z forum, tylko tablica w sterowniku producenta dla tego telefonu:

| rezystancja | tryb | co robi MUIC |
|---|---|---|
| 619 kΩ | `JIG UART ON` | przełącza `COM_UART`, telefon startuje normalnie |
| 523 kΩ | `JIG UART OFF` | też UART, ale inne zachowanie przy starcie |
| 301 kΩ | `JIG USB ON` | USB |
| 255 kΩ | `JIG USB OFF` | USB |

Wpis dla 619 kΩ: `sources/ds/max77705-muic.c:144-149` (`MAX77705_UIADC_619K`, `muic_switch =
COM_UART`, `vps_name = "JIG UART ON"`). W USB-C nie ma pinu ID, więc rezystancję mierzy blok PD
tego samego układu, sprzętowo: `sources/ds/max77705_pd.c:1386-1387` czyta pole `BIT_FCT_ID`
rejestru `REG_PD_STATUS1`, przerwanie `max77705_fctid_irq` (`:1397`) odpala to przy każdej
zmianie, a `max77705_pd_rid` (`:1093`) zamienia `FCT_619Kohm` na `RID_619K` i wysyła do MUIC-a
(`:1161-1167`). MUIC podstawia tę wartość w miejsce ADC przy dopasowywaniu akcesorium
(`sources/ds/max77705-muic.c:1525-1561`). Most po stronie MUIC-a:
`sources/ds/max77705-muic-ccic.c:131-138`.

**Co pokazał pomiar: na tym egzemplarzu to nie działa.** Przy wpiętym jigu blok CC zgłasza
`rid` równe 7, czyli `RID_OPEN`, gdzie 619 kΩ dałoby 6, a `attached_dev` pokazuje "No VPS",
czyli żadnego dopasowania. Na linii DP przez pełny start telefonu nie przyszedł ani jeden bajt.
Materiał, tor pomiarowy i jego weryfikacja: `measurements/2026-09-17-etap0/`.

Nie jest to wynik przeciw samej idei jiga: ścieżka rozpoznawania rezystancji jest w jądrze
producenta żywa, przerwaniowa i niczym nie obwarowana. Nierozstrzygnięte zostaje, czy 619 kΩ
w ogóle dociera do pinu układu przez dwa metry kabla USB-C, i to jest następny pomiar.

## Dwa warianty wykonania

**Wariant A, płytka z tego katalogu.** Schemat w `uart-jig.kicad_sch`, podgląd w `uart-jig.pdf`
i `uart-jig.png`. Gniazdo USB-C 16-pinowe, dwa rezystory 620 kΩ (po jednym na CC1 i CC2),
moduł konwertera poziomów BSS138 i stabilizator 1,8 V (XC6206P182 z dwoma kondensatorami 1 µF).
Wymaga zamówienia płytki i lutowania SMD.

**Wariant B, z części kupnych, bez zamawiania PCB.** To ten, który realizujemy. Ta sama
elektryka, tylko złożona z gotowych modułów na goldpinach:

| element | rola | cena orientacyjna |
|---|---|---|
| gniazdo USB-C 16 pin na płytce z 12 goldpinami | rozbija gniazdo na pojedyncze piny | 3 zł |
| moduł USB-UART na **CH343P** | ma pin VIO, więc pracuje wprost na logice 1,8 V | 11 zł |
| moduł stabilizatora **1,8 V** (AMS1117-1.8 albo XC6206P182) | zasila VIO | kilka zł |
| 2 × rezystor **619 kΩ** albo 620 kΩ | to one przełączają MUIC | grosze |
| kabel USB-C na USB-C **do danych** | musi mieć CC, D+ i D- | z szuflady |

Wariant B nie potrzebuje konwertera poziomów, bo CH343P sam pracuje na 1,8 V. To jedyna
różnica elektryczna wobec wariantu A.

## Montaż wariantu B

Na płytce gniazda:

- **619 kΩ z CC1 do GND** i **drugi 619 kΩ z CC2 do GND**. Dwa, nie jeden: wtyk kabla ma tylko
  jedną żyłę CC i trafia nią raz w CC1, raz w CC2, zależnie od tego, którą stroną go włożysz.
- **zworka DP1 z DP2** i **zworka DN1 z DN2**. Gniazdo wyprowadza obie pary danych osobno,
  a w telefonie są zwarte. Bez tych zworek odwrócony wtyk oznacza ciszę.
- **VCC zostaje wolne.** Telefonu nie zasilamy, pracuje na baterii.

Do modułu CH343P:

| skąd | dokąd |
|---|---|
| DP (zwarte DP1 i DP2) | TX albo RX modułu |
| DN (zwarte DN1 i DN2) | druga z nich |
| GND płytki gniazda | GND modułu |
| pin 5V modułu | wejście stabilizatora 1,8 V |
| wyjście stabilizatora | pin **VIO** modułu, **bez zworki** na VIO |

Zworka na VIO zwiera go z 3,3 V albo 5 V i jest przeznaczona do innych zastosowań. U nas ma
jej nie być.

## Kolejność uruchamiania

Każdy krok sprawdza jedną rzecz, żeby przy ciszy na terminalu nie zgadywać, gdzie leży problem.

1. **Sam moduł do komputera.** Czy pojawia się port szeregowy. Jeśli nie, doinstalować sterownik
   CH343 od WCH.
2. **Test pętli.** Zewrzeć TX z RX, terminal 115200 8N1, pisać. Znaki muszą wracać. To dowodzi,
   że komputer, sterownik i terminal działają.
3. **Napięcia.** VIO do GND około 1,8 V. TX do GND przy bezczynnym porcie też około 1,8 V,
   bo UART w spoczynku trzyma stan wysoki. Odczyt 3,3 V oznacza, że VIO jest zwarte z 3V3.
4. **Samo przełączenie MUIC, jeszcze bez linii danych.** Włączyć adb po sieci (`adb tcpip 5555`),
   odłączyć USB, uruchomić `adb shell "su -c 'dmesg -w'"` i dopiero wtedy wpiąć telefon w jig.
   Ten krok rozróżnia trzy rzeczy, których odczyt sysfs po fakcie nie rozróżnia, bo
   `max77705_check_rid` wypisuje `rid : N, fct_id : M` przy każdym przerwaniu FCT
   (`sources/ds/max77705_pd.c:1393`):
   - linia z `fct_id` wskazującym 619 kΩ: układ zmierzył i rozpoznał, problem leży dalej,
   - linia z `fct_id` otwartym: układ zmierzył i **nie widzi** rezystora, czyli wina kabla,
     wtyku albo samej wartości,
   - brak linii w ogóle: przerwanie nie przyszło, układ niczego nie mierzył.

   Kontrola po fakcie to `cat /sys/class/sec/ccic/rid` (ma być 6, nie 7) oraz
   `cat /sys/class/sec/switch/attached_dev` (ma być `JIG UART ON`, nie `No VPS`).
5. **Log.** Podłączyć DP i DN, zrestartować telefon, patrzeć na terminal.

Gdy w kroku 5 jest pusto: najpierw **zamienić TX z RX**, bo która z linii D+ i D- jest nadawaniem
telefonu, nie jest jeszcze u nas potwierdzone. Orientacja wtyku nie ma znaczenia, jeśli zworki
i oba rezystory są na miejscu. Zmierzona u nas linia DP dała zero bajtów; DN nie została
sprawdzona w warunkach dowodowych. Kolejność kroków nie jest kosmetyczna: krok 4 wykonany
przed krokiem 5 od razu pokazuje, że cisza w kroku 5 jest skutkiem, a nie zagadką.

## Czego ten jig nie robi

Nie zasila telefonu, nie przenosi USB i nie działa na telefonach Google. U Samsunga UART wychodzi
po pinach danych po przełączeniu MUIC-a, u Pixela po pinach SBU i tam trzeba innej przejściówki.
