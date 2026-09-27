// SPDX-License-Identifier: GPL-2.0-only
/*
 * Jasnosc panelu S6E3HA9 (Galaxy S10+) na lacze DSIM0 zostawionym przez S-Boot.
 *
 * Wysyla dokladnie to, co sterownik producenta przy zmianie jasnosci
 * (s6e3ha9_beyond2_a3_s0_panel.h): klucz poziomu 2, gamma 0xCA liczona z MTP
 * panelu silnikiem dimmingu z serii (panel-samsung-s6e3ha9-dimming.c), AOR
 * 0xB1, TSET/MPS/ELVSS 0xB5, VINT 0xF4 i zatrzasniecie 0xF7 0x03. Zapis dlugi
 * i odczyt DCS ida jak w dsim_drv.c producenta: dane slowami do PAYLOAD,
 * naglowek do PKTHDR, odczyt przez maksymalny rozmiar odpowiedzi, zadanie z BTA
 * i kolejke RX.
 *
 * tryb=0: tylko odczyt (MTP, gamma HBM, obecne 0xCA/0xB1/0xB5/0xF4) i
 *         porownanie gammy S-Boota z tabela policzona z MTP.
 * tryb=1: dodatkowo urzadzenie /sys/class/backlight/s6e3ha9, jasnosc w 0,1 nita
 *         (20..4200, z HBM do 8000, liniowo, jak zaklada KWin przy EDR).
 */
#include <linux/backlight.h>
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_clk.h>
#include <linux/platform_device.h>
#include <linux/slab.h>
#include <linux/workqueue.h>
#include <video/mipi_display.h>

#include "panel-samsung-s6e3ha9-dimming.h"
#include "s6e3ha9-tabele.h"

#define DSIM_BAZA		0x19080000
#define DSIM_INTSRC		0x0050
#define DSIM_INTSRC_RX_DATA_DONE	BIT(18)
#define DSIM_PKTHDR		0x0058
#define DSIM_PKTHDR_DANE	0x1ffffff
#define DSIM_PAYLOAD		0x005c
#define DSIM_RXFIFO		0x0060
#define DSIM_FIFOCTRL		0x0068
#define FIFO_PH_ILE(x)		(((x) >> 16) & 0x3f)
#define FIFO_PUSTY_RX		BIT(12)
#define FIFO_PUSTY_PH		BIT(10)
#define FIFO_PELNY_PL		BIT(9)

#define NR_ZWYKLE		74
#define NR_HBM			16
#define NITY_MAKS		420
#define NITY_HBM		800
/* Jednostka /sys/class/backlight/s6e3ha9: 0,1 nita (8000 = 800 nitow). */
#define DZIESIATE		10
#define NR_TP			12

static int tryb;
module_param(tryb, int, 0444);
/* Po kazdym ustawieniu odczyt 0xB1 i 0xCA z panelu i porownanie z wyslanym. */
static bool kontrola;
module_param(kontrola, bool, 0644);
/*
 * HBM (444..800 nitow) jak u producenta: gamma interpolowana miedzy krokiem 420
 * a gamma HBM z panelu (0xB3 od bajtu 2), ACL wlaczony (OPR 8%). Domyslnie
 * wylaczone: reczny suwak Androida konczy sie na 420 nitach, HBM daje tylko
 * automatyka jasnosci i HDR.
 */
static bool hbm;
module_param(hbm, bool, 0444);

static void __iomem *dsim;
static DEFINE_MUTEX(zamek);
static struct s6e3ha9_dimming *dim;
static bool gamma_ok;
static u8 gamma_hbm[NR_HBM][S6E3HA9_GAMMA_LEN];

/* Rozpakowanie gammy 0xCA na punkty (V255 10 bitow, V0/VT 4 bity), jak gamma_ctoi. */
static void gamma_na_liczby(const u8 *g, s32 t[NR_TP][3])
{
	int v, c, i;

	for (v = 2; v < NR_TP - 1; v++) {
		i = NR_TP - v - 1;
		for (c = 0; c < 3; c++)
			t[v][c] = g[i * 3 + c + 1];
	}
	for (c = 0; c < 3; c++)
		t[NR_TP - 1][c] = ((g[0] >> ((2 - c) * 2)) & 0x3) << 8 | g[c + 1];
	t[1][0] = g[31] >> 4;
	t[1][1] = g[31] & 0xf;
	t[1][2] = g[32] >> 4;
	t[0][0] = g[32] & 0xf;
	t[0][1] = g[33] >> 4;
	t[0][2] = g[33] & 0xf;
}

