# Mikrofon do rozmow: tlumienie echa i szumu

Odpowiednik przetwarzania glosu z Androida (rozmowy, VoIP, dyktowanie): WebRTC AEC
z redukcja szumu, filtrem gornoprzepustowym i automatycznym wzmocnieniem.
Odniesieniem jest monitor domyslnego wyjscia, wiec dziala dla kazdej aplikacji.
Surowy mikrofon zostaje domyslnym zrodlem dla zwyklych nagran.

Instalacja:

    sudo apk add pipewire-echo-cancel
    mkdir -p ~/.config/pipewire/pipewire.conf.d
    cp redukcja-echa.conf ~/.config/pipewire/pipewire.conf.d/
    systemctl --user restart pipewire wireplumber pipewire-pulse

W aplikacji do rozmow wybierz zrodlo "Mikrofon do rozmow (bez echa i szumu)".
Pomiar: docs/R19-dzwiek.md.
