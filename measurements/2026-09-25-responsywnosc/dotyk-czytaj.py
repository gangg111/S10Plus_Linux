#!/usr/bin/env python3
# Surowe zdarzenia evdev bez buforowania: czasy SYN_REPORT (s) do pliku.
# Uzycie: dotyk-czytaj.py <urzadzenie> <sekundy> <plik>
import os, select, struct, sys, time

dev, sek, wyj = sys.argv[1], float(sys.argv[2]), sys.argv[3]
fmt = 'llHHi'
rozm = struct.calcsize(fmt)
fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
koniec = time.monotonic() + sek
n = 0
with open(wyj, 'w', buffering=1) as f:
	while time.monotonic() < koniec:
		r, _, _ = select.select([fd], [], [], 0.5)
		if not r:
			continue
		try:
			dane = os.read(fd, rozm * 64)
		except BlockingIOError:
			continue
		for i in range(0, len(dane) - rozm + 1, rozm):
			s, us, typ, kod, war = struct.unpack_from(fmt, dane, i)
			if typ == 0 and kod == 0:
				f.write('%d.%06d\n' % (s, us))
				n += 1
print('raportow:', n)