static void liczby_na_gamme(s32 t[NR_TP][3], u8 *g)
{
	int v, c, i;

	memset(g, 0, S6E3HA9_GAMMA_LEN);
	for (v = 2; v < NR_TP - 1; v++) {
		i = NR_TP - v - 1;
		for (c = 0; c < 3; c++)
			g[i * 3 + c + 1] = t[v][c] & 0xff;
	}
	for (c = 0; c < 3; c++) {
		g[0] |= ((t[NR_TP - 1][c] >> 8) & 0x3) << ((2 - c) * 2);
		g[c + 1] = t[NR_TP - 1][c] & 0xff;
	}
	g[31] = (t[1][0] & 0xf) << 4 | (t[1][1] & 0xf);
	g[32] = (t[1][2] & 0xf) << 4 | (t[0][0] & 0xf);
	g[33] = (t[0][1] & 0xf) << 4 | (t[0][2] & 0xf);
}

/* generate_hbm_gamma_table producenta: interpolacja od kroku 420 do gammy HBM. */
static void licz_hbm(const u8 *hbm_z_panelu)
{
	s32 od[NR_TP][3], do_[NR_TP][3], wy[NR_TP][3];
	int k, v, c;

	gamma_na_liczby(dim->gamma[NR_ZWYKLE - 1], od);
	gamma_na_liczby(hbm_z_panelu, do_);
	for (k = 0; k < NR_HBM; k++) {
		int krok = s6e3ha9_kroki[NR_ZWYKLE + k].nity - NITY_MAKS;
		int razem = NITY_HBM - NITY_MAKS;

		for (v = 0; v < NR_TP; v++)
			for (c = 0; c < 3; c++)
				wy[v][c] = (krok == razem || od[v][c] == do_[v][c]) ? do_[v][c] :
					   od[v][c] + (s32)div_s64((s64)(do_[v][c] - od[v][c]) * krok, razem);
		liczby_na_gamme(wy, gamma_hbm[k]);
	}
}
static struct platform_device *pdev;

static int czekaj_ph(void)
{
	u32 v;

	return readl_poll_timeout(dsim + DSIM_FIFOCTRL, v,
				  (v & FIFO_PUSTY_PH) && !FIFO_PH_ILE(v), 50, 50000);
}

static int naglowek(u8 id, u8 d0, u8 d1, bool bta)
{
	u32 v;

	if (czekaj_ph())
		return -EBUSY;
	v = readl(dsim + DSIM_PKTHDR) & ~DSIM_PKTHDR_DANE;
	writel(v | ((u32)bta << 24) | ((u32)d1 << 16) | ((u32)d0 << 8) | id,
	       dsim + DSIM_PKTHDR);
	return czekaj_ph();
}

/* Zapis DCS: 1 bajt krotki, 2 bajty krotki z parametrem, wiecej dlugi. */
static int zapis(const u8 *b, size_t n)
{
	size_t i;
	u32 v;

	if (n == 1)
		return naglowek(MIPI_DSI_DCS_SHORT_WRITE, b[0], 0, false);
	if (n == 2)
		return naglowek(MIPI_DSI_DCS_SHORT_WRITE_PARAM, b[0], b[1], false);
	if (czekaj_ph())
		return -EBUSY;
	for (i = 0; i < n; i += 4) {
		u32 slowo = 0;
		size_t j;

		for (j = 0; j < 4 && i + j < n; j++)
			slowo |= (u32)b[i + j] << (8 * j);
		if (readl_poll_timeout(dsim + DSIM_FIFOCTRL, v, !(v & FIFO_PELNY_PL), 10, 10000))
			return -EBUSY;
		writel(slowo, dsim + DSIM_PAYLOAD);
	}
	return naglowek(MIPI_DSI_DCS_LONG_WRITE, n & 0xff, n >> 8, false);
}

#define ZAPISZ(...) ({ static const u8 _b[] = { __VA_ARGS__ }; zapis(_b, sizeof(_b)); })

