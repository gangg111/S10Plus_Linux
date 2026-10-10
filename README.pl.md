### Linux na Samsungu Galaxy S10+ (SM-G975F, Exynos 9820)

[English](README.md) | **Polski**

Linux oparty na mainline dla **Exynosowego** Galaxy S10+ (`beyond2lte`): własny bootloader
U-Boot (upstreamowy U-Boot plus łatki z `patches-uboot/`), jądro oparte na mainline oraz
pełna adaptacja urządzenia pod **Droidiana** (Plasma Mobile w stylu One UI).

> To jest **wyłącznie** dla Exynosowego **SM-G975F** (`beyond2lte`). **Nie** dla wersji
> Snapdragon (SM-G975U / SM-G975W) ani dla S10 / S10e. Wgranie na inny model nie wystartuje
> i może zablokować telefon.

Gotowe pliki do wgrania są na [stronie Releases](https://github.com/gangg111/S10Plus_Linux/releases/latest).

### Co działa

Dostępne są dwa obrazy. **pmOS** to mały szybki start, żeby sprawdzić, czy telefon w ogóle
wstaje na tym stosie; **Droidian** to pełny system codziennego użytku.

| | pmOS (szybki start) | Droidian (pełny) |
|---|---|---|
| Rozruch przez nasz U-Boot | tak | tak |
| Ekran | prosty framebuffer | 60 kl/s, sprzętowy potok DECON |
| Dotyk | tak | tak |
| Wi-Fi | nie | tak (BCM4375) |
| Dane / rozmowy | nie | tak (wymaga karty SIM) |
| Dźwięk (głośnik + mikrofony) | nie | tak |
| Aparat | nie | tak (ścieżka Camera2 / libcamera) |
| Sprzętowe dekodowanie wideo | nie | tak (MFC: H.264 / HEVC) |
| GPS, czujniki, czytnik linii | nie | GPS + czujniki tak; czytnik częściowo |
| Głęboki sen (suspend to RAM) | nie | tak, bezobsługowe usypianie, wybudzanie ~1 s |
| Pulpit | konsola / framebuffer | Plasma Mobile, motyw One UI |

Stan jest podany uczciwie i wciąż się zmienia; obraz Droidiana to realny telefon, którego
autor używa na co dzień.

### Zanim zaczniesz (przeczytaj)

- **Wgranie rootfs kasuje userdata** (wszystkie dane Androida). Zrób kopię.
- Bootloader musi być **odblokowany** (OEM unlocking). Na Exynosowym Samsungu to **trwale
  przepala Knoksa** (bit gwarancji) i nie da się tego cofnąć.
- **Pierwsza warstwa partycji (efs / IMEI / klucze) nie jest ruszana** przez te obrazy.
- Zawsze możesz wrócić do stockowego Androida przez Odina (patrz **Przywracanie**).
- Rób to z **naładowaną baterią** i pewnym kablem.

### Czego potrzebujesz

- Samsung Galaxy S10+ **SM-G975F**.
- Komputer z Windowsem z **Odinem 3.14+** i zainstalowanymi **sterownikami USB Samsunga**
  (na Linuksie możesz użyć **Heimdalla**).
- Kabel USB.
- Dwa pliki z [najnowszego release](https://github.com/gangg111/S10Plus_Linux/releases/latest):
  - `uboot-s10plus.tar.md5` — nasz U-Boot, idzie na partycję **boot**.
  - `pmos-s10plus-userdata.tar.md5` — rootfs pmOS, idzie na **userdata**.
  - Pełny obraz **Droidiana** dojdzie do tego samego release, gdy opublikuję jego czysty
    build; do tego czasu zbuduj go sam (patrz **Budowanie ze źródeł**).

### Wgrywanie przez Odina (Windows)

1. Na stockowym Androidzie włącz **Ustawienia → Opcje programisty → Odblokowanie OEM**.
2. Wyłącz telefon. Wejdź w **tryb Download**: przy wyłączonym telefonie przytrzymaj
   **Volume Up + Volume Down naraz**, potem wepnij kabel USB do PC. Pojawi się ekran
   ostrzeżenia; naciśnij **Volume Up**, żeby kontynuować. Jeśli bootloader jest jeszcze
   zablokowany, **przytrzymaj Volume Up** dłużej, żeby go odblokować (to wyczyści telefon).
3. Otwórz **Odina**. Telefon pojawi się jako niebieskie pole **Added!!** w logu.
4. Wrzuć `uboot-s10plus.tar.md5` w slot **AP** i naciśnij **Start**. To podmienia partycję
   boot na nasz U-Boot. (Plik w środku archiwum nazywa się `boot.img`, więc Odin sam celuje
   w partycję boot.)
5. Telefon zrestartuje się do U-Boota. Wejdź znów w tryb Download (krok 2), wrzuć
   `pmos-s10plus-userdata.tar.md5` w **AP**, naciśnij **Start**. To zapisuje rootfs Linuksa
   na userdata i **kasuje Androida**. (W środku jest `userdata.img`.)
6. Zrestartuj. U-Boot wstaje, znajduje partycję systemową EFI wewnątrz userdata i uruchamia
   Linuksa.

Sloty **BL**, **CP** i **CSC** w Odinie zostaw puste, a **Re-Partition** wyłączony. Odin
czyta tylko archiwa `ustar` z dopisaną sumą MD5; powyższe pliki są spakowane dokładnie tak.

### Pierwszy rozruch i logowanie

- Pierwszy rozruch jest wolniejszy (rozszerzanie systemu plików). Daj mu minutę.
- **Droidian** loguje się jako użytkownik `droidian`. Domyślne hasło to `1234`. Zmień je.
- **pmOS** wstaje jako generyczny obraz postmarketOS; użyj danych wbudowanych w ten obraz.
  (Jeśli nie masz pewności, wgraj Droidiana; to on jest wspieranym systemem codziennym.)

### Przywracanie (powrót do stockowego Androida)

1. Pobierz **stockowy firmware** dla swojego dokładnego SM-G975F (zgodny z regionem / CSC) ze
   źródła, któremu ufasz. Przychodzi jako cztery pliki: BL, AP, CP, CSC.
2. W Odinie załaduj BL/AP/CP/CSC do ich slotów i wgraj. To przywraca Androida.
3. Knox zostaje przepalony (to trwałe), ale telefon znów jest normalnym S10+.

### Budowanie ze źródeł

Wszystko tu jest odtwarzalne; nic nie jest zamkniętym blobem, którego nie da się zbudować.

- **U-Boot**: upstreamowy U-Boot plus `patches-uboot/` (patrz `patches-uboot/README.md`),
  pakowany do Odina przez `scripts/pack-uboot-odin.sh`.
- **rootfs pmOS**: pakowany do Odina przez `scripts/pack-pmos-odin.sh`.
- **Jądro i seria łatek na mainline**: `patches/`, `scripts/`, `SOURCES.md`; patrz
  `docs/mainline-submission.md` po notatki deweloperskie i do wysyłki na listę.
- **Adaptacja urządzenia pod Droidiana** (paczka `.deb` ze stylem One UI, modemem, dźwiękiem,
  czujnikami, demonem głębokiego snu i resztą): `tools/phone/adaptacja/`.

### Autorstwo i licencja

Port i adaptacja: **Artur Szafraniec**. Zmiany w jądrze i U-Boocie są wysyłane jako zwykłe
łatki upstream (patrz `docs/mainline-submission.md` i `patches-uboot/`). Każdy komponent
zachowuje licencję swojego projektu źródłowego.
