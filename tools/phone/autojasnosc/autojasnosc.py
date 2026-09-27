#!/usr/bin/python3
"""Automatyczna jasnosc ekranu Galaxy S10+ pod Plasma Mobile.

Czyta luksy z czujnika swiatla pod ekranem (IIO `als`, modul huba czujnikow),
przelicza je krzywa na nity i ustawia jasnosc przez org.kde.ScreenBrightness,
wiec suwak Plasmy zawsze pokazuje prawde.

Swiatlo samego ekranu odejmuje ta usluga wedlug COPR (jasnosc tresci nad
czujnikiem) i jasnosci panelu; zobacz przeciek().

Recznie przesuniety suwak jest zapamietywany jako mnoznik wzgledem krzywej
(w ~/.config/autojasnosc) i stosowany dalej, tak jak uczenie w Androidzie,
tylko prosciej.  Wlasne zmiany usluga oznacza kontekstem D-Bus, zeby odroznic
je od ruchu suwaka.
"""
import glob
import json
import math
import os
import signal
import sys
import time

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

SERWIS = 'org.kde.ScreenBrightness'
OBIEKT = '/org/kde/ScreenBrightness/display0'
INTERFEJS = 'org.kde.ScreenBrightness.Display'
KONTEKST = 'autojasnosc'
LCD_POWER = '/sys/class/lcd/exynos9820-dsim/lcd_power'
PLIK = os.path.expanduser('~/.config/autojasnosc/stan.json')

# Krzywa luksy -> nity, interpolowana w log(luksow).  Ciemny pokoj ~12 nitow,
# biuro ~150, pochmurny dzien przy oknie ~350, slonce 800 (HBM).
KRZYWA = [(0, 12), (3, 20), (10, 40), (40, 80), (100, 130), (300, 200),
          (1000, 300), (3000, 420), (10000, 600), (30000, 800)]
OKRES_MS = 1000
# Wygladzanie w log(luksow): w strone jasniej szybko, ciemniej wolno.
ALFA_JASNIEJ = 0.5
ALFA_CIEMNIEJ = 0.12
PROG = 0.10          # nowy cel blizej niz 10 % od obecnej jasnosci nie rusza ekranu
MNOZNIK_MIN, MNOZNIK_MAKS = 0.25, 4.0
# Przejscie do celu malymi krokami co 50 ms, w skali logarytmicznej.  Zmierzone:
# PowerDevil sam animuje skok tylko ~270 ms w 4-5 krokach, wiec skok co sekunde
# bylo widac jako szarpniecia.  3 % na krok to podwojenie w ~1,2 s (jasniej),
# 1 % to podwojenie w ~3,5 s (ciemniej).
ANIMACJA_MS = 50
KROK_JASNIEJ = 1.03
KROK_CIEMNIEJ = 1.01
# Hub odejmuje swiatlo ekranu wedlug stanu panelu, ktory dostaje dopiero 0,5 s
# po ustaleniu sie jasnosci (s6e3ha9_jas, ochrona DDI).  W trakcie przejscia
# i chwile po nim odczyt zawiera nieodjete swiatlo ekranu, wiec jest pomijany,
# inaczej rozjasnianie samo by sie napedzalo.
CISZA_PO_ZMIANIE = 1.5

# Swiatlo samego ekranu w czujniku.  Hub moglby je odejmowac, ale wiadomosci
# o stanie panelu do huba zostawialy ekran czarny, wiec odejmuje je usluga:
# COPR (jasnosc tresci) nad czujnikiem czyta s6e3ha9_jas po DSI.  Zmierzone
# 27.09.2026 przy tle 3 lux, x = (r+g+b obszaru nad czujnikiem) * nity:
# bialy ekran 150 nitow 29,5 lux, 300 nitow 121 lux; ciemny 300 nitow 9 lux.
# Przeciek = 118 * (x / 200700) ** 2.15 (z bialych punktow; ciemne i niskie
# jasnosci zgadzaja sie z nim do ~2 lux).
COPR = '/sys/devices/platform/s6e3ha9-jasnosc/copr'
BACKLIGHT = '/sys/class/backlight/s6e3ha9/actual_brightness'
PRZECIEK_X, PRZECIEK_LUX, PRZECIEK_WYK = 200700.0, 118.0, 2.15


