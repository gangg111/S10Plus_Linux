# Protokol dotyku przed i po poprawkach 0093 i 0094

Jadro `#38` (przed) kontra `#39` (po), ten sam telefon, ta sama sonda
`tools/klawiatura/sonda-osi`.

|  | przed | po |
|---|---|---|
| `ABS_MT_TRACKING_ID` w strumieniu | BRAK | JEST |
| zwolnienie sladu (`-1`) | BRAK | JEST |
| `BTN_TOUCH` wcisniecie | BRAK | JEST |
| `BTN_TOUCH` zwolnienie | BRAK | JEST |
| sloty przy nietknietym ekranie | 0:12 1:7 2:10 zajete | wszystkie 17 wolne |

Sloty odczytane wprost z jadra przez `EVIOCGMTSLOTS`, nie ze strumienia:
identyfikator sladu wysylany jest tylko przy przejsciu slotu z wolnego na
zajety, wiec slot zawieszony na stale wyglada w strumieniu tak samo jak
sterownik, ktory identyfikatorow nie wysyla wcale.
