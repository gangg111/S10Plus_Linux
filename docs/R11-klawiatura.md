# R11: klawiatura ekranowa dla konsoli

**Stan:** dziala na sprzecie. 21 wrzesnia 2026 zalogowano sie na telefonie
palcem, bez klawiatury USB: `pmos login: user`, haslo, `Welcome to
postmarketOS!`, prompt `pmos:~$`. Zrzut z bufora ramki:
`measurements/2026-09-20-klawiatura/zalogowany-palcem.png`.

Kod: `tools/klawiatura/`. Uruchamia sie jako usluga systemd, startuje schowana,
przycisk Bixby ja pokazuje i chowa.

## Dlaczego wlasna, a nie gotowa

Wszystkie gotowe klawiatury ekranowe dla Linuksa mobilnego (`wvkbd`,
`squeekboard`, `fbkeyboard`) zakladaja kompozytor Wayland albo wlasne
ustawianie trybu graficznego. U nas jest odwrotny wymog: klawiatura ma
wspolzyc z **zywa konsola tekstowa**, w ktorej uzytkownik sie loguje. Zadna
z nich tego nie robi.

## Cztery rzeczy, ktore rozstrzygnely projekt

### 1. Zapis do ekranu przez `pwrite`, nie przez odwzorowanie w pamieci

Zapis do odwzorowanego bufora sterownika opartego o DRM trafia w sciezke
`deferred_io`, ktora czeka `HZ/20` przed odswiezeniem (`fbdefio.delay`
w `drm_fbdev_shmem.c`). `pwrite` konczy sie w `drm_fb_helper_damage()`
zwyklym `schedule_work()` bez opoznienia. Zmierzony czas wyslania pasa
1440 na 1152 piksele: **46 ms** przy 134 MB/s.

### 2. Miejsce dla klawiatury bierzemy przez zwezenie konsoli

Ograniczenie obszaru przewijania sekwencja `ESC[1;60r` nie wystarcza: `clear`,
`vi`, `less` i wylogowanie maluja po calym ekranie. Konsole zwezamy przez
`VT_RESIZEX` (z zapasowym `VT_RESIZE`), co jest **trwalym stanem jadra** na
wszystkich konsolach, wiec musi byc cofniete takze po zabiciu programu; sluzy
do tego `--przywroc` w `ExecStopPost`.

Dowod liczbowy: przy czcionce 16x32 konsola ma 95 wierszy, po pokazaniu
klawiatury 60; przy czcionce 32x64 odpowiednio 47 i 29.

### 3. Puszczenie palca: najpierw cisza, dziś jawne zdarzenie

Poczatkowo kontroler nie zglaszal ani identyfikatora sladu przy nowym palcu,
ani `-1` przy puszczeniu, ani `BTN_TOUCH`. Program czekajacy na te zdarzenia
**milczal mimo dotykania ekranu** (tak padla pierwsza wersja sondy pomiarowej),
wiec koniec dotkniecia poznawalismy po ciszy w strumieniu, a znak wysylalismy
w chwili POSTAWIENIA palca.

Poprawki `0093` i `0094` w sterowniku to zmienily: kontroler wysyla dzis
i `BTN_TOUCH`, i zwolnienie sladu (`measurements/2026-09-21-dotyk-protokol`).
Klawiatura bierze to wprost, a cisza zostala tylko jako droga zapasowa. Bez tej
zmiany nie da sie odroznic przytrzymania od puszczenia: panel milczy, dopoki
palec lezy bez ruchu, wiec 80 ms ciszy konczyloby kazde przytrzymanie, zanim
doczeka progu 350 ms.

Znak wychodzi teraz przy PUSZCZENIU palca, bo dopiero wtedy wiadomo, czy
dotkniecie bylo krotkie (litera), czy dlugie (ogonek).

### 4. Orientacji dotyku nie da sie odczytac z opisu urzadzenia

Obie osie maja ten sam zakres 0 do 4096, wiec nie wynika z nich ani
orientacja, ani przypisanie do osi ekranu. Pomiar czterech rogow dal wynik
wskazujacy na obrot o 90 stopni i **byl mylacy**: telefon lezal wtedy inaczej,
niz zakladalem, wiec "lewy gorny rog" nim nie byl. Rozstrzygnela dopiero zywa
klawiatura: dotkniecie klawisza `r` trafialo w `8`, a te same surowe wartosci
przy mapowaniu bez obrotu wypadaja w srodku `r`.

