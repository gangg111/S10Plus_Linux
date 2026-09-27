"""Dwa tony naraz, -30 dBFS, 48 kHz, 16 bit: 1 kHz w lewym kanale (gorny
glosnik), 500 Hz w prawym (dolny).  Obwiednia 10 ms na brzegach."""
import math, struct, sys, wave
R, poziom, czas = 48000, 10 ** (-30 / 20), float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
n, r = int(R * czas), int(R * 0.01)
dane = bytearray()
for i in range(n):
    e = 32767 * poziom * min(1, i / r, (n - i) / r)
    dane += struct.pack('<hh', int(e * math.sin(2 * math.pi * 1000 * i / R)),
                        int(e * math.sin(2 * math.pi * 500 * i / R)))
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(R)
w.writeframes(bytes(dane)); w.close()
print('dwaton', sys.argv[1], n, 'ramek')
