#include "aguja_config.h"
#include "sdkconfig.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"
#include "esp_random.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "aguja_cfg";

#define AGUJA_CFG_MAGIC  0x4147554AUL /* 'AGUJ' */
#define NVS_NS           "aguja_cfg"
#define NVS_KEY_BLOB     "blob_v1"
#define NVS_KEY_INIT     "init_json"

static SemaphoreHandle_t s_mtx = NULL;
static aguja_config_t s_cfg;
static esp_err_t apply_json_locked(const cJSON *root, bool *needs_net_restart, bool *needs_tailnet_restart);

static void strlcpy_safe(char *dst, const char *src, size_t dst_sz) {
    if (!dst || dst_sz == 0) return;
    if (!src) { dst[0] = '\0'; return; }
    size_t n = strlen(src);
    if (n >= dst_sz) n = dst_sz - 1;
    memcpy(dst, src, n);
    dst[n] = '\0';
}

static void generate_token(char *out, size_t out_sz) {
    static const char hex[] = "0123456789abcdef";
    uint8_t rnd[24];
    esp_fill_random(rnd, sizeof(rnd));
    size_t pos = 0;
    const char *pfx = "agj_";
    while (*pfx && pos + 1 < out_sz) out[pos++] = *pfx++;
    for (size_t i = 0; i < sizeof(rnd) && pos + 2 < out_sz; i++) {
        out[pos++] = hex[(rnd[i] >> 4) & 0xF];
        out[pos++] = hex[rnd[i] & 0xF];
    }
    out[pos] = '\0';
}

static void populate_defaults(aguja_config_t *c) {
    memset(c, 0, sizeof(*c));
    c->magic = AGUJA_CFG_MAGIC;
    c->version = AGUJA_CFG_VERSION;

    /* Base WiFi profile (seeded only when compiled with a default SSID;
     * generic Flash Imager builds leave this empty and inject profiles via NVS) */
    if (CONFIG_AGUJA_DEFAULT_WIFI_SSID[0]) {
        c->wifi_count = 1;
        strlcpy_safe(c->wifi[0].ssid, CONFIG_AGUJA_DEFAULT_WIFI_SSID, sizeof(c->wifi[0].ssid));
        strlcpy_safe(c->wifi[0].pass, CONFIG_AGUJA_DEFAULT_WIFI_PASS, sizeof(c->wifi[0].pass));
    } else {
        c->wifi_count = 0;
    }
    c->wifi_tx_power_dbm = 20;
    c->wifi_ps_mode = 0; /* WIFI_PS_NONE for responsive Tailnet/API */

    /* SoftAP NAT gateway */
    c->ap_enabled = true;
    strlcpy_safe(c->ap_ssid, CONFIG_AGUJA_DEFAULT_AP_SSID, sizeof(c->ap_ssid));
    strlcpy_safe(c->ap_pass, CONFIG_AGUJA_DEFAULT_AP_PASS, sizeof(c->ap_pass));
    c->ap_channel = 6;
    c->ap_max_conn = 4;

    /* Tailnet / Headscale */
    strlcpy_safe(c->hostname, CONFIG_AGUJA_DEFAULT_HOSTNAME, sizeof(c->hostname));
    strlcpy_safe(c->ctrl_host, CONFIG_ML_CTRL_HOST, sizeof(c->ctrl_host));
    strlcpy_safe(c->ctrl_noise_pubkey_hex, CONFIG_ML_CTRL_NOISE_PUBKEY_HEX, sizeof(c->ctrl_noise_pubkey_hex));
    strlcpy_safe(c->auth_key, CONFIG_AGUJA_DEFAULT_AUTH_KEY, sizeof(c->auth_key));
    c->derp_region = CONFIG_ML_DERP_REGION;
    c->max_peers = CONFIG_ML_MAX_PEERS;
    c->disco_heartbeat_ms = 3000;
    strlcpy_safe(c->priority_peer_ip, CONFIG_ML_PRIORITY_PEER_IP, sizeof(c->priority_peer_ip));
    c->exit_node_enabled = true;
    c->advertise_upstream_subnet = true;
    c->advertise_ap_subnet = true;
    c->extra_routes[0] = '\0';
    c->dns_relay_enabled = true;
    strlcpy_safe(c->dns_upstream, "1.1.1.1", sizeof(c->dns_upstream));

    /* Hardware */
    c->antenna_external = false; /* onboard ceramic by default */
    c->led_mode = 0;             /* status indicator */
    c->led_pwm_pct = 50;
    c->led_blink_ms = 500;
#if CONFIG_IDF_TARGET_ESP32S3
    c->cpu_mhz = 240;
#else
    c->cpu_mhz = 160;
#endif
    for (int i = 0; i < AGUJA_MAX_BOOT_GPIOS; i++) {
        c->boot_gpios[i].pin = -1;
    }

    /* Control Plane & Beacon */
    if (strlen(CONFIG_AGUJA_DEFAULT_API_TOKEN) > 0) {
        strlcpy_safe(c->api_token, CONFIG_AGUJA_DEFAULT_API_TOKEN, sizeof(c->api_token));
    } else {
        generate_token(c->api_token, sizeof(c->api_token));
    }
    c->http_allow_lan = false; /* tailnet-only by default */
    c->beacon_enabled = true;
    strlcpy_safe(c->beacon_ip, CONFIG_AGUJA_DEFAULT_BEACON_IP, sizeof(c->beacon_ip));
    c->beacon_port = CONFIG_AGUJA_DEFAULT_BEACON_PORT;
    c->beacon_interval_s = 60;
}