Obowiazujace przeliczenie jest proste: `X_ekranu = X_dotyku * szerokosc /
4096`, `Y_ekranu = Y_dotyku * wysokosc / 4096`. Kontrola srodkiem: surowe
`1962, 2058` daje `690, 1527` przy srodku ekranu `720, 1520`.

## Wpisywanie

Wirtualna klawiatura przez `/dev/uinput`. Konsola wiaze sie tylko
z urzadzeniami zglaszajacymi **zwykle** klawisze (kody ponizej `BTN_MISC`),
i tylko wtedy, gdy zgloszono je PRZED utworzeniem urzadzenia, wiec deklarujemy
caly zakres od razu.

Zmierzone: caly zakres ASCII przechodzi do konsoli bez wyjatku, razem
z symbolami `` ` ~ ! @ # $ % ^ & * ( ) _ + - = [ ] { } \ | ; : " , . < > / ? ``.
Znaki ozdobne (`×`, `÷`, `€`, karty, waluty) nie maja swojego klawisza, bo nie
maja glifu w czcionce konsoli i klawisz bylby martwy.

## Polskie znaki pod przytrzymaniem klawisza

Przytrzymanie klawisza dluzej niz **350 ms** (`longPressThreshold` ze wzorca)
otwiera nad nim dymek z wariantami; nastepne dotkniecie wybiera wariant, a
dotkniecie poza dymkiem zamyka go bez wpisywania. Warianty sa ze wzorca:
a, c, e, l, n, o, s daja `ą ć ę ł ń ó ś`, x daje `ź`, z daje `ż` oraz `ź`,
przecinek daje `;`, kropka `!`, `?` i `:`, a cyfry `!` do `)`.

Kropki, ktora we wzorcu oznaczala klawisz z wariantami (`hasAlt`
w `KeyButton.qml`), u nas nie ma: zdjeta na zyczenie, bo na tym panelu siedziala
w narozniku kazdego drugiego klawisza i zasmiecala pasek. Warianty maja te same
klawisze, co zawsze, tylko nie sa juz oznaczone.

Klawiatura **nie wysyla kodow znakow**, tylko prawy Alt i te sama litere; znak
sklada mapa `pl` jadra, wczytywana przez `ExecStartPre` uslugi. Przypisanie nie
jest wymyslone, tylko odczytane z `/usr/share/keymaps/xkb/pl.map.gz`, kolumna
prawego Alta (`altgr keycode 30 = aogonek`, `keycode 44 = zabovedot`,
`keycode 45 = zacute`). Stad jedyna niespodzianka: `ź` siedzi pod x, a `ż`
pod z, dokladnie jak w ukladzie "polski programisty".

Dowody i pulapki: `measurements/2026-09-22-ogonki-przytrzymanie`.

## Czcionka konsoli musi miec tablice Unicode

Poprawne bajty nie wystarczaja, zeby uzytkownik zobaczyl ogonek. Pierwsza
wersja `ter32x64.psf` byla podwojonym Terminusem z jadra: 256 glifow i **zadna
tablica Unicode**. Dla znaku bez glifu jadro siega po litere bazowa, wiec
klawiatura wysylala `c5 bc`, a na ekranie stalo `z`; `printf 'zażółć'` dawal
`zazolc`. Zrodlem jest teraz `sources/fonts/ter-v32n.psf` z paczki
`font-terminus-4.49.1-r4`, czyli tej samej, ktora siedzi w obrazie telefonu:
512 glifow, tablica Unicode i komplet polskich liter. Generator podwaja piksele
i przepisuje tablice bez zmian, bo numery glifow zostaja te same.

## Proba gestu bez czlowieka

Przytrzymanie rozni sie od dotkniecia tylko czasem, wiec bez palca na szybie
nie da sie go sprawdzic. Sluzy do tego `tools/klawiatura/palec.c`: udaje panel
przez `/dev/uinput`, zglaszajac te same zdarzenia, co sterownik, i **milczy
miedzy postawieniem a zdjeciem palca**, tak jak prawdziwy panel. Klawiatura
uruchomiona z `--dotyk "sztuczny palec"` czyta z niego zamiast z szyby:

```
palec --czekaj 4000  310 2756 120  310 2756 700  217 2560 120
```

Zmierzony wynik odczytany z konsoli: `7a c5 bc`, czyli `z` z krotkiego
dotkniecia i `ż` z przytrzymania, po ktorym palec trafil w pierwsza komorke
dymka.

## Czytelnosc na tym panelu

Dwie poprawki wymuszone przez sprzet:

- **Czcionka konsoli 32x64** zamiast wbudowanej 16x32. Przy ponad 500
  pikselach na cal znak 16 pikseli szerokosci ma okolo 0,8 mm. Czcionke robi
  `scripts/gen-psf-konsoli.py`, podwajajac kazdy piksel Terminusa z jadra; to
  ta sama metoda, co `gen-font-32x64.py` dla konsoli bootloadera. Ladowana
  usluga `czcionka-konsoli.service`.
- **Bufor ramki wezszy o 32 piksele z kazdej strony.** Panel jest zakrzywiony
  po bokach, a konsola tekstowa nie umie przesunac swojego obszaru:
  `fbcon=margin` ustawia tylko KOLOR marginesu. Zwezenie robimy w opisie
  bufora w drzewie urzadzen, zostawiajac dlugosc wiersza bez zmian.

## Uklad: przeniesiony ze wzorca, nie wymyslony

Uklad, wymiary i zachowanie klawiszy sa przeniesione **jeden do jednego**
z klawiatury Qt uzytkownika. Jej pliki leza w `tools/klawiatura/wzorzec/`
i sa zrodlem prawdy:

| wzorzec | co z niego bierzemy |
|---|---|
| `Layouts.qml` | cztery warstwy, rzedy, kolejnosc i szerokosci klawiszy, warianty, autopowtarzanie |
| `Theme.qml` | paleta, wymiary w milimetrach, rozmiary pisma |
| `KeyButton.qml` | stany tla, prog przytrzymania, czasy powtarzania |
| `Keyboard.qml` | wysokosci rzedow, podzial szerokosci wagami, trzy stany Shifta |
| `AltPopup.qml` | dymek wariantow: rozmiar, obwodka, wybor komorki |

`tools/klawiatura/uklad.h` jest **generowany** z `Layouts.qml` przez
`scripts/gen-uklad-klawiatury.py`, a bramka `check-uklad-klawiatury.py`
porownuje plik z wyjsciem generatora, wiec zmiana wzorca bez przegenerowania
zapala bramke, a nie czeka na telefon.

Warstwa liter ma piec rzedow: nizszy rzad cyfr, `qwertyuiop`, wciety
`asdfghjkl`, `Shift zxcvbnm Backspace` oraz `?123`, przecinek, spacja, kropka,
`Fn`, `Enter`. Esc, Tab, klawisze funkcyjne, strzalki, Ctrl i Alt siedza pod
`Fn`, a pozostale znaki pod `?123` i `=\<`.

Zachowanie, takze ze wzorca: znak wychodzi przy PUSZCZENIU palca i tylko gdy
palec zszedl z tego samego klawisza; przytrzymanie 350 ms otwiera dymek
z wariantami (polskie ogonki, a na cyfrach znaki `!` do `)`); Shift ma trzy
stany (jednorazowy, blokada, zgaszony), a Ctrl i Alt gasna po nastepnym znaku;
Backspace, Delete i strzalki powtarzaja sie po 400 ms co 55 ms.

Odejscie od wzorca w POKAZYWANIU STANU, na zyczenie. Kolor akcentu znaczy
u nas stan, ktory TRWA, a nie chwilowe nacisniecie:

| co widac | kolor | kiedy |
|---|---|---|
| klawisz pod palcem | `Theme.keyBgActive` `#2c2c2e` | tylko na czas dotkniecia |
| zablokowany Shift | `Theme.keyBgDown` `#0a84ff` | az ktos go zgasi |
| uzbrojony Ctrl albo Alt | `Theme.keyBgDown` `#0a84ff` | do nastepnego znaku |

