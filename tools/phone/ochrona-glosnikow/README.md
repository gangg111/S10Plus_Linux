# Ochrona glosnikow

Wlacza firmware CSPL obu wzmacniaczy CS35L40 z kalibracja fabryczna tego egzemplarza
i ustawia wzmocnienie jak w Androidzie. Szczegoly i pomiary: `docs/R19-dzwiek.md`.

Instalacja (na telefonie, root):

    sh zainstaluj.sh

Usluga `ochrona-glosnikow.service` startuje po karcie dzwiekowej. Sprawdzenie stanu
(tylko w trakcie odtwarzania, bo cs_dsp nie czyta kontrolek zatrzymanego DSP):

    pw-play plik.wav & sudo ochrona-glosnikow --sprawdz

Oczekiwane: `CAL_SET_STATUS=2 CSPL_STATE=0` dla Bottom i Top.

Wartosci kalibracji (`KALIBRACJA` w `ochrona.py`) sa z partycji efs TEGO telefonu.
Na innym egzemplarzu trzeba je odczytac z jego kopii (`sec_efs/cirrus`).
