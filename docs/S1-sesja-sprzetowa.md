### S1: pierwsza sesja przy telefonie, 11 wrzesnia 2026

Etap 0a z `docs/UART-BRINGUP.md`, czyli jedyny etap, ktory nie potrzebuje ani UART-a, ani
naszego jadra. Telefon pracowal na stockowym Androidzie 12 z rootem Magiska, podpiety przez
adb. Material i metryka pochodzenia: `measurements/2026-09-11-etap0a/`.

Sesja skonczyla sie inaczej, niz zakladala procedura: dala wiecej, niz miala dac, i przy okazji
**zresetowala telefon**, co jest opisane nizej bez owijania.

#### Co zamknelo sie na sprzecie

Trzy pozycje wypadly z `docs/HW-BLOCKED.md` (leza tam teraz w sekcji "Zamkniete pomiarem"):

| pozycja | wartosc | skad |
|---|---|---|
| HW-31 mapa RAM-u | szesc bankow, razem 8082 MiB, dwie dziury ponizej 4 GiB | `/sys/firmware/fdt` |
| HW-34 obszary EL2 i KASLR | 0x80001000+0x1000, 0x87000000+0x200000, 0x9_fd800000+0x2800000 | `/sys/firmware/fdt` |
| HW-19 adres framebuffera | 0xca000000 | `/proc/cmdline` |

Kluczowy okazal sie **caly blob drzewa urzadzen**, ktory stockowe jadro wystawia pod
`/sys/firmware/fdt`: 371894 bajty tego, co bootloader tej plyty naprawde podaje jadru, z modelem
"Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820". Procedura przewidywala `/proc/iomem`
i `dmesg`, a blob jest od nich mocniejszy: niesie wezly `memory@` wprost, z granicami, ktorych
`/proc/iomem` nie rozroznia (trzy gorne banki po 2 GiB widac tam jako jeden ciagly zakres, bo
sie stykaja). `dmesg` nie dal nic, bo bufor zdazyl sie przewinac.

Przy okazji potwierdzil sie **komplet** rezerwacji w pliku plyty: wszystkie jedenascie, nie
tylko te trzy sporne. Kazda ma teraz pokrycie w odczycie z urzadzenia, a nie w cudzym drzewie.

Trafne okazaly sie tez wszystkie przewidywania z poprzedniej wersji HW-31: trzy banki ponizej
4 GiB rozdzielone dziurami, banki startujace pod 0x0_80000000 i 0x8_80000000, i to, ze wartosc
producenta (trzy plaskie banki po 2 GiB, razem 6 GiB) **nie** opisuje tego egzemplarza.

#### Co jeszcze widac w odczytach, choc nikt o to nie pytal

Porownanie naszych wezlow bloku wyswietlacza z drzewem z telefonu i z jego
`/proc/interrupts` dalo dwie rzeczy, ktore warto miec zapisane.

**Nasze trzy przerwania DECON-a to dokladnie te, ktorych uzywa producent.** Jego drzewo
wymienia ich **cztery** (`0xb7, 0xb8, 0xbd, 0x197`, czyli SPI 183, 184, 189 i 407), ale
w dzialajacym systemie rejestruje sie tylko trzy pierwsze: `GIC-0 215` i `216` z licznikami
po 6045 (start i koniec ramki) oraz `221` z zerem (linia bledu, w normalnej pracy milczy).
Czwartego, SPI 407, w `/proc/interrupts` nie ma wcale, wiec sterownik producenta go nie bierze.
Nasz plik SoC ma te trzy i nic nie pomija.

**Wyzwalacz TE nie jest przerwaniem GIC.** Na tym samym urzadzeniu wisi osobna linia
`exynos_gpio_irq_chip 0 Edge 19030000.decon_f` z licznikiem 8383, czyli TE przychodzi przez
kontroler GPIO, nie przez GIC. Zgadza sie to z `pinctrl-0 = <&decon_te_pins>` w naszym wezle
i jest kontekstem dla HW-38.