Wzorzec robil to odwrotnie (nacisniecie na akcent, stan napisem w narozniku),
przez co kazde uderzenie w klawisz wygladalo jak wlaczenie czegos, co zaraz
samo gasnie. Napisow `CAPS`, `CTRL` i `ALT` w narozniku nie ma wcale.
Dotyczy to zablokowanego Shifta (pali sie, az ktos go zgasi) oraz Ctrl i Alt
(pala sie, dopoki czekaja na nastepny znak). Stan widac tam, gdzie sie go
wlacza, nic nie nachodzi na rzad cyfr i nie ma dwoch nazw tego samego.

Shift jednorazowy zostaje bez podswietlenia, bo widac go po wielkich literach
na klawiszach. Ctrl i Alt zapalone z warstwy Fn nie sa widoczne po powrocie do
liter: ich klawisze zostaly na tamtej warstwie. To swiadomy koszt zdjecia
napisow; gdyby przeszkadzal, najtansza odpowiedz to zapalenie klawisza `Fn`,
bo to on prowadzi tam, gdzie ten stan mieszka.

Zmierzone na zrzucie: klawisz pod palcem `#2c2c2e` przy sasiadach `#1c1c1e`,
Shift przy blokadzie `#0a84ff`, bez blokady `#131315` (odcien pozostalych
klawiszy funkcyjnych), Ctrl i Alt zapalone na warstwie Fn `#0a84ff`, a jasnych
pikseli w narozniku przy zapalonych modyfikatorach zero.

