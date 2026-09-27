# DECON: M0 (odczyt potoku po S-Boocie) i M1a (podmiana bufora) (24.09.2026)

Jadro #60, DTB etapu 18, sesja na simpledrm. Plan calego uruchomienia:
plan-M0-M4.md (wynik przeplywu decon-plan, zwiadowcy + synteza).

## Skad biale glicze

Sesja bez GPU (panfrost na czarnej liscie modprobe, KWin na llvmpipe,
tylko card0 = simpledrm): 5 minut normalnego uzywania, zero glicz (ocena
uzytkownika). Z GPU glicze sa. Zrodlem sa bledy zadan GPU
(measurements/2026-09-24-gpu), nie kopia simpledrm; DECON ich nie usunie.
LIBGL_ALWAYS_SOFTWARE=1 nie wystarcza do takiego testu: KWin w trybie
"render device" otwiera renderD128 wprost i dalej uzywa panfrosta.

## M0: zrzut rejestrow (m0_dpu.c, tylko odczyty, zrzut-rejestrow.txt)

Modul najpierw otwiera bramki APB przez API zegarow CMU_DPU, potem czyta.
Synchroniczny abort (oops tylko w insmod, telefon zyje) daja: PMU 0x700..0x71c,
PMU 0x15861e10, sysreg DPU 0x19011000 (mimo bramki 63), SYSMMU +0x10.

| co | adres | wartosc | wniosek |
|----|-------|---------|---------|
| PMU RST_STAT | 0x15860404 | 0x20000000 | po resecie przez sysrq |
| domena DPU | 0x15861e00/04/08 | 1 / 1 / 0x10 | wlaczona |
| DECON GLOBAL_CONTROL | 0x19030000 | 0x133 | pracuje |
| SHADOW_REG_UPDATE_REQ | 0x19030060 | 0 | brak zadan w toku |
| HW_SW_TRIG_CONTROL | 0x19030070 | 0x1001 | TE odmaskowany |
| okno 5: WIN_CONTROL_0 / END | 0x190310f0 / 0x190310fc | 0x102 / 0x0bdf059f | S-Boot uzywa okna 5, COPY, 1440x3040 |
| DSC PPS16_19 (oba) | 0x19034030, 0x19035030 | 0x020001b4 | initial_dec_delay 436 (HW-12) |
| IDMA GF0 ENABLE | 0x19071000 | 0x4 | OP_STATUS zajety |
| IDMA IN_CON | 0x19071008 | 0x02000000 | format 0 = ARGB8888 |
| IDMA SRC_SIZE | 0x19071010 | 0x0be005a0 | 3040 x 1440 |
| IDMA IN_BASE_ADDR_Y | 0x19071040 | 0xca000000 | adres fizyczny framebuffera |
| SYSMMU DPUD0 MMU_CTRL | 0x190a0000 | 0x4 | bit ENABLE = 0: bypass (HW-35) |
| D-PHY PLL | 0x19161108 | 0x8a | M = 138 |
| D-PHY PLL_STAT0 | 0x19161140 | 1 | PLL zablokowany; tu, nie w LINK_STATUS DSIM (HW-26) |
| bias D-PHY | 0x19160000.. | 0x10, 0x110, 0x3223, 0, 0 | jak u producenta (HW-25) |
| DSIM TE | 0x19080084/88 | 0x56 / 0x22a32776 | jak 23.09 |

## M1a: jednorazowa podmiana bufora (m1a_flip.c)

Bufor 1440x3040 ARGB8888 z CMA (dma_alloc_coherent, maska 32 bity):
0xfe300000. Zapis IDMA_IN_BASE_ADDR_Y, potem SHADOW_REG_UPDATE_REQ = WIN(5)
(jak decon_reg_update_req_window producenta). Zadanie wykonane po 4,1-8,0 ms,
powrot do 0xca000000 po 3,5-6,5 ms, bez bledow, KWin zyje.

Zdjecie m1a-wzor-na-panelu.jpg: wzor na calym panelu, kolejnosc kolorow
wlasciwa (ARGB8888), siatka rowna, szachownica ostra: DECON skanuje bufor
z CMA bez kopii, DSC i rozmiar zgodne.
