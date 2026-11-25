#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "cJSON.h"

#ifdef __cplusplus
extern "C" {
#endif

#define AGUJA_CFG_VERSION        1
#define AGUJA_MAX_WIFI_PROFILES  8
#define AGUJA_MAX_BOOT_GPIOS     8
#define AGUJA_MAX_RULES          8

typedef struct {
    char ssid[33];
    char pass[65];
} aguja_wifi_profile_t;

typedef struct {
    int8_t  pin;      /* -1 = unused */
    uint8_t mode;     /* 0=in, 1=out, 2=od */
    uint8_t pull;     /* 0=none, 1=up, 2=down */
    uint8_t level;    /* 0 or 1 */
} aguja_boot_gpio_t;

typedef struct {
    uint8_t  enabled;
    char     name[24];
    uint8_t  trigger_type;  /* 0=none, 1=gpio_high, 2=gpio_low, 3=adc_gt, 4=adc_lt, 5=temp_gt */
    int8_t   trigger_pin;
    int32_t  threshold;     /* mV for ADC, tenths of degC for temp */
    uint8_t  action_type;   /* 0=none, 1=gpio_set, 2=led, 3=udp_alert */
    int8_t   action_pin;
    int32_t  action_val;
    uint32_t cooldown_s;
    char     alert_msg[48];
} aguja_rule_t;

typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t reserved;

    /* WiFi STA */
    uint8_t wifi_count;
    aguja_wifi_profile_t wifi[AGUJA_MAX_WIFI_PROFILES];
    int8_t  wifi_tx_power_dbm;  /* 8..20, 0 = default 20 */
    uint8_t wifi_ps_mode;       /* 0=none, 1=min_modem, 2=max_modem */

    /* SoftAP NAT Gateway */
    bool    ap_enabled;
    char    ap_ssid[33];
    char    ap_pass[65];
    uint8_t ap_channel;
    uint8_t ap_max_conn;

    /* Tailnet / Headscale */
    char     hostname[48];
    char     ctrl_host[64];
    char     ctrl_noise_pubkey_hex[65];
    char     auth_key[128];
    uint16_t derp_region;
    uint8_t  max_peers;
    uint16_t disco_heartbeat_ms;
    char     priority_peer_ip[20];
    bool     exit_node_enabled;
    bool     advertise_upstream_subnet;
    bool     advertise_ap_subnet;
    char     extra_routes[128];
    bool     dns_relay_enabled;
    char     dns_upstream[20];

    /* Hardware */
    bool    antenna_external;   /* false=ceramic(LOW), true=uFL(HIGH) */
    uint8_t led_mode;           /* 0=status, 1=off, 2=on, 3=blink, 4=pwm */
    uint8_t led_pwm_pct;
    uint16_t led_blink_ms;
    uint16_t cpu_mhz;           /* 40, 80, 160 */
    aguja_boot_gpio_t boot_gpios[AGUJA_MAX_BOOT_GPIOS];

    /* Agent Control Plane & Beacon */
    char     api_token[65];
    bool     http_allow_lan;
    bool     beacon_enabled;
    char     beacon_ip[20];
    uint16_t beacon_port;
    uint16_t beacon_interval_s;

    /* Automation rules */
    aguja_rule_t rules[AGUJA_MAX_RULES];
} aguja_config_t;

esp_err_t aguja_config_init(void);
void aguja_config_get(aguja_config_t *out);
esp_err_t aguja_config_set(const aguja_config_t *in);
esp_err_t aguja_config_reset_defaults(void);

/* JSON serialization (include_secrets=false redacts auth_key/wifi pass/token) */
cJSON *aguja_config_to_json(bool include_secrets);
esp_err_t aguja_config_apply_json(const cJSON *root, bool *needs_net_restart, bool *needs_tailnet_restart);

/* Lightweight zero-stack getters for event/ISR-adjacent/small-stack tasks */
bool aguja_config_http_allow_lan(void);
bool aguja_config_check_token(const char *candidate);
void aguja_config_get_token(char *out, size_t out_sz);
void aguja_config_get_hostname(char *out, size_t out_sz);
uint8_t aguja_config_get_wifi_profile(int idx, char *ssid_out, size_t ssid_sz, char *pass_out, size_t pass_sz);
void aguja_config_get_dns(bool *enabled, char *upstream_out, size_t upstream_sz);
void aguja_config_get_beacon(bool *enabled, char *ip_out, size_t ip_sz, uint16_t *port, uint16_t *interval_s);

/* Direct helpers */
esp_err_t aguja_config_set_wifi_primary(const char *ssid, const char *pass);
esp_err_t aguja_config_set_auth_key(const char *auth_key);
esp_err_t aguja_config_set_antenna(bool external);
esp_err_t aguja_config_set_ap(bool enabled, const char *ssid, const char *pass, uint8_t channel);
esp_err_t aguja_config_set_rules_json(const cJSON *rules_arr);
cJSON *aguja_config_rules_to_json(void);

#ifdef __cplusplus
}
#endif
