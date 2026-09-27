#!/bin/sh
# mpv z latka HDR (tools/phone/mpv-hdr). Panfrost kafelkuje tekstury na CPU
# przy kazdym wyslaniu klatki; przy dekodowaniu programowym 4K to wiekszosc
# czasu watku vo (memcpy + kafelkowanie). Tekstury liniowe: 2160p24 HDR10+
# z 51 do 2 zgubionych klatek na 10 s, obraz identyczny. Pomiar 25.09.2026,
# measurements/2026-09-25-hdr.
export PAN_MESA_DEBUG="${PAN_MESA_DEBUG:-linear}"
exec /usr/local/libexec/mpv-hdr/mpv "$@"
