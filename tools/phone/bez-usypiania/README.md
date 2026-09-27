# Bez usypiania

Uspienie (s2idle) zabija pamiec UFS: po wybudzeniu nie wraca i rootfs przechodzi w tryb
tylko do odczytu.  Dlatego usypianie jest wylaczone na kazdym poziomie:

- cele systemd sleep/suspend/hibernate zamaskowane,
- sleep.conf.d: wszystkie rodzaje uspienia wylaczone (logind CanSuspend nie daje "yes"),
- logind.conf.d: klawisze uspienia, zamkniecie etui i bezczynnosc ignorowane,
- powerdevilrc: brak automatycznego usypiania po bezczynnosci w kazdym profilu,
- PowerDevil z latka (tools/pmos/powerdevil): pole "Suspend device after" w ustawieniach
  zasilania znika, gdy uspienie jest niemozliwe; bez latki to pole nic nie robi.

Instalacja: sh zainstaluj.sh

PowerDevil osobno: budowa w WSL `pmbootstrap -y --no-cross build --arch aarch64 powerdevil`
(przepis skopiowany do pmaports/temp/powerdevil), na telefonie
`sudo apk add --allow-untrusted ./powerdevil*-6.7.5-r100.apk`. Wersja r100 wygrywa z r1
z repozytorium, ale nowsza wersja PowerDevil (6.7.6 i dalej) przy `apk upgrade` zastapi
paczke i pole wroci; wtedy przepis trzeba przeniesc na nowe zrodla.