DSIM tez sie zgadza: producent daje mu `0xbe` (SPI 190), a licznik `GIC-0 222` pokazuje 41618
zdarzen, czyli linia realnie pracuje. Nasz wezel ma dokladnie ten numer.

#### Co doszlo do kolejki

**HW-39, typ wyzwalania przerwan.** Nasz plik SoC opisuje kazde przerwanie jako poziomowe
(35 wpisow `IRQ_TYPE_LEVEL_HIGH`, 4 `IRQ_TYPE_LEVEL_LOW`). Drzewo producenta nie ustawia typu
prawie nigdzie (441 z 458 trojek ma `IRQ_TYPE_NONE`), a jego jadro konczy z 256 liniami jako
`Edge` i 33 jako `Level`. Numery przerwan sie zgadzaja i to zostalo sprawdzone osobno; otwarty
jest sam typ. To **nie jest** powod, zeby przepisac zero od producenta: poziom wysoki to
konwencja calego mainline dla tej rodziny (exynos5433 ma tak 108 wpisow, exynos8895 92,
exynos850 54). Pozycja istnieje dlatego, ze port twierdzi cos, czego na tym sprzecie nikt nie
sprawdzil, a rozjazd z jedynym dzialajacym systemem na tej plycie jest faktem.

**HW-40, rewizja panelu: powstala i zamknela sie tego samego dnia.** Bootloader podaje
`lcdtype=10555411`, czyli 0xA11013. Naglowek
producenta, z ktorego przepisano sekwencje inicjalizacyjna i tablice dimmingu, zna dla tej plyty
trzy warianty (0x900100, 0xA01010, 0xA01011) i **zadnego takiego**. Mlodszy polbajt pierwszego
bajtu to kolor obudowy (`sources/ds/panel_drv.c:145`), wiec rozni sie ostatni bajt: 0x13 zamiast
0x10 albo 0x11, a to u Samsunga rewizja sterownika wyswietlacza. Nasz sterownik panelu nie czyta
identyfikatora w ogole, wiec stosuje jeden staly zestaw tablic niezaleznie od tego, co siedzi
w telefonie. Wygladalo to powaznie, ale rozstrzygnelo sie po sciagnieciu jednego brakujacego pliku
producenta: wariantu **nie wybiera** pole `.id`, tylko tablica `panel-lut` z drzewa urzadzen,
dopasowywana z maska (`sources/ds/panel.c:187-207`). Tablica z tego telefonu ma na koncu wpis
z maska zero, ktory lapie wszystko i wskazuje `_default`, czyli dokladnie ten wariant, z ktorego
przepisano tablice do serii. Ostatni bajt identyfikatora nie ma znaczenia dla wyboru.
Szczegoly i bramka: `docs/HW-BLOCKED.md`, sekcja zamknietych.

#### Co sie nie zamknelo i dlaczego

**HW-20, odstepy czasowe szyn panelu.** Nie da sie odczytac przez adb. To pomiar sonda na
zlaczu panelu i zostaje na etap sprzed pierwszej proby zapalenia ekranu.

Material przepuszczono przez analize wszystkich 38 pozycji wobec nowego blobu: szesciu agentow
na plastrach listy, potem trzech sceptykow z osobnymi soczewkami (czy cytat istnieje, czy dotyczy
tej samej wielkosci, czy pochodzi z tej plyty). Z pieciu mocnych wnioskow **trzy przeszly
jednoglosnie** (te wyzej), a **dwa zostaly obalone** i slusznie:

- **HW-15** (numery przerwan): wniosek brzmial "zamkniete", ale pozycja wymaga porownania
  `/proc/interrupts` przy **wymuszonej aktywnosci** kazdego bloku, a nie cytatu z DTB. Do tego
  cytowana wartosc nie byla nowa: `sources/ds/exynos9820.dts:8235` ma ja od dawna. Zostaje otwarte.