Zasada tresci: kazdy DRUKOWALNY znak ASCII musi byc osiagalny, wprost albo pod
Shiftem, albo pod przytrzymaniem. Bramka to sprawdza. Powtorzen nie zabrania,
bo wzorzec ma je celowo (nawiasy sa i w symbolach, i w operatorach).

Jedno odstepstwo od wzorca jest swiadome: pas oddawany przez konsole liczymy
z NAJWYZSZEJ warstwy (896 px), a warstwy nizsze przyklejamy do dolnej
krawedzi. Qt zmienialo wysokosc okna, a u nas zwezenie konsoli jest trwalym
stanem jadra i zmiana przy kazdym przelaczeniu mrugalaby calym ekranem.

Dowod przeniesienia, z liczbami i zrzutami:
`measurements/2026-09-22-klawiatura-1do1`.

## Zeby nie zginela przy wgraniu

Klawiatura umarla juz dwa razy i za kazdym razem objaw byl ten sam, a przyczyna
ta sama: jej po prostu nie bylo w tym, co zostalo wgrane. Program, czcionka
i pliki uslug leza w SYSTEMIE PLIKOW, a ten wymienia sie w calosci przy wgraniu
partycji uzytkownika.

Stoja za tym dzis trzy warstwy, kazda od innego przypadku:

| warstwa | przed czym chroni | gdzie |
|---|---|---|
| kopia w systemie plikow obrazu | wgranie obrazu, ktory sami budujemy | `tools/phone/wszyj-wszystko-w-obraz.sh` |
| kopia w initramfs plus hook | KAZDY inny korzen: wgrany skadinad, przywrocony, wyczyszczony | `tools/phone/wszyj-klawiature-w-initramfs.sh` |
| audyt przerywajacy | pominiecie ktorejkolwiek pozycji | ten sam skrypt, sekcja audytu |

**Jak dziala hook.** Initramfs pmOS wola wszystkie skrypty z `/hooks-cleanup`
tuz przed `switch_root`, gdy docelowy korzen jest juz zamontowany na ZAPIS
(`init_2nd.sh`: montowanie korzenia, potem `run_hooks /hooks-cleanup`, potem
`switch_root`). Nasz `50-klawiatura.sh` dokłada stamtad brakujace pliki i sam
tworzy dowiazania rozruchowe, bo systemd jeszcze nie dziala, wiec `systemctl
enable` nie istnieje. Init nie ma `set -e`, a kazda operacja hooka jest osobno
zabezpieczona, wiec jego blad nie zatrzyma rozruchu.

**Zasada: dokladamy tylko to, czego brakuje.** Wersji wgranej recznie do prob
nie nadpisujemy, inaczej nie dalo by sie sprawdzic nowej binarki bez
przebudowy initramfs.

