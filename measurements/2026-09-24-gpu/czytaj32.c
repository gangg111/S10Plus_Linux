// Odczyt 32-bitowych slow z /dev/mem, tylko do odczytu (O_RDONLY, PROT_READ).
// Uzycie: czytaj32 ADRES [ADRES...]
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	long strona = sysconf(_SC_PAGESIZE);
	int fd = open("/dev/mem", O_RDONLY | O_SYNC);

	if (fd < 0) {
		perror("/dev/mem");
		return 1;
	}
	for (int i = 1; i < argc; i++) {
		unsigned long a = strtoul(argv[i], NULL, 0);
		unsigned long baza = a & ~(strona - 1);
		volatile uint32_t *m = mmap(NULL, strona, PROT_READ, MAP_SHARED, fd, baza);

		if (m == MAP_FAILED) {
			perror("mmap");
			return 1;
		}
		printf("0x%08lx = 0x%08x\n", a, m[(a - baza) / 4]);
		munmap((void *)m, strona);
	}
	close(fd);
	return 0;
}
