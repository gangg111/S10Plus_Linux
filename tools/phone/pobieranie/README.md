### Pobieranie: JDownloader 2 na telefonie

Interfejs Swing JDownloadera 2 nie nadaje sie na ekran 480 punktow (pod Xwayland bez
`_JAVA_AWT_WM_NONREPARENTING=1` jest wrecz pustym szarym oknem). JD2 dziala wiec w tle bez okna,
a obsluguje go wlasna aplikacja w stylu One UI (Qt 6 / QML, ta sama paleta co Ustawienia).

Skladniki:
- `jdownloader.service` (systemd --user): `java -Djava.awt.headless=true -jar ~/jd2/JDownloader.jar
  -norestart`, `-Xmx384m -XX:+UseSerialGC`, `Restart=always` (po aktualizacji JD2 sam sie zamyka,
  systemd go podnosi). Domyslnie uruchamia go aplikacja; start z sesja przelacznikiem w Ustawieniach.
- Lokalne API JD2 (`deprecatedapienabled`, 127.0.0.1:3128) przyjmuje GET bez uwierzytelnienia, wiec
  kazda strona w przegladarce telefonu moglaby nim sterowac (CSRF). Dlatego:
  `jdapi-firewall.service` (iptables `-m owner ! --gid-owner jdapi -j REJECT` na lo:3128) i
  `jdapi-proxy.py` / `jdapi-proxy.service` (grupa `jdapi`, gniazdo `/run/jdapi/jdapi.sock` 0600).
  Aplikacja mowi tylko do gniazda.
- `pobieranie` (`main.cpp`, `qml/`), piec zakladek, funkcje odpowiadaja wersji desktopowej
  (bez rozpakowywania archiwow, celowo):
  - Pobierane: pakiety z postepem, predkoscia i czasem, pliki po dotknieciu; Start/Pauza/Stop
    i menu calej listy (sprawdz wszystko, zatrzymaj po biezacym, premium wl./wyl., reconnect,
    czyszczenie: zakonczone, nieudane, offline, wylaczone, duplikaty, wszystko).
  - Linki (linkgrabber): dostepnosc linkow, warianty, Pobierz wszystko i menu (sprawdz, przerwij,
    usun offline/wylaczone/duplikaty, wyczysc).
  - Wspolne menu pakietu i pliku (przytrzymanie, `ItemActions.qml`): wznow, pobierz teraz,
    wlacz/wylacz, sprawdz dostepnosc, resetuj, odblokuj pominiete, zmien nazwe, folder, priorytet,
    haslo, komentarz, wariant, przenies na poczatek/koniec, nowy pakiet, podziel wedlug hostingu,
    kopiuj linki, zatrzymaj po tym, otworz folder, usun, usun z plikami.
  - Dodaj: wklej, nazwa, folder, od razu albo do sprawdzenia; Wiecej opcji (haslo, komentarz,
    priorytet, szukaj glebiej, pomin reguly Packagizera); plik kontenera DLC/CCF/RSDF.
  - Hostingi: konta premium (dodaj, odswiez, wlacz/wylacz, zmien login i haslo, usun), logowanie
    HTTP/FTP do stron, 4057 hostingow z wyszukiwarka; menu hostingu: ustawienia wtyczki, dodaj
    konto, kup konto.
  - Ustawienia: folder i wolne miejsce, jednoczesne pobrania, czesci na plik, limit predkosci, start
    z sesja, Restart/Wylacz JD2, Java, aktualizacje z paskiem postepu, Wszystkie ustawienia (pelne
    "Advanced Settings" JD2: 1959 pozycji w 210 grupach, wyszukiwarka, edycja wedlug typu, przywracanie
    domyslnych).
  - Captche i dialogi JD2 wyskakuja nad aplikacja (`AskOverlay.qml`).
  Link podany w wierszu polecen (`pobieranie URL`) otwiera Dodaj wypelnione.