static esp_err_t save_locked(void) {
    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READWRITE, &h);
    if (err != ESP_OK) return err;
    err = nvs_set_blob(h, NVS_KEY_BLOB, &s_cfg, sizeof(s_cfg));
    if (err == ESP_OK) err = nvs_commit(h);
    nvs_close(h);
    return err;
}

esp_err_t aguja_config_init(void) {
    if (!s_mtx) s_mtx = xSemaphoreCreateMutex();
    xSemaphoreTake(s_mtx, portMAX_DELAY);

    populate_defaults(&s_cfg);

    nvs_handle_t h;
    esp_err_t err = nvs_open(NVS_NS, NVS_READWRITE, &h);
    bool loaded = false;
    bool bootstrapped = false;
    if (err == ESP_OK) {
        /* 1. Check for Flash Imager pure-JSON bootstrap key first */
        size_t jlen = 0;
        if (nvs_get_str(h, NVS_KEY_INIT, NULL, &jlen) == ESP_OK && jlen > 2 && jlen <= 8192) {
            char *jbuf = malloc(jlen);
            if (jbuf && nvs_get_str(h, NVS_KEY_INIT, jbuf, &jlen) == ESP_OK) {
                cJSON *root = cJSON_Parse(jbuf);
                if (root && cJSON_IsObject(root)) {
                    apply_json_locked(root, NULL, NULL);
                    nvs_erase_key(h, NVS_KEY_INIT);
                    nvs_commit(h);
                    loaded = true;
                    bootstrapped = true;
                    ESP_LOGI(TAG, "Provisioned config from NVS init_json (%u bytes)", (unsigned)jlen);
                }
                if (root) cJSON_Delete(root);
            }
            free(jbuf);
        }

        /* 2. Otherwise load persisted binary blob_v1 */
        if (!bootstrapped) {
            size_t sz = sizeof(s_cfg);
            aguja_config_t *tmp = malloc(sizeof(aguja_config_t));
            if (tmp && nvs_get_blob(h, NVS_KEY_BLOB, tmp, &sz) == ESP_OK &&
                sz == sizeof(*tmp) && tmp->magic == AGUJA_CFG_MAGIC &&
                tmp->version == AGUJA_CFG_VERSION) {
                s_cfg = *tmp;
                loaded = true;
            }
            free(tmp);
        }
        nvs_close(h);
    }

    /* If compiled auth_key or token was empty in NVS, backfill from Kconfig */
    bool dirty = !loaded || bootstrapped;
    if (!s_cfg.auth_key[0] && CONFIG_AGUJA_DEFAULT_AUTH_KEY[0]) {
        strlcpy_safe(s_cfg.auth_key, CONFIG_AGUJA_DEFAULT_AUTH_KEY, sizeof(s_cfg.auth_key));
        dirty = true;
    }
    if (!s_cfg.api_token[0]) {
        if (CONFIG_AGUJA_DEFAULT_API_TOKEN[0]) {
            strlcpy_safe(s_cfg.api_token, CONFIG_AGUJA_DEFAULT_API_TOKEN, sizeof(s_cfg.api_token));
        } else {
            generate_token(s_cfg.api_token, sizeof(s_cfg.api_token));
        }
        dirty = true;
    }
    if (dirty) {
        save_locked();
    }

    ESP_LOGI(TAG, "Config %s: host=%s ctrl=%s wifi[0]=%s ap=%d exit=%d",
             loaded ? "loaded from NVS" : "initialized defaults",
             s_cfg.hostname, s_cfg.ctrl_host,
             s_cfg.wifi_count > 0 ? s_cfg.wifi[0].ssid : "(none)",
             (int)s_cfg.ap_enabled, (int)s_cfg.exit_node_enabled);

    xSemaphoreGive(s_mtx);
    return ESP_OK;
}