def przeciek():
    """Luksy, ktore czujnik dostaje od ekranu przy obecnej tresci i jasnosci."""
    try:
        with open(COPR) as f:
            p = f.read().split()
        suma = int(p[3]) + int(p[4]) + int(p[5])
        nity = (czytaj_int(BACKLIGHT) or 0) / 10
    except (OSError, ValueError, IndexError):
        return 0.0
    return PRZECIEK_LUX * (suma * nity / PRZECIEK_X) ** PRZECIEK_WYK


def log(msg):
    print(msg, flush=True)


def znajdz_als():
    for d in glob.glob('/sys/bus/iio/devices/iio:device*'):
        try:
            with open(os.path.join(d, 'name')) as f:
                if f.read().strip() == 'als':
                    return os.path.join(d, 'in_illuminance_input')
        except OSError:
            pass
    return None


def czytaj_int(sciezka):
    try:
        with open(sciezka) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def krzywa(lux):
    """Nity dla danej liczby luksow, interpolacja liniowa w log(1+lux)."""
    x = math.log1p(max(lux, 0))
    for (l0, n0), (l1, n1) in zip(KRZYWA, KRZYWA[1:]):
        x0, x1 = math.log1p(l0), math.log1p(l1)
        if x <= x1:
            t = (x - x0) / (x1 - x0)
            return n0 + t * (n1 - n0)
    return KRZYWA[-1][1]