- **HW-22**: wezel w blobie ze stocka jest znak w znak tym samym wezlem, ktory pozycja **juz**
  cytuje z drzewa producenta. Nowy material nie wnosi tu nic. Zostaje otwarte.

Dwadziescia dwie pozycje dostaly werdykt "potwierdza": blob zgadza sie z tym, co mielismy, ale
nie jest pomiarem tej wielkosci (czestotliwosci na pinach, zawartosc rejestrow w locie, MTP
panelu). Zadna z nich nie wypada z listy.

#### Czym to zaplacono: reset telefonu

Proba odczytu `/sys/kernel/debug/vclk/VCLK_BLK_DPU/*` **wywrocila jadro i zresetowala telefon**.
Dowod z `/sys/fs/pstore/dmesg-ramoops-0` po restarcie, slad z procesu `cat`:

```
ra_get_div_mux+0x8/0x40
vclk_recalc_rate.part.0+0x74/0xf0
vclk_table_dump+0x3c/0x180
seq_read -> full_proxy_read -> vfs_read
Code: f9400c01 b40001a1 (b9400021)
```

Handler `read` tego wezla chodzi po tablicy zegarow i luska wskaznik, ktory dla czesci wpisow
jest zly. Sec_debug zamienia kazdy Oops w reset, wiec telefon wstal z `/proc/reset_reason` = `KPON`.

**Lekcja: debugfs producenta nie jest kanalem tylko do odczytu.** Nie wracac do `vclk/*`,
`decon/dump0`, `decon/event0`, `exynos-ss/*`, `exynos-rgt/*`. Bezpieczne sa `/proc/*`,
`/sys/firmware/fdt`, `/sys/firmware/devicetree`, pojedyncze atrybuty `/sys/class/*` i
`/sys/fs/pstore/*`. Nic nie zostalo utracone: mapa RAM-u wyszla ze zrodla pewniejszego niz
cokolwiek w debugfs, a na telefon nic nie bylo zapisywane.

Druga pulapka, tansza: `adb exec-out` psuje dane binarne na tej maszynie (blob 371894 B wyszedl
jako 372365 B, zamiana koncow linii). Binaria brac przez `base64` i sprawdzac `totalsize`
z naglowka wzgledem rozmiaru pliku.

#### Co z tego zmienilo sie w repozytorium

**Znaleziony przy okazji rozjazd, ktorego nikt nie pilnowal.** Plik plyty ma generator, ktory
sam o sobie pisze, ze jest zrodlem prawdy, ale nikt go nie uruchamial od rundy R9 i **rozjechal
sie z seria**: caly blok `reserved-memory`, jedenascie rezerwacji, istnial tylko w serii.
Wersja z generatora byla o 79 wierszy krotsza i cofnelaby ta prace, gdyby ktos jej uzyl.
Generator zostal uzupelniony, plik plyty jest teraz co do znaku jego wyjsciem, a rozjazd pilnuje
nowa bramka. Drugi generator, ten od pliku SoC, byl zgodny na wszystkich czterech etapach.

| co | gdzie |
|---|---|
| banki RAM-u w drzewie plyty | przez `scripts/gen-dts-beyond2lte.py`, wszczepione w `patches/0015` |
| adnotacja HW-39 | przez `scripts/gen-dts-exynos9820.py`, wszczepione w `patches/0014` |
| bramka zgodnosci z generatorami | `scripts/check-gen-dts.py`, trzy testy negatywne |
| bramka mapy pamieci wobec sprzetu | `scripts/check-memory-map.py`, trzy testy negatywne |

Obie bramki mialy przy pierwszym podejsciu **ten sam blad, ktory same tropia**: przy braku
materialu konczyly sie kodem zero, wiec `verify.sh` raportowalby zielone o czyms, czego nie
sprawdzil. Zwracaja teraz kod 2, a skrypt liczy to jako bramke nieuruchomiona; sprawdzone na
atrapie katalogu bez pomiarow i bez repozytorium.
| nowa suma kontrolna DTB | `scripts/golden/dtb.sha256`, poprzednia jako `.przed-mapa-ram` |
| trzy adnotacje `UNVERIFIED` mniej, jedna wiecej | `scripts/golden/unverified-sites.txt` |