void aguja_config_get(aguja_config_t *out) {
    if (!out) return;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    *out = s_cfg;
    xSemaphoreGive(s_mtx);
}

esp_err_t aguja_config_set(const aguja_config_t *in) {
    if (!in) return ESP_ERR_INVALID_ARG;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_cfg = *in;
    s_cfg.magic = AGUJA_CFG_MAGIC;
    s_cfg.version = AGUJA_CFG_VERSION;
    esp_err_t err = save_locked();
    xSemaphoreGive(s_mtx);
    return err;
}

esp_err_t aguja_config_reset_defaults(void) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    populate_defaults(&s_cfg);
    esp_err_t err = save_locked();
    xSemaphoreGive(s_mtx);
    return err;
}

static const char *trigger_name(uint8_t t) {
    switch (t) {
        case 1: return "gpio_high";
        case 2: return "gpio_low";
        case 3: return "adc_gt";
        case 4: return "adc_lt";
        case 5: return "temp_gt";
        default: return "none";
    }
}

static uint8_t parse_trigger(const char *s) {
    if (!s) return 0;
    if (strcmp(s, "gpio_high") == 0) return 1;
    if (strcmp(s, "gpio_low") == 0) return 2;
    if (strcmp(s, "adc_gt") == 0) return 3;
    if (strcmp(s, "adc_lt") == 0) return 4;
    if (strcmp(s, "temp_gt") == 0) return 5;
    return 0;
}

static const char *action_name(uint8_t a) {
    switch (a) {
        case 1: return "gpio_set";
        case 2: return "led";
        case 3: return "udp_alert";
        default: return "none";
    }
}

static uint8_t parse_action(const char *s) {
    if (!s) return 0;
    if (strcmp(s, "gpio_set") == 0) return 1;
    if (strcmp(s, "led") == 0) return 2;
    if (strcmp(s, "udp_alert") == 0) return 3;
    return 0;
}

cJSON *aguja_config_rules_to_json(void) {
    cJSON *arr = cJSON_CreateArray();
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    for (int i = 0; i < AGUJA_MAX_RULES; i++) {
        const aguja_rule_t *r = &s_cfg.rules[i];
        if (!r->name[0] && r->trigger_type == 0) continue;
        cJSON *o = cJSON_CreateObject();
        cJSON_AddNumberToObject(o, "id", i);
        cJSON_AddBoolToObject(o, "enabled", r->enabled != 0);
        cJSON_AddStringToObject(o, "name", r->name);
        cJSON_AddStringToObject(o, "trigger", trigger_name(r->trigger_type));
        cJSON_AddNumberToObject(o, "trigger_pin", r->trigger_pin);
        cJSON_AddNumberToObject(o, "threshold", r->threshold);
        cJSON_AddStringToObject(o, "action", action_name(r->action_type));
        cJSON_AddNumberToObject(o, "action_pin", r->action_pin);
        cJSON_AddNumberToObject(o, "action_val", r->action_val);
        cJSON_AddNumberToObject(o, "cooldown_s", r->cooldown_s);
        cJSON_AddStringToObject(o, "alert_msg", r->alert_msg);
        cJSON_AddItemToArray(arr, o);
    }
    xSemaphoreGive(s_mtx);
    return arr;
}

esp_err_t aguja_config_set_rules_json(const cJSON *rules_arr) {
    if (!cJSON_IsArray(rules_arr)) return ESP_ERR_INVALID_ARG;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    memset(s_cfg.rules, 0, sizeof(s_cfg.rules));
    int idx = 0;
    const cJSON *item = NULL;
    cJSON_ArrayForEach(item, rules_arr) {
        if (idx >= AGUJA_MAX_RULES) break;
        if (!cJSON_IsObject(item)) continue;
        aguja_rule_t *r = &s_cfg.rules[idx++];
        const cJSON *j;
        if ((j = cJSON_GetObjectItem(item, "enabled")) && cJSON_IsBool(j)) r->enabled = cJSON_IsTrue(j) ? 1 : 0;
        else r->enabled = 1;
        if ((j = cJSON_GetObjectItem(item, "name")) && cJSON_IsString(j)) strlcpy_safe(r->name, j->valuestring, sizeof(r->name));
        if ((j = cJSON_GetObjectItem(item, "trigger")) && cJSON_IsString(j)) r->trigger_type = parse_trigger(j->valuestring);
        if ((j = cJSON_GetObjectItem(item, "trigger_pin")) && cJSON_IsNumber(j)) r->trigger_pin = (int8_t)j->valueint;
        if ((j = cJSON_GetObjectItem(item, "threshold")) && cJSON_IsNumber(j)) r->threshold = j->valueint;
        if ((j = cJSON_GetObjectItem(item, "action")) && cJSON_IsString(j)) r->action_type = parse_action(j->valuestring);
        if ((j = cJSON_GetObjectItem(item, "action_pin")) && cJSON_IsNumber(j)) r->action_pin = (int8_t)j->valueint;
        if ((j = cJSON_GetObjectItem(item, "action_val")) && cJSON_IsNumber(j)) r->action_val = j->valueint;
        if ((j = cJSON_GetObjectItem(item, "cooldown_s")) && cJSON_IsNumber(j)) r->cooldown_s = (uint32_t)j->valueint;
        else r->cooldown_s = 10;
        if ((j = cJSON_GetObjectItem(item, "alert_msg")) && cJSON_IsString(j)) strlcpy_safe(r->alert_msg, j->valuestring, sizeof(r->alert_msg));
    }
    esp_err_t err = save_locked();
    xSemaphoreGive(s_mtx);
    return err;
}

