### Droidian na Galaxy S10+: zbuduj sam z łatek

[English](README.md) | **Polski**

Droidiana na Galaxy S10+ (**SM-G975F**, Exynos 9820) można wgrać na dwa sposoby:

1. **Gotowe obrazy** ze [strony Releases](https://github.com/gangg111/S10Plus_Linux/releases/latest),
   wgrywane Odinem jak w [głównym README](../README.pl.md). Nic do budowania.
2. **Własna budowa** z tego katalogu: każda zmiana portu jako seria łatek na przypięte commity
   upstream oraz skrypty, które robią z nich paczki i obraz do wgrania. Ta droga jest dla tych,
   którzy chcą coś zmienić albo zobaczyć dokładnie, co działa na telefonie.

Czysty Droidian na tym telefonie nie działa. Bez tych łatek trafia się na wszystko, co port
musiał rozwiązać: jądro, które nie startuje pod bootloaderem Samsunga, brak firmware procesora
dźwięku, brak głębokiego uśpienia (watchdog resetuje telefon w uśpieniu), powłoka zamarzająca
po wygaszeniu ekranu, modem, który nigdy nie włącza radia, i tak dalej. Z łatkami telefon jest
gotowy do codziennego użytku; nie działa tylko **czytnik linii papilarnych** (rejestracja palca
pada w HAL-u producenta).

### Co tu jest

| Część | Baza upstream (przypięta) | Zmiany | Skrypt budowy |
|---|---|---|---|
| Jądro (LineageOS 4.14) | `LineageOS/android_kernel_samsung_exynos9820` `a412cfaf` | [`kernel/patches`](kernel/patches), 29 łatek | [`kernel/build.sh`](kernel/build.sh) |
| Powłoka, Plasma Mobile na wayfire | `droidian/plasma-mobile-wf` `91ba13c8` | [`plasma-mobile-wf/patches`](plasma-mobile-wf/patches), 29 łatek | [`plasma-mobile-wf/build.sh`](plasma-mobile-wf/build.sh) |
| Ustawienia w stylu One UI | `plasma-mobile/plasma-settings` `v26.04.0` | [`../tools/phone/plasma-settings-oneui`](../tools/phone/plasma-settings-oneui), 4 łatki | gotowa binarka w adaptacji, opis tam |
| Aparat | `droidian/droidian-camera` `7071899` | [`../tools/phone/aparat/patches`](../tools/phone/aparat/patches), 8 łatek | [`camera/build.sh`](camera/build.sh) |
| Adaptacja urządzenia | brak, nasza paczka | [`../tools/phone/adaptacja`](../tools/phone/adaptacja) | [`adaptation/build.sh`](adaptation/build.sh) |
| `qt6-text-input-v3`, `maliit-framework` | git Droidiana, commity, z których zbudowano binarki w archiwum | przebudowane bez zmian pod bieżące Qt (binarki z archiwum wciąż chcą Qt 6.10.2, którego już nie ma) | [`archive-rebuild/build.sh`](archive-rebuild/build.sh) |
| `libbatman-wrappers` | brak | pusta atrapa | [`libbatman-wrappers/build.sh`](libbatman-wrappers/build.sh) |
| Obraz | `droidian-images/droidian` `b1fe26b4`, `rootfs-templates` `d2212f43` | [`image/`](image): wpis urządzenia i 1 łatka | [`image/build.sh`](image/build.sh), [`image/pack-odin.sh`](image/pack-odin.sh) |

Commity upstream są przypięte w [`env.sh`](env.sh). Serie są sprawdzone dokładnie na tych
drzewach: każda nałożona na swoją bazę daje to samo drzewo źródeł (ten sam hash drzewa git), z
którego zbudowano działający telefon. Jądro `70e417bc`, powłoka `33a021e1`, ustawienia
`fce527c1`. Jedyna różnica w jądrze to zmiana drzewa urządzeń z bring-upu, której telefon nie
używa (startuje ze stockowym DTB, węzły ekranu ma włączone), więc nie weszła do serii.

Adaptacja niesie wszystko, czego system potrzebuje poza jądrem i powłoką: uprawnienia węzłów
urządzeń, trasę dźwięku (głośnik z pominięciem procesora ochrony), radio modemu i poprawkę
ofono2mm, demona głębokiego uśpienia z szybkim wybudzeniem, gaszenie i budzenie ekranu,
automatyczną jasność, podbicie zegara przy dotyku, ekran startowy i elementy One UI pulpitu.
Paczka `-tools` niesie kilka gotowych binarek; [README adaptacji](../tools/phone/adaptacja/README.md)
podaje źródło każdej z nich.

### Czego potrzebujesz

- Komputera z Linuksem albo Windowsa z **WSL2** (Debian lub Ubuntu). Jądro WSL2 ma już
  sterowniki loop i device-mapper, których potrzebuje krok z obrazem.
- **Dockera**, około **60 GB** wolnego miejsca i internetu.
- RAM: budowy arm64 uruchamiają mniej więcej jedno zadanie kompilacji na 2 GB (zadanie C++
  w emulacji zajmuje grubo ponad gigabajt; zbyt wiele naraz położyło maszynę WSL z 15 GB).
  `JOBS=n` ustawia to ręcznie.
- **Emulacji arm64** dla kontenerów (krok 1).
- **Firmware ABOX** z S10+ (krok 2). Należy do Samsunga, więc nie ma go w tym repozytorium.

Pod Windowsem sklonuj repozytorium **wewnątrz WSL** (na przykład `~/S10Plus_Linux`), a nie pod
`/mnt/c`: pliki z dysku Windowsa mają ustawione wszystkie bity uprawnień, a narzędzia budowy
Debiana uruchamiają wtedy pliki, które powinny tylko czytać.

### Krok 1: narzędzia i emulacja arm64

```bash
sudo apt install docker.io git
sudo usermod -aG docker "$USER"     # potem wyloguj się i zaloguj
docker run --privileged --rm tonistiigi/binfmt --install arm64
ls /proc/sys/fs/binfmt_misc/qemu-aarch64     # musi istnieć
git clone https://github.com/gangg111/S10Plus_Linux.git
cd S10Plus_Linux/droidian
```

### Krok 2: firmware ABOX

Procesor dźwięku prosi o firmware, zanim zostanie zamontowane `/vendor`, dlatego jądro ma je
w sobie. Potrzebne są cztery pliki z `/vendor/firmware` modelu SM-G975F:
`calliope_sram.bin`, `calliope_sram_2.bin`, `calliope_dram.bin`, `calliope_dram_2.bin`.

- Z telefonu, który już ma tego Droidiana: `scp droidian@<telefon>:/android/vendor/firmware/calliope_* abox-fw/`
- Ze zrootowanego stockowego Androida: `adb pull /vendor/firmware/calliope_sram.bin` (i trzy pozostałe).

Włóż je do jednego katalogu i wskaż go w `ABOX_FIRMWARE`. Pliki, których używa działający
telefon (vendor z firmware G975FXXSGHWC1, Android 12), mają takie sumy; inne mogą działać, te
są sprawdzone:

```
62897bf2ff849e20955b3d47be3c13039a722fb87bcae934b4d09a3bcf64e6e4  calliope_sram.bin
10e19314d1b765ce8b0da1673985196040e2bcf1f98f44ddcb2b5d3e1224224b  calliope_sram_2.bin
b3afb1a41154630f25284e2358af0b28936e6e8cc508d4552cfd56bf99bc57e8  calliope_dram.bin
c0ca54cdef0ab850d7a229ac6f5b2e3e09797ca344227a72d91b3a7d036c0904  calliope_dram_2.bin
```

### Krok 3: budowa

Wszystko naraz (paczki, potem obraz, potem pliki dla Odina):

```bash
ABOX_FIRMWARE=$HOME/abox-fw ./build-all.sh
```

albo po kolei, w tej kolejności; każdy krok dokłada swoje paczki do `~/s10plus-build/localrepo`:

```bash
ABOX_FIRMWARE=$HOME/abox-fw ./kernel/build.sh
./archive-rebuild/build.sh
./plasma-mobile-wf/build.sh
./camera/build.sh
./adaptation/build.sh
docker run --rm -v "$PWD":/d:ro -v ~/s10plus-build/localrepo:/out quay.io/droidian/build-essential:next-amd64 sh /d/libbatman-wrappers/build.sh /out
./image/build.sh
./image/pack-odin.sh
```

Jądro budowane jest krzyżowo (od 15 do 40 minut). Cała reszta budowana jest dla arm64 w
emulacji, co jest wolne: na komputerze licz kilka godzin na całość. Katalog roboczy zmienisz
przez `WORK=/jakis/katalog`.

Wynik ląduje w `~/s10plus-build/odin`: `droidian-boot-s10plus.tar.md5` i
`droidian-userdata.tar.md5`, te same dwa pliki co na stronie Releases (tam userdata jest
skompresowane xz). Wgraj je Odinem dokładnie tak, jak opisuje [główne README](../README.pl.md).

Po pierwszym starcie telefon przyjmuje SSH jako `droidian` (hasło `1234`) zarówno po Wi-Fi,
jak i po kablu USB (`ssh droidian@169.254.172.1`; adres link-local, więc PC nie potrzebuje DHCP,
a Windows sam ładuje sterownik RNDIS). Ten sam kabel daje też dostęp do plików: Windows widzi
telefon jako urządzenie przenośne (MTP) z katalogiem domowym. Zwykły obraz plamo-wf nie ma ani SSH, ani działającej
sieci po USB; adaptacja dodaje oba, a klucze hosta SSH powstają od nowa przy pierwszym starcie,
więc telefony wgrane z tego samego obrazu ich nie współdzielą. Pierwszy start powiększa też
system plików na całą partycję userdata, więc trwa dłużej.

Ta droga jest sprawdzona od początku do końca 12.10.2026: obraz zbudowany wyłącznie z tego
katalogu, wgrany Odinem, uruchomił działający telefon.

### Jak obraz trzyma paczki portu

Łatka obrazu dodaje lokalne repozytorium (na telefonie `/opt/localrepo`), zanim zostanie
zainstalowana pierwsza paczka, i przypina je priorytetem 1100 (Droidian przypina swoje
archiwum na 1002, więc niższy priorytet przegrywa z kopią z archiwum). Każda paczka przebudowana przez
port wygrywa z kopią z archiwum, zarówno przy budowie obrazu, jak i później na telefonie:
aktualizacja Droidiana nie podmieni poprawionej powłoki ani jądra. Żeby zaktualizować paczkę
portu, przebuduj ją i zainstaluj (albo przebuduj obraz).

Archiwum to migawka 102 plus kroczące repozytorium production (`env.sh`). Repozytorium
production się zmienia; jeśli kiedyś nowsze Qt zepsuje budowę, skrypty zatrzymają się z błędem
apt, a naprawa jest taka sama jak przy `qt6-text-input-v3`: przebudować paczkę, która trzyma
stare Qt.

### Gdy coś nie wychodzi

| Objaw | Przyczyna | Naprawa |
|---|---|---|
| `exec format error` w kontenerze | emulacja arm64 niezarejestrowana (znika po restarcie WSL) | krok 1, ponownie `tonistiigi/binfmt --install arm64` |
| `the series did not apply` | checkout nie stoi na przypiętym commicie albo plik łatki się zmienił (końce linii) | uruchom skrypt jeszcze raz (pobiera przypięty commit od nowa); pod Windowsem trzymaj repo w WSL |
| budowa paczki zaczyna uruchamiać programy (`plasma_session` i inne) | źródła leżą na dysku Windowsa, każdy plik jest wykonywalny, a debhelper uruchamia wykonywalny plik `.install` | sklonuj w WSL; skrypt adaptacji i tak ustawia tryby od zera |
| debos staje na `qt6-base-private-abi (= X) ... none of the choices are installable` | archiwum przeszło na nowsze Qt, a jakiejś paczki archiwum nie przebudowano | `archive-rebuild/find-stale.py` wypisze wszystkie takie paczki; tę nazwaną w błędzie apt dopisz do `COMMIT` w `archive-rebuild/build.sh`, przebuduj i uruchom `image/build.sh` ponownie (paczki, których obraz nie instaluje, jak `qt6-qpa-hwcomposer-plugin`, mogą zostać nieaktualne) |
| `cannot remove ... belong to root` | budowa została przerwana (albo padła maszyna WSL), zanim kontener oddał swoje pliki | wykonaj `sudo rm -rf` z komunikatu i uruchom skrypt ponownie |
| Odin odrzuca plik tar | linia md5 nie zawiera nazwy pliku `.tar.md5` | używaj `pack-odin.sh` i nie zmieniaj potem nazw plików |

### Gdzie jest reszta pracy

- [`../tools/phone`](../tools/phone): każdy element portu z notatkami, pomiarami i skryptami
  testowymi. Część katalogów należy do drogi mainline (postmarketOS), a nie do Droidiana:
  `decon9820`, `hub-modul`, `abox9820`, `tzdev`, `bez-usypiania`, `ucm`, `ochrona-glosnikow`.
- [`../tools/phone/obraz-boot`](../tools/phone/obraz-boot): historia obrazów boot Droidiana,
  wydanie po wydaniu; aktualny stan tych zmian jądra to `kernel/patches`.
- [`../patches`](../patches) i [`../patches-uboot`](../patches-uboot): serie jądra mainline
  i U-Boota drogi pmOS.