Zmierzone (osobna przestrzen montowan, podstawione `/usr/share/klawiatura`
i `/sysroot`, uruchomiony DOKLADNIE ten plik, ktory trafia do initramfs):

- na pustym korzeniu powstaje komplet: binarka `755 root:root`, czcionka
  konsoli, oba pliki uslug i oba dowiazania `../<usluga>` w
  `multi-user.target.wants`,
- przy powtorzeniu z wlasna wersja binarki tresc zostaje nietknieta.

Initramfs rosnie o ladunek, ale wynikowy plik jest MNIEJSZY od oryginalnego
(9,24 MB wobec 11,80 MB), bo pakujemy `zstd -19`; rozpakowany cpio rosnie
zgodnie z oczekiwaniem (26 126 848 B do 27 239 936 B) i nie gubi ani jednej
pozycji (329 do 335, czyli nasze szesc; dowiazan 47 do 47).

**Wynik jest powtarzalny co do bajtu**, ale wymagalo to jednej sztuczki:
`cpio --reproducible` zeruje numery urzadzenia i i-wezla, lecz NIE czas
modyfikacji, a przy rozpakowywaniu nie odtwarza czasu KATALOGOW, do ktorych
wlasnie wypakowal pliki. Dwa przebiegi roznily sie w naglowku pozycji `etc`
o szesc sekund. Dlatego przed pakowaniem calemu drzewu ustawiany jest staly
czas.

**Pulapka, ktora przy okazji wyszla i byla grozniejsza od samej klawiatury.**
Fastboot wgrywa obraz RZADKI (`pmos-nasza-seria.sparse.img`), a skrypt
wszywania pisal tylko do surowego. Zmierzone 22 wrzesnia 2026: plik do
wgrywania byl o OSIEM GODZIN starszy od obrazu, czyli caly wczorajszy wsad
nie mial jak trafic na telefon, a nic o tym nie mowilo. Skrypt konczy teraz
przebieg wywolaniem `img2simg` i sprawdza, ze plik do wgrywania jest nowszy od
surowego.

## Bramki

| bramka | co pilnuje |
|---|---|
| `check-font-klawiatury.py` | naglowek czcionki konsoli rowna sie wyjsciu generatora |
| `check-font-sans.py` | naglowek czcionki proporcjonalnej rowna sie wyjsciu generatora |
| `check-uklad-klawiatury.py` | uklad rowna sie wzorcowi QML, kazdy klawisz zywy, komplet drukowalnego ASCII |

## Pulapki, ktore kosztowaly iteracje

1. **Objaw:** program czeka na dotkniecia i nie zapisuje nic, mimo ze
   przerwania rosna. **Przyczyna:** czekal na `ABS_MT_TRACKING_ID`, ktorego ten
   kontroler nie wysyla. **Poprawka:** rozpoznawac dotkniecia po przerwie
   w strumieniu.
2. **Objaw:** dotkniecia w ogole nie docieraja, choc sterownik jest zwiazany.
   **Przyczyna:** panel wygaszony po dziesieciu minutach bezczynnosci
   (`/sys/class/graphics/fb0/blank` rowne 4); uklad dotykowy nie zglasza wtedy
   nic. **Poprawka z tamtej rundy:** wygaszacz wylaczany sekwencja `ESC[9;0]`.
   **Ta poprawka byla za szeroka i zostala wycofana 23.09.2026**: `ESC[9;0]`
   wylacza wygaszanie CALEMU systemowi i na zawsze, bo nikt go potem nie
   wlaczal z powrotem. Na AMOLED to znaczy panel, ktory nigdy sam nie gasnie,
   i napis logowania stojacy godzinami w jednym miejscu. Dzis klawiatura tylko
   ODGASZA ekran przy kazdym dotknieciu (`konsola_odgas`, samo
   `TIOCL_UNBLANKSCREEN`), a czas do wygaszenia ustawia wiersz rozruchowy
   (`consoleblank=120`). Patrz rozdzial o ochronie matrycy nizej.
3. **Objaw:** `test123` wpisane przez uinput dociera jako `ngbn123`.
   **Przyczyna:** kod klawisza liczony jako `KEY_A` plus pozycja w alfabecie,
   a kody ida w kolejnosci QWERTY. **Poprawka:** tablica wypisana wprost.
