# Pasek stanu Plasma Mobile: odsunięcie od aparatu i krzywizny

Na S10+ otwór podwójnego aparatu w prawym górnym rogu zasłania ikony
paska stanu, a zegar po lewej wchodzi w zakrzywioną krawędź.

Plasma Mobile 6.7.5 (pmOS edge) ma do tego gotowy mechanizm: preset
urządzenia `plasma-mobile-device-presets/<compatible>.conf`, szukany
najpierw w `~/.local/share`, potem w `/usr/share`. Nazwa pochodzi
z pierwszego wpisu `compatible` drzewa urządzenia, u nas
`samsung,beyond2lte`. Przy logowaniu `plasma-mobile-envmanager` przepisuje
`[Panels][Top]` do `plasmamobilerc` (`[Panels][WhenOnTop]`), a powłoka
czyta te wartości w pikselach fizycznych i dzieli przez skalę.
Źródła: plasma-mobile v6.7.5 `envmanager/devicepresets.cpp`,
`components/mobileshellstate/panelsettingsdbusobjectmanager.cpp`.

Pułapka upstream: `components/mobileshell/qml/statusbar/StatusBar.qml`
zamienia strony (lewy margines z presetu odsuwa od PRAWEJ krawędzi). Dlatego
od aparatu odsuwa `leftPadding`, a od lewej krzywizny `rightPadding`.

## Liczby

- Aparat: LineageOS beyond2lte, `config_mainBuiltInDisplayCutout`
  `M 0,0 H -326 V 142 H 0 V 0 Z @right`, czyli 326 x 142 px przy prawej
  krawędzi. Android dokłada 21 px kropki prywatności, więc cel to 350 px
  od prawej krawędzi (ikony kończą się na x <= 1090).
- Krzywizna: nigdzie nie podana. 120 px to szacunek z obszaru krawędzi
  dotyku (`sec,area-size` 341 z 4096 w drzewie producenta). Do strojenia
  na oko drugim argumentem.
- Wysokość paska w Androidzie: 142 px (dolna krawędź wycięcia), opcjonalnie
  trzecim argumentem.

## Użycie (na telefonie, jako user)

    sh zainstaluj.sh              # jak One UI: 370 / 110 px, wysokosc 200, wielkosc 1.5
    sh zainstaluj.sh 370 110 210  # tresc 5 px nizej (srodek = wysokosc / 2)
    WIELKOSC=1.25 sh zainstaluj.sh  # mniejsze ikony i zegar
    sh sprawdz.sh ~/pasek.png     # stan, wartości na D-Bus, zrzut
    sh cofnij.sh                  # przywrócenie stanu sprzed instalacji

Instalacja robi kopię stanu w `~/.local/state/nakladka-pasek/`, nie rusza
`/usr` ani `/etc` i przerywa (kod 4), jeśli w `~/.config/plasmamobilerc`
są własne wartości, które wygrałyby z presetem.

Niesprawdzone na telefonie (był niedostępny): przeładowanie na żywo po
sygnale KConfig, obecność `kwriteconfig6` i `busctl`, nazwa wyjścia na
D-Bus, rzeczywista skala. Preset i błąd zamiany stron warto zgłosić
do plasma-mobile.

## Stan 26.09.2026 (sprawdzone na telefonie)

Dostrojone do zdjecia One UI: srodek zegara i ikon na y 99 (zakladany srodek
obiektywow ~100 px, szacunek ze zdjecia), cyfry zegara 37 px wysokosci,
tresc od x 113 do 1064. Wielkosc (`statusBarScaleFactor` w `[General]`
`~/.config/plasmamobilerc`) powloka czyta tylko przy starcie, dlatego skrypt
restartuje `plasma-plasmashell.service`; `cofnij.sh` przywraca poprzednia.