/* Odczyt DCS jak dsim_read_data producenta; zwraca liczbe bajtow. */
static int odczyt(u8 cmd, u8 *buf, size_t ile)
{
	int glebia = 64, n = 0, i, j, ret;
	u32 rx, v;

	while (!(readl(dsim + DSIM_FIFOCTRL) & FIFO_PUSTY_RX) && glebia--)
		readl(dsim + DSIM_RXFIFO);
	writel(DSIM_INTSRC_RX_DATA_DONE, dsim + DSIM_INTSRC);
	ret = naglowek(MIPI_DSI_SET_MAXIMUM_RETURN_PACKET_SIZE, ile & 0xff, ile >> 8, false);
	if (ret)
		return ret;
	ret = naglowek(MIPI_DSI_DCS_READ, cmd, 0, true);
	if (ret)
		return ret;
	if (readl_poll_timeout(dsim + DSIM_INTSRC, v, v & DSIM_INTSRC_RX_DATA_DONE, 100, 100000))
		return -ETIMEDOUT;
	writel(DSIM_INTSRC_RX_DATA_DONE, dsim + DSIM_INTSRC);
	glebia = 64;
	do {
		rx = readl(dsim + DSIM_RXFIFO);
		switch (rx & 0xff) {
		case MIPI_DSI_RX_ACKNOWLEDGE_AND_ERROR_REPORT:
			pr_warn("s6e3ha9: odczyt %#x: raport bledu %#x\n", cmd, rx >> 8);
			break;
		case MIPI_DSI_RX_END_OF_TRANSMISSION:
			break;
		case MIPI_DSI_RX_DCS_SHORT_READ_RESPONSE_1BYTE:
		case MIPI_DSI_RX_GENERIC_SHORT_READ_RESPONSE_1BYTE:
			buf[0] = rx >> 8;
			n = 1;
			break;
		case MIPI_DSI_RX_DCS_SHORT_READ_RESPONSE_2BYTE:
		case MIPI_DSI_RX_GENERIC_SHORT_READ_RESPONSE_2BYTE:
			buf[0] = rx >> 8;
			if (ile > 1)
				buf[1] = rx >> 16;
			n = 2;
			break;
		case MIPI_DSI_RX_DCS_LONG_READ_RESPONSE:
		case MIPI_DSI_RX_GENERIC_LONG_READ_RESPONSE:
			n = (rx >> 8) & 0xffff;
			for (i = 0; i < n; i += 4) {
				rx = readl(dsim + DSIM_RXFIFO);
				for (j = 0; j < 4 && i + j < n; j++)
					if (i + j < ile)
						buf[i + j] = rx >> (8 * j);
			}
			break;
		default:
			pr_warn("s6e3ha9: odczyt %#x: nieznany pakiet %#x\n", cmd, rx);
			return -EIO;
		}
	} while (!(readl(dsim + DSIM_FIFOCTRL) & FIFO_PUSTY_RX) && --glebia);
	return n;
}

static int klucze(bool wl)
{
	int ret = 0;

	if (wl) {
		ret |= ZAPISZ(0x9f, 0xa5, 0xa5);
		ret |= ZAPISZ(0xf0, 0x5a, 0x5a);
		ret |= ZAPISZ(0xfc, 0x5a, 0x5a);
	} else {
		ret |= ZAPISZ(0xfc, 0xa5, 0xa5);
		ret |= ZAPISZ(0xf0, 0xa5, 0xa5);
		ret |= ZAPISZ(0x9f, 0x5a, 0x5a);
	}
	return ret;
}

static void zrzut(const char *nazwa, const u8 *b, int n)
{
	pr_info("s6e3ha9: %s (%d B): %*ph\n", nazwa, n, min(n, 36), b);
}

/*
 * COPR: blok DDI liczacy jasnosc tresci obrazu w obszarach ROI.  Czyta go hub
 * czujnikow po wlasnym SPI i odejmuje od czujnika swiatla pod ekranem
 * swiatlo samego panelu; bez COPR hub zwraca copr_lux=0 i odczyt rosnie
 * z jasnoscia ekranu.  Bajty to BEYOND2_A3_S0_COPR producenta
 * (s6e3ha9_beyond2_a3_s0_panel_copr.h), rowne temu, co z ustawien
 * beyond2 sklada copy_copr_maptbl: en=1, ilc=1, gamma 1, wspolczynniki
 * 768, max_cnt 3, piec ROI od paska stanu do okolic czujnika.
 */
