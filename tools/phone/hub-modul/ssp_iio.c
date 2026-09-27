/*
 *  Copyright (C) 2012, Samsung Electronics Co. Ltd. All Rights Reserved.
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 */
#include "ssp.h"
#include "ssp_iio.h"
#include "ssp_sensorhub.h"
#include <linux/string.h>
#include <linux/iio/iio.h>
#include <linux/iio/sysfs.h>
#include <linux/iio/events.h>
#include <linux/iio/buffer.h>
#include <linux/iio/buffer_impl.h>
#include <linux/iio/types.h>
#include <linux/iio/kfifo_buf.h>

static struct sensor_info info_table[] = {
	SENSOR_INFO_ACCELEROMETER,
	SENSOR_INFO_GEOMAGNETIC,
	SENSOR_INFO_GEOMAGNETIC_POWER,
	SENSOR_INFO_GEOMAGNETIC_UNCAL,
	SENSOR_INFO_GYRO,
	SENSOR_INFO_GYRO_UNCALIBRATED,
	SENSOR_INFO_INTERRUPT_GYRO,
	SENSOR_INFO_PRESSURE,
	SENSOR_INFO_LIGHT,
	SENSOR_INFO_LIGHT_IR,
	SENSOR_INFO_LIGHT_FLICKER,
	SENSOR_INFO_PROXIMITY,
	SENSOR_INFO_PROXIMITY_ALERT,
	SENSOR_INFO_PROXIMITY_RAW,
	SENSOR_INFO_ROTATION_VECTOR,
	SENSOR_INFO_GAME_ROTATION_VECTOR,
	SENSOR_INFO_SIGNIFICANT_MOTION,
	SENSOR_INFO_STEP_DETECTOR,
	SENSOR_INFO_STEP_COUNTER,
	SENSOR_INFO_TILT_DETECTOR,
	SENSOR_INFO_PICK_UP_GESTURE,
	SENSOR_INFO_SCONTEXT,
	SENSOR_INFO_LIGHT_CCT,
	SENSOR_INFO_THERMISTOR,
	SENSOR_INFO_PROXIMITY_POCKET,
	SENSOR_INFO_ACCEL_UNCALIBRATED,
	SENSOR_INFO_META,
	SENSOR_INFO_WAKE_UP_MOTION,
	SENSOR_INFO_MOVE_DETECTOR,
	SENSOR_INFO_CALL_GESTURE,
	SENSOR_INFO_PROXIMITY_ADC_CALIB,
	SENSOR_INFO_UNCAL_LIGHT,
	SENSOR_INFO_POCKET_MODE,
	SENSOR_INFO_LED_COVER_EVENT,
	SENSOR_INFO_AUTO_ROTATION,
	SENSOR_INFO_SAR_BACKOFF_MOTION,
};

#define IIO_ST(si, rb, sb, sh)	\
	{ .sign = si, .realbits = rb, .storagebits = sb, .shift = sh }

int info_table_size =  sizeof(info_table)/sizeof(struct sensor_info);

/*
 * Port: iio_dev->mlock jest w mainline prywatny (iio_dev_opaque). Zapisy
 * do buforow serializuje jeden wlasny mutex.
 */
static DEFINE_MUTEX(ssp_iio_push_lock);
#define SSP_IIO_PUSH_MAX	256

static struct sensor_info sensors_info[SENSOR_MAX];
static struct iio_chan_spec indio_channels[SENSOR_MAX];

static const struct iio_info indio_info = {
};
static int initialize_iio_buffer_and_device(struct iio_dev *indio_dev, struct ssp_data *data)
{
	int iRet = 0;

	iRet = ssp_iio_configure_ring(indio_dev);
	if (iRet)
		goto err_config_ring_buffer;

	iRet = iio_device_register(indio_dev);
	if (iRet)
		goto err_register_device;

	iio_device_set_drvdata(indio_dev, data);

	return iRet;

err_register_device:
	pr_err("[SSP]: failed to register %s device\n", indio_dev->name);
	iio_device_unregister(indio_dev);
err_config_ring_buffer:
	pr_err("[SSP]: failed to configure %s buffer\n", indio_dev->name);
	ssp_iio_unconfigure_ring(indio_dev);

	return iRet;
}

static int ssp_push_iio_buffer(struct iio_dev *indio_dev, u64 timestamp, u8 *data, int data_len)
{
	/*
	 * Port: VLA zastapiona stala tablica (W=1 -Wvla-larger-than). Najwiekszy
	 * rekord to scontext 64 B + 8 B czasu; zera chronia przed odczytem poza
	 * danymi, gdy bytes_per_datum kanalu jest wiekszy niz data_len + 8.
	 */
	u8 buf[SSP_IIO_PUSH_MAX] = {0};
	int iRet = 0, retry = 3;

	if (data_len < 0 || data_len + sizeof(timestamp) > sizeof(buf)) {
		pr_err("[SSP] %s - %s: data_len %d too big\n", __func__, indio_dev->name, data_len);
		return -EINVAL;
	}
	memcpy(buf, data, data_len);
	memcpy(&buf[data_len], &timestamp, sizeof(timestamp));

	mutex_lock(&ssp_iio_push_lock);

	do {
		if(retry != 3)
			usleep_range(150, 151);

		iRet = iio_push_to_buffers(indio_dev, buf);
	} while(iRet < 0 && retry-- > 0);

	if(retry == 0 && iRet < 0)
		pr_err("[SSP] %s - %s push fail erro %d", __func__, indio_dev->name, iRet);

	mutex_unlock(&ssp_iio_push_lock);

	return 0;
}

