// Okno aplikacji DeepSeek Harness: Web UI serwera dsh w WebKitGTK (GTK4)
// z akceleracja GPU na Droidianie (libhybris, Mali).
//
// Dlaczego WebKitGTK i dlaczego C (zmierzone 30.09.2026):
// - Qt WebEngine 6.10 przekazuje klatke z Chromium do Qt tylko przez dma-buf
//   albo Vulkan; libhybris nie daje zadnego, wiec z GPU okno jest czarne.
// - Sterowniki Androida trzymaja kontekst GL w gniazdach TLS bionica
//   (tpidr_el0 + 24). Droidian chroni je preloadem libtls-padding.so, ale
//   TLS samego pliku wykonywalnego lezy przed preloadem. Firefox (56 B TLS)
//   i python3 (libpython wbudowany) maja wlasny TLS, wiec Mali czyta ich
//   zmienne zamiast kontekstu i pada. Ten program NIE MOZE miec zmiennych
//   __thread / thread_local (sprawdza zainstaluj: readelf -l, brak TLS).
//   Procesy WebKitGTK (WebProcess, GPUProcess) tez sa bez TLS.
//
// Uzycie: DSH_OKNO_ADRES=<adres z tokenem> deepseek-harness-okno
// cc okno.c -o deepseek-harness-okno $(pkg-config --cflags --libs gtk4 webkitgtk-6.0 libdrm) \
//    -Wl,--export-dynamic-symbol=drmGetDevices2,--export-dynamic-symbol=drmFreeDevices
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <gtk/gtk.h>
#include <string.h>
#include <webkit/webkit.h>
#include <xf86drm.h>

static const char *adres;

// Klatki bez kopii (Panfrost w procesie tresci, gralloc do okna): WebKit wlacza
// przekazywanie sprzetowe tylko, gdy zna urzadzenie DRM z wezlem primary
// (DRMMainDevice.cpp: WEBKIT_WEB_RENDER_DEVICE_FILE daje sam wezel render, primary
// szuka przez drmGetDevices2, a DRMDevice::isNull() patrzy na primary). Jadro
// Droidiana nie ma DRM wcale, wiec wywolaniom z libwebkitgtk podajemy jedno
// urzadzenie z oboma wezlami = WEBKIT_WEB_RENDER_DEVICE_FILE. Reszta procesu
// dostaje prawdziwe libdrm.
static drmDevice atrapa;
static char *atrapa_wezly[DRM_NODE_MAX];

static int wola_webkit(const void *adres_powrotu)
{
	Dl_info i;
	return dladdr(adres_powrotu, &i) && i.dli_fname && strstr(i.dli_fname, "libwebkitgtk");
}

int drmGetDevices2(uint32_t flagi, drmDevicePtr urzadzenia[], int max)
{
	const char *wezel = getenv("WEBKIT_WEB_RENDER_DEVICE_FILE");
	if (wezel && *wezel && wola_webkit(__builtin_return_address(0))) {
		for (int k = 0; k < DRM_NODE_MAX; k++)
			atrapa_wezly[k] = (char *)wezel;
		atrapa.nodes = atrapa_wezly;
		atrapa.available_nodes = (1 << DRM_NODE_PRIMARY) | (1 << DRM_NODE_RENDER);
		atrapa.bustype = DRM_BUS_PLATFORM;
		if (urzadzenia && max > 0)
			urzadzenia[0] = &atrapa;
		return 1;
	}
	int (*prawdziwa)(uint32_t, drmDevicePtr *, int) = dlsym(RTLD_NEXT, "drmGetDevices2");
	return prawdziwa ? prawdziwa(flagi, urzadzenia, max) : -ENODEV;
}

void drmFreeDevices(drmDevicePtr urzadzenia[], int ile)
{
	if (ile > 0 && urzadzenia && urzadzenia[0] == &atrapa)
		return;
	void (*prawdziwa)(drmDevicePtr *, int) = dlsym(RTLD_NEXT, "drmFreeDevices");
	if (prawdziwa)
		prawdziwa(urzadzenia, ile);
}

// linki otwierajace nowe okno ida do zwyklej przegladarki
static gboolean decyzja(WebKitWebView *widok, WebKitPolicyDecision *d,
			WebKitPolicyDecisionType typ, gpointer okno)
{
	(void)widok;
	if (typ != WEBKIT_POLICY_DECISION_TYPE_NEW_WINDOW_ACTION)
		return FALSE;
	WebKitNavigationAction *a =
		webkit_navigation_policy_decision_get_navigation_action(WEBKIT_NAVIGATION_POLICY_DECISION(d));
	const char *uri = webkit_uri_request_get_uri(webkit_navigation_action_get_request(a));
	GtkUriLauncher *l = gtk_uri_launcher_new(uri);
	gtk_uri_launcher_launch(l, GTK_WINDOW(okno), NULL, NULL, NULL);
	g_object_unref(l);
	webkit_policy_decision_ignore(d);
	return TRUE;
}