cJSON *aguja_config_to_json(bool include_secrets) {
    aguja_config_t *cp = malloc(sizeof(aguja_config_t));
    if (!cp) return cJSON_CreateObject();
    aguja_config_get(cp);
#define c (*cp)

    cJSON *root = cJSON_CreateObject();

    /* WiFi */
    cJSON *wifi = cJSON_AddObjectToObject(root, "wifi");
    cJSON *profiles = cJSON_AddArrayToObject(wifi, "profiles");
    for (int i = 0; i < c.wifi_count && i < AGUJA_MAX_WIFI_PROFILES; i++) {
        cJSON *p = cJSON_CreateObject();
        cJSON_AddStringToObject(p, "ssid", c.wifi[i].ssid);
        cJSON_AddStringToObject(p, "pass", include_secrets ? c.wifi[i].pass : (c.wifi[i].pass[0] ? "***" : ""));
        cJSON_AddItemToArray(profiles, p);
    }
    cJSON_AddNumberToObject(wifi, "tx_power_dbm", c.wifi_tx_power_dbm);
    cJSON_AddNumberToObject(wifi, "ps_mode", c.wifi_ps_mode);

    /* SoftAP */
    cJSON *ap = cJSON_AddObjectToObject(root, "ap");
    cJSON_AddBoolToObject(ap, "enabled", c.ap_enabled);
    cJSON_AddStringToObject(ap, "ssid", c.ap_ssid);
    cJSON_AddStringToObject(ap, "pass", include_secrets ? c.ap_pass : (c.ap_pass[0] ? "***" : ""));
    cJSON_AddNumberToObject(ap, "channel", c.ap_channel);
    cJSON_AddNumberToObject(ap, "max_conn", c.ap_max_conn);

    /* Tailnet */
    cJSON *tn = cJSON_AddObjectToObject(root, "tailnet");
    cJSON_AddStringToObject(tn, "hostname", c.hostname);
    cJSON_AddStringToObject(tn, "ctrl_host", c.ctrl_host);
    cJSON_AddStringToObject(tn, "ctrl_noise_pubkey_hex", c.ctrl_noise_pubkey_hex);
    cJSON_AddStringToObject(tn, "auth_key", include_secrets ? c.auth_key : (c.auth_key[0] ? "***" : ""));
    cJSON_AddNumberToObject(tn, "derp_region", c.derp_region);
    cJSON_AddNumberToObject(tn, "max_peers", c.max_peers);
    cJSON_AddNumberToObject(tn, "disco_heartbeat_ms", c.disco_heartbeat_ms);
    cJSON_AddStringToObject(tn, "priority_peer_ip", c.priority_peer_ip);
    cJSON_AddBoolToObject(tn, "exit_node_enabled", c.exit_node_enabled);
    cJSON_AddBoolToObject(tn, "advertise_upstream_subnet", c.advertise_upstream_subnet);
    cJSON_AddBoolToObject(tn, "advertise_ap_subnet", c.advertise_ap_subnet);
    cJSON_AddStringToObject(tn, "extra_routes", c.extra_routes);
    cJSON_AddBoolToObject(tn, "dns_relay_enabled", c.dns_relay_enabled);
    cJSON_AddStringToObject(tn, "dns_upstream", c.dns_upstream);

    /* Hardware */
    cJSON *hw = cJSON_AddObjectToObject(root, "hw");
    cJSON_AddBoolToObject(hw, "antenna_external", c.antenna_external);
    cJSON_AddNumberToObject(hw, "led_mode", c.led_mode);
    cJSON_AddNumberToObject(hw, "led_pwm_pct", c.led_pwm_pct);
    cJSON_AddNumberToObject(hw, "led_blink_ms", c.led_blink_ms);
    cJSON_AddNumberToObject(hw, "cpu_mhz", c.cpu_mhz);
    cJSON *bg = cJSON_AddArrayToObject(hw, "boot_gpios");
    for (int i = 0; i < AGUJA_MAX_BOOT_GPIOS; i++) {
        if (c.boot_gpios[i].pin < 0) continue;
        cJSON *g = cJSON_CreateObject();
        cJSON_AddNumberToObject(g, "pin", c.boot_gpios[i].pin);
        cJSON_AddNumberToObject(g, "mode", c.boot_gpios[i].mode);
        cJSON_AddNumberToObject(g, "pull", c.boot_gpios[i].pull);
        cJSON_AddNumberToObject(g, "level", c.boot_gpios[i].level);
        cJSON_AddItemToArray(bg, g);
    }

    /* Agent */
    cJSON *ag = cJSON_AddObjectToObject(root, "agent");
    cJSON_AddStringToObject(ag, "api_token", include_secrets ? c.api_token : "***");
    cJSON_AddBoolToObject(ag, "http_allow_lan", c.http_allow_lan);
    cJSON_AddBoolToObject(ag, "beacon_enabled", c.beacon_enabled);
    cJSON_AddStringToObject(ag, "beacon_ip", c.beacon_ip);
    cJSON_AddNumberToObject(ag, "beacon_port", c.beacon_port);
    cJSON_AddNumberToObject(ag, "beacon_interval_s", c.beacon_interval_s);

    cJSON_AddItemToObject(root, "rules", aguja_config_rules_to_json());
#undef c
    free(cp);
    return root;
}