void report_meta_data(struct ssp_data *data, int sensor_type, struct sensor_value *s)
{
	pr_info("[SSP]: %s - what: %d, sensor: %d\n", __func__,
		s->meta_data.what, s->meta_data.sensor);

	if (s->meta_data.sensor == ACCELEROMETER_SENSOR) {
		s16 accel_buf[3];

		memset(accel_buf, 0, sizeof(s16) * 3);
		ssp_push_iio_buffer(data->indio_dev[ACCELEROMETER_SENSOR], 0, (u8 *)accel_buf, sizeof(accel_buf));
	} else if (s->meta_data.sensor == GYROSCOPE_SENSOR) {
		int gyro_buf[3];

		memset(gyro_buf, 0, sizeof(int) * 3);
		ssp_push_iio_buffer(data->indio_dev[GYROSCOPE_SENSOR], 0, (u8 *)gyro_buf, sizeof(gyro_buf));
	} else if (s->meta_data.sensor == GYRO_UNCALIB_SENSOR) {
		s32 uncal_gyro_buf[6];

		memset(uncal_gyro_buf, 0, sizeof(uncal_gyro_buf));
		ssp_push_iio_buffer(data->indio_dev[GYRO_UNCALIB_SENSOR], 0, (u8 *)uncal_gyro_buf, sizeof(uncal_gyro_buf));
	} else if (s->meta_data.sensor == GEOMAGNETIC_SENSOR) {
		u8 mag_buf[8];

		memset(mag_buf, 0, sizeof(mag_buf));
		ssp_push_iio_buffer(data->indio_dev[GEOMAGNETIC_SENSOR], 0, (u8 *)mag_buf, sizeof(mag_buf));
	} else if (s->meta_data.sensor == GEOMAGNETIC_UNCALIB_SENSOR) {
		u8 uncal_mag_buf[13];

		memset(uncal_mag_buf, 0, sizeof(uncal_mag_buf));
		ssp_push_iio_buffer(data->indio_dev[GEOMAGNETIC_UNCALIB_SENSOR], 0, (u8 *)uncal_mag_buf, sizeof(uncal_mag_buf));
	} else if (s->meta_data.sensor == PRESSURE_SENSOR) {
		int pressure_buf[3];

		memset(pressure_buf, 0, sizeof(int) * 3);
		ssp_push_iio_buffer(data->indio_dev[PRESSURE_SENSOR], 0, (u8 *)pressure_buf, sizeof(pressure_buf));
	} else if (s->meta_data.sensor == ROTATION_VECTOR) {
		int rot_buf[5];

		memset(rot_buf, 0, sizeof(int) * 5);
		ssp_push_iio_buffer(data->indio_dev[ROTATION_VECTOR], 0, (u8 *)rot_buf, sizeof(rot_buf));
	} else if (s->meta_data.sensor == GAME_ROTATION_VECTOR) {
		int grot_buf[5];

		memset(grot_buf, 0, sizeof(int) * 5);
		ssp_push_iio_buffer(data->indio_dev[GAME_ROTATION_VECTOR], 0, (u8 *)grot_buf, sizeof(grot_buf));
	} else if (s->meta_data.sensor == STEP_DETECTOR) {
		u8 step_buf[1] = {0};

		ssp_push_iio_buffer(data->indio_dev[STEP_DETECTOR], 0, (u8 *)step_buf, sizeof(step_buf));
	} else {
		ssp_push_iio_buffer(data->meta_indio_dev, 0, (u8 *)(&s->meta_data), 8);
	}
}

static void report_iio_data(struct ssp_data *data, int type, struct sensor_value *sensor_data)
{
	memcpy(&data->buf[type], sensor_data, sensors_info[type].get_data_len);
	ssp_push_iio_buffer(data->indio_dev[type], sensor_data->timestamp, (u8 *)(&data->buf[type]), sensors_info[type].report_data_len);
}

void report_acc_data(struct ssp_data *data, int sensor_type, struct sensor_value *accdata)
{
	//this exception is for CTS suspend test
	if ((accdata->x != 0 || accdata->y != 0 || accdata->z != 0)
			&& accdata->timestamp == 0)
		return;
	report_iio_data(data, ACCELEROMETER_SENSOR, accdata);
}

void report_gyro_data(struct ssp_data *data, int sensor_type, struct sensor_value *gyrodata)
{
	report_iio_data(data, GYROSCOPE_SENSOR, gyrodata);
}

void report_interrupt_gyro_data(struct ssp_data *data, int sensor_type, struct sensor_value *gyrodata)
{
	report_iio_data(data, INTERRUPT_GYRO_SENSOR, gyrodata);
}

void report_geomagnetic_raw_data(struct ssp_data *data, int sensor_type, struct sensor_value *magrawdata)
{
	data->buf[GEOMAGNETIC_RAW].x = magrawdata->x;
	data->buf[GEOMAGNETIC_RAW].y = magrawdata->y;
	data->buf[GEOMAGNETIC_RAW].z = magrawdata->z;
}

void report_mag_data(struct ssp_data *data, int sensor_type, struct sensor_value *magdata)
{
	report_iio_data(data, GEOMAGNETIC_SENSOR, magdata);
}

void report_mag_uncaldata(struct ssp_data *data, int sensor_type, struct sensor_value *magdata)
{
	report_iio_data(data, GEOMAGNETIC_UNCALIB_SENSOR, magdata);
}

void report_uncalib_gyro_data(struct ssp_data *data, int sensor_type, struct sensor_value *gyrodata)
{
	report_iio_data(data, GYRO_UNCALIB_SENSOR, gyrodata);
}

