**Plan uruchomienia DECON na S10+, od M0 do KWin przy 60 Hz bez kopii**

**Co sprawdziłem w plikach przed planem**
- **DT:** w `exynos9820-beyond2lte.dts` (wezly `&decon0` i `&dsim0`, generator `scripts/gen-dts-beyond2lte.py`) `&decon0` i `&dsim0` mają status "okay". "disabled" jest tylko w dtsi. Stan "potok disabled" z zadania jest więc nieaktualny albo dotyczy innego DTB, stąd pomiar w M0.
- **HW-26 na pewno zablokuje pełny modeset.** 9820 ma `pll_stable_bit = 0` (`samsung-dsim.c:788`) na LINK_STATUS 0x14 (`:460`). `set_external_pll` czeka 20 ms (`:1053-1055`), a na działającym łączu `link3 = 00000000` (`proba-0x28-0x29.txt:9,13,19`).
- **Nikt nie przejmuje sprzętu po bootloaderze.** W decon, dsim i panelu nie ma żadnej ścieżki przejęcia. Panel przy probe ustawia reset przez `GPIOD_OUT_HIGH` (`panel-samsung-s6e3ha9-main.c:551`). `decon_atomic_enable` przeprogramowuje blok bez `decon_stop` (`exynos9820_drm_decon.c:685-736`). Flush wysyła tylko `WIN(0)` (`:885-886`).
- **KWin daje zero kopii tylko przy jednej karcie.** Warunek to `m_gpu == eglBackend->gpu()` (`kwin/drm_egl_layer_surface.cpp:421`). W innym wypadku KWin idzie w GpuCopy, a potem DumbBuffer (`:431-438`). Exynos musi więc być jedyną kartą KMS, a simpledrm trzeba usunąć.
- **KWin wybierze render node exynosa.** Przy remisie wygrywa "to samo urządzenie" (`gpumanager.cpp:180-183`), a exynos ma `DRIVER_RENDER` (`exynos_drm_drv.c:107-108`).
- **Mesa:** fallback do kmsro dla nieznanego sterownika KMS potwierdzony (`pipe_loader_drm.c:181-183`).
- **CMA:** 32 MiB pod 0xee000000, czyli poniżej 4 GiB (`measurements/2026-09-20-logdump/dmesg.txt:24`).
- **Nie wyłączać sysmmu_dpud0-2.** Są konsumentami `pd_dpu` (`exynos9820.dtsi`, wezly `sysmmu_dpud0` do `sysmmu_dpud2`). Po wyłączeniu domena dostaje `sync_state` i może zgasić ekran. Zamiast tego `/delete-property/ iommus;` w `&decon0`.

**M0: pomiary tylko do odczytu (sesja z użytkownikiem)**
1. **Najpierw białe glicze (Twój punkt 2), bo od nich zależy, czy DECON w ogóle je usunie.**
   - Zanotuj godzinę glicza i zestaw z liniami błędów panfrosta w `dmesg` (DATA_INVALID_FAULT itd., `measurements/2026-09-24-gpu/README.md:74-78`).
   - Odpal KWin i plasmashell z `LIBGL_ALWAYS_SOFTWARE=1`.
   - Jeśli glicze znikają na llvmpipe i pokrywają się z błędami zadań, to Mesa/panfrost i DECON ich NIE usunie. Jeśli zostają, to kopia bez synchronizacji w simpledrm i DECON pomoże.
2. `zcat /proc/config.gz`, `cat /proc/device-tree/.../display@19030000/status`, `ls /dev/dri`, `grep dpu /sys/kernel/debug/clk/clk_summary`.
3. **Rozszerzony `s10_dcs.c`, same odczyty** (mapować tylko bramki, które `clk_summary` pokazuje jako włączone):
   - DECON: 0x040, 0x060, 0x070, 0x214, 0x218, 0x230, 0x1000..0x10ff, 0x4000..0x40ff, 0x5000..0x50ff;
   - IDMA 0x19071000: +0x08, +0x10, +0x18, +0x40;
   - DPP 0x19021000: +0x08, +0x18;
   - D-PHY 0x19161140; MMU_CTRL w SYSMMU DPUD0..2; PMU 0x15861e00.