static bool is_redacted(const char *s) {
    return !s || strcmp(s, "***") == 0;
}

static esp_err_t apply_json_locked(const cJSON *root, bool *needs_net_restart, bool *needs_tailnet_restart) {
    if (!cJSON_IsObject(root)) return ESP_ERR_INVALID_ARG;
    bool net_chg = false, tn_chg = false;
    const cJSON *sec, *j;

    /* WiFi */
    if ((sec = cJSON_GetObjectItem(root, "wifi")) && cJSON_IsObject(sec)) {
        if ((j = cJSON_GetObjectItem(sec, "profiles")) && cJSON_IsArray(j)) {
            int n = 0;
            const cJSON *item;
            cJSON_ArrayForEach(item, j) {
                if (n >= AGUJA_MAX_WIFI_PROFILES || !cJSON_IsObject(item)) break;
                const cJSON *ssid = cJSON_GetObjectItem(item, "ssid");
                const cJSON *pass = cJSON_GetObjectItem(item, "pass");
                if (cJSON_IsString(ssid) && ssid->valuestring[0]) {
                    char prev_pass[65] = {0};
                    /* Preserve existing pass if redacted */
                    for (int k = 0; k < s_cfg.wifi_count; k++) {
                        if (strcmp(s_cfg.wifi[k].ssid, ssid->valuestring) == 0) {
                            strlcpy_safe(prev_pass, s_cfg.wifi[k].pass, sizeof(prev_pass));
                            break;
                        }
                    }
                    strlcpy_safe(s_cfg.wifi[n].ssid, ssid->valuestring, sizeof(s_cfg.wifi[n].ssid));
                    if (cJSON_IsString(pass) && !is_redacted(pass->valuestring)) {
                        strlcpy_safe(s_cfg.wifi[n].pass, pass->valuestring, sizeof(s_cfg.wifi[n].pass));
                    } else {
                        strlcpy_safe(s_cfg.wifi[n].pass, prev_pass, sizeof(s_cfg.wifi[n].pass));
                    }
                    n++;
                }
            }
            if (n > 0) {
                s_cfg.wifi_count = (uint8_t)n;
                net_chg = true;
            }
        }
        if ((j = cJSON_GetObjectItem(sec, "tx_power_dbm")) && cJSON_IsNumber(j)) {
            int v = j->valueint;
            if (v >= 8 && v <= 20) s_cfg.wifi_tx_power_dbm = (int8_t)v;
        }
        if ((j = cJSON_GetObjectItem(sec, "ps_mode")) && cJSON_IsNumber(j)) {
            if (j->valueint >= 0 && j->valueint <= 2) s_cfg.wifi_ps_mode = (uint8_t)j->valueint;
        }
    }

    /* SoftAP */
    if ((sec = cJSON_GetObjectItem(root, "ap")) && cJSON_IsObject(sec)) {
        if ((j = cJSON_GetObjectItem(sec, "enabled")) && cJSON_IsBool(j)) {
            s_cfg.ap_enabled = cJSON_IsTrue(j);
            net_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "ssid")) && cJSON_IsString(j) && j->valuestring[0]) {
            strlcpy_safe(s_cfg.ap_ssid, j->valuestring, sizeof(s_cfg.ap_ssid));
            net_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "pass")) && cJSON_IsString(j) && !is_redacted(j->valuestring)) {
            strlcpy_safe(s_cfg.ap_pass, j->valuestring, sizeof(s_cfg.ap_pass));
            net_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "channel")) && cJSON_IsNumber(j) && j->valueint >= 1 && j->valueint <= 13) {
            s_cfg.ap_channel = (uint8_t)j->valueint;
            net_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "max_conn")) && cJSON_IsNumber(j) && j->valueint >= 1 && j->valueint <= 8) {
            s_cfg.ap_max_conn = (uint8_t)j->valueint;
            net_chg = true;
        }
    }

    /* Tailnet */
    if ((sec = cJSON_GetObjectItem(root, "tailnet")) && cJSON_IsObject(sec)) {
        if ((j = cJSON_GetObjectItem(sec, "hostname")) && cJSON_IsString(j) && j->valuestring[0]) {
            strlcpy_safe(s_cfg.hostname, j->valuestring, sizeof(s_cfg.hostname));
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "ctrl_host")) && cJSON_IsString(j) && j->valuestring[0]) {
            strlcpy_safe(s_cfg.ctrl_host, j->valuestring, sizeof(s_cfg.ctrl_host));
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "ctrl_noise_pubkey_hex")) && cJSON_IsString(j)) {
            strlcpy_safe(s_cfg.ctrl_noise_pubkey_hex, j->valuestring, sizeof(s_cfg.ctrl_noise_pubkey_hex));
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "auth_key")) && cJSON_IsString(j) && !is_redacted(j->valuestring)) {
            strlcpy_safe(s_cfg.auth_key, j->valuestring, sizeof(s_cfg.auth_key));
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "derp_region")) && cJSON_IsNumber(j) && j->valueint > 0) {
            s_cfg.derp_region = (uint16_t)j->valueint;
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "max_peers")) && cJSON_IsNumber(j) && j->valueint >= 1 && j->valueint <= 64) {
            s_cfg.max_peers = (uint8_t)j->valueint;
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "disco_heartbeat_ms")) && cJSON_IsNumber(j) && j->valueint >= 500) {
            s_cfg.disco_heartbeat_ms = (uint16_t)j->valueint;
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "priority_peer_ip")) && cJSON_IsString(j)) {
            strlcpy_safe(s_cfg.priority_peer_ip, j->valuestring, sizeof(s_cfg.priority_peer_ip));
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "exit_node_enabled")) && cJSON_IsBool(j)) {
            s_cfg.exit_node_enabled = cJSON_IsTrue(j);
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "advertise_upstream_subnet")) && cJSON_IsBool(j)) {
            s_cfg.advertise_upstream_subnet = cJSON_IsTrue(j);
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "advertise_ap_subnet")) && cJSON_IsBool(j)) {
            s_cfg.advertise_ap_subnet = cJSON_IsTrue(j);
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "extra_routes")) && cJSON_IsString(j)) {
            strlcpy_safe(s_cfg.extra_routes, j->valuestring, sizeof(s_cfg.extra_routes));
            tn_chg = true;
        }
        if ((j = cJSON_GetObjectItem(sec, "dns_relay_enabled")) && cJSON_IsBool(j)) {
            s_cfg.dns_relay_enabled = cJSON_IsTrue(j);
        }
        if ((j = cJSON_GetObjectItem(sec, "dns_upstream")) && cJSON_IsString(j) && j->valuestring[0]) {
            strlcpy_safe(s_cfg.dns_upstream, j->valuestring, sizeof(s_cfg.dns_upstream));
        }
    }

    /* Hardware */
    if ((sec = cJSON_GetObjectItem(root, "hw")) && cJSON_IsObject(sec)) {
        if ((j = cJSON_GetObjectItem(sec, "antenna_external")) && cJSON_IsBool(j)) {
            s_cfg.antenna_external = cJSON_IsTrue(j);
        }
        if ((j = cJSON_GetObjectItem(sec, "led_mode")) && cJSON_IsNumber(j)) {
            s_cfg.led_mode = (uint8_t)j->valueint;
        }
        if ((j = cJSON_GetObjectItem(sec, "led_pwm_pct")) && cJSON_IsNumber(j)) {
            s_cfg.led_pwm_pct = (uint8_t)j->valueint;
        }
        if ((j = cJSON_GetObjectItem(sec, "led_blink_ms")) && cJSON_IsNumber(j)) {
            s_cfg.led_blink_ms = (uint16_t)j->valueint;
        }
        if ((j = cJSON_GetObjectItem(sec, "cpu_mhz")) && cJSON_IsNumber(j)) {
            int m = j->valueint;
#if CONFIG_IDF_TARGET_ESP32S3
            if (m == 80 || m == 160 || m == 240) s_cfg.cpu_mhz = (uint16_t)m;
#else
            if (m == 40 || m == 80 || m == 160) s_cfg.cpu_mhz = (uint16_t)m;
#endif
        }
        if ((j = cJSON_GetObjectItem(sec, "boot_gpios")) && cJSON_IsArray(j)) {
            for (int i = 0; i < AGUJA_MAX_BOOT_GPIOS; i++) s_cfg.boot_gpios[i].pin = -1;
            int idx = 0;
            const cJSON *g;
            cJSON_ArrayForEach(g, j) {
                if (idx >= AGUJA_MAX_BOOT_GPIOS || !cJSON_IsObject(g)) break;
                const cJSON *pin = cJSON_GetObjectItem(g, "pin");
                if (cJSON_IsNumber(pin)) {
                    s_cfg.boot_gpios[idx].pin = (int8_t)pin->valueint;
                    const cJSON *f;
                    s_cfg.boot_gpios[idx].mode = ((f = cJSON_GetObjectItem(g, "mode")) && cJSON_IsNumber(f)) ? (uint8_t)f->valueint : 0;
                    s_cfg.boot_gpios[idx].pull = ((f = cJSON_GetObjectItem(g, "pull")) && cJSON_IsNumber(f)) ? (uint8_t)f->valueint : 0;
                    s_cfg.boot_gpios[idx].level = ((f = cJSON_GetObjectItem(g, "level")) && cJSON_IsNumber(f)) ? (uint8_t)(f->valueint ? 1 : 0) : 0;
                    idx++;
                }
            }
        }
    }

    /* Agent */
    if ((sec = cJSON_GetObjectItem(root, "agent")) && cJSON_IsObject(sec)) {
        if ((j = cJSON_GetObjectItem(sec, "api_token")) && cJSON_IsString(j) &&
            !is_redacted(j->valuestring) && strlen(j->valuestring) >= 8) {
            strlcpy_safe(s_cfg.api_token, j->valuestring, sizeof(s_cfg.api_token));
        }
        if ((j = cJSON_GetObjectItem(sec, "http_allow_lan")) && cJSON_IsBool(j)) {
            s_cfg.http_allow_lan = cJSON_IsTrue(j);
        }
        if ((j = cJSON_GetObjectItem(sec, "beacon_enabled")) && cJSON_IsBool(j)) {
            s_cfg.beacon_enabled = cJSON_IsTrue(j);
        }
        if ((j = cJSON_GetObjectItem(sec, "beacon_ip")) && cJSON_IsString(j)) {
            strlcpy_safe(s_cfg.beacon_ip, j->valuestring, sizeof(s_cfg.beacon_ip));
        }
        if ((j = cJSON_GetObjectItem(sec, "beacon_port")) && cJSON_IsNumber(j) && j->valueint > 0) {
            s_cfg.beacon_port = (uint16_t)j->valueint;
        }
        if ((j = cJSON_GetObjectItem(sec, "beacon_interval_s")) && cJSON_IsNumber(j) && j->valueint >= 5) {
            s_cfg.beacon_interval_s = (uint16_t)j->valueint;
        }
    }

    if (needs_net_restart) *needs_net_restart = net_chg;
    if (needs_tailnet_restart) *needs_tailnet_restart = tn_chg;
    return ESP_OK;
}

