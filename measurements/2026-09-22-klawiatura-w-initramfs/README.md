# Klawiatura wraca sama na kazdy system plikow

Klawiatura umarla juz dwa razy i za kazdym razem z tego samego powodu: program
i jego pliki leza w SYSTEMIE PLIKOW, a ten wymienia sie w calosci przy wgraniu
partycji uzytkownika.  Ta runda dokłada warstwe, ktora nie zalezy od tego, co
jest w korzeniu: kopie w initramfs i hook, ktory dokłada brakujace pliki tuz
przed przejsciem na docelowy korzen.

Narzedzie: `tools/phone/wszyj-klawiature-w-initramfs.sh`, wolane przez
`tools/phone/wszyj-wszystko-w-obraz.sh`.

## Gdzie wpina sie hook

Initramfs pmOS wola wszystkie skrypty z `/hooks-cleanup` przez `run_hooks`.
Kolejnosc w `init_2nd.sh`: `mount_root_partition` (wiersz 53), `run_hooks
/hooks-cleanup` (67), `switch_root` (106).  Katalog `/hooks-cleanup` w naszym
initramfs byl PUSTY, wiec nic nie nadpisujemy.  `run_hooks` uruchamia kazdy
plik `*.sh` przez `sh`, a init nie ma `set -e`, wiec blad hooka nie zatrzyma
rozruchu.

## Proba dzialania (`proba-hooka.txt`)

Uruchomiony DOKLADNIE ten plik, ktory trafia do initramfs, w osobnej
przestrzeni montowan z podstawionymi `/usr/share/klawiatura` i `/sysroot`.

| co sprawdzone | wynik |
|---|---|
| pusty korzen | powstaje `usr/local/bin/klawiatura`, `usr/share/consolefonts/ter32x64.psf`, oba pliki uslug i oba dowiazania w `multi-user.target.wants` |
| prawa binarki | `755 root:root` |
| postac dowiazan | `../klawiatura.service`, `../czcionka-konsoli.service` |
| powtorzenie na korzeniu z wlasna wersja | tresc nietknieta (`MOJA-WERSJA`) |

Zasada „dokladamy tylko brakujace" jest celowa: inaczej nie dalo by sie
sprawdzic recznie wgranej binarki bez przebudowy initramfs.

## Kontrola obrazu (`kontrola-obrazu.txt`)

| co | wynik |
|---|---|
| partycja rozruchowa obrazu | nietknieta: oba wpisy rozruchowe, `vmlinuz-s10`, `dtbs`, `EFI` |
| initramfs | `Zstandard compressed data`, 9 243 421 B |
| pozycji w initramfs | 335 (oryginal 329, nasze szesc) |
| binarka w initramfs kontra zbudowana | ta sama suma: `30a721db210f84d5...` |
| plik do wgrywania | naglowek `3a ff 26 ed`, 989 677 752 B |

Uwaga do czytania tej kontroli: `bin` i `sbin` w initramfs sa DOWIAZANIAMI do
`usr/bin`, wiec szukanie `bin/busybox` po nazwie daje falszywy brak.  Pierwsza
wersja skryptu kontrolnego tak wlasnie zglosila dwa nieistniejace braki.

## Rozmiar i powtarzalnosc

Ladunek to okolo 1,1 MB, a mimo to wynikowy initramfs jest MNIEJSZY od
oryginalnego (9,24 MB wobec 11,80 MB), bo pakujemy `zstd -19`.  Rozpakowany
cpio rosnie zgodnie z oczekiwaniem: 26 126 848 B do 27 239 936 B, dowiazan 47
do 47, nie ginie ani jedna pozycja.

Wynik jest powtarzalny co do bajtu, ale wymagalo to jednej rzeczy:
`cpio --reproducible` zeruje numery urzadzenia i i-wezla, ale NIE czas
modyfikacji, a przy rozpakowywaniu nie odtwarza czasu KATALOGOW, do ktorych
wlasnie wypakowal pliki.  Dwa przebiegi roznily sie w naglowku pozycji `etc`
o szesc sekund (`0x6AB249C6` wobec `0x6AB249CC`).  Po ustawieniu stalego czasu
calemu drzewu dwa przebiegi daja identyczna sume
`6205918f207637bfa4c86c70f45d0e059fbaa1c26316a6f3e6e1d7c29b1cbf19`.

## Pulapka grozniejsza od samej klawiatury

Fastboot wgrywa obraz RZADKI (`pmos-nasza-seria.sparse.img`), a skrypt
wszywania pisal tylko do surowego.  Zmierzone 22 wrzesnia 2026: plik do
wgrywania byl o OSIEM GODZIN starszy od obrazu (21.09 21:04 wobec 22.09 05:21),
czyli caly wczorajszy i dzisiejszy wsad nie mial jak trafic na telefon, a nic
o tym nie mowilo.  Skrypt konczy teraz przebieg wywolaniem `img2simg`,
sprawdza, ze plik do wgrywania jest nowszy od surowego, i ostrzega, gdy plik
dla Odina jest przeterminowany.
