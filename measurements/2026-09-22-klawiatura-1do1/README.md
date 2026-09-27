# Uklad i wyglad przeniesione z klawiatury Qt jeden do jednego

Wzorzec: klawiatura Qt uzytkownika, zrzut z telefonu (`wzorzec-qt.png`).
Wynik: klawiatura w C, zrzuty z tego samego telefonu (`wynik-c*.png`).
Oba pochodza z bufora ramki, nie z rysunku ani z opisu.

## Co wlasnie zostalo przeniesione

Poprzednia wersja miala przeniesione kolory, wymiary w milimetrach,
zaokraglenia, czcionke i ikony, ale NIE rozmieszczenie: zostawala stara siatka
szesciu rzedow z Esc, Tab, strzalkami i osobnym rzedem Ctrl i Alt.  Teraz
rozmieszczenie idzie ze wzorca:

| | wzorzec Qt | przed | po |
|---|---|---|---|
| rzedow w literach | 5 | 6 | 5 |
| rzad cyfr | nizszy (rh 0,78) | pelny | nizszy |
| Esc i Tab w literach | nie ma | sa | nie ma |
| rzad a..l | wciety o pol klawisza z obu stron | na calej szerokosci | wciety |
| dolny rzad | ?123, przecinek, spacja, kropka, Fn, Enter | Sym, Ctrl, Alt i osobny rzad ze strzalkami | jak wzorzec |
| warstw | 4 (litery, symbole, operatory, Fn) | 3 | 4 |
| warianty pod klawiszem | dymek z lista | jeden ogonek na klawiszu | dymek z lista |
| Shift | jedno dotkniecie, drugie blokada | tylko jednorazowy | jak wzorzec |
| autopowtarzanie | 400 ms, potem 55 ms | brak | jak wzorzec |

## Dowod liczbowy (`porownanie-prostokatow.txt`)

`porownaj-uklad.py` nie zaklada niczego o ukladzie: szuka w obrazie pasm
jasniejszych od tla, czyli PROSTOKATOW klawiszy, i porownuje ich krawedzie.

| rzad | klawiszy | wysokosc Qt | wysokosc C |
|---|---|---|---|
| 0 (cyfry) | 10 | 132 px | 132 px |
| 1 (qwerty) | 10 | 173 px | 173 px |
| 2 (a..l) | 9 | 173 px | 173 px |
| 3 (zxcvbnm) | 9 | 173 px | 173 px |
| 4 (dolny) | 6 | 173 px | 173 px |

Krawedzie klawiszy zgodne z dokladnoscia do **jednego piksela** (prog bramki
to trzy).  Roznica bierze sie z gestosci: Qt liczy 20,5 px/mm, my 20,57 px/mm
(1440 pikseli na 70 mm czynnej szerokosci panelu).  Werdykt skryptu:
`ZGODNE: te same rzedy, te same szerokosci i wysokosci klawiszy`.

## Audyt wygladu element po elemencie (`audyt-wygladu.txt`)

`audyt-wygladu.py` mierzy zrzuty i porownuje kazda liczbe z wzorcem.  Kolory
i wymiary z `Theme.qml`, a ksztalt naroznika i rozmiary pisma z renderem Qt, bo
dla krzywej i dla kroju tylko render jest uczciwym wzorcem.

| element | zmierzone | wzorzec |
|---|---|---|
| tlo paska | `#000000` | `bg` |
| klawisz zwykly | `#1c1c1e` | `keyBg` |
| klawisz z akcja | `#131315` | `keyBgAlt` |
| klawisz wcisniety | `#0a84ff` | `keyBgDown` |
| tlo dymka | `#2c2c2e` | `keyBgActive` |
| obwodka dymka | `#0a84ff` | `accent` |
| napis na klawiszu | `#f2f2f7` | `text` |
| wysokosc rzedu pelnego | 185 px | 9,0 mm |
| wysokosc rzedu cyfr | 144 px | 9,0 mm razy 0,78 |
| odstep miedzy klawiszami | 12 px | 0,6 mm |
| lewa krawedz pierwszego klawisza | 44 px | 1,6 mm plus odstep |
| szerokosc dymka na wariant | 185 px | wysokosc rzedu |
| naroznik: wciecia wierszy | 22,19,17,15,13,12,11 | Qt: 22,19,17,15,14,12,11 |
| glif litery q | 32 na 58 px | Qt: 32 na 57 px |
| napis `?123` | 93 na 35 px | Qt: 94 na 34 px |
| wskaznik w narozniku | 24 px | 0,18 wysokosci rzedu |

Wszystkie osiem kolorow zgadza sie **co do bajtu**, wymiary co do piksela,
a naroznik i pismo miesza sie z Qt w granicach jednego piksela.

Dwie pulapki samego mierzenia, warte zapisania, bo pierwsza wersja skryptu
zglosila piec falszywych alarmow: probka z SRODKA klawisza lapie wygladzony
brzeg litery, a nie tlo (`#2993fe` zamiast `#0a84ff`), a dymek trzeba szukac po
kolorze obwodki, bo stoi NAD klawiszami i szukanie krawedzi po jasnosci wchodzi
w klawisz sasiada.  Promienia nie wolno liczyc ze skrocenia gornego wiersza
(wzor daje 15 wobec 24); trzeba porownac caly profil wciec z wzorcem.

## Czym sie ROZNI i dlaczego

