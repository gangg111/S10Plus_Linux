# Rdzenie: trzeci krok producenta nie wystarcza, PSCI wykluczone (22.09.2026)

## Co bylo sprawdzane

Czy brakujacy trzeci krok sekwencji producenta (`CLUSTER<k>_CPU<m>_INT_EN`,
bit 3) tlumaczy to, ze `echo 1 > /sys/devices/system/cpu/cpu1/online` zabija
telefon.

## Jak zmierzone

Sterownik `drivers/soc/samsung/exynos-pmu.c` dostal pelna sekwencje: obok
dwoch krokow z kodu Tensora (`GRP2_INTR_BID_ENABLE`, `GRP2_INTR_BID_CLEAR`)
zerowanie bitu 3 rejestru `CLUSTER<k>_CPU<m>_INT_EN` przy wlaczaniu rdzenia
i ustawianie go przy wylaczaniu. Offsety z makr mainline dla gs101, ktore
odtwarzaja tabele producenta co do bitu; `drivers/soc/samsung/gs101-pmu.c`
potwierdza, ze te rejestry leza w bloku jednostki zasilania.

Jadro **#41** (zbudowane 19:56) wgrane po sieci, sumy zgodne po obu stronach.

## Wynik: bez zmiany

```
jadro: #41 SMP PREEMPT Tue Sep 22 19:56:00 CEST 2026
uptime po probie: 68 s
online: 0, nproc 1
```

Telefon zresetowal sie natychmiast, tak samo jak bez tego kroku: bez jednego
bajtu od jadra, bez sladu w `pstore`, bez zmiany w `RST_STAT`.

## Co to wyklucza: niezgodnosc PSCI

Drzewo producenta (`sources/ds/exynos9820.dts:5669`) deklaruje:

```
	psci {
		compatible = "arm,psci";
		method = "smc";
		cpu_suspend = <0xc4000001>;
		cpu_off = <0x84000002>;
		cpu_on = <0xc4000003>;
	};
```

czyli **dokladnie to samo, co nasze drzewo**, i sa to standardowe numery
funkcji PSCI 0.2, nie wlasne Samsunga. Wolamy wiec to samo, co producent,
ta sama metoda i tymi samymi identyfikatorami. Hipoteza o zlym wywolaniu
SMC odpada bez potrzeby czegokolwiek wgrywania.

## Co zostaje

Zasilanie klastra. Drzewo producenta obok PSCI niesie caly wezel `cpupm`
(`sources/ds/exynos9820.dts:5677`) z osobnym zarzadzaniem zasilaniem
klastrow, wiec ich jadro **nie polega na samym PSCI**. To spina sie z runda
R16: glowny uklad zasilania tego telefonu jest osiagalny tylko przez firmware
ACPM, przez skrzynke pod `0x15900000`.

## Decyzja: poprawka wycofana

Zgodnie z zasada czystosci serii zmiana zostala **wycofana z drzewa**: nie
wolno zostawiac w serii kodu, ktory jest zgodny z dokumentacja producenta,
ale nie zmienia zachowania, bo przy nastepnej hipotezie nie wiadomo, czy brak
reakcji to jej wina, czy interakcja z nim. Tresc ponizej, zeby nie trzeba
bylo jej odtwarzac.

### Wycofana tresc

W `drivers/soc/samsung/exynos-pmu.h`, pole struktury `exynos_pmu_data`:

```c
	bool cpu_int_en;
```

W `drivers/soc/samsung/exynos-pmu.c`, przed `__gs101_cpu_pmu_online()`:

```c
static unsigned int exynos9820_cpu_int_en(unsigned int cpu)
{
	if (cpu < 4)
		return GS101_CLUSTER_CPU_INT_EN(GS101_CLUSTER0_OFFSET, cpu);
	if (cpu < 6)
		return GS101_CLUSTER_CPU_INT_EN(GS101_CLUSTER1_OFFSET, cpu - 4);

	return GS101_CLUSTER_CPU_INT_EN(GS101_CLUSTER2_OFFSET, cpu - 6);
}

#define EXYNOS9820_CPU_INT_EN_BIT	BIT(3)
```

Na koncu `__gs101_cpu_pmu_online()` (zdjecie maski) oraz, z odwrotna
wartoscia, na koncu `__gs101_cpu_pmu_offline()`:

```c
	if (pmu_context->pmu_data->cpu_int_en)
		regmap_update_bits(pmu_context->pmureg,
				   exynos9820_cpu_int_en(cpu),
				   EXYNOS9820_CPU_INT_EN_BIT, 0);
```

oraz `.cpu_int_en = true` we wpisie `exynos9820_pmu_data`.

## Uwaga o stanie telefonu

Telefon ma wgrane jadro **#41**, czyli Z tym krokiem, a drzewo jest juz bez
niego. Poniewaz krok nie zmienia zachowania, roznica jest bez znaczenia dla
pomiarow, ale przy nastepnym wgraniu jadra telefon i drzewo znow sie zejda.
