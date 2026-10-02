#!/usr/bin/python3
"""Podbicie zegara CPU na dotyk (Galaxy S10+, Droidian).

Jadro LineageOS nie ma samsungowego input_boostera (urzadzenie
/sys/devices/platform/input_booster bez sterownika), a schedutil rozkreca
rdzenie za wolno: wysuniecie belki Plasmy pokazywalo pierwsza klatke po
280-320 ms, na stalym zegarze po ~170 ms (zmierzone 30.09.2026).

Na kazdy dotyk ekranu podnosi minimalny zegar klastrow do BOOST, a 1 s po
ostatnim zdarzeniu dotyku przywraca poprzednie minimum.  Jak touch boost
w Androidzie.
"""
import os
import select
import signal
import sys
import time

POLICY = '/sys/devices/system/cpu/cpufreq/policy%d/scaling_min_freq'
# policy0: 4x A55, policy4: 2x A75, policy6: 2x M4
BOOST = {0: 1456000, 4: 1794000, 6: 1820000}
TRZYMAJ_S = 1.0
URZADZENIE = 'sec_touchscreen'


def znajdz_dotyk():
    for e in sorted(os.listdir('/dev/input')):
        if not e.startswith('event'):
            continue
        try:
            with open('/sys/class/input/%s/device/name' % e) as f:
                if f.read().strip() == URZADZENIE:
                    return '/dev/input/' + e
        except OSError:
            pass
    return None


def czytaj(p):
    with open(p) as f:
        return int(f.read().strip())


def zapisz(p, v):
    try:
        with open(p, 'w') as f:
            f.write(str(v))
    except OSError as e:
        print('%s: %s' % (p, e), flush=True)


def main():
    dev = None
    while dev is None:
        dev = znajdz_dotyk()
        if dev is None:
            time.sleep(2)
    fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
    bazowe = {c: czytaj(POLICY % c) for c in BOOST}
    print('start: %s, minimum %s, podbicie %s' % (dev, bazowe, BOOST), flush=True)

    def przywroc(*_):
        for c, v in bazowe.items():
            zapisz(POLICY % c, v)
        sys.exit(0)

    signal.signal(signal.SIGTERM, przywroc)
    signal.signal(signal.SIGINT, przywroc)

    podbite = False
    ostatnio = 0.0
    while True:
        timeout = max(0.0, ostatnio + TRZYMAJ_S - time.monotonic()) if podbite else None
        r, _, _ = select.select([fd], [], [], timeout)
        if r:
            try:
                while os.read(fd, 4096):
                    pass
            except BlockingIOError:
                pass
            ostatnio = time.monotonic()
            if not podbite:
                for c, v in BOOST.items():
                    zapisz(POLICY % c, max(v, bazowe[c]))
                podbite = True
        elif podbite:
            for c, v in bazowe.items():
                zapisz(POLICY % c, v)
            podbite = False


if __name__ == '__main__':
    main()