esp_err_t aguja_config_apply_json(const cJSON *root, bool *needs_net_restart, bool *needs_tailnet_restart) {
    if (!cJSON_IsObject(root)) return ESP_ERR_INVALID_ARG;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    esp_err_t err = apply_json_locked(root, needs_net_restart, needs_tailnet_restart);
    if (err == ESP_OK) err = save_locked();
    xSemaphoreGive(s_mtx);

    /* Rules (uses its own lock) */
    const cJSON *j;
    if ((j = cJSON_GetObjectItem(root, "rules")) && cJSON_IsArray(j)) {
        aguja_config_set_rules_json(j);
    }
    return err;
}

esp_err_t aguja_config_set_wifi_primary(const char *ssid, const char *pass) {
    if (!ssid || !ssid[0]) return ESP_ERR_INVALID_ARG;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    /* Shift existing profiles down if ssid not already at 0 */
    int found = -1;
    for (int i = 0; i < s_cfg.wifi_count; i++) {
        if (strcmp(s_cfg.wifi[i].ssid, ssid) == 0) { found = i; break; }
    }
    if (found > 0) {
        for (int i = found; i > 0; i--) s_cfg.wifi[i] = s_cfg.wifi[i - 1];
    } else if (found < 0) {
        int lim = s_cfg.wifi_count < AGUJA_MAX_WIFI_PROFILES ? s_cfg.wifi_count : AGUJA_MAX_WIFI_PROFILES - 1;
        for (int i = lim; i > 0; i--) s_cfg.wifi[i] = s_cfg.wifi[i - 1];
        if (s_cfg.wifi_count < AGUJA_MAX_WIFI_PROFILES) s_cfg.wifi_count++;
    }
    strlcpy_safe(s_cfg.wifi[0].ssid, ssid, sizeof(s_cfg.wifi[0].ssid));
    strlcpy_safe(s_cfg.wifi[0].pass, pass ? pass : "", sizeof(s_cfg.wifi[0].pass));
    esp_err_t err = save_locked();
    xSemaphoreGive(s_mtx);
    return err;
}