4. **Objaw:** `make` buduje natywnie zamiast krzyzowo, mimo `CC ?= $(CROSS)gcc`.
   **Przyczyna:** `CC` jest w make zmienna wbudowana, wiec `?=` jej nie ustawia.
   **Poprawka:** `ifeq ($(origin CC),default)`.
5. **Objaw:** bramka ukladu zglasza rzedy o zlej liczbie klawiszy.
   **Przyczyna:** licznik klamer liczyl `{` i `}` bedace ETYKIETAMI klawiszy.
   **Poprawka:** pomijac tresc w cudzyslowach.
6. **Objaw:** jedno dotkniecie zglaszane dwa razy (w `--surowy` dwie linie
   z tym samym klawiszem). **Przyczyna:** ramka puszczenia to
   `ABS_MT_TRACKING_ID -1`, `BTN_TOUCH 0`, `SYN_REPORT`, a czytanie konczylo
   sie na zwolnieniu sladu, wiec `SYN_REPORT` zostawal w kolejce i przy
   nastepnym wywolaniu wygladal jak NOWE postawienie palca z ostatnia znana
   pozycja. Przy wysylce na puszczeniu wpisywaloby to litere dwa razy.
   **Poprawka:** orzekac tylko na `SYN_REPORT`, zeby ramka puszczenia zjadla
   swoj wlasny koniec.
7. **Objaw:** `printf 'zażółć'` na konsoli daje `zazolc`, choc bajty sa
   poprawne. **Przyczyna:** czcionka konsoli bez tablicy Unicode; jadro dla
   znaku bez glifu siega po litere bazowa. **Poprawka:** czcionka z 512 glifami
   i tablica Unicode.
8. **Objaw:** `chvt` albo `openvt` nie wraca i wiesza proces wolajacy (przez
   ssh znika cala sesja). **Przyczyna:** przelaczenie terminala na tym
   telefonie. **Poprawka:** zrzuty i przechwytywanie robic na AKTYWNEJ konsoli
   tty1, po zdjeciu getty; nie przelaczac terminali.
9. **Objaw:** proba przechwycenia wpisywanego tekstu oddaje pusty plik.
   **Przyczyna:** `stty -F /dev/tty1 raw` psuje odczyt, a w trybie liniowym
   konsola nie oddaje nic bez Entera. **Poprawka:** zostawic tryb liniowy
   i zakonczyc probe dotknieciem Entera.
10. **Objaw:** skrypt proby przez ssh konczy sie bez zadnego wyjscia.
    **Przyczyna:** `pkill -f klawiatura-nowa` trafia takze w powloke ssh, bo
    jej wiersz polecenia zawiera te nazwe. **Poprawka:** ubijac po numerze
    procesu zapisanym przy starcie.

## Ochrona matrycy przed wypaleniem

Panel tego telefonu to AMOLED: kazdy piksel swieci wlasna dioda i starzeje
sie proporcjonalnie do czasu swiecenia i do jasnosci. Klawiatura jest przy
tym najgorszym mozliwym obciazeniem, bo zajmuje **staly pas 1440 na 896**
**pikseli od y=2144**, czyli 29,5 procent panelu, klawisze pokrywaja 78
procent tego pasa, a obraz jest **pikselowo niezmienny**, bo rysuje sie
wylacznie ze zdarzen. Do tego dochodzi konsola, ktora potrafi stac
godzinami na jednym napisie logowania.

### Co zostalo zrobione

| warstwa | prog | co robi |
|---|---|---|
| napisy i tla klawiszy | 20 s ciszy | wszystkie kolory pasa schodza na polowe jasnosci (`przygas`), napisy dodatkowo na `Theme.textDim` |
| zapalone modyfikatory | 30 s ciszy | gasna Shift, Ctrl i Alt, bo ich tlo to czysty niebieski 255, a niebieski subpiksel starzeje sie najszybciej |
| przesuniecie ukladu | co 60 s | caly uklad jedzie o kilka pikseli po osmiopunktowym cyklu, zeby krawedzie klawiszy i napisy nie staly latami w tym samym miejscu |
| chowanie | 90 s ciszy | pas gasnie w calosci, z JAWNYM zamalowaniem czernia przed oddaniem go konsoli |
| konsola | 120 s ciszy | `consoleblank` w wierszu rozruchowym; sciezka DRM dla sysfb zeruje wtedy bufor obrazu, a sterownik z latki 0100 wylacza obraz panelu komenda 0x28 |
| awaria jadra | 30 s | `panic=30`, zeby jasny zrzut bledu nie zostal na ekranie do wyczerpania baterii |

