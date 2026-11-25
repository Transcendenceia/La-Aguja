#pragma once

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"
#include "cJSON.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Seeed Studio XIAO ESP32-C6 Hardware Pin Map */
#define XIAO_PIN_RF_SWITCH_EN   3   /* Active LOW: enable RF switch power */
#define XIAO_PIN_RF_ANT_SEL     14  /* LOW = internal ceramic, HIGH = external u.FL */
#define XIAO_PIN_USER_LED       15  /* Active LOW onboard orange LED */
#define XIAO_PIN_BOOT_BTN       9

#define XIAO_PIN_D0             0   /* ADC1_CH0 */
#define XIAO_PIN_D1             1   /* ADC1_CH1 */
#define XIAO_PIN_D2             2   /* ADC1_CH2 */
#define XIAO_PIN_D3             21
#define XIAO_PIN_D4_SDA         22
#define XIAO_PIN_D5_SCL         23
#define XIAO_PIN_D6_TX          16
#define XIAO_PIN_D7_RX          17
#define XIAO_PIN_D8_SCK         19
#define XIAO_PIN_D9_MISO        20
#define XIAO_PIN_D10_MOSI       18

typedef enum {
    AGUJA_LED_STATUS = 0,
    AGUJA_LED_OFF    = 1,
    AGUJA_LED_ON     = 2,
    AGUJA_LED_BLINK  = 3,
    AGUJA_LED_PWM    = 4,
} aguja_led_mode_t;

typedef enum {
    AGUJA_NET_STAGE_BOOT = 0,
    AGUJA_NET_STAGE_WIFI_CONNECTING,
    AGUJA_NET_STAGE_TAILNET_CONNECTING,
    AGUJA_NET_STAGE_CONNECTED,
    AGUJA_NET_STAGE_ERROR,
} aguja_net_stage_t;

esp_err_t aguja_hw_init(void);
void aguja_hw_set_net_stage(aguja_net_stage_t stage);

/* RF Antenna switch (GPIO3 / GPIO14) */
esp_err_t aguja_hw_set_antenna(bool external);
bool aguja_hw_get_antenna_external(void);

/* Onboard User LED (GPIO15) */
esp_err_t aguja_hw_set_led(aguja_led_mode_t mode, uint8_t pwm_pct, uint16_t blink_ms);
void aguja_hw_get_led(aguja_led_mode_t *mode, uint8_t *pwm_pct, uint16_t *blink_ms);

/* Die temperature sensor */
esp_err_t aguja_hw_read_temp_c(float *out_c);

/* Dynamic CPU frequency scaling (40/80/160 MHz) */
esp_err_t aguja_hw_set_cpu_mhz(uint16_t mhz);
uint16_t aguja_hw_get_cpu_mhz(void);

/* GPIO control (D0..D10 safe map, force=true allows other non-flash/USB pins) */
bool aguja_hw_pin_is_safe(int pin);
esp_err_t aguja_hw_gpio_config(int pin, const char *mode, const char *pull, bool force);
esp_err_t aguja_hw_gpio_write(int pin, int level, bool force);
esp_err_t aguja_hw_gpio_pulse(int pin, int level, uint32_t duration_ms, bool force);
int aguja_hw_gpio_read(int pin);
cJSON *aguja_hw_gpio_dump_json(void);

/* PWM / LEDC */
esp_err_t aguja_hw_pwm_set(int channel, int pin, uint32_t freq_hz, float duty_pct, bool stop);

/* ADC1 calibrated readings (D0=GPIO0, D1=GPIO1, D2=GPIO2) */
esp_err_t aguja_hw_adc_read(int pin, int *raw_out, int *mv_out);
cJSON *aguja_hw_adc_dump_json(void);

/* I2C Master */
esp_err_t aguja_hw_i2c_config(int sda, int scl, uint32_t freq_hz);
cJSON *aguja_hw_i2c_scan(void);
esp_err_t aguja_hw_i2c_xfer(uint8_t addr, const uint8_t *tx, size_t tx_len,
                            uint8_t *rx, size_t rx_len, uint32_t timeout_ms);

/* UART1 Bridge */
esp_err_t aguja_hw_uart_config(int tx_pin, int rx_pin, int baud);
int aguja_hw_uart_tx(const uint8_t *data, size_t len);
int aguja_hw_uart_rx(uint8_t *out, size_t max_len, uint32_t timeout_ms);

/* SPI Master */
esp_err_t aguja_hw_spi_xfer(int sck, int miso, int mosi, int cs, uint32_t clock_hz,
                            const uint8_t *tx, uint8_t *rx, size_t len);

/* Automation rule engine task */
typedef void (*aguja_rule_alert_cb_t)(const char *rule_name, const char *msg, int value);
void aguja_hw_start_tasks(aguja_rule_alert_cb_t alert_cb);

#ifdef __cplusplus
}
#endif
