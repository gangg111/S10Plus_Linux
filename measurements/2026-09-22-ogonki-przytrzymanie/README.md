# Polskie znaki pod przytrzymaniem klawisza

Telefon beyond2lte, jadro `7.2.0-01001-ga9d566a524be-dirty`, klawiatura
`tools/klawiatura`.  Dotykal sztuczny palec (`tools/klawiatura/palec.c`),
wiec kazda liczba nizej da sie powtorzyc bez czlowieka przy telefonie.

## Skad wziete przypisanie ogonkow

Z mapy `pl` konsoli, nie z pomyslu.  `/usr/share/keymaps/xkb/pl.map.gz`,
kolumny: zwykla, Shift, prawy Alt, prawy Alt z Shiftem.

| keycode | litera | prawy Alt | prawy Alt z Shiftem |
|---|---|---|---|
| 30 | a | U+0105 | U+0104 |
| 46 | c | U+0107 | U+0106 |
| 18 | e | U+0119 | U+0118 |
| 38 | l | U+0142 | U+0141 |
| 49 | n | U+0144 | U+0143 |
| 24 | o | U+00f3 | U+00d3 |
| 31 | s | U+015b | U+015a |
| 45 | x | U+017a | U+0179 |
| 44 | z | U+017c | U+017b |

Klawiatura nie wysyla wiec kodow znakow, tylko prawy Alt i te sama litere.

## Proba gestu (`proba-gestu.txt`)

Cztery dotkniecia sztucznym palcem w jedno miejsce kazdego klawisza,
odczyt wprost z aktywnej konsoli tty1:

| gest | klawisz | oczekiwane | odebrane |
|---|---|---|---|
| 120 ms | z | `z` | `7a` |
| 700 ms | z | `ż` | `c5 bc` |
| 120 ms | x | `x` | `78` |
| 700 ms | x | `ź` | `c5 ba` |

Odebrane bajty: `7a c5 bc 78 c5 ba 0a`, czyli co do jednego to samo, co
oczekiwane.  Prog przytrzymania to 350 ms, jak `longPressThreshold` w
klawiaturze Qt.

## Wielkie ogonki (`proba-shift.txt`)

Mapa `pl` trzyma wielkie ogonki w kolumnie prawy Alt z Shiftem, wiec nie trzeba
do nich ani jednej linii kodu wiecej.  Gesty: Shift (dotkniecie), z (700 ms),
z (120 ms), Enter.

| oczekiwane | odebrane |
|---|---|
| `Żz` | `c5 bb 7a` |

Drugie, krotkie dotkniecie dalo male `z`, czyli Shift obowiazywal na jeden
znak, tak jak ma obowiazywac.

## Mapa wczytywana przez usluge (`mapa-z-uslugi.txt`)

Zeby wykluczyc, ze ogonki dzialaja tylko dlatego, ze mape wczytalem recznie,
mapa zostala najpierw skasowana (`loadkeys us`), a potem sprawdzona przed i po
starcie uslugi:

| moment | `altgr keycode 30 = aogonek` |
|---|---|
| po `loadkeys us`, usluga stoi | 0 trafien |
| po starcie `klawiatura.service` | 1 trafienie |

Czyli mape wczytuje `ExecStartPre` uslugi, a nie moja sesja.

## Wyglad (`klawiatura-kropki.png`, `klawiatura-ogonek-uzbrojony.png`)

- W spokoju kropka w prawym gornym narozniku stoi na dokladnie dziewieciu
  klawiszach: a, c, e, l, n, o, s, x, z.  W rzedzie `zxcvbnm`
  (`rzad-zxcvbnm-kropki.png`) kropki maja z, x, c, n, a nie maja v, b, m.
- W trakcie przytrzymania klawisz jest niebieski (`Theme.keyBgDown`) i pokazuje
  `ż` zamiast `z`, a kropka znika, bo ogonek widac wprost.

## Czcionka konsoli (`konsola-stara-czcionka.png`, `konsola-nowa-czcionka.png`)

Poprawne bajty nie wystarczaja: glif bierze sie z czcionki konsoli.  Nasza
`ter32x64.psf` byla podwojonym Terminusem z jadra, czyli **256 glifow i zadnej
tablicy Unicode** (naglowek PSF2, flagi 0).  Dla znaku bez glifu jadro siega po
litere bazowa, wiec to samo `printf` dawalo na ekranie:

| czcionka | wyslane | na ekranie |
|---|---|---|
| stara, 256 glifow, flagi 0 | `zażółć gęślą jaźń` | `zazolc gesla jazn` |
| nowa, 512 glifow, flagi 1 | `zażółć gęślą jaźń ĄĆĘŁŃÓŚŹŻ` | to samo, komplet ogonkow |

Zrodlem jest teraz `sources/fonts/ter-v32n.psf` z paczki
`font-terminus-4.49.1-r4`, czyli tej samej, ktora siedzi w obrazie telefonu
(`apk info -W` wskazuje ten pakiet), bajt w bajt:
`08a389d4…92709354`.  Ma 512 glifow, tablice Unicode 1757 bajtow i komplet
polskich liter (U+0105 to glif 215, U+017c to glif 303).  Generator podwaja
piksele i **przepisuje tablice bez zmian**, bo numery glifow zostaja te same.

## Dwie usterki znalezione po drodze

1. **Duch postawienia palca.**  Ramka puszczenia to `ABS_MT_TRACKING_ID -1`,
   `BTN_TOUCH 0`, `SYN_REPORT`.  Czytanie konczylo sie na zwolnieniu sladu,
   wiec `SYN_REPORT` zostawal w kolejce i przy nastepnym wywolaniu wygladal jak
   NOWE postawienie palca: jedno dotkniecie dawalo dwa razy `z` (widoczne
   w `--surowy`).  Przy wysylce na puszczeniu wpisywaloby to litere dwa razy.
   Teraz czytanie orzeka tylko na `SYN_REPORT` i ramka puszczenia zjada swoj
   wlasny koniec.
2. **Cisza brana za puszczenie.**  Panel nie przysyla paczek, dopoki palec lezy
   bez ruchu, a 80 ms ciszy oznaczalo puszczenie, wiec przytrzymanie nigdy nie
   doczekaloby 350 ms.  Teraz puszczenie poznajemy po `BTN_TOUCH` albo po
   zwolnieniu sladu (sterownik wysyla oba, patrz
   `measurements/2026-09-21-dotyk-protokol`), a cisza zostaje tylko dla panelu,
   ktory o puszczeniu nie mowi nic.

## Pulapki samego mierzenia

- `chvt` i `openvt` na tym telefonie **wieszaja** proces, ktory je wywolal, i
  nie wracaja; zrzut trzeba robic z AKTYWNEJ konsoli tty1, po zdjeciu getty.
- `stty -F /dev/tty1 raw` psuje przechwytywanie: to samo przechwycenie karmione
  trybem `--wpisz` nie oddaje ani bajtu.  Konsola zostaje w trybie liniowym,
  a proba konczy sie dotknieciem Entera.
- `pkill -f klawiatura-nowa` trafia rowniez w powloke uruchomiona przez ssh,
  bo jej wiersz polecenia zawiera te nazwe: ubija cala sesje razem z wynikiem.
  Procesy proby ubijac po numerze zapisanym przy starcie.