Przesuniecie wchodzi w `geometria()`, a nie w rysowaniu, bo z tej samej
funkcji korzysta trafianie w klawisz: gdyby obraz jezdzil, a trafianie nie,
palec zaczalby chybiac o tyle, o ile przesuniety jest uklad.

### Zmierzone, nie oszacowane

Srednia luminancja pasa klawiatury, liczona z calego zrzutu `/dev/fb0`:

| stan | luminancja pasa | swiecacych pikseli |
|---|---|---|
| swiezo pokazana | 24,823 | 990 766 |
| po 25 s ciszy | 11,331 | 988 262 |
| po 105 s ciszy | **0,000** | **0** |

Czyli samo przyciemnienie scina emisje o 54 procent, a po dwoch progach
panel jest czarny w calosci (caly ekran 0,000, bo w tym czasie wygasza sie
takze konsola).

### Wylaczenie obrazu panelu (latka 0100)

Do 23.09.2026 wygaszenie znaczylo tylko **wyzerowanie bufora obrazu**. Na
AMOLED to prawie to samo, bo czarny piksel nie przewodzi pradu przez diode,
ale panel dalej skanowal czarny obraz. Od latki 0100 kazde wygaszenie
konsoli wysyla panelowi DCS 0x28 (display off), a odgaszenie 0x29
(display on).

Idzie to przez lacze DSIM0 w stanie, w jakim zostawil je bootloader:
jeden naglowek do kolejki naglowkow, tak jak krotki zapis DCS u producenta,
bez ruszania DSIM, D-PHY ani DECON. Sterownik
(`drivers/video/backlight/exynos9820-dsim-lcd.c`) jest urzadzeniem klasy
LCD, a `fb_blank` powiadamia klase LCD, wiec reaguje na kazda droge
wygaszenia: przycisk, dwuklik, 30 s ciszy w klawiaturze i `consoleblank`.
Stan widac w `/sys/class/lcd/exynos9820-dsim/lcd_power` (4 wylaczony,
0 wlaczony). Wymaga `CONFIG_LCD_CLASS_DEVICE=y` (wbudowanej, bo `fbmem`
wola powiadomienie tylko wtedy) i jest dostepny tylko bez sterownika DSI,
czyli w nakladce `scripts/bringup.config`.

Zmierzone (`measurements/2026-09-23-dcs-display-off/`): obie komendy
wychodza z kolejki bez bitow bledu, panel gasnie na 0x28 i wraca z tym
samym obrazem na 0x29, a TE plynie dalej z czestotliwoscia 60 Hz przy
wylaczonym obrazie, wiec DECON nie staje. Z wbudowanym sterownikiem kazde
wygaszenie i odgaszenie przestawialo `lcd_power` w ciagu 200 ms od zmiany
DPMS, a obraz wracal za kazdym razem.

**Czego nadal NIE robi:** `sleep in` (0x10) i zdjecia trzech szyn panelu.
Producent po `sleep in` nigdy nie wraca samym 0x11, tylko pelnym
uruchomieniem panelu (DSC, PPS, okno, TE, jasnosc), a to jest napisane
w sterowniku panelu (`s6e3ha9_disable`, `s6e3ha9_unprepare`) i dziala
dopiero z wlasnym stosem wyswietlania, ktory nie ruszyl na sprzecie. To
samo dotyczy sterowania jasnoscia.

Osobna pozycja do rozstrzygniecia: sekwencja wlaczania panelu w serii
**wylacza ACL** (`0x55 0x00`), czyli sprzetowy ogranicznik pradu, ktory
producent trzyma po to, zeby matryca nie wypalala sie przy jasnych
obrazach. Red team odradza jego wlaczenie, bo ACL zmienia luminancje
globalnie i moze rozjechac tablice dimmingu liczone przy ustalonej
jasnosci. Do sprawdzenia dopiero wtedy, gdy panel realnie zapali sie
naszym sterownikiem.