class Autojasnosc:
    def __init__(self):
        self.bus = dbus.SessionBus()
        self.ekran = dbus.Interface(self.bus.get_object(SERWIS, OBIEKT), INTERFEJS)
        wl = dbus.Interface(self.bus.get_object(SERWIS, OBIEKT), 'org.freedesktop.DBus.Properties')
        self.maks = int(wl.Get(INTERFEJS, 'MaxBrightness'))
        # sterownik s6e3ha9_jas liczy w 0,1 nita (8000 = 800 nitow)
        self.nity_maks = (czytaj_int('/sys/class/backlight/s6e3ha9/max_brightness') or 8000) / 10
        self.als = znajdz_als()
        self.mnoznik, self.wlaczona = self.wczytaj_stan()
        self.wygladzone = None      # log1p(lux) po wygladzeniu
        self.ostatnio = None        # obecna jasnosc w skali Plasmy (float, nasza albo suwaka)
        self.cel = None             # dokad zmierza animacja (skala Plasmy)
        self.animacja = None        # id zegara GLib w trakcie przejscia
        self.cisza_do = 0.0         # do tej chwili (monotonic) odczyty sa pomijane
        self.bus.add_signal_receiver(self.zmiana, 'BrightnessChanged', SERWIS, SERWIS,
                                     '/org/kde/ScreenBrightness')
        log('start: als=%s, skala Plasmy 0..%d = 0..%d nitow, mnoznik %.2f, %s'
            % (self.als, self.maks, self.nity_maks, self.mnoznik,
               'wlaczona' if self.wlaczona else 'wylaczona'))

    def wczytaj_stan(self):
        try:
            with open(PLIK) as f:
                s = json.load(f)
            m = min(max(float(s.get('mnoznik', 1.0)), MNOZNIK_MIN), MNOZNIK_MAKS)
            return m, bool(s.get('wlaczona', True))
        except (OSError, ValueError):
            return 1.0, True

    def zapisz_mnoznik(self):
        os.makedirs(os.path.dirname(PLIK), exist_ok=True)
        tmp = PLIK + '.tmp'
        with open(tmp, 'w') as f:
            json.dump({'mnoznik': round(self.mnoznik, 3), 'wlaczona': self.wlaczona}, f)
        os.replace(tmp, PLIK)

    def ustaw(self, wl):
        """Przycisk w szufladzie Plasmy: wlacza lub wylacza automatyke."""
        self.wlaczona = bool(wl)
        if not self.wlaczona:
            self.zatrzymaj_animacje()
        # po wlaczeniu od razu zmierz na nowo, bez starego wygladzenia
        self.wygladzone = None
        self.ostatnio = None
        self.zapisz_mnoznik()
        log('automatyka %s' % ('wlaczona' if self.wlaczona else 'wylaczona'))

    def do_plasmy(self, nity):
        return int(round(min(max(nity, 2), self.nity_maks) * self.maks / self.nity_maks))

    def z_plasmy(self, wartosc):
        return wartosc * self.nity_maks / self.maks

    def zmiana(self, nazwa, wartosc, klient, kontekst):
        """Sygnal BrightnessChanged: ruch suwaka uczy mnoznika."""
        if nazwa != 'display0' or str(kontekst) == KONTEKST or not self.wlaczona:
            return
        if self.wygladzone is None:
            return
        cel = krzywa(math.expm1(self.wygladzone))
        nity = self.z_plasmy(int(wartosc))
        if cel <= 0 or nity <= 0:
            return
        self.mnoznik = min(max(nity / cel, MNOZNIK_MIN), MNOZNIK_MAKS)
        self.zatrzymaj_animacje()
        self.ostatnio = float(wartosc)
        self.cisza_do = time.monotonic() + CISZA_PO_ZMIANIE
        self.zapisz_mnoznik()
        log('suwak: %d nitow przy %.0f lux, mnoznik %.2f'
            % (nity, math.expm1(self.wygladzone), self.mnoznik))

    def krok(self):
        if not self.wlaczona:
            return True
        if czytaj_int(LCD_POWER) not in (0, None):
            return True                 # ekran wygaszony: nic nie ustawiamy
        if not self.als:
            self.als = znajdz_als()
            return True
        if self.animacja is not None or time.monotonic() < self.cisza_do:
            return True
        lux = czytaj_int(self.als)
        if lux is None:
            return True
        lux = max(lux - przeciek(), 0)
        x = math.log1p(max(lux, 0))
        if self.wygladzone is None:
            self.wygladzone = x
        else:
            a = ALFA_JASNIEJ if x > self.wygladzone else ALFA_CIEMNIEJ
            self.wygladzone += a * (x - self.wygladzone)
        cel = self.do_plasmy(krzywa(math.expm1(self.wygladzone)) * self.mnoznik)
        if self.ostatnio is None:
            try:
                self.ostatnio = float(dbus.Interface(
                    self.bus.get_object(SERWIS, OBIEKT),
                    'org.freedesktop.DBus.Properties').Get(INTERFEJS, 'Brightness'))
            except dbus.DBusException:
                return True
        if self.animacja is None and abs(cel - self.ostatnio) <= PROG * max(self.ostatnio, 1):
            return True
        if cel != self.cel:
            log('%4d lux -> cel %3.0f nitow' % (lux, self.z_plasmy(cel)))
        self.cel = cel
        if self.animacja is None:
            self.animacja = GLib.timeout_add(ANIMACJA_MS, self.animuj)
        return True

    def zatrzymaj_animacje(self):
        if self.animacja is not None:
            GLib.source_remove(self.animacja)
            self.animacja = None

    def animuj(self):
        """Jeden maly krok w strone celu; False konczy zegar."""
        teraz = max(self.ostatnio, 1.0)
        if self.cel > teraz:
            nowa = min(teraz * KROK_JASNIEJ, self.cel)
        else:
            nowa = max(teraz / KROK_CIEMNIEJ, self.cel)
        if int(round(nowa)) != int(round(self.ostatnio)):
            try:
                self.ekran.SetBrightnessWithContext(dbus.Int32(int(round(nowa))),
                                                    dbus.UInt32(1), KONTEKST)
            except dbus.DBusException as e:
                log('SetBrightness: %s' % e)
                self.animacja = None
                return False
        self.ostatnio = nowa
        self.cisza_do = time.monotonic() + CISZA_PO_ZMIANIE
        if abs(nowa - self.cel) < 0.5:
            self.animacja = None
            return False
        return True


USLUGA = 'pl.s10plus.Autojasnosc'


class Przelacznik(dbus.service.Object):
    """pl.s10plus.Autojasnosc /Autojasnosc: Stan() -> b, Ustaw(b); dla przycisku w szufladzie."""

    def __init__(self, bus, a):
        self.a = a
        dbus.service.Object.__init__(self, bus, '/Autojasnosc')

    @dbus.service.method(USLUGA, in_signature='', out_signature='b')
    def Stan(self):
        return self.a.wlaczona

    @dbus.service.method(USLUGA, in_signature='b', out_signature='')
    def Ustaw(self, wl):
        self.a.ustaw(wl)


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    petla = GLib.MainLoop()
    a = Autojasnosc()
    nazwa = dbus.service.BusName(USLUGA, a.bus)
    przelacznik = Przelacznik(a.bus, a)
    GLib.timeout_add(OKRES_MS, a.krok)
    try:
        from gi.repository import GLibUnix
        sygnal = GLibUnix.signal_add
    except ImportError:
        sygnal = GLib.unix_signal_add
    for s in (signal.SIGTERM, signal.SIGINT):
        sygnal(GLib.PRIORITY_DEFAULT, s, petla.quit)
    petla.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
