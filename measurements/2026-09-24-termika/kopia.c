// Ile kosztuje skopiowanie jednej klatki 1440x3040x4 (tyle simpledrm kopiuje
// przy pelnym odswiezeniu) na wybranym rdzeniu.  Czas scienny, najlepszy z 20.
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define KLATKA (1440 * 3040 * 4)

static double teraz(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec + t.tv_nsec * 1e-9;
}

int main(int argc, char **argv)
{
	char *a = malloc(KLATKA), *b = malloc(KLATKA);

	if (!a || !b)
		return 1;
	memset(a, 1, KLATKA);
	memset(b, 2, KLATKA);
	for (int i = 1; i < argc; i++) {
		int c = atoi(argv[i]);
		cpu_set_t s;
		double best = 1e9;

		CPU_ZERO(&s);
		CPU_SET(c, &s);
		if (sched_setaffinity(0, sizeof(s), &s))
			continue;
		for (int r = 0; r < 20; r++) {
			double t0 = teraz();

			memcpy(b, a, KLATKA);
			double t = teraz() - t0;
			if (t < best)
				best = t;
			a[r] = b[KLATKA - 1 - r];
		}
		printf("cpu%d: klatka %.2f ms, %.2f GB/s kopii\n", c, best * 1e3,
		       KLATKA / best / 1e9);
	}
	return 0;
}