## Gaszenie i budzenie ekranu

Klawiatura jest jedynym wlascicielem stanu ekranu. Licznik jadra
(`consoleblank=120`) zostaje tylko jako siatka, gdyby program nie dzialal:
dwa liczniki naraz dawaly wyscig, bo jadro budzilo konsole na WCISNIECIE
klawisza, a program przelaczal ekran przy PUSZCZENIU (w dzienniku zapalenie
i zgaszenie w odstepie 55 ms).

| gest | skutek |
|---|---|
| samo zasilanie, krocej niz 1,5 s | gasi albo budzi, liczone przy puszczeniu |
| samo zasilanie, 10 s | gasi ekran, potem `systemctl poweroff` |
| zasilanie razem z innym przyciskiem, w dowolnej kolejnosci | nic, to osobna komenda |
| dwuklik przy zgaszonym ekranie | budzi, rozpoznaje go uklad dotyku (latka 0099) |
| pojedyncze dotkniecie albo przesuw przy zgaszonym | nic |
| Bixby przy zgaszonym | nic |
| 30 s bez dotkniecia i przycisku | gasi |

Wygaszanie idzie przez `TIOCL_BLANKSCREEN`, czyli z `ignore_poke`: zaden
klawisz nie budzi konsoli sam, budzi ja tylko ten program. Po drodze jadro
wylacza obraz panelu komenda 0x28, a przy budzeniu wlacza 0x29 (latka 0100,
opis wyzej). logind ma
`HandlePowerKey=ignore` i `HandlePowerKeyLongPress=ignore`, bo jego dlugie
przytrzymanie to okolo 5 s i nie patrzy na inne przyciski.

### Trzy pulapki, kazda zmierzona

1. **Objaw:** DRM mowi `dpms: Off`, jadro `blanked=1`, a panel swieci.
   **Przyczyna:** emulacja fbdev przepisuje zmiany z bufora cienia do
   prawdziwego z opoznieniem, wiec ostatni rysunek dojezdzal PO wyzerowaniu.
   **Poprawka:** przed wygaszeniem program sam maluje caly ekran na czarno
   i czeka 120 ms. Po obudzeniu konsole przemalowuje jadro z bufora
   tekstowego, a pas klawiatury `pokaz()`. Czern zostaje takze po latce
   0100: DECON wysyla ramki do pamieci panelu rowniez przy wylaczonym
   obrazie, a po 0x29 panel pokazuje to, co tam ma, wiec bez czerni moglby
   blysnac ostatni rysunek sprzed zgaszenia (wniosek z budowy, nie pomiar).
2. **Objaw:** sciszanie wpisuje `^[[26~` w wiersz logowania, a przy
   zgaszonym ekranie znaki czekaja i wylewaja sie po obudzeniu.
   **Przyczyna:** przyciski obudowy i dotyk maja w jadrze uchwyt `kbd`.
   **Poprawka:** program zabiera oba urzadzenia na wylacznosc (`EVIOCGRAB`);
   wylacznosc znika z zamknieciem deskryptora, wiec pad programu oddaje
   przyciski konsoli.
3. **Objaw:** zgaszony ekran budzi sie sam, gdy ktos trzyma telefon.
   **Przyczyna:** kontroler w trybie normalnym sypie wspolrzednymi bez
   przerwy, wiec dwa „stukniecia” robi zwykly przesuw palca.
   **Poprawka:** tryb niskiego poboru ukladu (latka 0099). Zmierzone przez
   i2c-dev przed napisaniem latki: przesuw 0 przerwan, pojedyncze
   stukniecie 0, dwuklik dokladnie 1. Filtr programowy zostal jako zapas.

Wylaczanie przez 10 s zasilania dziala (potwierdzone na telefonie) i idzie
przez `syscon-poweroff` na PS_HOLD w PMU, mimo ze PSCI 0.1 nie ma
`SYSTEM_OFF`. W odroznieniu od restartu nie zawislo na synchronizacji UFS.
