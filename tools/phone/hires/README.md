# Hi-res w PipeWire

Port kodeka (sluchawki, mikrofony) przyjmuje 48, 96 i 192 kHz (latka 0140). Ten plik
pozwala PipeWire przelaczyc graf na czestotliwosc odtwarzanego pliku.

Instalacja (jako uzytkownik):

    mkdir -p ~/.config/pipewire/pipewire.conf.d
    cp hires.conf ~/.config/pipewire/pipewire.conf.d/
    systemctl --user restart pipewire wireplumber pipewire-pulse

Sprawdzenie: plik 96 kHz na sluchawki, `grep rate /proc/asound/card0/pcm1p/sub0/hw_params`
ma dac 96000; na glosnikach pcm0p zostaje 48000.
