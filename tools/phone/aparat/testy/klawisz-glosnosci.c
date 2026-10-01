// Wirtualna klawiatura (uinput): jedno nacisniecie i puszczenie KEY_VOLUMEUP albo
// KEY_VOLUMEDOWN. Kompozytor dostaje to jak z przycisku; aparat nie (czyta gpio_keys).
// Uzycie (root): klawisz-glosnosci up|down
#include <fcntl.h>
#include <linux/uinput.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void emit(int fd, int type, int code, int value)
{
	struct input_event ev;
	memset(&ev, 0, sizeof(ev));
	ev.type = type;
	ev.code = code;
	ev.value = value;
	if (write(fd, &ev, sizeof(ev)) != sizeof(ev))
		perror("write");
}

int main(int argc, char **argv)
{
	const int key = argc > 1 && !strcmp(argv[1], "down") ? KEY_VOLUMEDOWN : KEY_VOLUMEUP;
	int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
	if (fd < 0) {
		perror("/dev/uinput");
		return 1;
	}
	ioctl(fd, UI_SET_EVBIT, EV_KEY);
	ioctl(fd, UI_SET_KEYBIT, KEY_VOLUMEUP);
	ioctl(fd, UI_SET_KEYBIT, KEY_VOLUMEDOWN);
	struct uinput_setup us;
	memset(&us, 0, sizeof(us));
	us.id.bustype = BUS_VIRTUAL;
	strcpy(us.name, "s10-test-glosnosc");
	ioctl(fd, UI_DEV_SETUP, &us);
	ioctl(fd, UI_DEV_CREATE);
	sleep(2); // libinput i kompozytor musza zobaczyc nowe urzadzenie
	emit(fd, EV_KEY, key, 1);
	emit(fd, EV_SYN, SYN_REPORT, 0);
	usleep(80000);
	emit(fd, EV_KEY, key, 0);
	emit(fd, EV_SYN, SYN_REPORT, 0);
	sleep(1);
	ioctl(fd, UI_DEV_DESTROY);
	close(fd);
	return 0;
}
