#include "aguja_hw.h"
#include "aguja_config.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/temperature_sensor.h"
#include "driver/i2c_master.h"
#include "driver/uart.h"
#include "driver/spi_master.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_pm.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "aguja_hw";

/* Target-specific exposed safe GPIO pins */
static const struct {
    const char *label;
    int gpio;
    const char *func;
} s_board_pins[] = {
#if CONFIG_IDF_TARGET_ESP32S3
    { "IO1",  1,  "ADC1_CH0" },
    { "IO2",  2,  "ADC1_CH1" },
    { "IO4",  4,  "ADC1_CH3" },
    { "IO5",  5,  "ADC1_CH4" },
    { "IO6",  6,  "ADC1_CH5" },
    { "IO7",  7,  "ADC1_CH6" },
    { "IO8",  8,  "I2C_SDA" },
    { "IO9",  9,  "I2C_SCL" },
    { "IO10", 10, "SPI_CS" },
    { "IO11", 11, "SPI_MOSI" },
    { "IO12", 12, "SPI_SCK" },
    { "IO13", 13, "SPI_MISO" },
    { "IO14", 14, "GPIO" },
    { "IO15", 15, "GPIO" },
    { "IO16", 16, "GPIO" },
    { "IO17", 17, "UART_TX" },
    { "IO18", 18, "UART_RX" },
    { "IO21", 21, "GPIO" },
    { "IO38", 38, "GPIO" },
    { "IO39", 39, "GPIO" },
    { "IO40", 40, "GPIO" },
    { "IO41", 41, "GPIO" },
    { "IO42", 42, "GPIO" },
#else
    { "D0",  XIAO_PIN_D0,       "ADC1_CH0" },
    { "D1",  XIAO_PIN_D1,       "ADC1_CH1" },
    { "D2",  XIAO_PIN_D2,       "ADC1_CH2" },
    { "D3",  XIAO_PIN_D3,       "GPIO" },
    { "D4",  XIAO_PIN_D4_SDA,   "I2C_SDA" },
    { "D5",  XIAO_PIN_D5_SCL,   "I2C_SCL" },
    { "D6",  XIAO_PIN_D6_TX,    "UART_TX" },
    { "D7",  XIAO_PIN_D7_RX,    "UART_RX" },
    { "D8",  XIAO_PIN_D8_SCK,   "SPI_SCK" },
    { "D9",  XIAO_PIN_D9_MISO,  "SPI_MISO" },
    { "D10", XIAO_PIN_D10_MOSI, "SPI_MOSI" },
#endif
};

static bool s_antenna_external = false;
static volatile aguja_led_mode_t s_led_mode = AGUJA_LED_STATUS;
static volatile uint8_t s_led_pwm_pct = 50;
static volatile uint16_t s_led_blink_ms = 500;
static volatile aguja_net_stage_t s_net_stage = AGUJA_NET_STAGE_BOOT;
static bool s_led_pwm_active = false;
static uint16_t s_cpu_mhz = AGUJA_DEFAULT_CPU_MHZ;

static temperature_sensor_handle_t s_tsens = NULL;
static adc_oneshot_unit_handle_t s_adc1 = NULL;
static adc_cali_handle_t s_adc_cali = NULL;

static SemaphoreHandle_t s_bus_mtx = NULL;
static i2c_master_bus_handle_t s_i2c_bus = NULL;
static int s_i2c_sda = AGUJA_DEFAULT_I2C_SDA;
static int s_i2c_scl = AGUJA_DEFAULT_I2C_SCL;
static uint32_t s_i2c_freq = 100000;

static bool s_uart1_init = false;
static aguja_rule_alert_cb_t s_alert_cb = NULL;
static int64_t s_rule_last_fire[AGUJA_MAX_RULES] = {0};

/* Track GPIO output states for telemetry */
static int8_t s_gpio_out_state[49];