Na zrzucie wzorca klawisze Shift, Backspace i Enter sa PUSTE: ich etykiety to
znaki Unicode, ktorych czcionka telefonu nie ma.  To byla uwaga uzytkownika
(„klawiatura ma prostokaty zamiast glifow"), wiec u nas te trzy klawisze maja
ikony rysowane kreska, a nie brane z czcionki.  To jedyna widoczna roznica na
`obok-siebie.png`.

Drugi wybor, ktory nie wynika ze wzorca: pas oddawany przez konsole liczymy
z NAJWYZSZEJ warstwy (litery, 896 px po zaokragleniu do wiersza konsoli),
a warstwy nizsze przyklejamy do dolu.  Qt zmienialo wysokosc okna, a u nas
zwezenie konsoli jest trwalym stanem jadra i zmiana przy kazdym przelaczeniu
mrugalaby calym ekranem.  Klawisze nie ruszaja sie przy tym spod palca, bo
licza sie od dolnej krawedzi.

## Proba pisania (`proba-pisania.txt`)

Dotykal sztuczny palec (`tools/klawiatura/palec.c`), czytalismy z konsoli:

| gest | oczekiwane | odebrane |
|---|---|---|
| z krotko | `z` | `7a` |
| z przez 700 ms, potem pierwsza komorka dymka | `ż` | `c5 bc` |
| z przez 700 ms, potem druga komorka dymka | `ź` | `c5 ba` |
| Shift, potem z | `Z` | `5a` |
| Enter | koniec linii | `0a` |

Dymek nad klawiszem z ma DWIE komorki, bo tyle wariantow ma ten klawisz we
wzorcu (`{t:"z", alt:["ż","ź"]}`).

## Stan modyfikatorow: na klawiszu, nie w narozniku

Napisy `CAPS`, `CTRL` i `ALT` z wzorca zostaly zdjete; stan pokazuje sam
klawisz, zapalony kolorem `Theme.keyBgDown`.

Dwa sygnaly sa rozdzielone: kolor akcentu znaczy stan, ktory TRWA, a samo
nacisniecie klawisza tylko go rozjasnia (`nacisniety-klawisz.png`).

| probka | zmierzone | wzorzec |
|---|---|---|
| klawisz pod palcem | `#2c2c2e` | `keyBgActive` |
| klawisz zwykly obok | `#1c1c1e` | `keyBg` |
| klawisz funkcyjny | `#131315` | `keyBgAlt` |
| Shift przy blokadzie | `#0a84ff` | `keyBgDown` |
| Ctrl zapalony (warstwa Fn) | `#0a84ff` | `keyBgDown` |
| Alt zapalony (warstwa Fn) | `#0a84ff` | `keyBgDown` |
| jasne piksele w narozniku, warstwa Fn | 0 | brak napisu |
| jasne piksele w narozniku, warstwa liter | 0 | pusto |

`keyBgActive` to jedyny jasniejszy odcien klawisza w palecie wzorca; wzorzec go
deklaruje i nigdzie nie uzywa, wiec pisanie dostalo go bez wymyslania nowego
koloru. Nacisniecie sprawdzane jest OSTATNIE, wiec widac je takze na klawiszu
juz zapalonym akcentem.

Zrzuty `wynik-c-blokada-shift.png` i `wynik-c-fn-modyfikatory.png` powstaly
trybem `--zrzut` na komputerze, bo telefon byl w tym czasie odlaczony. Tryb
rysuje do wlasnego bufora tym samym kodem i z tymi samymi wymiarami panelu,
wiec mierzy to, co pokaze urzadzenie; pierwszy zrzut z telefonu po jego
powrocie to potwierdzi.

## Zachowanie klawiszy (`proba-zachowania.txt`)

Trzy rzeczy, ktorych nie widac na zrzucie, sprawdzone tym samym sztucznym
palcem:

| gesty | co ma sie stac | odebrano |
|---|---|---|
| Shift, Shift, z, z, Shift, z | blokada daje `ZZ`, po zgaszeniu male `z` | `5a 5a 7a` |
| trzy razy z, Backspace przez 900 ms | autopowtarzanie kasuje wszystkie trzy | linia pusta |
| `?123`, pierwszy klawisz, `ABC`, pierwszy klawisz | `@` z symboli, `q` z liter | `40 71` |

Pulapka wlasnego pomiaru: pierwszy klawisz rzedu z literami i pierwszy klawisz
rzedu z symbolami maja INNE y, bo warstwa symboli ma o rzad mniej i jest
przyklejona do dolu.  Pierwsza wersja proby celowala w oba w to samo miejsce
i trafila w odstep przed `a`, ktory z zalozenia nie reaguje.

## Jak to sie nie rozjedzie

`tools/klawiatura/uklad.h` jest **generowany** ze wzorca przez
`scripts/gen-uklad-klawiatury.py`, a bramka `scripts/check-uklad-klawiatury.py`
porownuje plik z wyjsciem generatora i sprawdza, ze kazdy drukowalny znak ASCII
jest osiagalny.  Zmiana w `wzorzec/Layouts.qml` bez przegenerowania zapala
bramke, a nie czeka na telefon.

## Co zdjete z wzorca na zyczenie

| element wzorca | stan u nas |
|---|---|
| napisy `CAPS`, `CTRL`, `ALT` w narozniku | usuniete, stan pokazuje sam klawisz |
| kropka `hasAlt` na klawiszu z wariantami | usunieta, warianty zostaja bez oznaczenia |
| akcent jako kolor NACISNIECIA | akcent znaczy dzis stan trwaly, nacisniecie tylko rozjasnia |

Audyt wygladu przestal wiec mierzyc kropke i napis w narozniku; reszta miar
zostala bez zmian i nadal wypada zgodnie.
