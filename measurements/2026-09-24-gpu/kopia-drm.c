// Ile kosztuje simpledrm przeniesienie klatki z bufora do framebuffera:
// bufor dumb XR24 na calym ekranie, DirtyFB z pelnym obszarem, czas scienny
// kazdego wywolania (DirtyFB robi zatwierdzenie z blokowaniem, wiec wraca
// dopiero po skopiowaniu).  Wymaga mistrza DRM, czyli zatrzymanego KWin.
// Uzycie: kopia-drm [powtorzenia] [wysokosc_obszaru]
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <xf86drm.h>
#include <xf86drmMode.h>
#include <drm_fourcc.h>

static double teraz(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1e3 + t.tv_nsec * 1e-6;
}

static int por(const void *a, const void *b)
{
	double x = *(const double *)a, y = *(const double *)b;

	return (x > y) - (x < y);
}

int main(int argc, char **argv)
{
	int n = argc > 1 ? atoi(argv[1]) : 30;
	int fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
	drmModeRes *res;
	drmModeConnector *con = NULL;
	struct drm_mode_create_dumb cd = { 0 };
	struct drm_mode_map_dumb md = { 0 };
	uint32_t fb, uchwyty[4] = { 0 }, pitch[4] = { 0 }, off[4] = { 0 };
	unsigned char *p;
	double *t;

	if (fd < 0 || drmSetMaster(fd)) {
		perror("card0 / mistrz");
		return 1;
	}
	res = drmModeGetResources(fd);
	for (int i = 0; i < res->count_connectors && !con; i++) {
		con = drmModeGetConnector(fd, res->connectors[i]);
		if (con && con->connection != DRM_MODE_CONNECTED) {
			drmModeFreeConnector(con);
			con = NULL;
		}
	}
	if (!con || !con->count_modes)
		return 1;
	drmModeModeInfo m = con->modes[0];
	int wys = argc > 2 ? atoi(argv[2]) : m.vdisplay;

	cd.width = m.hdisplay;
	cd.height = m.vdisplay;
	cd.bpp = 32;
	if (drmIoctl(fd, DRM_IOCTL_MODE_CREATE_DUMB, &cd))
		return 1;
	uchwyty[0] = cd.handle;
	pitch[0] = cd.pitch;
	if (drmModeAddFB2(fd, m.hdisplay, m.vdisplay, DRM_FORMAT_XRGB8888, uchwyty, pitch, off, &fb, 0))
		return 1;
	md.handle = cd.handle;
	drmIoctl(fd, DRM_IOCTL_MODE_MAP_DUMB, &md);
	p = mmap(NULL, cd.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, md.offset);
	for (size_t i = 0; i < cd.size; i++)
		p[i] = (i / 4 / 1440 * 7 + i) & 0xff;
	if (drmModeSetCrtc(fd, res->crtcs[0], fb, 0, 0, &con->connector_id, 1, &m))
		return 1;

	drmModeClip c = { 0, 0, m.hdisplay, wys };
	t = calloc(n, sizeof(*t));
	for (int i = 0; i < n; i++) {
		double a = teraz();

		if (drmModeDirtyFB(fd, fb, &c, 1)) {
			perror("DirtyFB");
			return 1;
		}
		t[i] = teraz() - a;
	}
	qsort(t, n, sizeof(*t), por);
	printf("obszar %dx%d (%.1f MB): mediana %.2f ms, min %.2f, max %.2f, n=%d\n",
	       m.hdisplay, wys, m.hdisplay * wys * 4 / 1048576.0, t[n / 2], t[0], t[n - 1], n);
	return 0;
}
