#!/usr/bin/python3
"""Blokada wygaszania ekranu od aplikacji pod wayfire (Plasma Mobile bez KWin).

Ekran gasi wtyczka idle wayfire.  Szanuje ona protokol Wayland idle-inhibit
(mpv), ale blokad przez D-Bus nikt jej nie przekazywal: nikt nie wystawial
org.freedesktop.ScreenSaver (Firefox, Chromium, aplikacje KDE), a blokady
powerdevil (portal Inhibit, PolicyAgent) nie maja wplywu na wayfire.

Ta usluga:
- wystawia org.freedesktop.ScreenSaver (/org/freedesktop/ScreenSaver i
  /ScreenSaver); kazde Inhibit przekazuje do powerdevil jako blokade
  ChangeScreenSettings, wiec aplet baterii widzi, kto trzyma ekran, a
  ciasteczko gasnie razem z klientem, ktory je wzial;
- slucha PolicyAgent.InhibitionsChanged i pyta HasInhibition(ChangeScreenSettings);
- stan (wlasne ciasteczka albo blokada w powerdevil) wysyla do wayfire metoda
  IPC podglad/idle-inhibit; wtyczka podglad zwalnia blokade sama, gdy
  polaczenie zniknie, wiec awaria tej uslugi nie zostawia ekranu wlaczonego.
"""
import glob
import json
import os
import signal
import socket
import struct
import sys

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

SERWIS = 'org.freedesktop.ScreenSaver'
INTERFEJS = 'org.freedesktop.ScreenSaver'
SCIEZKI = ('/org/freedesktop/ScreenSaver', '/ScreenSaver')
PA_SERWIS = 'org.kde.Solid.PowerManagement.PolicyAgent'
PA_OBIEKT = '/org/kde/Solid/PowerManagement/PolicyAgent'
PA_INTERFEJS = 'org.kde.Solid.PowerManagement.PolicyAgent'
CHANGE_SCREEN_SETTINGS = 4


def log(*a):
    print('blokada-wygaszania:', *a, flush=True)


class Wayfire:
    """Jedno trwale polaczenie IPC; po zerwaniu laczy sie od nowa i powtarza stan."""

    def __init__(self):
        self.gniazdo = None
        self.stan = False

    def _sciezka(self):
        s = os.environ.get('WAYFIRE_SOCKET')
        if s and os.path.exists(s):
            return s
        kandydaci = glob.glob('/run/user/%d/wayfire-*.socket' % os.getuid())
        return kandydaci[0] if kandydaci else None

    def _wyslij(self, metoda, dane):
        if self.gniazdo is None:
            sciezka = self._sciezka()
            if not sciezka:
                raise OSError('brak gniazda wayfire')
            self.gniazdo = socket.socket(socket.AF_UNIX)
            self.gniazdo.settimeout(2)
            self.gniazdo.connect(sciezka)
        b = json.dumps({'method': metoda, 'data': dane}).encode()
        self.gniazdo.sendall(struct.pack('<I', len(b)) + b)
        n = struct.unpack('<I', self._czytaj(4))[0]
        odp = json.loads(self._czytaj(n))
        if odp.get('result') != 'ok':
            raise OSError('wayfire: %s' % odp)

    def _czytaj(self, n):
        b = b''
        while len(b) < n:
            k = self.gniazdo.recv(n - len(b))
            if not k:
                raise OSError('wayfire zamknal polaczenie')
            b += k
        return b

    def wywolaj(self, metoda, dane):
        for proba in (1, 2):
            try:
                self._wyslij(metoda, dane)
                return True
            except (OSError, ValueError, struct.error) as e:
                if self.gniazdo is not None:
                    self.gniazdo.close()
                    self.gniazdo = None
                if proba == 2:
                    log('IPC %s nieudane: %s' % (metoda, e))
                elif metoda != 'podglad/idle-inhibit' and self.stan:
                    # nowe polaczenie nie ma blokady, ktora trzymalo stare
                    self._wyslij_bezpiecznie({'enabled': True})
        return False

    def _wyslij_bezpiecznie(self, dane):
        try:
            self._wyslij('podglad/idle-inhibit', dane)
        except (OSError, ValueError, struct.error):
            pass

    def ustaw(self, stan):
        if self.wywolaj('podglad/idle-inhibit', {'enabled': bool(stan)}):
            self.stan = stan