void report_sig_motion_data(struct ssp_data *data, int sensor_type,
	struct sensor_value *sig_motion_data)
{
	report_iio_data(data, SIG_MOTION_SENSOR, sig_motion_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
}

void report_rot_data(struct ssp_data *data, int sensor_type, struct sensor_value *rotdata)
{
	report_iio_data(data, ROTATION_VECTOR, rotdata);
}

void report_game_rot_data(struct ssp_data *data, int sensor_type, struct sensor_value *grvec_data)
{
	report_iio_data(data, GAME_ROTATION_VECTOR, grvec_data);
}

void report_pressure_data(struct ssp_data *data, int sensor_type, struct sensor_value *predata)
{
	int temp[3] = {0, };

	data->buf[PRESSURE_SENSOR].pressure =
		predata->pressure - data->iPressureCal;
	data->buf[PRESSURE_SENSOR].temperature = predata->temperature;

	temp[0] = data->buf[PRESSURE_SENSOR].pressure;
	temp[1] = data->buf[PRESSURE_SENSOR].temperature;
	temp[2] = data->sealevelpressure;

	ssp_push_iio_buffer(data->indio_dev[PRESSURE_SENSOR], predata->timestamp, (u8 *)temp, sizeof(temp));
}

#if defined(CONFIG_SENSORS_SABC)
void report_light_data(struct ssp_data *data,int sensor_type, struct sensor_value *lightdata)
{
	if (!data->camera_lux_en &&
			(lightdata->light_t.lux <= 100) &&
			(data->brightness >= 77))
	{
		if (data->light_log_cnt == 0)
		{
			pr_info("[SSP]: Light AB Sensor : report first lux form light sensor");
			report_camera_lux_data(data, lightdata->light_t.lux);
		}
		data->camera_lux_en	= true;
		lightdata->light_t.lux = CAMERA_LUX_ENABLE;
	} else if (data->camera_lux_en &&
		((lightdata->light_t.lux >= 150) ||
		(data->brightness	< 77)))	{
		pr_info("[SSP]: Light AB Sensor : report cam disable");
		data->camera_lux_en	= false;
		lightdata->light_t.lux = CAMERA_LUX_DISABLE;
		if (data->brightness < 77)
			pr_info("[SSP]: Light AB Sensor at low brightness: report cam disable");
		else
			data->pre_camera_lux = CAM_LUX_INITIAL;
	} else if (data->camera_lux_en == false && data->pre_camera_lux != CAM_LUX_INITIAL) {
		pr_info("[SSP]: when first lux after sABC precamlux : %d lightlux : %d",
		data->pre_camera_lux, lightdata->light_t.lux);
		if (data->pre_camera_lux >= (50 + lightdata->light_t.lux) ||
			lightdata->light_t.lux >= (data->pre_camera_lux + 50)) {
			lightdata->light_t.lux = (lightdata->light_t.lux + data->pre_camera_lux)/2;
			pr_info("[SSP] sABC_average_value %d", lightdata->light_t.lux);
		}
		data->pre_camera_lux = CAM_LUX_INITIAL;
	} else if (data->camera_lux_en)
		return;

	report_iio_data(data, sensor_type, lightdata);
	if (data->light_log_cnt < 3) {
		ssp_dbg("[SSP] #>UL lux=%u cct=%d r=%d g=%d b=%d c=%d atime=%d again=%d",
			data->buf[sensor_type].light_t.lux, data->buf[sensor_type].light_t.cct,
			data->buf[sensor_type].light_t.r, data->buf[sensor_type].light_t.g, data->buf[sensor_type].light_t.b,
			data->buf[sensor_type].light_t.w, data->buf[sensor_type].light_t.a_time, data->buf[sensor_type].light_t.a_gain);

		data->light_log_cnt++;
	}
}

void report_uncal_light_data(struct ssp_data *data,int sensor_type, struct sensor_value *lightdata)
{
	report_iio_data(data, sensor_type, lightdata);
	if (data->light_log_cnt < 3) {
		ssp_dbg("[SSP] #>UL lux=%u cct=%d r=%d g=%d b=%d c=%d atime=%d again=%d",
			data->buf[sensor_type].light_t.lux, data->buf[sensor_type].light_t.cct,
			data->buf[sensor_type].light_t.r, data->buf[sensor_type].light_t.g, data->buf[sensor_type].light_t.b,
			data->buf[sensor_type].light_t.w, data->buf[sensor_type].light_t.a_time, data->buf[sensor_type].light_t.a_gain);

		data->light_log_cnt++;
	}
}

void report_camera_lux_data(struct ssp_data *data, int cur_lux)
{
	int report_lux;
	pr_info("[SSP]: %s: prelux :%d  curlux :%d", __func__,data->pre_camera_lux,cur_lux);
	if (data->pre_camera_lux == CAM_LUX_INITIAL)
		report_lux = cur_lux;
	else
		report_lux = (cur_lux + data->pre_camera_lux)/2;
	if (cur_lux > -1)
		data->pre_camera_lux = cur_lux;
	data->buf[LIGHT_SENSOR].light_t.lux = report_lux;
	ssp_push_iio_buffer(data->indio_dev[LIGHT_SENSOR], get_current_timestamp(),
	                     (char *)&data->buf[LIGHT_SENSOR], sensors_info[LIGHT_SENSOR].report_data_len);
}
#else
void report_light_data(struct ssp_data *data, int sensor_type, struct sensor_value *lightdata)
{
	report_iio_data(data, sensor_type, lightdata);
	if (data->light_log_cnt < 8) {
		char *header = sensor_type == UNCAL_LIGHT_SENSOR ? "#>UL" : "#>L";
#ifdef CONFIG_SENSORS_SSP_LIGHT_REPORT_LUX
#ifdef CONFIG_SENSORS_SSP_LIGHT_ADDING_LUMINANCE
		ssp_dbg("[SSP] %s lux=%u cct=%d r=%d g=%d b=%d c=%d atime=%d again=%d brightness=%d",
			header, data->buf[sensor_type].lux, data->buf[sensor_type].cct,
			data->buf[sensor_type].r, data->buf[sensor_type].g, data->buf[sensor_type].b,
			data->buf[sensor_type].w, data->buf[sensor_type].a_time, data->buf[sensor_type].a_gain,
			data->buf[sensor_type].brightness);
#else
		ssp_dbg("[SSP] %s lux=%u cct=%d r=%d g=%d b=%d c=%d atime=%d again=%d",
			header, data->buf[sensor_type].lux, data->buf[sensor_type].cct,
			data->buf[sensor_type].r, data->buf[sensor_type].g, data->buf[sensor_type].b,
			data->buf[sensor_type].w, data->buf[sensor_type].a_time, data->buf[sensor_type].a_gain);
#endif
#else
		ssp_dbg("[SSP] %s r=%d g=%d b=%d c=%d atime=%d again=%d",
			header, data->buf[sensor_type].r, data->buf[sensor_type].g, data->buf[sensor_type].b,
			data->buf[sensor_type].w, data->buf[sensor_type].a_time, data->buf[sensor_type].a_gain);
#endif
		data->light_log_cnt++;
	}
}
#endif

#ifdef CONFIG_SENSORS_SSP_IRDATA_FOR_CAMERA
void report_light_ir_data(struct ssp_data *data, int sensor_type, struct sensor_value *lightirdata)
{
	report_iio_data(data, LIGHT_IR_SENSOR, lightirdata);

	if (data->light_ir_log_cnt < 3) {
		ssp_dbg("[SSP]#>IR irdata=%d r=%d g=%d b=%d c=%d atime/brightness_level=%d again=%d \n",
			data->buf[LIGHT_IR_SENSOR].irdata, data->buf[LIGHT_IR_SENSOR].ir_r, data->buf[LIGHT_IR_SENSOR].ir_g,
			data->buf[LIGHT_IR_SENSOR].ir_b, data->buf[LIGHT_IR_SENSOR].ir_w, data->buf[LIGHT_IR_SENSOR].ir_a_time,
			data->buf[LIGHT_IR_SENSOR].ir_a_gain);
		data->light_ir_log_cnt++;
	}

}
#endif
void report_light_cct_data(struct ssp_data *data, int sensor_type, struct sensor_value *lightdata)
{
	report_iio_data(data, LIGHT_CCT_SENSOR, lightdata);

	if (data->light_cct_log_cnt< 3) {
#ifdef CONFIG_SENSORS_SSP_LIGHT_REPORT_LUX
#ifdef CONFIG_SENSORS_SSP_LIGHT_LUX_RAW
		ssp_dbg("[SSP] #>CCT lux=%u cct=%d r=%d g=%d b=%d c=%d atime=%d again=%d lux_raw=%d",
			data->buf[LIGHT_CCT_SENSOR].lux, data->buf[LIGHT_CCT_SENSOR].cct,
			data->buf[LIGHT_CCT_SENSOR].r, data->buf[LIGHT_CCT_SENSOR].g, data->buf[LIGHT_CCT_SENSOR].b,
			data->buf[LIGHT_CCT_SENSOR].w, data->buf[LIGHT_CCT_SENSOR].a_time, data->buf[LIGHT_CCT_SENSOR].a_gain,
			data->buf[LIGHT_CCT_SENSOR].lux_raw);
#else
	ssp_dbg("[SSP] #>CCT lux=%u cct=%d r=%d g=%d b=%d c=%d atime=%d again=%d",
			data->buf[LIGHT_CCT_SENSOR].lux, data->buf[LIGHT_CCT_SENSOR].cct,
			data->buf[LIGHT_CCT_SENSOR].r, data->buf[LIGHT_CCT_SENSOR].g, data->buf[LIGHT_CCT_SENSOR].b,
			data->buf[LIGHT_CCT_SENSOR].w, data->buf[LIGHT_CCT_SENSOR].a_time, data->buf[LIGHT_CCT_SENSOR].a_gain);

#endif
#else
		ssp_dbg("[SSP] #>CCT r=%d g=%d b=%d c=%d atime=%d again=%d",
			data->buf[LIGHT_CCT_SENSOR].r, data->buf[LIGHT_CCT_SENSOR].g, data->buf[LIGHT_CCT_SENSOR].b,
			data->buf[LIGHT_CCT_SENSOR].w, data->buf[LIGHT_CCT_SENSOR].a_time, data->buf[LIGHT_CCT_SENSOR].a_gain);
#endif
		data->light_cct_log_cnt++;
	}
}

void report_light_flicker_data(struct ssp_data *data, int sensor_type, struct sensor_value *lightFlickerData)
{
	report_iio_data(data, LIGHT_FLICKER_SENSOR, lightFlickerData);
}

static unsigned int prox_near = 3200;
module_param(prox_near, uint, 0644);
MODULE_PARM_DESC(prox_near, "proximity ADC count from which an object is near");

/*
 * A hand moving over the sensor makes the hub report far and near again
 * within a second (measured: far at 3835, near 0.94 s later), which would
 * light the screen at the ear during a call.  Going near takes effect at
 * once; going far only once far has held for prox_far_ms.
 */
static unsigned int prox_far_ms = 1500;
module_param(prox_far_ms, uint, 0644);
MODULE_PARM_DESC(prox_far_ms, "time far must hold after near before it is reported, in ms");

static bool prox_was_near;
static bool prox_far_pending;
static unsigned long prox_far_at;

void report_prox_data(struct ssp_data *data, int sensor_type, struct sensor_value *proxdata)
{
	u32 ts_high, ts_low;

        usleep_range(500, 1000);

	report_iio_data(data, PROXIMITY_SENSOR, proxdata);
	prox_far_pending = prox_was_near && proxdata->prox_detect == 0;
	if (prox_far_pending)
		prox_far_at = jiffies;
	prox_was_near = proxdata->prox_detect == 1 ||
		(proxdata->prox_detect != 0 && proxdata->prox_adc >= prox_near);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));

        ts_high = (u32)((proxdata->timestamp)>>32);
        ts_low = (u32)((proxdata->timestamp)&0x00000000ffffffff);