#define COPR_LEN		60
static const u8 copr_e1[1 + COPR_LEN] = {
	0xe1,
	0x05, 0x3f, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x03, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x05, 0x9f, 0x00, 0x53,
	0x00, 0x00, 0x00, 0x54, 0x05, 0x9f, 0x00, 0xb8, 0x00, 0x00,
	0x00, 0xb9, 0x05, 0x9f, 0x0a, 0xe7, 0x00, 0x00, 0x0a, 0xe8,
	0x05, 0x9f, 0x0b, 0x8f, 0x03, 0xc9, 0x00, 0xa5, 0x03, 0xf0,
	0x00, 0xc5, 0x03, 0xc9, 0x00, 0xa5, 0x03, 0xf0, 0x00, 0xc5,
};

/* Odczyt 0xE1 (ustawienia) i 0x5A (wynik: gotowosc, licznik, COPR) do logu. */
static void copr_stan(const char *kiedy)
{
	u8 e1[COPR_LEN] = {}, wynik[41] = {};
	int n, m;

	mutex_lock(&zamek);
	klucze(true);
	n = odczyt(0xe1, e1, sizeof(e1));
	m = odczyt(0x5a, wynik, sizeof(wynik));
	klucze(false);
	mutex_unlock(&zamek);
	pr_info("s6e3ha9: COPR %s: 0xE1 %s (%d B): %*ph\n", kiedy,
		n == COPR_LEN && !memcmp(e1, &copr_e1[1], COPR_LEN) ? "jak producent" : "inne",
		n, min(n, 16), e1);
	if (m >= 5)
		pr_info("s6e3ha9: COPR %s: gotowy %d licznik %d copr %d\n", kiedy,
			wynik[0] & 1, wynik[1] << 8 | wynik[2], wynik[3] << 8 | wynik[4]);
}

/*
 * Wynik COPR do przestrzeni uzytkownika: "gotowy cur avg r g b", gdzie r g b to
 * ROI5 (969..1008 x 165..197), prostokat nad czujnikiem swiatla pod ekranem.
 * Uklad bajtow 0x5A jak panel_read_copr_spi producenta (COPR_VER_3).  Odczyt
 * po DSI pod ta sama blokada co zapisy jasnosci, bez udzialu huba.
 */
static ssize_t copr_show(struct device *dev, struct device_attribute *attr, char *buf)
{
	u8 w[41] = {};
	int n;

	mutex_lock(&zamek);
	klucze(true);
	n = odczyt(0x5a, w, sizeof(w));
	klucze(false);
	mutex_unlock(&zamek);
	if (n < 41)
		return n < 0 ? n : -EIO;
	return sysfs_emit(buf, "%d %d %d %d %d %d\n", w[0] & 1,
			  w[3] << 8 | w[4], w[5] << 8 | w[6],
			  w[35] << 8 | w[36], w[37] << 8 | w[38], w[39] << 8 | w[40]);
}
static DEVICE_ATTR_RO(copr);

static int copr_ustaw(bool wl)
{
	u8 b[1 + COPR_LEN];
	int ret;

	memcpy(b, copr_e1, sizeof(b));
	if (!wl)
		b[1] &= ~1;
	mutex_lock(&zamek);
	ret = klucze(true);
	ret |= zapis(b, sizeof(b));
	ret |= klucze(false);
	mutex_unlock(&zamek);
	copr_stan(wl ? "po wlaczeniu" : "po wylaczeniu");
	return ret;
}

/* Wlaczany przy starcie; bez niego hub nie odejmie swiatla ekranu od czujnika. */
static bool copr = true;

static int copr_param(const char *val, const struct kernel_param *kp)
{
	bool wl;
	int ret = kstrtobool(val, &wl);

	if (ret)
		return ret;
	if (!gamma_ok) {
		/* przy ladowaniu modulu: tylko zapamietaj, init wysle */
		copr = wl;
		return 0;
	}
	ret = copr_ustaw(wl);
	if (!ret)
		copr = wl;
	return ret;
}

static const struct kernel_param_ops copr_ops = {
	.set = copr_param,
	.get = param_get_bool,
};
module_param_cb(copr, &copr_ops, &copr, 0644);
MODULE_PARM_DESC(copr, "1: wlacz pomiar COPR w DDI dla huba czujnikow (sekwencja producenta)");