- Ustawienia wtyczki: grupy ustawien wtyczek nie zawsze nazywaja sie jak klasa wtyczki
  (`OneFichierCom` trzyma je w `OneFichierConfigInterface`), wiec dopasowanie idzie po rdzeniu nazwy
  (bez `Config`/`ConfigInterface` i koncowki domeny). Na 319 wtyczek z ustawieniami 162 ma swoja grupe.
- Odpowiedzi API pomijaja wartosci falszywe i domyslne (`enabled:false`, priorytet `DEFAULT`), stad
  w QML `!!x.enabled`, nigdy `x.enabled !== false`. `getDownloadUrls` zwraca mape URL -> id linkow;
  typ `ORIGIN` jest pusty dla zwyklych linkow, kopiujemy `CONTENT`.

Java: Eclipse Temurin 21 JRE aarch64 w `/opt/java` (repozytorium Droidiana nie ma OpenJDK), JD2
z `JDownloader.jar` w `~/jd2` (pierwszy start sam dociaga reszte i sie aktualizuje).

Budowa (WSL, kontener `pmwf-krzyz`): `bash buduj.sh`; najpierw `qmlformat` sprawdza skladnie QML.
Instalacja na telefonie: binarka `pobieranie` i pliki z tego katalogu, potem `sh zainstaluj.sh`.
Diagnostyka wywolan: `JDAPI_TRACE=1 pobieranie` wypisuje kazde zapytanie i wynik.
Test przycisku Zainstaluj bez prawdziwej aktualizacji: `POBIERANIE_TEST_UPDATE=1 pobieranie`
(kazde sprawdzenie zglasza aktualizacje; Zainstaluj restartuje JD2 przez `/update/restartAndUpdate`).
Dowod 03.10.2026: Sprawdz -> zapytanie do update.jdownloader.org w `UpdateManager.log` ("Nothing to
install"); Zainstaluj -> plansza "Instalowanie aktualizacji", JD2 nowy PID (NRestarts 1 -> 2), po ok. 20 s
Ustawienia z rewizja. Prawdziwej instalacji nowej wersji nie bylo czym sprawdzic (brak aktualizacji).

Dowod (03.10.2026): dodanie linku w aplikacji -> sprawdzenie -> pobranie 10,5 MB -> status
"Zakonczone"; zapis ustawien sprawdzony odczytem z JD2 (`MaxChunksPerFile` 1 -> 2 -> 1); bezposredni
dostep do 127.0.0.1:3128 jako uzytkownik telefonu: `Connection refused`, przez gniazdo: odpowiedz.

Dowod funkcji (03.10.2026, dotyk wstrzykiwany przez `stipc`, wynik czytany z API JD2):
- Ustawienia wtyczki 1fichier z Hostingow: 10 pozycji `OneFichierConfigInterface`.
- Dodaj z opcjami: link w JD2 z `comment:"opcjetest"` i `priority:"HIGH"`.
- Logowanie HTTP: dodanie (test.example/testuser), wylaczenie (`enabled:false`), usuniecie (lista pusta).
- Kopiuj linki: toast "Skopiowano linki: 1", Wklej w Dodaj wstawia ten sam URL.
- Restart: nowy PID i plansza "Uruchamianie JDownloadera"; Wylacz: usluga `inactive` jeszcze po 40 s
  (wczesniej aplikacja sama ja podnosila), Uruchom: `active`.
- Wczesniej: wylacz/priorytet/komentarz/zmiana nazwy w linkgrabberze, Pobierz, premium w obie strony,
  Usun nieudane, edycja `MaxChunksPerFile` w Wszystkich ustawieniach.
Niesprawdzone na zywo: captcha i dialogi JD2 (nie bylo zadnej), edycja prawdziwego konta premium
(nie wpisuje cudzych hasel), wybor pliku kontenera, instalacja realnej aktualizacji.
