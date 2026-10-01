#!/usr/bin/env python3
# Okno aplikacji DeepSeek Harness: Web UI serwera dsh w WebKitGTK (GTK4),
# z akceleracja GPU. Na Droidianie (libhybris) jedyny silnik, ktory moze
# rysowac przez Mali: Qt WebEngine nie ma dma-buf do przekazania klatki,
# a Firefox ma wlasny TLS w pliku wykonywalnym, ktory nachodzi na gniazda
# TLS sterownikow Androida (tp[3] = kontekst GL). Procesy WebKitGTK nie maja
# TLS w plikach wykonywalnych.
# Uzycie: deepseek-harness-okno.py <adres z tokenem>
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, WebKit  # noqa: E402


def uruchom(app):
    okno = Gtk.ApplicationWindow(application=app, title="DeepSeek Harness")
    okno.set_default_size(480, 1013)
    widok = WebKit.WebView()
    ust = widok.get_settings()
    ust.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
    ust.set_enable_developer_extras(False)
    # linki do innych stron w zwyklej przegladarce, nie w oknie aplikacji
    def decyzja(_w, d, typ):
        if typ == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
            Gtk.UriLauncher.new(d.get_navigation_action().get_request().get_uri()).launch(okno, None, None)
            d.ignore()
            return True
        return False
    widok.connect("decide-policy", decyzja)
    widok.load_uri(sys.argv[1])
    okno.set_child(widok)
    okno.maximize()
    okno.present()


app = Gtk.Application(application_id="pl.s10plus.DeepSeekHarness")
app.connect("activate", uruchom)
app.run([sys.argv[0]])