/*
 * Stan panelu dla huba czujnikow, jak panel_bl_thread producenta
 * (panel_notifier PANEL_EVENT_BL_CHANGED): poziom platformy razy 100 (PAC 3.0)
 * i AOR_TO_RATIO(aor, vtotal 3064) w 0,01 %.  Poziom 0 (krok 2 nitow) idzie
 * jako 1: seria z poziomem 0 zostawila ekran czarny do restartu, a roznica
 * to jeden stopien skali.  Hub to osobny modul, wiec wiazanie przez
 * symbol_get w obie strony: ten modul wysyla przy kazdej zmianie, hub
 * dopytuje o stan przy swoim starcie.
 */
#define VTOTAL			3064
static int panel_poziom, panel_aor;

int ssp_panel_bl(int brightness, int aor_ratio);

/*
 * Na kazda wiadomosc hub robi set_copr_mode na DDI przez wlasne SPI.  Jesli
 * w tej chwili ten modul pisze gamme i AOR przez DSI, ekran zostaje czarny do
 * restartu (27.09.2026, dwa razy).  Zmierzone osobno: 300 wiadomosci w minute
 * bez zapisow DSI i 1372 zmiany jasnosci po jednej wiadomosci nie szkodza;
 * szkodzi tylko jedno w trakcie drugiego.  Dlatego stan idzie do huba dopiero
 * HUB_ZWLOKA_MS po ostatniej zmianie (w trakcie animacji wcale), pod blokada
 * zapisow DSI, ktora zostaje trzymana jeszcze HUB_OCHRONA_MS.
 */
#define HUB_ZWLOKA_MS		500
#define HUB_OCHRONA_MS		200
/*
 * Domyslnie WYLACZONE.  Zwloka i ochrona przetrwaly 2 minuty testu D, ale
 * usluga automatycznej jasnosci po godzinie znow zostawila czarny ekran
 * (hub odpowiadal wtedy "set_copr_mode 255 0" zamiast "0 N").  Kompensacja
 * swiatla ekranu idzie teraz przez odczyt COPR po DSI (atrybut copr).
 */
static bool hub;
module_param(hub, bool, 0644);
MODULE_PARM_DESC(hub, "1: wysylaj stan panelu do huba czujnikow po ustaleniu sie jasnosci");

static void hub_praca(struct work_struct *w)
{
	int (*wyslij)(int, int) = symbol_get(ssp_panel_bl);

	if (!wyslij)
		return;
	mutex_lock(&zamek);
	wyslij(READ_ONCE(panel_poziom), READ_ONCE(panel_aor));
	msleep(HUB_OCHRONA_MS);
	mutex_unlock(&zamek);
	symbol_put(ssp_panel_bl);
}
static DECLARE_DELAYED_WORK(hub_zadanie, hub_praca);

static void panel_do_huba(int k, u32 aor)
{
	WRITE_ONCE(panel_poziom, max_t(int, s6e3ha9_poziom[k], 1) * 100);
	WRITE_ONCE(panel_aor, (aor * 100000 / VTOTAL + 5) / 10);
	if (hub)
		mod_delayed_work(system_wq, &hub_zadanie, msecs_to_jiffies(HUB_ZWLOKA_MS));
}

/* Wolane przez huba po jego (re)starcie: stan idzie ta sama chroniona droga. */
void s6e3ha9_panel_bl_odswiez(void);
void s6e3ha9_panel_bl_odswiez(void)
{
	if (hub && READ_ONCE(panel_poziom))
		mod_delayed_work(system_wq, &hub_zadanie, msecs_to_jiffies(HUB_ZWLOKA_MS));
}
EXPORT_SYMBOL_GPL(s6e3ha9_panel_bl_odswiez);