#if defined(CONFIG_SENSORS_SSP_PROX_LIGHT_DIFF)
	   ssp_dbg("[SSP] Proximity Sensor Detect : %u, raw : %u light_diff: %d ts : %llu %d %d\n",
		proxdata->prox_detect, proxdata->prox_adc, proxdata->light_diff, proxdata->timestamp, ts_high, ts_low);
#else
        ssp_dbg("[SSP] Proximity Sensor Detect : %u, raw : %u ts : %llu %d %d\n",
		proxdata->prox_detect, proxdata->prox_adc, proxdata->timestamp, ts_high, ts_low);
#endif
}

void report_prox_raw_data(struct ssp_data *data, int sensor_type,
	struct sensor_value *proxrawdata)
{
	if (data->uFactoryProxAvg[0]++ >= PROX_AVG_READ_NUM) {
		data->uFactoryProxAvg[2] /= PROX_AVG_READ_NUM;
		data->buf[PROXIMITY_RAW].prox_raw[1] = (u16)data->uFactoryProxAvg[1];
		data->buf[PROXIMITY_RAW].prox_raw[2] = (u16)data->uFactoryProxAvg[2];
		data->buf[PROXIMITY_RAW].prox_raw[3] = (u16)data->uFactoryProxAvg[3];

		data->uFactoryProxAvg[0] = 0;
		data->uFactoryProxAvg[1] = 0;
		data->uFactoryProxAvg[2] = 0;
		data->uFactoryProxAvg[3] = 0;
	} else {
		data->uFactoryProxAvg[2] += proxrawdata->prox_raw[0];

		if (data->uFactoryProxAvg[0] == 1)
			data->uFactoryProxAvg[1] = proxrawdata->prox_raw[0];
		else if (proxrawdata->prox_raw[0] < data->uFactoryProxAvg[1])
			data->uFactoryProxAvg[1] = proxrawdata->prox_raw[0];

		if (proxrawdata->prox_raw[0] > data->uFactoryProxAvg[3])
			data->uFactoryProxAvg[3] = proxrawdata->prox_raw[0];
	}
	
	data->buf[PROXIMITY_RAW].prox_raw[0] = proxrawdata->prox_raw[0];
	
	report_iio_data(data, PROXIMITY_RAW, proxrawdata);	
}

void report_proximity_pocket_data(struct ssp_data *data, int sensor_type, struct sensor_value *proximity_pocket)
{
	usleep_range(500, 1000);

	report_iio_data(data, PROXIMITY_POCKET, proximity_pocket);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
}