4. **Czego się spodziewam:** IDMA+0x40 = 0xca000000, bit 0 w PLL_STAT0 = 1, MMU w bypassie, niskie 16 bitów PPS16_19 = 436 albo 616 (HW-12). DATA_PATH_CONTROL_0 powie, które okna są włączone (okno 5 z S-Boota?). Dodatkowo `/proc/interrupts` dla SPI 184.
5. **Ryzyko:** odczyt przy zamkniętej bramce zawiesza telefon. **Odwrót:** reset przez sysrq po ssh.

**M1: sterownik bierze potok bez modesetu i raz podmienia bufor**
- **M1a: moduł testowy poza DRM, wzorowany na `s10_dcs.c`.**
  - Alokuje przez `dma_alloc_coherent` 17 510 400 B. To mieści się w obecnych 32 MiB CMA.
  - Rysuje wzór, zapisuje IDMA+0x40, wysyła GLOBAL|0x3f do 0x060, czeka, aż 0x060 wróci do 0, i przywraca 0xca000000.
  - Rozstrzyga, czy IDMA ma własny cień i czy wystarczy WIN(0), czy potrzebny jest GLOBAL.
  - **Pomiar:** zdjęcie ekranu od użytkownika, czas powrotu 0x060 do zera poniżej 17 ms. **Odwrót:** `rmmod`.
- **M1b: DRM z przejęciem stanu.**
  - **Kconfig:** z fragmentu (`scripts/exynos9820.config:34-40`), ale `DRM_EXYNOS=m`. Odwrót to wtedy `modprobe.blacklist=exynosdrm` na /boot (z fsync).
  - **DT:** `/delete-property/ iommus` w `&decon0`; zegary PCLKS i PCLKM (N1).
  - **decon:** przy bind odczytać RUN_STATUS. Jeśli blok działa, ustawić `started=true` i zbudować aktywny stan CRTC z trybem panelu.
  - **dsim:** pominąć reset łącza i `set_external_pll`, gdy łącze działa.
  - **panel:** `GPIOD_ASIS` zamiast `GPIOD_OUT_HIGH` i pominięcie sekwencji init.
  - **exynos_drm_bind:** `aperture_remove_conflicting_devices(0xca000000, 17510400, ...)` przed `drm_dev_register`.
  - **Pomiar:** jedna karta `/dev/dri/card0` na sterowniku exynos, IDMA+0x40 = adres z CMA, brak "PLL failed", SPI 184 około 60/s.
  - **Ryzyko:** czarny ekran. **Odwrót:** ssh, blacklist, restart; simpledrm wraca.

**M2: flipy na TE i vblank, KWin na exynosie z kmsro**
- **Flush:** maska aktualizacji według wyniku M1a. Zdarzenie flip wysyłać w FRAME_DONE dopiero, gdy 0x060 = 0, bo dziś może przyjść o ramkę za wcześnie.
- **HW-38: zostawić wyzwalacz odmaskowany.** Klawiatura pisze do `/dev/fb0` przez `pwrite` bez commitu, więc maskowanie na klatkę zamroziłoby jej obraz. Koszt: około 1,05 GB/s pasma (17,5 MB × 60). Maskowanie dopiero razem z obsługą dirty w fbdev.
- **Zdjąć `DRIVER_RENDER`.** Wtedy KWin nie otworzy EGL na render node exynosa, gdzie `CREATE_DUMB` jest zabronione.
- **Pamięć:** `cma=256M`.
- **Pomiar:**
  - log `QT_LOGGING_RULES=kwin_*.debug=true` bez "chose cpu import";
  - mediana odstępu klatek 16,7 ms (dziś 43-51 ms, `measurements/2026-09-24-gpu/README.md:62`);
  - `CmaFree` w `/proc/meminfo`.
- **Ryzyko:** HW-39 (poziom czy zbocze), czyli timeout vblank i zamrożony KWin. **Odwrót:** ssh, restart KWin, blacklist.