esp_err_t aguja_config_set_auth_key(const char *auth_key) {
    if (!auth_key) return ESP_ERR_INVALID_ARG;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    strlcpy_safe(s_cfg.auth_key, auth_key, sizeof(s_cfg.auth_key));
    esp_err_t err = save_locked();
    xSemaphoreGive(s_mtx);
    return err;
}

esp_err_t aguja_config_set_antenna(bool external) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_cfg.antenna_external = external;
    esp_err_t err = save_locked();
    xSemaphoreGive(s_mtx);
    return err;
}

esp_err_t aguja_config_set_ap(bool enabled, const char *ssid, const char *pass, uint8_t channel) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    s_cfg.ap_enabled = enabled;
    if (ssid && ssid[0]) strlcpy_safe(s_cfg.ap_ssid, ssid, sizeof(s_cfg.ap_ssid));
    if (pass) strlcpy_safe(s_cfg.ap_pass, pass, sizeof(s_cfg.ap_pass));
    if (channel >= 1 && channel <= 13) s_cfg.ap_channel = channel;
    esp_err_t err = save_locked();
    xSemaphoreGive(s_mtx);
    return err;
}

bool aguja_config_http_allow_lan(void) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    bool v = s_cfg.http_allow_lan;
    xSemaphoreGive(s_mtx);
    return v;
}