// DSH_OKNO_KONSOLA=1: skale okna widziane przez GTK (diagnostyka dpr w WebKicie)
static gboolean pokaz_skale(gpointer widok)
{
	GdkSurface *s = gtk_native_get_surface(gtk_widget_get_native(GTK_WIDGET(widok)));
	g_print("skala: widget=%d surface_int=%d surface=%.3f rozmiar=%dx%d\n",
		gtk_widget_get_scale_factor(GTK_WIDGET(widok)),
		s ? gdk_surface_get_scale_factor(s) : -1, s ? gdk_surface_get_scale(s) : -1.0,
		gtk_widget_get_width(GTK_WIDGET(widok)), gtk_widget_get_height(GTK_WIDGET(widok)));
	return G_SOURCE_CONTINUE;
}

static void uruchom(GtkApplication *app, gpointer dane)
{
	(void)dane;
	// Sesja Plasmy na Droidianie nie podaje GTK gtk-xft-dpi (0). WebKit liczy
	// z niego powiekszenie tekstu (DPI/96), wiec strona dostaje devicePixelRatio 0
	// i innerWidth/innerHeight = INT_MAX, a uklad sie zapada. 96 DPI = 96*1024.
	GtkSettings *gs = gtk_settings_get_default();
	gint dpi = 0;
	g_object_get(gs, "gtk-xft-dpi", &dpi, NULL);
	if (dpi <= 0)
		g_object_set(gs, "gtk-xft-dpi", 96 * 1024, NULL);
	if (g_getenv("DSH_OKNO_KONSOLA"))
		g_print("gtk-xft-dpi: bylo %d\n", dpi);

	GtkWidget *okno = gtk_application_window_new(app);
	gtk_window_set_title(GTK_WINDOW(okno), "DeepSeek Harness");
	gtk_window_set_default_size(GTK_WINDOW(okno), 480, 1013);

	GtkWidget *widok = webkit_web_view_new();
	WebKitSettings *u = webkit_web_view_get_settings(WEBKIT_WEB_VIEW(widok));
	// DSH_OKNO_POLITYKA=never: bez kompozycji na GPU (pomiar, porownanie z oknem Qt)
	webkit_settings_set_hardware_acceleration_policy(u, g_strcmp0(g_getenv("DSH_OKNO_POLITYKA"), "never") ?
		WEBKIT_HARDWARE_ACCELERATION_POLICY_ALWAYS : WEBKIT_HARDWARE_ACCELERATION_POLICY_NEVER);
	// DSH_OKNO_KONSOLA=1: komunikaty konsoli JavaScript na stdout (diagnostyka)
	if (g_getenv("DSH_OKNO_KONSOLA")) {
		webkit_settings_set_enable_write_console_messages_to_stdout(u, TRUE);
		webkit_settings_set_enable_developer_extras(u, TRUE);
		g_timeout_add_seconds(3, pokaz_skale, widok);
	}
	g_signal_connect(widok, "decide-policy", G_CALLBACK(decyzja), okno);
	webkit_web_view_load_uri(WEBKIT_WEB_VIEW(widok), adres);

	gtk_window_set_child(GTK_WINDOW(okno), widok);
	gtk_window_maximize(GTK_WINDOW(okno));
	gtk_window_present(GTK_WINDOW(okno));
}

int main(int argc, char **argv)
{
	// adres z tokenem dsh najlepiej w DSH_OKNO_ADRES: argv kazdego procesu jest
	// czytelny dla wszystkich w /proc, srodowisko tylko dla wlasciciela
	adres = argc > 1 ? argv[1] : g_getenv("DSH_OKNO_ADRES");
	if (!adres || !*adres) {
		g_printerr("uzycie: %s <adres>  (albo DSH_OKNO_ADRES=<adres>)\n", argv[0]);
		return 1;
	}
	GtkApplication *app = gtk_application_new("pl.s10plus.DeepSeekHarness", G_APPLICATION_NON_UNIQUE);
	g_signal_connect(app, "activate", G_CALLBACK(uruchom), NULL);
	char *argv0[] = { argv[0], NULL };
	int ret = g_application_run(G_APPLICATION(app), 1, argv0);
	g_object_unref(app);
	return ret;
}