static int czytaj_panel(void)
{
	u8 mtp[S6E3HA9_MTP_LEN], ca[S6E3HA9_GAMMA_LEN], b1[4] = {}, b5[4] = {}, f4[4] = {};
	u8 b3[2 + S6E3HA9_GAMMA_LEN] = {}, b4[8] = {}, acl[2] = {}, test[S6E3HA9_GAMMA_LEN];
	s32 t[NR_TP][3];
	int n, i, zgodny = -1, ret;

	mutex_lock(&zamek);
	ret = klucze(true);
	n = odczyt(0xc8, mtp, sizeof(mtp));
	zrzut("MTP 0xC8", mtp, n);
	i = odczyt(0xca, ca, sizeof(ca));
	zrzut("gamma 0xCA (S-Boot)", ca, i);
	zrzut("AOR 0xB1", b1, odczyt(0xb1, b1, 2));
	zrzut("ELVSS 0xB5", b5, odczyt(0xb5, b5, 3));
	zrzut("VINT 0xF4", f4, odczyt(0xf4, f4, 2));
	/* Ten DDI nie przesuwa odczytu przez 0xB0: czytamy od zera i odcinamy 2 bajty (panel.c). */
	zrzut("gamma HBM 0xB3 (od 0)", b3, odczyt(0xb3, b3, sizeof(b3)));
	zrzut("ACL 0xB4", b4, odczyt(0xb4, b4, 6));
	zrzut("ACL 0x55", acl, odczyt(0x55, acl, 1));
	{
		/* Stan IRC i POC po S-Boocie, do porownania z tabelami producenta. */
		u8 irc[28] = {}, poc[4] = {};

		zrzut("IRC 0x95", irc, odczyt(0x95, irc, sizeof(irc)));
		zrzut("POC 0x96 (od 0)", poc, odczyt(0x96, poc, sizeof(poc)));
	}
	ret |= klucze(false);
	mutex_unlock(&zamek);
	if (ret)
		pr_warn("s6e3ha9: blad zapisu kluczy/przesuniecia (%d)\n", ret);
	if (n != S6E3HA9_MTP_LEN) {
		pr_err("s6e3ha9: MTP %d B zamiast %d, bez gammy\n", n, S6E3HA9_MTP_LEN);
		return -EIO;
	}
	s6e3ha9_dimming_unpack_mtp(dim, mtp);
	s6e3ha9_dimming_process(dim);
	gamma_ok = true;
	/* Kontrola rozpakowania: gamma -> liczby -> gamma musi dac to samo. */
	gamma_na_liczby(dim->gamma[NR_ZWYKLE - 1], t);
	liczby_na_gamme(t, test);
	pr_info("s6e3ha9: rozpakowanie gammy %s\n",
		memcmp(test, dim->gamma[NR_ZWYKLE - 1], sizeof(test)) ? "BLEDNE" : "odwracalne");
	licz_hbm(&b3[2]);
	pr_info("s6e3ha9: HBM krok 0 (%u nitow): %*ph\n", s6e3ha9_kroki[NR_ZWYKLE].nity,
		S6E3HA9_GAMMA_LEN, gamma_hbm[0]);
	pr_info("s6e3ha9: HBM krok 15 (%u nitow): %*ph\n", s6e3ha9_kroki[NR_ZWYKLE + NR_HBM - 1].nity,
		S6E3HA9_GAMMA_LEN, gamma_hbm[NR_HBM - 1]);
	for (n = 0; n < NR_ZWYKLE; n++)
		if (!memcmp(dim->gamma[n], ca, sizeof(ca)))
			zgodny = n;
	for (n = 0; n < NR_ZWYKLE; n += 12)
		pr_info("s6e3ha9: krok %2d (%3u nitow): %*ph\n", n, s6e3ha9_kroki[n].nity,
			S6E3HA9_GAMMA_LEN, dim->gamma[n]);
	if (zgodny >= 0)
		pr_info("s6e3ha9: gamma S-Boota = policzona dla kroku %d (%u nitow), silnik zgodny bit w bit\n",
			zgodny, s6e3ha9_kroki[zgodny].nity);
	else
		pr_info("s6e3ha9: gamma S-Boota nie rowna sie zadnemu krokowi; krok 73 (420 nitow): %*ph\n",
			S6E3HA9_GAMMA_LEN, dim->gamma[NR_ZWYKLE - 1]);
	return 0;
}

/*
 * Zapis rejestru od przesuniecia: DDI przyjmuje najpierw {0xB0, przesuniecie,
 * rejestr} (DDI_SUPPORT_POINT_GPARA producenta, common_mipi_lcd.c), potem
 * zwykly zapis rejestru.
 */
static int zapis_od(u8 ofs, const u8 *b, size_t n)
{
	u8 gpara[3] = { 0xb0, ofs, b[0] };

	return zapis(gpara, sizeof(gpara)) | zapis(b, n);
}