**M3: DPMS, DSC, zgodność z 0100**
- 0100 znika sama (`depends on !DRM_EXYNOS_DSI`). Wygaszanie przez fbcon i klawiaturę pójdzie wtedy w DPMS panelu.
- **Pierwsza wersja `disable`:** tylko 0x28 i sleep in, bez odcinania szyn w `unprepare`. To odpowiada dzisiejszemu zachowaniu 0100.
- `pd_dpu` zostaje włączona, dopóki nie ma SMC (HW-08).
- DSC poprawić według zrzutu z M0 (HW-12, HW-13).
- **Pomiar:** 20 cykli wygaś/odgaś, po każdym TE 60 Hz i poprawny obraz (ocena użytkownika).

**M4: pełny modeset i wznowienie**
- Zakończenie blokady PLL czytać z PLL_STAT0 D-PHY (0x19161140, bit 0), nie z LINK_STATUS (HW-26).
- Pełna inicjalizacja panelu z MTP (HW-06), czasy szyn (HW-20, HW-21), cykl domeny z SMC 0x82000410.
- "Wznowienie" znaczy tu DPMS z wyłączeniem domeny, nie s2idle, bo usypianie zabija UFS.
- **Pomiar:** `modetest` powtarza ustawienie trybu, 10 cykli domeny.

**Decyzja pamięci: CMA teraz, SYSMMU później**
- Jeden bufor to 17 510 400 B (16,7 MiB).
- Potrzeba: fbdev 1 + swapchain KWin 3-4 (NIESPRAWDZONE) + zapas na rekonfigurację około 4. Razem około 9 buforów, czyli około 150 MiB. Dlatego `cma=256M`: 3% z 8 GB, a region `reusable` oddaje wolne strony.
- Warunek: dmesg `cma: Reserved 256 MiB at` poniżej 0x100000000, bo adres w IDMA jest 32-bitowy (`exynos9820_drm_decon.c:182`).
- SYSMMU dopiero po HW-35/09/10. Da import buforów klientów (`exynos_drm_gem.c:446-447`); zero kopii dla wyjścia KWin i tak daje dumb z CMA.

**Sprzeczności między raportami**
1. Status decon w DT: raporty mówią "okay" (dts), zadanie "disabled". Rozstrzyga M0.2.
2. "Mesa ma wpis exynos": jawnego wpisu nie ma, działa fallback. Skutek ten sam.
3. Trzy różne configi: fragment (DRM_EXYNOS=y, S2DOS05=y), `sources/linux/.config` (DRM_EXYNOS=m) i jądro na telefonie (simpledrm). Rozstrzyga `/proc/config.gz`.
4. Rozmiar CMA: 64, 96, 128 albo 256 MB. Wybieram 256 MB.
5. Raport seria uznaje DSIM za gotowy, raport blokery pokazuje HW-26. Blokery mają rację; w M1-M3 omijamy to przejęciem.
6. Raport seria proponuje wyłączyć sysmmu. To ryzyko zgaszenia `pd_dpu`, patrz wyżej.
7. Mainline: "zero kopii tylko przy tym samym GPU" kontra "kmsro na card0 bez kopii". Pogodzone: wystarczy, że exynos jest jedyną kartą.

**Nadal NIESPRAWDZONE**
- Cień IDMA (rozstrzyga M1a).
- HW-39.
- panvk na G76, bo zmienia wybór render node w KWin.
- Liczba slotów swapchaina KWin.
- Czy okno 5 z S-Boota jest włączone.

**Wymaga Ciebie przy telefonie**
- M0: obserwacja glicz i porównanie z llvmpipe, zdjęcie ich kształtu.
- M1a i M1b: zdjęcia ekranu.
- M2: ocena płynności.
- M3: cykle wygaszania, dwuklik i dotyk.
- Po resecie ciepłym może być trzeba przepiąć kabel.
- Zasada wgrywania: jedno wgranie to jedna zmiana.

Uwaga: serwery MCP Adobe i huggingface-skills czekają na autoryzację, a desktop-commander się nie połączył. Do tego zadania żaden nie był potrzebny.