bool aguja_hw_pin_is_safe(int pin) {
    for (size_t i = 0; i < sizeof(s_board_pins) / sizeof(s_board_pins[0]); i++) {
        if (s_board_pins[i].gpio == pin) return true;
    }
    return false;
}

static bool pin_is_forbidden(int pin) {
#if CONFIG_IDF_TARGET_ESP32S3
    if (pin < 0 || pin > 48) return true;
    /* USB D-/D+ (19, 20), Flash/Octal PSRAM (26..37), UART0 (43, 44) */
    if (pin == 19 || pin == 20 || (pin >= 26 && pin <= 37) || pin == 43 || pin == 44) return true;
    return false;
#else
    if (pin < 0 || pin > 30) return true;
    /* USB-Serial/JTAG D-/D+ (12, 13) and internal SPI flash (24..30) */
    if (pin == 12 || pin == 13 || pin >= 24) return true;
    return false;
#endif
}

esp_err_t aguja_hw_set_antenna(bool external) {
#if AGUJA_HAS_RF_SWITCH
    /* XIAO ESP32-C6: GPIO3 LOW activates RF switch; GPIO14 LOW=ceramic, HIGH=uFL */
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << XIAO_PIN_RF_SWITCH_EN) | (1ULL << XIAO_PIN_RF_ANT_SEL),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io);
    gpio_set_level(XIAO_PIN_RF_SWITCH_EN, 0);
    gpio_set_level(XIAO_PIN_RF_ANT_SEL, external ? 1 : 0);
    s_antenna_external = external;
    ESP_LOGI(TAG, "RF antenna switch: %s (GPIO3=0, GPIO14=%d)",
             external ? "EXTERNAL u.FL" : "INTERNAL ceramic", external ? 1 : 0);
#else
    (void)external;
    s_antenna_external = false;
#endif
    return ESP_OK;
}

bool aguja_hw_get_antenna_external(void) {
    return s_antenna_external;
}

static void led_set_raw(bool on) {
    if (s_led_pwm_active) {
        ledc_stop(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_5, AGUJA_USER_LED_ACTIVE_LOW ? (on ? 0 : 1) : (on ? 1 : 0));
        s_led_pwm_active = false;
        gpio_reset_pin(AGUJA_USER_LED_PIN);
        gpio_set_direction(AGUJA_USER_LED_PIN, GPIO_MODE_OUTPUT);
    }
    gpio_set_level(AGUJA_USER_LED_PIN, AGUJA_USER_LED_ACTIVE_LOW ? (on ? 0 : 1) : (on ? 1 : 0));
}

static void led_set_pwm_raw(uint8_t pct) {
    if (pct > 100) pct = 100;
    if (!s_led_pwm_active) {
        ledc_timer_config_t tc = {
            .speed_mode = LEDC_LOW_SPEED_MODE,
            .duty_resolution = LEDC_TIMER_10_BIT,
            .timer_num = LEDC_TIMER_3,
            .freq_hz = 2000,
            .clk_cfg = LEDC_AUTO_CLK,
        };
        ledc_timer_config(&tc);
        ledc_channel_config_t cc = {
            .gpio_num = AGUJA_USER_LED_PIN,
            .speed_mode = LEDC_LOW_SPEED_MODE,
            .channel = LEDC_CHANNEL_5,
            .timer_sel = LEDC_TIMER_3,
            .duty = AGUJA_USER_LED_ACTIVE_LOW ? 1023 : 0,
            .hpoint = 0,
        };
        ledc_channel_config(&cc);
        s_led_pwm_active = true;
    }
    uint32_t duty = AGUJA_USER_LED_ACTIVE_LOW
        ? (uint32_t)((100 - pct) * 1023 / 100)
        : (uint32_t)(pct * 1023 / 100);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_5, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_5);
}

