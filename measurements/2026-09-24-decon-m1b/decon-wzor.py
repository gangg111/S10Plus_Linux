import os
W, H = 1440, 3040
pasy = [0xffff0000, 0xff00ff00, 0xff0000ff, 0xffffff00, 0xffff00ff, 0xff00ffff, 0xffffffff, 0xff404040]
wiersz = bytearray()
for x in range(W):
    c = 0xff000000 if x % 180 < 4 else pasy[x * 8 // W]
    wiersz += c.to_bytes(4, 'little')
czarny = (0xff000000).to_bytes(4, 'little') * W
fd = os.open('/dev/fb0', os.O_WRONLY)
for y in range(H):
    os.pwrite(fd, bytes(czarny) if y % 190 < 4 else bytes(wiersz), y * W * 4)
os.close(fd)
print('wzor zapisany')
