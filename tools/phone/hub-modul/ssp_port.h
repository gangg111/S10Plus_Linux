/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Warstwa portu: odpowiedniki infrastruktury Samsunga, ktorej nie ma
 * w mainline 7.2 (sec_class, initcalle kilku sterownikow w jednym
 * module, parametry z linii polecen).
 */
#ifndef _SSP_PORT_H_
#define _SSP_PORT_H_

#include <linux/device.h>
#include <linux/pm_wakeup.h>

/* /sys/class/sec/<name>, zamiennik ssp_sec_device_create() (sec_class.c) */
struct device *ssp_sec_device_create(void *drvdata, const char *name);
void ssp_sec_device_destroy(struct device *dev);

/* zamiennik wake_lock_active() z API wakelockow Androida */
static inline bool ssp_ws_active(struct wakeup_source *ws)
{
	return ws && ws->active;
}

/*
 * Odczyt "klucz=liczba" z /chosen/bootargs (w module nie ma
 * early_param ani __setup). 0 = znaleziono, <0 = brak.
 */
int ssp_port_cmdline_int(const char *key, int *val);

/* dawne initcalle, teraz wolane z ssp_port.c */
int sensors_class_init(void);
void sensors_class_exit(void);
int bcm_spi_init(void);
void bcm_spi_exit(void);
#ifdef CONFIG_BCM_GPS_HOSTWAKE_DRIVER
int gps_hostwake_init(void);
void gps_hostwake_exit(void);
#endif

/*
 * Funkcje producenta wolane miedzy plikami, dotad bez prototypu
 * (W=1 -Wmissing-prototypes). Sygnatury skopiowane z definicji.
 */
struct decimal_point;
struct device;
struct device_attribute;
struct ois_sensor_interface;
struct remove_af_noise;
struct ssp_data;
/* bbdpl/bbd.c */
s64 get_sensor_time_delta_us(void);
ssize_t bbd_request_mcu(bool on);
ssize_t bbd_sensor_write(const char *buf, size_t size);
/* bbdpl/bbd_rpc_lh.c */
void bbd_parse_asic_data(unsigned char *pucData, unsigned short usLen, void (*to_gpsd)(unsigned char *packet, unsigned short len, void *priv), void *priv);
/* bbdpl/bcm_gps_spi.c */
void bcm_on_packet_received(void *_priv, unsigned char *data, unsigned int size);
/* factory/light_tmg399x.c */
void set_decimal_point(struct decimal_point* dp, int i, int p);
/* sensors_core.c */
int sensors_register(struct device *dev, void *drvdata, struct device_attribute *attributes[], char *name);
void destroy_sensor_class(void);
void sensors_unregister(struct device * const dev, struct device_attribute *attributes[]);
/* ssp_data.c */
u64 get_leveling_timestamp(u64 timestamp, struct ssp_data *data, u64 time_delta, int sensor_type);
void handle_timestamp_sync(struct ssp_data *data, char *pchRcvDataFrame, int *index);
/* ssp_dev.c */
int ois_fw_update_register(struct ois_sensor_interface *ois);
int ois_reset_register(struct ois_sensor_interface *ois);
void ois_fw_update_unregister(void);
void ois_reset_unregister(void);
/* ssp_misc.c */
int remove_af_noise_register(struct remove_af_noise *af_cam);
void remove_af_noise_unregister(struct remove_af_noise *af_cam);

#endif /* _SSP_PORT_H_ */