void report_prox_alert_data(struct ssp_data *data, int sensor_type, struct sensor_value *prox_alert_data)
{
	report_iio_data(data, PROXIMITY_ALERT_SENSOR, prox_alert_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
    
        ssp_dbg("[SSP] Proximity alert Sensor Detect : %d, raw : %u ts : %llu\n",
            prox_alert_data->prox_alert_detect, prox_alert_data->prox_alert_adc, prox_alert_data->timestamp);
}

#ifdef CONFIG_SENSORS_SSP_PROX_ADC_CAL
void report_prox_adc_calib_data(struct ssp_data *data, int sensor_type, struct sensor_value *proxcalibdata)
{
	data->ProxOffset = proxcalibdata->proxcal_offset;
	data->uProxHiThresh = proxcalibdata->proxcal_thresh_hi;
	data->uProxLoThresh = proxcalibdata->proxcal_thresh_lo;
	data->uProxLoThresh_detect = proxcalibdata->proxcal_thresh_lo;
	proximity_save_calibration(data);
}
#endif

void report_step_det_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *stepdet_data)
{
	data->buf[STEP_DETECTOR].step_det = stepdet_data->step_det;
	ssp_push_iio_buffer(data->indio_dev[STEP_DETECTOR], stepdet_data->timestamp, (u8 *)&stepdet_data->step_det, 1);
}

void report_step_cnt_data(struct ssp_data *data, int sensor_type,
	struct sensor_value *sig_motion_data)
{
	data->buf[STEP_COUNTER].step_diff = sig_motion_data->step_diff;
	data->step_count_total += data->buf[STEP_COUNTER].step_diff;
	ssp_push_iio_buffer(data->indio_dev[STEP_COUNTER], sig_motion_data->timestamp,
			(u8 *)(&data->step_count_total), sensors_info[STEP_COUNTER].report_data_len);
}

void report_tilt_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *tilt_data)
{
	report_iio_data(data, TILT_DETECTOR, tilt_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: %d", __func__,  tilt_data->tilt_detector);
}

void report_pickup_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *pickup_data)
{
	report_iio_data(data, PICKUP_GESTURE, pickup_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: %d", __func__,  pickup_data->pickup_gesture);
}

void report_wakeup_motion_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *wakeup_motion_data)
{
	memcpy(&data->buf[WAKE_UP_MOTION], &wakeup_motion_data->wakeup_move_event[0], sensors_info[WAKE_UP_MOTION].get_data_len);
	ssp_push_iio_buffer(data->indio_dev[WAKE_UP_MOTION], wakeup_motion_data->timestamp, 
		(u8 *)(&data->buf[WAKE_UP_MOTION]), sensors_info[WAKE_UP_MOTION].report_data_len);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: %d", __func__,  wakeup_motion_data->wakeup_move_event[0]);
}

void report_move_detector_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *move_detector_data)
{
	memcpy(&data->buf[MOVE_DETECTOR], &move_detector_data->wakeup_move_event[1], sensors_info[MOVE_DETECTOR].get_data_len);
	ssp_push_iio_buffer(data->indio_dev[MOVE_DETECTOR], move_detector_data->timestamp, 
		(u8 *)(&data->buf[MOVE_DETECTOR]), sensors_info[MOVE_DETECTOR].report_data_len);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: %d", __func__,  move_detector_data->wakeup_move_event[1]);
}

void report_call_gesture_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *call_gesture_data)
{
	report_iio_data(data, CALL_GESTURE, call_gesture_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: %d", __func__,  call_gesture_data->call_gesture);
}

void report_scontext_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *scontextbuf)
{
	short start, end;
	char printbuf[72] = {0, };

	memcpy(printbuf, scontextbuf, 72);
	memcpy(&start, printbuf+4, sizeof(short));
	memcpy(&end, printbuf+6, sizeof(short));

	if (end - start + 1 <= 64) {
		ssp_sensorhub_log("ssp_AlgoPacket", printbuf + 8, end - start + 1);
	} else {
		pr_err("[SSP] : ssp_AlgoPacket packet error start:%d end:%d", start, end);
	}

	mutex_lock(&ssp_iio_push_lock);
	iio_push_to_buffers(data->indio_scontext_dev, scontextbuf);
	mutex_unlock(&ssp_iio_push_lock);

	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
}
void report_uncalib_accel_data(struct ssp_data *data, int sensor_type, struct sensor_value *acceldata)
{
	report_iio_data(data, ACCEL_UNCALIB_SENSOR, acceldata);
}

void report_pocket_mode_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *pocket_data)
{
	report_iio_data(data, POCKET_MODE_SENSOR, pocket_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: state = %d reason = %d base = %d current = %d temp = %d ts: %llu", __func__,
		pocket_data->pocket_mode, pocket_data->pocket_reason, pocket_data->pocket_base_proxy,
		pocket_data->pocket_current_proxy, pocket_data->pocket_temp, pocket_data->timestamp);
}

void report_led_cover_event_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *led_cover_event_data)
{
	report_iio_data(data, LED_COVER_EVENT_SENSOR, led_cover_event_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: %d ts: %llu", __func__,  led_cover_event_data->led_cover_event, led_cover_event_data->timestamp);
}

void report_auto_rotation_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *auto_rotation_data)
{
	report_iio_data(data, AUTO_ROTATION_SENSOR, auto_rotation_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: %d ts: %llu", __func__, auto_rotation_data->auto_rotation_event, auto_rotation_data->timestamp);
}

void report_sar_backoff_motion_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *sar_backoff_motion_data)
{
	report_iio_data(data, SAR_BACKOFF_MOTION, sar_backoff_motion_data);
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));
	pr_err("[SSP]: %s: %d ts: %llu", __func__,
	sar_backoff_motion_data->sar_backoff_motion_event,
	sar_backoff_motion_data->timestamp);
}

#define THM_UP		0
#define THM_SUB		1
short thermistor_rawToTemperature(struct ssp_data *data, int type, s16 raw)
{
	int startTemp = -20, i = 0, diff;
	int temperature = 0, temperature_norm = 0;

	for (i = 0; i < ARRAY_SIZE(data->tempTable_up) - 1; i++) {
		if (type == THM_UP) {
			if (raw > data->tempTable_up[0]) {
				temperature = -20; // MIN value
				break;
			} else if (raw <= data->tempTable_up[22]) {
				temperature = 90; // MAX value
				break;
			} else if (data->tempTable_up[i] >= raw && raw > data->tempTable_up[i + 1]) {
				diff = data->tempTable_up[i] - data->tempTable_up[i + 1];
				//value : diff = temperature : 5
				temperature = startTemp + (5 * i) + ((data->tempTable_up[i] - raw) * 5 / diff);
				temperature_norm = ((data->tempTable_up[i] - raw) * 5 % diff);
				temperature_norm = (temperature_norm * 10) / diff;
				break;
			}
		} else {
			if (raw > data->tempTable_sub[0]) {
				temperature = -20; // MIN value
				break;
			} else if (raw <= data->tempTable_sub[22]) {
				temperature = 90; // MAX value
				break;
			} else if (data->tempTable_sub[i] >= raw && raw > data->tempTable_sub[i + 1]) {
				diff = data->tempTable_sub[i] - data->tempTable_sub[i + 1];
				temperature = startTemp + (5 * i) + ((data->tempTable_sub[i] - raw) * 5 / diff);
				temperature_norm = ((data->tempTable_sub[i] - raw) * 5 % diff);
				temperature_norm = (temperature_norm * 10) / diff;
				break;
			}
		}
	}

	temperature = temperature * 10 + temperature_norm;
	pr_info("[SSP] %s type: %d raw: %d temper: %d", __func__, type, raw, temperature);
	return temperature;
}