static int ustaw_krok(int k, u16 aor_rej)
{
	u8 g[1 + S6E3HA9_GAMMA_LEN] = { 0xca };
	u8 aor[3] = { 0xb1, aor_rej >> 8, aor_rej & 0xff };
	/* MPS_CON 0xCC do 39 nitow, wyzej 0xDC (getidx_mps_table producenta). */
	u8 elvss[4] = { 0xb5, 0x19, s6e3ha9_kroki[k].nity <= 39 ? 0xcc : 0xdc,
			s6e3ha9_kroki[k].elvss };
	/* ELVSS_TEMP (0xB5 od 56) dla temperatury powyzej zera: 0 dla kazdego kroku. */
	static const u8 elvss_temp[2] = { 0xb5, 0x00 };
	u8 vint[3] = { 0xf4, 0xeb, s6e3ha9_kroki[k].vint };
	/*
	 * IRC, POC: pakiety sekwencji jasnosci producenta (set_bl_cmdtbl), ktorych
	 * ten modul wczesniej nie wysylal.  Bez nich kroki HBM dawaly zazolcony
	 * obraz przy 444 nitach i czarny ekran od 500, ktory nie wracal bez
	 * restartu (27.09.2026).
	 */
	u8 irc[1 + 28] = { 0x95 };
	static const u8 irc_wl[2] = { 0x95, 0x2e };
	static const u8 poc1[12] = { 0xb1, 0x01, 0xaf, 0x00, 0x54, 0x68, 0xcc, 0x78,
				     0x30, 0xcc, 0x64, 0xff };
	u8 poc2[3] = { 0x96, s6e3ha9_poc[k][0], s6e3ha9_poc[k][1] };
	int ret;

	/* ACL: wylaczony w zwyklym zakresie, 8% OPR w HBM (tablice producenta). */
	const bool w_hbm = k >= NR_ZWYKLE;
	u8 acl_ster[7] = { 0xb4, 0x00, w_hbm ? 0x55 : 0x44, w_hbm ? 0x80 : 0x40,
			   w_hbm ? 0x65 : 0xff, 0x26, w_hbm ? 0x26 : 0x00 };
	u8 acl_wl[2] = { 0x55, w_hbm ? 0x02 : 0x00 };

	memcpy(&g[1], w_hbm ? gamma_hbm[k - NR_ZWYKLE] : dim->gamma[k], S6E3HA9_GAMMA_LEN);
	memcpy(&irc[1], s6e3ha9_irc[k], sizeof(s6e3ha9_irc[k]));
	mutex_lock(&zamek);
	/* Kolejnosc jak beyond2_a3_s0_set_bl_cmdtbl producenta. */
	ret = ZAPISZ(0xf0, 0x5a, 0x5a);
	ret |= zapis(g, sizeof(g));
	ret |= zapis(aor, sizeof(aor));
	ret |= zapis(elvss, sizeof(elvss));
	ret |= zapis_od(56, elvss_temp, sizeof(elvss_temp));
	ret |= zapis(vint, sizeof(vint));
	ret |= zapis(acl_ster, sizeof(acl_ster));
	ret |= zapis(acl_wl, sizeof(acl_wl));
	ret |= zapis(irc, sizeof(irc));
	ret |= zapis(irc_wl, sizeof(irc_wl));
	ret |= zapis_od(6, poc1, sizeof(poc1));
	ret |= zapis_od(2, poc2, sizeof(poc2));
	ret |= ZAPISZ(0xf7, 0x03);
	if (kontrola) {
		u8 b1[2] = {}, ca[S6E3HA9_GAMMA_LEN] = {};
		int nb = odczyt(0xb1, b1, sizeof(b1));
		int nc = odczyt(0xca, ca, sizeof(ca));

		pr_info("s6e3ha9: krok %d (%u nitow), AOR %#06x: AOR %s (%*ph), gamma %s, zapis %d\n", k,
			s6e3ha9_kroki[k].nity, aor_rej,
			nb == 2 && !memcmp(b1, &aor[1], 2) ? "zgodny" : "ROZNY", 2, b1,
			nc == S6E3HA9_GAMMA_LEN && !memcmp(ca, &g[1], S6E3HA9_GAMMA_LEN) ? "zgodna" : "ROZNA",
			ret);
	}
	ret |= ZAPISZ(0xf0, 0xa5, 0xa5);
	mutex_unlock(&zamek);
	return ret;
}

/*
 * Jasnosc miedzy krokami tabeli, jak S_DIMMING producenta
 * (panel_bl_aor_interpolation, VIRTUAL_BASE_LUMINANCE): gamma najblizszego
 * kroku nie ciemniejszego niz cel, a AOR tak dobrany, zeby zgasic nadmiar,
 * bo luminancja jest proporcjonalna do czesci ramki, w ktorej panel swieci:
 * vtotal - aor = (vtotal - aor_u) * cel / L_u.  Dokladnie w krokach tabeli
 * wychodzi AOR z tabeli.  Bez tego kazda zmiana byla skokiem o ~6 %
 * (105 -> 112 -> 119 nitow), co przy animacji wygladalo jak schodki.
 */