class ScreenSaver(dbus.service.Object):
    SUPPORTS_MULTIPLE_OBJECT_PATHS = True

    def __init__(self, bus, wayfire):
        super().__init__(bus, SCIEZKI[0])
        for s in SCIEZKI[1:]:
            self.add_to_connection(bus, s)
        self.bus = bus
        self.wayfire = wayfire
        self.ciasteczka = {}     # nasze ciasteczko -> (nadawca, aplikacja, ciasteczko powerdevil)
        self.obserwatorzy = {}   # nadawca -> dopasowanie NameOwnerChanged
        self.nastepne = 1
        self.blokada_pa = False
        self.stan = None

    # stan

    def przelicz(self):
        stan = bool(self.ciasteczka) or self.blokada_pa
        if stan != self.stan:
            log('ekran %s (aplikacje: %s, powerdevil: %s)' % (
                'trzymany' if stan else 'moze gasnac',
                sorted({a for _, a, _ in self.ciasteczka.values()}) or '-', self.blokada_pa))
            self.stan = stan
            self.wayfire.ustaw(stan)

    def odswiez_pa(self, *_):
        try:
            pa = self.bus.get_object(PA_SERWIS, PA_OBIEKT)
            self.blokada_pa = bool(pa.HasInhibition(dbus.UInt32(CHANGE_SCREEN_SETTINGS),
                                                    dbus_interface=PA_INTERFEJS))
        except dbus.exceptions.DBusException:
            self.blokada_pa = False
        self.przelicz()

    # klienci

    def _pa(self, metoda, *argumenty):
        try:
            pa = self.bus.get_object(PA_SERWIS, PA_OBIEKT)
            return getattr(pa, metoda)(*argumenty, dbus_interface=PA_INTERFEJS)
        except dbus.exceptions.DBusException as e:
            log('powerdevil %s: %s' % (metoda, e.get_dbus_name()))
            return None

    def _obserwuj(self, nadawca):
        if nadawca in self.obserwatorzy:
            return
        self.obserwatorzy[nadawca] = self.bus.add_signal_receiver(
            lambda nazwa, stary, nowy: nowy or self._zniknal(nazwa),
            'NameOwnerChanged', 'org.freedesktop.DBus', 'org.freedesktop.DBus',
            '/org/freedesktop/DBus', arg0=nadawca)

    def _zniknal(self, nadawca):
        for c in [c for c, (n, _, _) in self.ciasteczka.items() if n == nadawca]:
            self._zwolnij(c)
        dopasowanie = self.obserwatorzy.pop(nadawca, None)
        if dopasowanie:
            dopasowanie.remove()
        self.przelicz()

    def _zwolnij(self, ciasteczko):
        _, aplikacja, pa = self.ciasteczka.pop(ciasteczko)
        if pa is not None:
            self._pa('ReleaseInhibition', dbus.UInt32(pa))
        log('zwolnione %d (%s)' % (ciasteczko, aplikacja))

    # org.freedesktop.ScreenSaver

    @dbus.service.method(INTERFEJS, in_signature='ss', out_signature='u', sender_keyword='nadawca')
    def Inhibit(self, aplikacja, powod, nadawca=None):
        c = self.nastepne
        self.nastepne += 1
        pa = self._pa('AddInhibition', dbus.UInt32(CHANGE_SCREEN_SETTINGS), aplikacja, powod)
        self.ciasteczka[c] = (nadawca, str(aplikacja), None if pa is None else int(pa))
        self._obserwuj(nadawca)
        log('blokada %d od %s (%s): %s' % (c, aplikacja, nadawca, powod))
        self.przelicz()
        return dbus.UInt32(c)

    @dbus.service.method(INTERFEJS, in_signature='u', out_signature='', sender_keyword='nadawca')
    def UnInhibit(self, ciasteczko, nadawca=None):
        wpis = self.ciasteczka.get(int(ciasteczko))
        if wpis is None or wpis[0] != nadawca:
            raise dbus.exceptions.DBusException(
                'cookie %d does not belong to %s' % (ciasteczko, nadawca),
                name='org.freedesktop.DBus.Error.InvalidArgs')
        self._zwolnij(int(ciasteczko))
        self.przelicz()

    @dbus.service.method(INTERFEJS, in_signature='', out_signature='')
    def SimulateUserActivity(self):
        self.wayfire.wywolaj('podglad/idle-activity', {})

    @dbus.service.method(INTERFEJS, in_signature='', out_signature='b')
    def GetActive(self):
        return False

    @dbus.service.method(INTERFEJS, in_signature='b', out_signature='b')
    def SetActive(self, stan):
        return False

    @dbus.service.method(INTERFEJS, in_signature='', out_signature='u')
    def GetActiveTime(self):
        return dbus.UInt32(0)

    @dbus.service.method(INTERFEJS, in_signature='', out_signature='u')
    def GetSessionIdleTime(self):
        return dbus.UInt32(0)

    @dbus.service.method(INTERFEJS, in_signature='', out_signature='')
    def Lock(self):
        raise dbus.exceptions.DBusException('locking is done by the shell',
                                            name='org.freedesktop.DBus.Error.NotSupported')

    @dbus.service.signal(INTERFEJS, signature='b')
    def ActiveChanged(self, stan):
        pass


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    wynik = bus.request_name(SERWIS, dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
    if wynik not in (dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER, dbus.bus.REQUEST_NAME_REPLY_ALREADY_OWNER):
        log('%s ma juz wlasciciela, koncze' % SERWIS)
        return 0

    ss = ScreenSaver(bus, Wayfire())
    bus.add_signal_receiver(ss.odswiez_pa, 'InhibitionsChanged', PA_INTERFEJS, None, PA_OBIEKT)
    # powerdevil moze wstac po nas albo zrestartowac sie
    bus.watch_name_owner(PA_SERWIS, ss.odswiez_pa)

    petla = GLib.MainLoop()
    try:
        from gi.repository import GLibUnix
        dodaj_sygnal = GLibUnix.signal_add
    except ImportError:
        dodaj_sygnal = GLib.unix_signal_add
    for s in (signal.SIGTERM, signal.SIGINT):
        dodaj_sygnal(GLib.PRIORITY_DEFAULT, s, petla.quit)
    log('gotowa')
    petla.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