void report_thermistor_data(struct ssp_data *data, int sensor_type,
		struct sensor_value *thermistor_data)
{
	u8 reportData[3];
	s16 temperature = thermistor_rawToTemperature(data, thermistor_data->thermistor_type, thermistor_data->thermistor_raw);

	reportData[0] = thermistor_data->thermistor_type;
	memcpy(&reportData[1], &temperature, sizeof(temperature));
	ssp_push_iio_buffer(data->indio_dev[THERMISTOR_SENSOR], thermistor_data->timestamp, (u8 *)reportData, sizeof(reportData));
	__pm_wakeup_event(data->ssp_wake_lock, jiffies_to_msecs(0.3*HZ));

	data->buf[THERMISTOR_SENSOR].thermistor_type = thermistor_data->thermistor_type;
	data->buf[THERMISTOR_SENSOR].thermistor_raw = thermistor_data->thermistor_raw;

	/*
	 * Port: psy_do_property("battery", POWER_SUPPLY_EXT_PROP_OVERHEAT_NOTIFY)
	 * to wlasnosc sterownika baterii Samsunga; mainline jej nie zna.
	 */
}
void report_temp_humidity_data(struct ssp_data *data, int sensor_type,
	struct sensor_value *temp_humi_data)
{
	return;
}

#ifdef CONFIG_SENSORS_SSP_SHTC1
void report_bulk_comp_data(struct ssp_data *data)
{
	return;
}
#endif

void report_gesture_data(struct ssp_data *data, int sensor_type, struct sensor_value *gesdata)
{
	return;
}


int initialize_event_symlink(struct ssp_data *data)
{
	return SUCCESS;
}

void remove_event_symlink(struct ssp_data *data)
{
	return;
}

static const struct iio_chan_spec indio_meta_channels[] = {
	{
		.type = IIO_TIMESTAMP,
		.channel = IIO_CHANNEL,
		.scan_index = IIO_SCAN_INDEX,
		.scan_type = IIO_ST('s', 16 * 8, 16 * 8, 0)
	}
};

static const struct iio_chan_spec indio_scontext_channels[] = {
	{
		.type = IIO_TIMESTAMP,
		.channel = IIO_CHANNEL,
		.scan_index = IIO_SCAN_INDEX,
		.scan_type.sign = 's',
		.scan_type.realbits = 192,
		.scan_type.storagebits = 192,
		.scan_type.shift = 0,
		.scan_type.repeat = 3
	}
};

/*
 * A plain three axis view of the accelerometer for generic readers such as
 * iio-sensor-proxy, which look for in_accel_*_raw and a scale.  The values
 * are the last sample the hub reported, in the Android frame the hub already
 * rotates to.  The hub reports 4096 counts per g (4099 lying flat), so the
 * scale is 9.80665 / 4096 m/s^2.
 */
/*
 * The hub reports in the Android frame, where a phone held upright reads
 * +1 g on y.  Linux readers take the opposite sign (iio-sensor-proxy called
 * that position bottom-up), so the mount matrix flips all three axes.
 * Measured on the phone in all four positions.
 */
static const struct iio_mount_matrix ssp_accel_mount_matrix = {
	.rotation = { "-1", "0", "0", "0", "-1", "0", "0", "0", "-1" },
};

static const struct iio_mount_matrix *
ssp_accel_get_mount_matrix(const struct iio_dev *indio_dev,
			   const struct iio_chan_spec *chan)
{
	return &ssp_accel_mount_matrix;
}

static const struct iio_chan_spec_ext_info ssp_accel_ext_info[] = {
	IIO_MOUNT_MATRIX(IIO_SHARED_BY_TYPE, ssp_accel_get_mount_matrix),
	{ }
};

#define SSP_ACCEL_CHAN(_axis) {					\
	.type = IIO_ACCEL,						\
	.modified = 1,							\
	.channel2 = IIO_MOD_##_axis,					\
	.info_mask_separate = BIT(IIO_CHAN_INFO_RAW),			\
	.info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),		\
	.ext_info = ssp_accel_ext_info,					\
}

static const struct iio_chan_spec ssp_accel_channels[] = {
	SSP_ACCEL_CHAN(X),
	SSP_ACCEL_CHAN(Y),
	SSP_ACCEL_CHAN(Z),
};

static int ssp_accel_read_raw(struct iio_dev *indio_dev,
			      struct iio_chan_spec const *chan,
			      int *val, int *val2, long mask)
{
	struct ssp_data *data = *(struct ssp_data **)iio_priv(indio_dev);
	struct sensor_value *s = &data->buf[ACCELEROMETER_SENSOR];

	switch (mask) {
	case IIO_CHAN_INFO_RAW:
		switch (chan->channel2) {
		case IIO_MOD_X:
			*val = s->x;
			break;
		case IIO_MOD_Y:
			*val = s->y;
			break;
		default:
			*val = s->z;
			break;
		}
		return IIO_VAL_INT;
	case IIO_CHAN_INFO_SCALE:
		*val = 0;
		*val2 = 2394;
		return IIO_VAL_INT_PLUS_MICRO;
	}
	return -EINVAL;
}

static const struct iio_info ssp_accel_info = {
	.read_raw = ssp_accel_read_raw,
};

/*
 * The light sensor (TCS3407 under the panel) as a plain IIO device for
 * iio-sensor-proxy, which looks for in_illuminance_input.  The hub already
 * computes lux (CONFIG_SENSORS_SSP_LIGHT_REPORT_LUX); the value is the last
 * one it reported.  The hub reports only on change, so a reader sees the
 * last lux until the light changes.
 */
static const struct iio_chan_spec ssp_als_channels[] = {
	{
		.type = IIO_LIGHT,
		.info_mask_separate = BIT(IIO_CHAN_INFO_PROCESSED),
	},
};

static int ssp_als_read_raw(struct iio_dev *indio_dev,
			    struct iio_chan_spec const *chan,
			    int *val, int *val2, long mask)
{
	struct ssp_data *data = *(struct ssp_data **)iio_priv(indio_dev);

	if (mask != IIO_CHAN_INFO_PROCESSED)
		return -EINVAL;
	*val = data->buf[LIGHT_SENSOR].lux;
	return IIO_VAL_INT;
}

