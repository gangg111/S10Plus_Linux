"""Nagranie stereo 16 bit: RMS, szczyt i amplituda Goertzela na 500 Hz,
1 kHz i 2 kHz (kontrolnie) w kazdym kanale, z pominieciem pierwszych 100 ms."""
import math, struct, sys, wave
w = wave.open(sys.argv[1]); R = w.getframerate(); k = w.getnchannels()
raw = w.readframes(w.getnframes()); w.close()
s = struct.unpack('<%dh' % (len(raw) // 2), raw)
pomin = R // 10
print('plik', sys.argv[1], 'ramek', len(s) // k, 'kanalow', k, 'Hz', R)
for c in range(k):
    x = s[c::k][pomin:]
    n = len(x)
    if not n:
        print('kanal', c, 'pusty'); continue
    sr = sum(x) / n
    rms = math.sqrt(sum((v - sr) ** 2 for v in x) / n)
    wynik = []
    for f in (500, 1000, 2000):
        wsp = 2 * math.cos(2 * math.pi * f / R); q1 = q2 = 0.0
        for v in x:
            q0 = wsp * q1 - q2 + v - sr; q2 = q1; q1 = q0
        amp = 2 * math.sqrt(max(q1 * q1 + q2 * q2 - wsp * q1 * q2, 0)) / n
        wynik.append('%d Hz %.1f' % (f, amp))
    zera = sum(1 for v in x if v == 0)
    print('kanal %d (%s): srednia %.1f RMS %.1f min %d max %d zer %d/%d | %s' % (
        c, 'lewy=gorny' if c == 0 else 'prawy=dolny', sr, rms, min(x), max(x),
        zera, n, ', '.join(wynik)))
