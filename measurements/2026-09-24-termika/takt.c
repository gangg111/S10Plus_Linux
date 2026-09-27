// Pomiar realnego taktowania kazdego rdzenia bez sterownika cpufreq.
// Lancuch zaleznych ADD: opoznienie 1 cykl na A55, A75 i M4, wiec
// liczba dodawan na sekunde czasu procesora watku = czestotliwosc.
// CLOCK_THREAD_CPUTIME_ID liczy tylko czas, gdy watek naprawde chodzil,
// wiec inne obciazenie (Plasma) nie zanizy wyniku.
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <time.h>

#define A1 "add %0, %0, #1\n\t"
#define A10 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1
#define A100 A10 A10 A10 A10 A10 A10 A10 A10 A10 A10

static double teraz(void)
{
	struct timespec t;

	clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t);
	return t.tv_sec + t.tv_nsec * 1e-9;
}

int main(void)
{
	for (int c = 0; c < 8; c++) {
		cpu_set_t s;
		unsigned long x = 0;
		const long n = 2000000;
		double best = 1e9;

		CPU_ZERO(&s);
		CPU_SET(c, &s);
		if (sched_setaffinity(0, sizeof(s), &s)) {
			printf("cpu%d niedostepny\n", c);
			continue;
		}
		for (long i = 0; i < n / 10; i++)
			asm volatile(A100 : "+r"(x));
		for (int r = 0; r < 5; r++) {
			double t0 = teraz();

			for (long i = 0; i < n; i++)
				asm volatile(A100 : "+r"(x));
			double t = teraz() - t0;
			if (t < best)
				best = t;
		}
		printf("cpu%d (na cpu%d) %.0f MHz\n", c, sched_getcpu(),
		       n * 100.0 / best / 1e6);
	}
	return 0;
}