static const struct iio_info ssp_als_info = {
	.read_raw = ssp_als_read_raw,
};

/*
 * The proximity sensor as in_proximity_raw, the ADC count of the reflected
 * infrared pulse, larger when something is near.  The hub reports only when
 * its own near/far decision changes, so the count is the one of the last
 * change, and once the hub has decided, near comes from its detect flag
 * rather than from a host threshold: the raw value is kept on the matching
 * side of nearlevel, which tells iio-sensor-proxy where near begins.  Measured on the phone: about
 * 3060 uncovered, near reported at 3244 and 3735, far at 3046 and 3047.
 */
static ssize_t ssp_prox_nearlevel(struct iio_dev *indio_dev, uintptr_t priv,
				  const struct iio_chan_spec *chan, char *buf)
{
	return sysfs_emit(buf, "%u\n", prox_near);
}

static const struct iio_chan_spec_ext_info ssp_prox_ext_info[] = {
	{
		.name = "nearlevel",
		.shared = IIO_SEPARATE,
		.read = ssp_prox_nearlevel,
	},
	{ }
};

static const struct iio_chan_spec ssp_prox_channels[] = {
	{
		.type = IIO_PROXIMITY,
		.info_mask_separate = BIT(IIO_CHAN_INFO_RAW),
		.ext_info = ssp_prox_ext_info,
	},
};

static int ssp_prox_read_raw(struct iio_dev *indio_dev,
			     struct iio_chan_spec const *chan,
			     int *val, int *val2, long mask)
{
	struct ssp_data *data = *(struct ssp_data **)iio_priv(indio_dev);
	struct sensor_value *s = &data->buf[PROXIMITY_SENSOR];

	if (mask != IIO_CHAN_INFO_RAW)
		return -EINVAL;
	/*
	 * The first report after enabling carries detect 255: the hub has not
	 * decided yet, and it reports again only on a near/far change, so an
	 * uncovered phone would stay at 255 for good.  Measured: 255 at raw
	 * 3065 uncovered, then 1 at 3532 covered and 0 at 3051 uncovered.  Until
	 * the hub decides, the raw count alone says which side it is on.
	 */
	switch (s->prox_detect) {
	case 1:
		*val = max_t(unsigned int, s->prox_adc, prox_near);
		break;
	case 0:
		if (prox_far_pending &&
		    time_before(jiffies, prox_far_at + msecs_to_jiffies(prox_far_ms)))
			*val = max_t(unsigned int, s->prox_adc, prox_near);
		else
			*val = min_t(unsigned int, s->prox_adc, prox_near - 1);
		break;
	default:
		*val = s->prox_adc;
		break;
	}
	return IIO_VAL_INT;
}

static const struct iio_info ssp_prox_info = {
	.read_raw = ssp_prox_read_raw,
};

/*
 * Gyroscope (LSM6DSO), magnetometer (AK09916C) and barometer (LPS22H) behind
 * the hub, as plain IIO devices like accel_3d, with the same mount matrix
 * (the hub reports in the Android frame).  The values are the last ones the
 * hub reported for the calibrated sensor types.
 *
 * The hub does not report chip counts, so the datasheet scales do not apply
 * (70 mdps per count gave 31 deg/s lying still).  Both scales were measured
 * on the phone lying flat and turned by hand in four quarter turns back to
 * the start (27.09.2026):
 * - gyroscope: the four turns integrate to 2609039, 2575653, 2609296 and
 *   2615750 count*s, together 10409738 = 2*pi rad, so 603.6 nrad/s per count;
 * - magnetometer: the six rests lie on a circle of radius 267.4 counts around
 *   (1177, -269), the offset of the phone's own magnets (the hub reports
 *   accuracy 0).  With the horizontal field of central Poland, 19.1 uT, one
 *   count is 0.0714 uT; indoor steel makes this good to about 10-15 %.
 * Module parameters in nano-units (rad/s and gauss per count).
 */
static unsigned int gyro_skala_nano = 604;
module_param(gyro_skala_nano, uint, 0644);
MODULE_PARM_DESC(gyro_skala_nano, "gyroscope scale, nrad/s per count");
static unsigned int magn_skala_nano = 714000;	/* 0.0714 uT = 0.714 mG */
module_param(magn_skala_nano, uint, 0644);
MODULE_PARM_DESC(magn_skala_nano, "magnetometer scale, nano-gauss per count");

#define SSP_3D_CHAN(_type, _axis) {					\
	.type = _type,							\
	.modified = 1,							\
	.channel2 = IIO_MOD_##_axis,					\
	.info_mask_separate = BIT(IIO_CHAN_INFO_RAW),			\
	.info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),		\
	.ext_info = ssp_accel_ext_info,					\
}

static const struct iio_chan_spec ssp_gyro_channels[] = {
	SSP_3D_CHAN(IIO_ANGL_VEL, X),
	SSP_3D_CHAN(IIO_ANGL_VEL, Y),
	SSP_3D_CHAN(IIO_ANGL_VEL, Z),
};

static const struct iio_chan_spec ssp_magn_channels[] = {
	SSP_3D_CHAN(IIO_MAGN, X),
	SSP_3D_CHAN(IIO_MAGN, Y),
	SSP_3D_CHAN(IIO_MAGN, Z),
};

static int ssp_3d_read_raw(struct iio_dev *indio_dev,
			   struct iio_chan_spec const *chan,
			   int *val, int *val2, long mask)
{
	struct ssp_data *data = *(struct ssp_data **)iio_priv(indio_dev);
	bool gyro = chan->type == IIO_ANGL_VEL;
	struct sensor_value *s = &data->buf[gyro ? GYROSCOPE_SENSOR : GEOMAGNETIC_SENSOR];
	int i = chan->channel2 == IIO_MOD_X ? 0 : chan->channel2 == IIO_MOD_Y ? 1 : 2;

	switch (mask) {
	case IIO_CHAN_INFO_RAW:
		if (gyro)
			*val = i == 0 ? s->gyro.x : i == 1 ? s->gyro.y : s->gyro.z;
		else
			*val = i == 0 ? s->cal_x : i == 1 ? s->cal_y : s->cal_z;
		return IIO_VAL_INT;
	case IIO_CHAN_INFO_SCALE:
		*val = 0;
		*val2 = gyro ? gyro_skala_nano : magn_skala_nano;
		return IIO_VAL_INT_PLUS_NANO;
	}
	return -EINVAL;
}