esp_err_t aguja_hw_set_led(aguja_led_mode_t mode, uint8_t pwm_pct, uint16_t blink_ms) {
    s_led_mode = mode;
    if (pwm_pct <= 100) s_led_pwm_pct = pwm_pct;
    if (blink_ms >= 50) s_led_blink_ms = blink_ms;
    if (mode == AGUJA_LED_OFF) led_set_raw(false);
    else if (mode == AGUJA_LED_ON) led_set_raw(true);
    else if (mode == AGUJA_LED_PWM) led_set_pwm_raw(s_led_pwm_pct);
    return ESP_OK;
}

void aguja_hw_get_led(aguja_led_mode_t *mode, uint8_t *pwm_pct, uint16_t *blink_ms) {
    if (mode) *mode = s_led_mode;
    if (pwm_pct) *pwm_pct = s_led_pwm_pct;
    if (blink_ms) *blink_ms = s_led_blink_ms;
}

void aguja_hw_set_net_stage(aguja_net_stage_t stage) {
    s_net_stage = stage;
}

esp_err_t aguja_hw_read_temp_c(float *out_c) {
    if (!out_c) return ESP_ERR_INVALID_ARG;
    if (!s_tsens) return ESP_ERR_INVALID_STATE;
    return temperature_sensor_get_celsius(s_tsens, out_c);
}

esp_err_t aguja_hw_set_cpu_mhz(uint16_t mhz) {
#if CONFIG_IDF_TARGET_ESP32S3
    if (mhz != 80 && mhz != 160 && mhz != 240) return ESP_ERR_INVALID_ARG;
    int min_mhz = 80;
#else
    if (mhz != 40 && mhz != 80 && mhz != 160) return ESP_ERR_INVALID_ARG;
    int min_mhz = 40;
#endif
#if CONFIG_PM_ENABLE
    esp_pm_config_t pm = {
        .max_freq_mhz = mhz,
        .min_freq_mhz = min_mhz,
        .light_sleep_enable = false,
    };
    esp_err_t err = esp_pm_configure(&pm);
    if (err == ESP_OK) {
        s_cpu_mhz = mhz;
        ESP_LOGI(TAG, "CPU max freq set to %u MHz", mhz);
    }
    return err;
#else
    return ESP_ERR_NOT_SUPPORTED;
#endif
}

uint16_t aguja_hw_get_cpu_mhz(void) {
    return s_cpu_mhz;
}