bool aguja_config_check_token(const char *candidate) {
    if (!candidate) return false;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    const char *tok = s_cfg.api_token;
    size_t la = strlen(candidate), lb = strlen(tok);
    size_t m = la > lb ? la : lb;
    unsigned char diff = (la != lb) ? 1 : 0;
    for (size_t i = 0; i < m; i++) {
        unsigned char ca = i < la ? (unsigned char)candidate[i] : 0;
        unsigned char cb = i < lb ? (unsigned char)tok[i] : 0;
        diff |= (ca ^ cb);
    }
    xSemaphoreGive(s_mtx);
    return diff == 0;
}

void aguja_config_get_token(char *out, size_t out_sz) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    strlcpy_safe(out, s_cfg.api_token, out_sz);
    xSemaphoreGive(s_mtx);
}

void aguja_config_get_hostname(char *out, size_t out_sz) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    strlcpy_safe(out, s_cfg.hostname, out_sz);
    xSemaphoreGive(s_mtx);
}

uint8_t aguja_config_get_wifi_profile(int idx, char *ssid_out, size_t ssid_sz, char *pass_out, size_t pass_sz) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    uint8_t count = s_cfg.wifi_count;
    if (count > 0) {
        int i = idx % count;
        if (ssid_out) strlcpy_safe(ssid_out, s_cfg.wifi[i].ssid, ssid_sz);
        if (pass_out) strlcpy_safe(pass_out, s_cfg.wifi[i].pass, pass_sz);
    } else {
        if (ssid_out && ssid_sz) ssid_out[0] = '\0';
        if (pass_out && pass_sz) pass_out[0] = '\0';
    }
    xSemaphoreGive(s_mtx);
    return count;
}

void aguja_config_get_dns(bool *enabled, char *upstream_out, size_t upstream_sz) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    if (enabled) *enabled = s_cfg.dns_relay_enabled;
    if (upstream_out) strlcpy_safe(upstream_out, s_cfg.dns_upstream, upstream_sz);
    xSemaphoreGive(s_mtx);
}

void aguja_config_get_beacon(bool *enabled, char *ip_out, size_t ip_sz, uint16_t *port, uint16_t *interval_s) {
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    if (enabled) *enabled = s_cfg.beacon_enabled;
    if (ip_out) strlcpy_safe(ip_out, s_cfg.beacon_ip, ip_sz);
    if (port) *port = s_cfg.beacon_port;
    if (interval_s) *interval_s = s_cfg.beacon_interval_s;
    xSemaphoreGive(s_mtx);
}