static int bl_ustaw(struct backlight_device *bl)
{
	unsigned int cel = backlight_get_brightness(bl);	/* 0,1 nita */
	int ostatni = (hbm ? NR_ZWYKLE + NR_HBM : NR_ZWYKLE) - 1;
	int u, ret;
	u32 aor_u, lum_u, gaszone;

	if (!gamma_ok)
		return -ENODEV;
	cel = max_t(unsigned int, cel, s6e3ha9_kroki[0].nity * DZIESIATE);
	for (u = 0; u < ostatni && s6e3ha9_kroki[u].nity * DZIESIATE < cel; u++)
		;
	lum_u = s6e3ha9_kroki[u].nity * DZIESIATE;
	cel = min(cel, lum_u);
	aor_u = s6e3ha9_kroki[u].aor[0] << 8 | s6e3ha9_kroki[u].aor[1];
	gaszone = VTOTAL - DIV_ROUND_CLOSEST((VTOTAL - aor_u) * cel, lum_u);
	ret = ustaw_krok(u, gaszone);
	if (!ret)
		panel_do_huba(u, gaszone);
	return ret;
}

static const struct backlight_ops bl_ops = {
	.update_status = bl_ustaw,
};

static int zegar_dsim(void)
{
	struct of_phandle_args a = { .args_count = 1, .args = { 21 } };
	struct clk *c;
	int ret;

	a.np = of_find_compatible_node(NULL, NULL, "samsung,exynos9820-cmu-dpu");
	if (!a.np)
		return -ENODEV;
	c = of_clk_get_from_provider(&a);
	of_node_put(a.np);
	if (IS_ERR(c))
		return PTR_ERR(c);
	ret = clk_prepare_enable(c);
	clk_put(c);
	return ret;
}

static int __init jasnosc_init(void)
{
	struct backlight_properties p = {
		.type = BACKLIGHT_RAW,
		.max_brightness = NITY_MAKS * DZIESIATE,
		.brightness = NITY_MAKS * DZIESIATE,
		.scale = BACKLIGHT_SCALE_LINEAR,
	};
	struct backlight_device *bl;
	int ret;

	ret = zegar_dsim();
	if (ret)
		return ret;
	dsim = ioremap(DSIM_BAZA, 0x100);
	dim = kzalloc(sizeof(*dim), GFP_KERNEL);
	if (!dsim || !dim) {
		ret = -ENOMEM;
		goto blad;
	}
	ret = czytaj_panel();
	if (ret || !tryb)
		goto blad;
	copr_stan("po starcie");
	if (copr)
		copr_ustaw(true);
	if (hbm)
		p.max_brightness = NITY_HBM * DZIESIATE;
	pdev = platform_device_register_simple("s6e3ha9-jasnosc", -1, NULL, 0);
	if (IS_ERR(pdev)) {
		ret = PTR_ERR(pdev);
		goto blad;
	}
	bl = devm_backlight_device_register(&pdev->dev, "s6e3ha9", &pdev->dev, NULL, &bl_ops, &p);
	if (IS_ERR(bl)) {
		ret = PTR_ERR(bl);
		platform_device_unregister(pdev);
		goto blad;
	}
	pr_info("s6e3ha9: jasnosc 2..%u nitow w /sys/class/backlight/s6e3ha9 (jednostka 0,1 nita)\n",
		p.max_brightness / DZIESIATE);
	if (device_create_file(&pdev->dev, &dev_attr_copr))
		pr_warn("s6e3ha9: bez atrybutu copr\n");
	return 0;
blad:
	kfree(dim);
	if (dsim)
		iounmap(dsim);
	return ret ? ret : -EAGAIN;
}

static void __exit jasnosc_exit(void)
{
	platform_device_unregister(pdev);
	cancel_delayed_work_sync(&hub_zadanie);
	mutex_lock(&zamek);
	mutex_unlock(&zamek);
	kfree(dim);
	iounmap(dsim);
}

module_init(jasnosc_init);
module_exit(jasnosc_exit);
MODULE_DESCRIPTION("Jasnosc panelu S6E3HA9 na laczu DSIM S-Boota");
MODULE_LICENSE("GPL");