static const struct iio_info ssp_3d_info = {
	.read_raw = ssp_3d_read_raw,
};

/*
 * LPS22H: pressure in 1/4096 hPa (measured 4163785 = 1016.5 hPa), temperature
 * in 1/100 degC (3505 = 35.05).  IIO wants kPa and milli-degC.
 */
static const struct iio_chan_spec ssp_baro_channels[] = {
	{
		.type = IIO_PRESSURE,
		.info_mask_separate = BIT(IIO_CHAN_INFO_RAW) | BIT(IIO_CHAN_INFO_SCALE),
	},
	{
		.type = IIO_TEMP,
		.info_mask_separate = BIT(IIO_CHAN_INFO_RAW) | BIT(IIO_CHAN_INFO_SCALE),
	},
};

static int ssp_baro_read_raw(struct iio_dev *indio_dev,
			     struct iio_chan_spec const *chan,
			     int *val, int *val2, long mask)
{
	struct ssp_data *data = *(struct ssp_data **)iio_priv(indio_dev);
	struct sensor_value *s = &data->buf[PRESSURE_SENSOR];

	switch (mask) {
	case IIO_CHAN_INFO_RAW:
		*val = chan->type == IIO_PRESSURE ? s->pressure : s->temperature;
		return IIO_VAL_INT;
	case IIO_CHAN_INFO_SCALE:
		if (chan->type == IIO_PRESSURE) {
			*val = 1;		/* 0.1 kPa / 4096 */
			*val2 = 40960;
			return IIO_VAL_FRACTIONAL;
		}
		*val = 10;			/* 1/100 degC = 10 milli-degC */
		return IIO_VAL_INT;
	}
	return -EINVAL;
}

static const struct iio_info ssp_baro_info = {
	.read_raw = ssp_baro_read_raw,
};

static int initialize_plain_iio(struct ssp_data *data, const char *name,
				const struct iio_info *info,
				const struct iio_chan_spec *channels,
				int num_channels)
{
	struct iio_dev *indio_dev;

	indio_dev = devm_iio_device_alloc(&data->spi->dev, sizeof(data));
	if (!indio_dev)
		return -ENOMEM;
	*(struct ssp_data **)iio_priv(indio_dev) = data;
	indio_dev->name = name;
	indio_dev->info = info;
	indio_dev->channels = channels;
	indio_dev->num_channels = num_channels;
	indio_dev->modes = INDIO_DIRECT_MODE;
	return devm_iio_device_register(&data->spi->dev, indio_dev);
}

int initialize_input_dev(struct ssp_data *data)
{
	int iRet = 0, i = 0;

	memset(&sensors_info, -1, sizeof(struct sensor_info) * SENSOR_MAX);

	for (i = 0; i < info_table_size; i++) {
		int index = info_table[i].type;

		if (index < SENSOR_MAX) {
			int bit_size = (info_table[i].report_data_len + 8) * BITS_PER_BYTE;
			int repeat_size = bit_size / 256 + 1;

			sensors_info[index] = info_table[i];

			indio_channels[index].type = IIO_TIMESTAMP;
			indio_channels[index].channel = IIO_CHANNEL;
			indio_channels[index].scan_index = IIO_SCAN_INDEX;
			indio_channels[index].scan_type.sign = 's';
			indio_channels[index].scan_type.realbits = bit_size / repeat_size;
			indio_channels[index].scan_type.storagebits = bit_size / repeat_size;
			indio_channels[index].scan_type.shift = 0;
			indio_channels[index].scan_type.repeat = repeat_size;
		}

		// we do not check index < SENSOR_MAX because of META_SENSOR
		// scontext indio is not a sensor type
		if (index != -1 && info_table[i].report_data_len > 0) {
			struct iio_dev *indio_dev = NULL;

			indio_dev = iio_device_alloc(&data->spi->dev, 0);
			if (!indio_dev)
				return -ENOMEM;
			indio_dev->name = info_table[i].name;
			indio_dev->dev.parent = &data->spi->dev;
			indio_dev->info = &indio_info;
			if (index == META_SENSOR)
				indio_dev->channels = indio_meta_channels;
			else if (strcmp(info_table[i].name, "scontext_iio") == 0)
				indio_dev->channels = indio_scontext_channels;
			else
				indio_dev->channels = &indio_channels[index];
			indio_dev->num_channels = 1;
			indio_dev->modes = INDIO_DIRECT_MODE;

			iRet = initialize_iio_buffer_and_device(indio_dev, data);

			if (index == META_SENSOR)
				data->meta_indio_dev = indio_dev;
			else if (strcmp(info_table[i].name, "scontext_iio") == 0)
				data->indio_scontext_dev = indio_dev;
			else
				data->indio_dev[index] = indio_dev;

			pr_err("[SSP] %s(%d) - iio_device, iRet = %d\n", info_table[i].name, i, iRet);
		}
	}

	iRet = initialize_plain_iio(data, "accel_3d", &ssp_accel_info,
				    ssp_accel_channels, ARRAY_SIZE(ssp_accel_channels));
	pr_info("[SSP] accel_3d - iio_device, iRet = %d\n", iRet);
	if (iRet)
		return iRet;
	iRet = initialize_plain_iio(data, "als", &ssp_als_info, ssp_als_channels,
				    ARRAY_SIZE(ssp_als_channels));
	pr_info("[SSP] als - iio_device, iRet = %d\n", iRet);
	if (iRet)
		return iRet;
	iRet = initialize_plain_iio(data, "proximity", &ssp_prox_info,
				    ssp_prox_channels, ARRAY_SIZE(ssp_prox_channels));
	pr_info("[SSP] proximity - iio_device, iRet = %d\n", iRet);
	if (iRet)
		return iRet;
	iRet = initialize_plain_iio(data, "gyro_3d", &ssp_3d_info, ssp_gyro_channels,
				    ARRAY_SIZE(ssp_gyro_channels));
	pr_info("[SSP] gyro_3d - iio_device, iRet = %d\n", iRet);
	if (iRet)
		return iRet;
	iRet = initialize_plain_iio(data, "magn_3d", &ssp_3d_info, ssp_magn_channels,
				    ARRAY_SIZE(ssp_magn_channels));
	pr_info("[SSP] magn_3d - iio_device, iRet = %d\n", iRet);
	if (iRet)
		return iRet;
	iRet = initialize_plain_iio(data, "baro", &ssp_baro_info, ssp_baro_channels,
				    ARRAY_SIZE(ssp_baro_channels));
	pr_info("[SSP] baro - iio_device, iRet = %d\n", iRet);
	return iRet;
}

void remove_input_dev(struct ssp_data *data)
{
	return;
}