esp_err_t aguja_hw_gpio_config(int pin, const char *mode, const char *pull, bool force) {
    if (pin_is_forbidden(pin)) return ESP_ERR_INVALID_ARG;
    if (!force && !aguja_hw_pin_is_safe(pin)) return ESP_ERR_INVALID_ARG;

    gpio_config_t io = {
        .pin_bit_mask = (1ULL << pin),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    if (mode) {
        if (strcmp(mode, "out") == 0) io.mode = GPIO_MODE_INPUT_OUTPUT;
        else if (strcmp(mode, "od") == 0) io.mode = GPIO_MODE_INPUT_OUTPUT_OD;
        else if (strcmp(mode, "in") == 0) io.mode = GPIO_MODE_INPUT;
        else return ESP_ERR_INVALID_ARG;
    }
    if (pull) {
        if (strcmp(pull, "up") == 0) io.pull_up_en = GPIO_PULLUP_ENABLE;
        else if (strcmp(pull, "down") == 0) io.pull_down_en = GPIO_PULLDOWN_ENABLE;
    }
    return gpio_config(&io);
}

esp_err_t aguja_hw_gpio_write(int pin, int level, bool force) {
    if (pin_is_forbidden(pin)) return ESP_ERR_INVALID_ARG;
    if (!force && !aguja_hw_pin_is_safe(pin)) return ESP_ERR_INVALID_ARG;
    s_gpio_out_state[pin] = level ? 1 : 0;
    return gpio_set_level((gpio_num_t)pin, level ? 1 : 0);
}

esp_err_t aguja_hw_gpio_pulse(int pin, int level, uint32_t duration_ms, bool force) {
    if (duration_ms > 10000) duration_ms = 10000;
    esp_err_t err = aguja_hw_gpio_config(pin, "out", "none", force);
    if (err != ESP_OK) return err;
    aguja_hw_gpio_write(pin, level ? 1 : 0, force);
    vTaskDelay(pdMS_TO_TICKS(duration_ms));
    aguja_hw_gpio_write(pin, level ? 0 : 1, force);
    return ESP_OK;
}

int aguja_hw_gpio_read(int pin) {
#if CONFIG_IDF_TARGET_ESP32S3
    if (pin < 0 || pin > 48) return -1;
#else
    if (pin < 0 || pin > 30) return -1;
#endif
    return gpio_get_level((gpio_num_t)pin);
}

cJSON *aguja_hw_gpio_dump_json(void) {
    cJSON *arr = cJSON_CreateArray();
    for (size_t i = 0; i < sizeof(s_board_pins) / sizeof(s_board_pins[0]); i++) {
        cJSON *o = cJSON_CreateObject();
        cJSON_AddStringToObject(o, "label", s_board_pins[i].label);
        cJSON_AddNumberToObject(o, "gpio", s_board_pins[i].gpio);
        cJSON_AddStringToObject(o, "func", s_board_pins[i].func);
        cJSON_AddNumberToObject(o, "level", gpio_get_level((gpio_num_t)s_board_pins[i].gpio));
        cJSON_AddItemToArray(arr, o);
    }
    return arr;
}

esp_err_t aguja_hw_pwm_set(int channel, int pin, uint32_t freq_hz, float duty_pct, bool stop) {
    if (channel < 0 || channel > 4) return ESP_ERR_INVALID_ARG; /* ch 5 reserved for LED */
    if (!stop) {
        if (!aguja_hw_pin_is_safe(pin)) return ESP_ERR_INVALID_ARG;
        if (freq_hz < 10 || freq_hz > 40000) return ESP_ERR_INVALID_ARG;
        if (duty_pct < 0.0f) duty_pct = 0.0f;
        if (duty_pct > 100.0f) duty_pct = 100.0f;

        ledc_timer_t timer = (channel < 2) ? LEDC_TIMER_0 : ((channel < 4) ? LEDC_TIMER_1 : LEDC_TIMER_2);
        ledc_timer_config_t tc = {
            .speed_mode = LEDC_LOW_SPEED_MODE,
            .duty_resolution = LEDC_TIMER_10_BIT,
            .timer_num = timer,
            .freq_hz = freq_hz,
            .clk_cfg = LEDC_AUTO_CLK,
        };
        esp_err_t err = ledc_timer_config(&tc);
        if (err != ESP_OK) return err;

        uint32_t duty = (uint32_t)(duty_pct * 1023.0f / 100.0f);
        ledc_channel_config_t cc = {
            .gpio_num = pin,
            .speed_mode = LEDC_LOW_SPEED_MODE,
            .channel = (ledc_channel_t)channel,
            .timer_sel = timer,
            .duty = duty,
            .hpoint = 0,
        };
        return ledc_channel_config(&cc);
    } else {
        return ledc_stop(LEDC_LOW_SPEED_MODE, (ledc_channel_t)channel, 0);
    }
}

static int gpio_to_adc_ch(int pin) {
#if CONFIG_IDF_TARGET_ESP32S3
    if (pin >= 1 && pin <= 10) return pin - 1;
    return -1;
#else
    if (pin == XIAO_PIN_D0) return ADC_CHANNEL_0;
    if (pin == XIAO_PIN_D1) return ADC_CHANNEL_1;
    if (pin == XIAO_PIN_D2) return ADC_CHANNEL_2;
    return -1;
#endif
}

esp_err_t aguja_hw_adc_read(int pin, int *raw_out, int *mv_out) {
    int ch = gpio_to_adc_ch(pin);
    if (ch < 0 || !s_adc1) return ESP_ERR_INVALID_ARG;
    adc_oneshot_chan_cfg_t cfg = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    esp_err_t err = adc_oneshot_config_channel(s_adc1, (adc_channel_t)ch, &cfg);
    if (err != ESP_OK) return err;

    int raw = 0;
    err = adc_oneshot_read(s_adc1, (adc_channel_t)ch, &raw);
    if (err != ESP_OK) return err;
    if (raw_out) *raw_out = raw;

    int mv = (raw * 3300) / 4095;
    if (s_adc_cali) {
        adc_cali_raw_to_voltage(s_adc_cali, raw, &mv);
    }
    if (mv_out) *mv_out = mv;
    return ESP_OK;
}

cJSON *aguja_hw_adc_dump_json(void) {
    cJSON *arr = cJSON_CreateArray();
#if CONFIG_IDF_TARGET_ESP32S3
    const int pins[3] = { 1, 2, 4 };
    const char *lbl[3] = { "IO1", "IO2", "IO4" };
#else
    const int pins[3] = { XIAO_PIN_D0, XIAO_PIN_D1, XIAO_PIN_D2 };
    const char *lbl[3] = { "D0", "D1", "D2" };
#endif
    for (int i = 0; i < 3; i++) {
        int raw = 0, mv = 0;
        if (aguja_hw_adc_read(pins[i], &raw, &mv) == ESP_OK) {
            cJSON *o = cJSON_CreateObject();
            cJSON_AddStringToObject(o, "label", lbl[i]);
            cJSON_AddNumberToObject(o, "gpio", pins[i]);
            cJSON_AddNumberToObject(o, "raw", raw);
            cJSON_AddNumberToObject(o, "mv", mv);
            cJSON_AddItemToArray(arr, o);
        }
    }
    return arr;
}

static esp_err_t ensure_i2c_locked(void) {
    if (s_i2c_bus) return ESP_OK;
    i2c_master_bus_config_t cfg = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = (gpio_num_t)s_i2c_sda,
        .scl_io_num = (gpio_num_t)s_i2c_scl,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    return i2c_new_master_bus(&cfg, &s_i2c_bus);
}

esp_err_t aguja_hw_i2c_config(int sda, int scl, uint32_t freq_hz) {
    if (!aguja_hw_pin_is_safe(sda) || !aguja_hw_pin_is_safe(scl) || sda == scl) {
        return ESP_ERR_INVALID_ARG;
    }
    if (freq_hz < 10000 || freq_hz > 400000) freq_hz = 100000;
    xSemaphoreTake(s_bus_mtx, portMAX_DELAY);
    if (s_i2c_bus) {
        i2c_del_master_bus(s_i2c_bus);
        s_i2c_bus = NULL;
    }
    s_i2c_sda = sda;
    s_i2c_scl = scl;
    s_i2c_freq = freq_hz;
    esp_err_t err = ensure_i2c_locked();
    xSemaphoreGive(s_bus_mtx);
    return err;
}

cJSON *aguja_hw_i2c_scan(void) {
    cJSON *arr = cJSON_CreateArray();
    xSemaphoreTake(s_bus_mtx, portMAX_DELAY);
    if (ensure_i2c_locked() == ESP_OK) {
        for (uint16_t addr = 0x08; addr <= 0x77; addr++) {
            if (i2c_master_probe(s_i2c_bus, addr, 25) == ESP_OK) {
                char hex[8];
                snprintf(hex, sizeof(hex), "0x%02X", addr);
                cJSON_AddItemToArray(arr, cJSON_CreateString(hex));
            }
        }
    }
    xSemaphoreGive(s_bus_mtx);
    return arr;
}

esp_err_t aguja_hw_i2c_xfer(uint8_t addr, const uint8_t *tx, size_t tx_len,
                            uint8_t *rx, size_t rx_len, uint32_t timeout_ms) {
    if (timeout_ms == 0) timeout_ms = 200;
    xSemaphoreTake(s_bus_mtx, portMAX_DELAY);
    esp_err_t err = ensure_i2c_locked();
    if (err == ESP_OK) {
        i2c_device_config_t dev_cfg = {
            .dev_addr_length = I2C_ADDR_BIT_LEN_7,
            .device_address = addr,
            .scl_speed_hz = s_i2c_freq,
        };
        i2c_master_dev_handle_t dev = NULL;
        err = i2c_master_bus_add_device(s_i2c_bus, &dev_cfg, &dev);
        if (err == ESP_OK) {
            if (tx && tx_len > 0 && rx && rx_len > 0) {
                err = i2c_master_transmit_receive(dev, tx, tx_len, rx, rx_len, (int)timeout_ms);
            } else if (tx && tx_len > 0) {
                err = i2c_master_transmit(dev, tx, tx_len, (int)timeout_ms);
            } else if (rx && rx_len > 0) {
                err = i2c_master_receive(dev, rx, rx_len, (int)timeout_ms);
            }
            i2c_master_bus_rm_device(dev);
        }
    }
    xSemaphoreGive(s_bus_mtx);
    return err;
}

esp_err_t aguja_hw_uart_config(int tx_pin, int rx_pin, int baud) {
    if (!aguja_hw_pin_is_safe(tx_pin) || !aguja_hw_pin_is_safe(rx_pin) || tx_pin == rx_pin) {
        return ESP_ERR_INVALID_ARG;
    }
    if (baud < 300 || baud > 2000000) baud = 115200;
    xSemaphoreTake(s_bus_mtx, portMAX_DELAY);
    if (s_uart1_init) {
        uart_driver_delete(UART_NUM_1);
        s_uart1_init = false;
    }
    uart_config_t uc = {
        .baud_rate = baud,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    esp_err_t err = uart_driver_install(UART_NUM_1, 1024, 512, 0, NULL, 0);
    if (err == ESP_OK) err = uart_param_config(UART_NUM_1, &uc);
    if (err == ESP_OK) err = uart_set_pin(UART_NUM_1, tx_pin, rx_pin, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (err == ESP_OK) s_uart1_init = true;
    xSemaphoreGive(s_bus_mtx);
    return err;
}

int aguja_hw_uart_tx(const uint8_t *data, size_t len) {
    if (!data || len == 0) return 0;
    if (!s_uart1_init) {
        if (aguja_hw_uart_config(AGUJA_DEFAULT_UART_TX, AGUJA_DEFAULT_UART_RX, 115200) != ESP_OK) return -1;
    }
    return uart_write_bytes(UART_NUM_1, data, len);
}

int aguja_hw_uart_rx(uint8_t *out, size_t max_len, uint32_t timeout_ms) {
    if (!out || max_len == 0) return 0;
    if (!s_uart1_init) {
        if (aguja_hw_uart_config(AGUJA_DEFAULT_UART_TX, AGUJA_DEFAULT_UART_RX, 115200) != ESP_OK) return -1;
    }
    if (timeout_ms > 2000) timeout_ms = 2000;
    return uart_read_bytes(UART_NUM_1, out, max_len, pdMS_TO_TICKS(timeout_ms));
}

esp_err_t aguja_hw_spi_xfer(int sck, int miso, int mosi, int cs, uint32_t clock_hz,
                            const uint8_t *tx, uint8_t *rx, size_t len) {
    if (!aguja_hw_pin_is_safe(sck) || !aguja_hw_pin_is_safe(miso) ||
        !aguja_hw_pin_is_safe(mosi) || (cs >= 0 && !aguja_hw_pin_is_safe(cs))) {
        return ESP_ERR_INVALID_ARG;
    }
    if (len == 0 || len > 256) return ESP_ERR_INVALID_ARG;
    if (clock_hz < 10000 || clock_hz > 10000000) clock_hz = 1000000;

    xSemaphoreTake(s_bus_mtx, portMAX_DELAY);
    spi_bus_config_t bus = {
        .mosi_io_num = mosi,
        .miso_io_num = miso,
        .sclk_io_num = sck,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 256,
    };
    esp_err_t err = spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO);
    if (err == ESP_OK) {
        spi_device_interface_config_t dev_cfg = {
            .clock_speed_hz = (int)clock_hz,
            .mode = 0,
            .spics_io_num = cs,
            .queue_size = 1,
        };
        spi_device_handle_t dev = NULL;
        err = spi_bus_add_device(SPI2_HOST, &dev_cfg, &dev);
        if (err == ESP_OK) {
            spi_transaction_t t = {
                .length = len * 8,
                .tx_buffer = tx,
                .rx_buffer = rx,
            };
            err = spi_device_transmit(dev, &t);
            spi_bus_remove_device(dev);
        }
        spi_bus_free(SPI2_HOST);
    }
    xSemaphoreGive(s_bus_mtx);
    return err;
}

static void led_and_rules_task(void *arg) {
    (void)arg;
    uint32_t tick = 0;
    while (1) {
        /* 1. LED state machine */
        aguja_led_mode_t m = s_led_mode;
        if (m == AGUJA_LED_STATUS) {
            switch (s_net_stage) {
                case AGUJA_NET_STAGE_BOOT:
                case AGUJA_NET_STAGE_WIFI_CONNECTING:
                    led_set_raw((tick % 2) == 0); /* fast blink 200ms */
                    vTaskDelay(pdMS_TO_TICKS(150));
                    break;
                case AGUJA_NET_STAGE_TAILNET_CONNECTING:
                    led_set_raw((tick % 4) < 2); /* medium blink */
                    vTaskDelay(pdMS_TO_TICKS(250));
                    break;
                case AGUJA_NET_STAGE_CONNECTED:
                    /* Brief heartbeat pulse every 3s */
                    led_set_raw((tick % 15) == 0);
                    vTaskDelay(pdMS_TO_TICKS(200));
                    break;
                case AGUJA_NET_STAGE_ERROR:
                    led_set_raw((tick % 2) == 0);
                    vTaskDelay(pdMS_TO_TICKS(80));
                    break;
            }
        } else if (m == AGUJA_LED_BLINK) {
            led_set_raw((tick % 2) == 0);
            uint16_t d = s_led_blink_ms;
            if (d < 50) d = 50;
            vTaskDelay(pdMS_TO_TICKS(d));
        } else {
            vTaskDelay(pdMS_TO_TICKS(250));
        }
        tick++;

        /* 2. Evaluate automation rules ~every 1s */
        if ((tick % 5) == 0) {
            static aguja_config_t cfg;
            aguja_config_get(&cfg);
            int64_t now_s = esp_timer_get_time() / 1000000LL;
            for (int i = 0; i < AGUJA_MAX_RULES; i++) {
                const aguja_rule_t *r = &cfg.rules[i];
                if (!r->enabled || r->trigger_type == 0) continue;
                if (now_s - s_rule_last_fire[i] < (int64_t)(r->cooldown_s ? r->cooldown_s : 10)) continue;

                bool triggered = false;
                int val = 0;
                if (r->trigger_type == 1) { /* gpio_high */
                    val = aguja_hw_gpio_read(r->trigger_pin);
                    triggered = (val == 1);
                } else if (r->trigger_type == 2) { /* gpio_low */
                    val = aguja_hw_gpio_read(r->trigger_pin);
                    triggered = (val == 0);
                } else if (r->trigger_type == 3 || r->trigger_type == 4) { /* adc_gt / adc_lt */
                    int mv = 0;
                    if (aguja_hw_adc_read(r->trigger_pin, NULL, &mv) == ESP_OK) {
                        val = mv;
                        triggered = (r->trigger_type == 3) ? (mv > r->threshold) : (mv < r->threshold);
                    }
                } else if (r->trigger_type == 5) { /* temp_gt (tenths of degC) */
                    float tc = 0;
                    if (aguja_hw_read_temp_c(&tc) == ESP_OK) {
                        val = (int)(tc * 10.0f);
                        triggered = (val > r->threshold);
                    }
                }

                if (triggered) {
                    s_rule_last_fire[i] = now_s;
                    if (r->action_type == 1) {
                        aguja_hw_gpio_config(r->action_pin, "out", "none", false);
                        aguja_hw_gpio_write(r->action_pin, r->action_val ? 1 : 0, false);
                    } else if (r->action_type == 2) {
                        aguja_hw_set_led((aguja_led_mode_t)r->action_val, 50, 300);
                    } else if (r->action_type == 3 && s_alert_cb) {
                        s_alert_cb(r->name, r->alert_msg, val);
                    }
                }
            }
        }
    }
}

esp_err_t aguja_hw_init(void) {
    if (!s_bus_mtx) s_bus_mtx = xSemaphoreCreateMutex();
    memset(s_gpio_out_state, -1, sizeof(s_gpio_out_state));

    aguja_config_t cfg;
    aguja_config_get(&cfg);

    /* 1. RF antenna switch FIRST (before WiFi starts!) */
    aguja_hw_set_antenna(cfg.antenna_external);

    /* 2. User LED */
    gpio_config_t led_io = {
        .pin_bit_mask = (1ULL << AGUJA_USER_LED_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&led_io);
    aguja_hw_set_led((aguja_led_mode_t)cfg.led_mode, cfg.led_pwm_pct, cfg.led_blink_ms);

    /* 3. Internal temperature sensor */
    temperature_sensor_config_t tcfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(-10, 80);
    if (temperature_sensor_install(&tcfg, &s_tsens) == ESP_OK) {
        temperature_sensor_enable(s_tsens);
    }

    /* 4. ADC1 oneshot + curve-fitting calibration */
    adc_oneshot_unit_init_cfg_t adc_cfg = {
        .unit_id = ADC_UNIT_1,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    if (adc_oneshot_new_unit(&adc_cfg, &s_adc1) == ESP_OK) {
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
        adc_cali_curve_fitting_config_t cali_cfg = {
            .unit_id = ADC_UNIT_1,
            .atten = ADC_ATTEN_DB_12,
            .bitwidth = ADC_BITWIDTH_DEFAULT,
        };
        adc_cali_create_scheme_curve_fitting(&cali_cfg, &s_adc_cali);
#endif
    }

    /* 5. CPU frequency */
    aguja_hw_set_cpu_mhz(cfg.cpu_mhz);

    /* 6. Apply boot GPIO presets from NVS */
    for (int i = 0; i < AGUJA_MAX_BOOT_GPIOS; i++) {
        if (cfg.boot_gpios[i].pin < 0) continue;
        const char *m = cfg.boot_gpios[i].mode == 1 ? "out" : (cfg.boot_gpios[i].mode == 2 ? "od" : "in");
        const char *p = cfg.boot_gpios[i].pull == 1 ? "up" : (cfg.boot_gpios[i].pull == 2 ? "down" : "none");
        if (aguja_hw_gpio_config(cfg.boot_gpios[i].pin, m, p, false) == ESP_OK && cfg.boot_gpios[i].mode > 0) {
            aguja_hw_gpio_write(cfg.boot_gpios[i].pin, cfg.boot_gpios[i].level, false);
        }
    }

    ESP_LOGI(TAG, "%s hardware ready (ant=%s, cpu=%uMHz)",
             AGUJA_BOARD_NAME,
             AGUJA_HAS_RF_SWITCH ? (s_antenna_external ? "uFL" : "ceramic") : "pcb", s_cpu_mhz);
    return ESP_OK;
}

void aguja_hw_start_tasks(aguja_rule_alert_cb_t alert_cb) {
    s_alert_cb = alert_cb;
    xTaskCreate(led_and_rules_task, "aguja_hw", 3072, NULL, 3, NULL);
}