Po tych zmianach caly przebieg jest zielony: **65 bramek, 0 padlo, 0 nieuruchomionych**,
z bisectowalnoscia wlacznie (25 punktow serii, w czterech budowane DT),
`build-logs/54-verify-bisect-po-pomiarze.log`.

Zmiana sumy kontrolnej DTB zostala udowodniona, nie nadpisana: build z rewizji sprzed sesji
odtwarza poprzedni hash co do bajtu, a dekompilacja obu blobow rozni sie **wylacznie** szescioma
wezlami `memory@`.

#### Po sesji: warunek konieczny, ktorego nie bylo

Przy porzadkowaniu planu okazalo sie, ze `docs/UART-BRINGUP.md` stawial przed pierwszym bootem
przeszkode, ktorej nie ma. Etap 0- twierdzil, ze bez przebudowy uniLoadera nie da sie podmienic
DTB, i kazal dopisac do niego `board-beyond2lte.c` oraz `beyond2lte_defconfig`. Dla uniLoadera
to prawda, tylko **port, na ktorym stoja etapy 1 i 2, nie startuje przez uniLoader**: pakiet
urzadzenia zalezy od `systemd-boot`, a DT tego portu zyje w forku U-Boota.

W lancuchu EFI jadro samo umie zaladowac wskazany DTB. Konfiguracja portu ma
`CONFIG_EFI_ARMSTUB_DTB_LOADER=y`, co wlacza parametr `dtb=`: stub wczytuje plik z tego samego
systemu plikow, z ktorego wczytano jadro, i **podstawia go w miejsce drzewa od firmware**,
wypisujac przy tym `Using DTB from command line`. Warunek jest jeden: secure boot musi byc
zgloszony jako wylaczony, a brak zmiennej `SecureBoot` liczy sie wlasnie tak, wiec U-Boot bez
`CONFIG_EFI_SECURE_BOOT` przechodzi. Gdyby jednak stub odmowil, powie to wprost linia
`Ignoring DTB from command line.`, i dopiero wtedy wraca temat uniLoadera.

Sprawdzona jest tez droga pliku do `/boot/dtbs`: nasz DTB jest wymieniony w
`arch/arm64/boot/dts/exynos/Makefile`, a pakiet jadra portu wola `dtbs_install`. Cala procedura,
z podzialem na to, co potwierdzone w zrodlach, i to, co rozstrzyga sie przy telefonie, jest
w `docs/UART-BRINGUP.md`, etap 0-.

Druga poprawka z tego samego przegladu: blokada `# CONFIG_DEVMEM is not set` dotyczy **tylko**
pakietu jadra portu pmOS. W mainline `DEVMEM` ma `default y`, a `STRICT_DEVMEM` na arm64 nie
zamyka drogi do rejestrow urzadzen, bo przepuszcza wszystko, co nie jest pamiecia RAM, dopoki
nikt nie wlaczy `IO_STRICT_DEVMEM`. Na naszym jadrze odczyty z etapu 2 zadzialaja bez zadnej
dodatkowej opcji.

#### Nastepny krok

Etap 0a jest zamkniety poza HW-20. Kolejne piec pozycji (HW-23, HW-11, HW-07, HW-08, HW-09)
czeka na etapy 1 i 2, czyli na **istniejacy port pmOS**, a nie na nasza serie. Warunek
wstepny sprzed telefonu jest nadal niespelniony: pakiet jadra tego portu
jest zbudowany z `# CONFIG_DEVMEM is not set`, wiec zaden odczyt rejestru w nim nie zadziala.
Szczegoly i dwie drogi wyjscia: `docs/UART-BRINGUP.md`, etap 1.
