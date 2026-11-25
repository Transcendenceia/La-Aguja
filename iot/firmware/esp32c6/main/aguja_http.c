#include "aguja_http.h"
#include "aguja_webui.h"
#include "aguja_config.h"
#include "aguja_hw.h"
#include "aguja_net.h"
#include "aguja_log.h"
#include "microlink.h"
#include "esp_http_server.h"
#include "esp_ota_ops.h"
#include "esp_app_desc.h"
#include "esp_chip_info.h"
#include "esp_mac.h"
#include "esp_sleep.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_netif.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "mbedtls/base64.h"
#include "lwip/sockets.h"
#include "cJSON.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

static const char *TAG = "aguja_http";
static httpd_handle_t s_httpd = NULL;

/* ============================================================================
 * Access Control: Tailnet VPN IP only (unless http_allow_lan=true) + Token/Basic Auth
 * ========================================================================== */

static bool request_local_ipv4(httpd_req_t *req, uint32_t *ip_out) {
    int fd = httpd_req_to_sockfd(req);
    struct sockaddr_storage ss;
    socklen_t sl = sizeof(ss);
    if (getsockname(fd, (struct sockaddr *)&ss, &sl) != 0) return false;
    if (ss.ss_family == AF_INET) {
        *ip_out = ntohl(((struct sockaddr_in *)&ss)->sin_addr.s_addr);
        return true;
    }
#if LWIP_IPV6
    if (ss.ss_family == AF_INET6) {
        const uint8_t *a = (const uint8_t *)&((struct sockaddr_in6 *)&ss)->sin6_addr;
        static const uint8_t v4map[12] = {0,0,0,0,0,0,0,0,0,0,0xFF,0xFF};
        if (memcmp(a, v4map, 12) == 0) {
            *ip_out = ((uint32_t)a[12] << 24) | ((uint32_t)a[13] << 16) |
                      ((uint32_t)a[14] << 8) | (uint32_t)a[15];
            return true;
        }
    }
#endif
    return false;
}

static bool check_interface_allowed(httpd_req_t *req) {
    if (aguja_config_http_allow_lan()) return true;

    uint32_t local_ip = 0;
    if (!request_local_ipv4(req, &local_ip) || local_ip == 0) return false;

    microlink_t *ml = aguja_net_get_ml();
    uint32_t vpn_ip = ml ? microlink_get_vpn_ip(ml) : 0;
    return (vpn_ip != 0 && local_ip == vpn_ip);
}

static bool check_auth(httpd_req_t *req) {
    char hdr[192] = {0};
    if (httpd_req_get_hdr_value_str(req, "X-Aguja-Token", hdr, sizeof(hdr)) == ESP_OK) {
        if (aguja_config_check_token(hdr)) return true;
    }
    if (httpd_req_get_hdr_value_str(req, "Authorization", hdr, sizeof(hdr)) == ESP_OK) {
        if (strncmp(hdr, "Bearer ", 7) == 0) {
            if (aguja_config_check_token(hdr + 7)) return true;
        } else if (strncmp(hdr, "Basic ", 6) == 0) {
            unsigned char dec[128] = {0};
            size_t olen = 0;
            if (mbedtls_base64_decode(dec, sizeof(dec) - 1, &olen,
                                      (const unsigned char *)(hdr + 6), strlen(hdr + 6)) == 0) {
                dec[olen] = '\0';
                char *colon = strchr((char *)dec, ':');
                if (colon && aguja_config_check_token(colon + 1)) return true;
            }
        }
    }
    return false;
}

static esp_err_t send_json(httpd_req_t *req, int status_code, cJSON *json) {
    if (status_code == 400) httpd_resp_set_status(req, "400 Bad Request");
    else if (status_code == 401) httpd_resp_set_status(req, "401 Unauthorized");
    else if (status_code == 403) httpd_resp_set_status(req, "403 Forbidden");
    else if (status_code == 404) httpd_resp_set_status(req, "404 Not Found");
    else if (status_code == 500) httpd_resp_set_status(req, "500 Internal Server Error");
    else httpd_resp_set_status(req, "200 OK");

    httpd_resp_set_type(req, "application/json");
    char *s = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    if (!s) {
        httpd_resp_sendstr(req, "{\"error\":\"oom\"}");
        return ESP_FAIL;
    }
    esp_err_t err = httpd_resp_send(req, s, HTTPD_RESP_USE_STRLEN);
    free(s);
    return err;
}

static esp_err_t send_err(httpd_req_t *req, int code, const char *msg) {
    cJSON *j = cJSON_CreateObject();
    cJSON_AddBoolToObject(j, "ok", false);
    cJSON_AddStringToObject(j, "error", msg ? msg : "error");
    return send_json(req, code, j);
}

static esp_err_t send_ok(httpd_req_t *req, const char *msg) {
    cJSON *j = cJSON_CreateObject();
    cJSON_AddBoolToObject(j, "ok", true);
    if (msg) cJSON_AddStringToObject(j, "message", msg);
    return send_json(req, 200, j);
}

static cJSON *read_json_body(httpd_req_t *req) {
    size_t len = req->content_len;
    if (len == 0 || len > 8192) return NULL;
    char *buf = malloc(len + 1);
    if (!buf) return NULL;
    size_t got = 0;
    while (got < len) {
        int r = httpd_req_recv(req, buf + got, len - got);
        if (r <= 0) {
            if (r == HTTPD_SOCK_ERR_TIMEOUT) continue;
            free(buf);
            return NULL;
        }
        got += (size_t)r;
    }
    buf[len] = '\0';
    cJSON *j = cJSON_Parse(buf);
    free(buf);
    return j;
}

static int parse_hex_str(const char *hex, uint8_t *out, size_t max_len) {
    if (!hex) return 0;
    size_t n = 0;
    while (*hex && n < max_len) {
        while (*hex == ' ' || *hex == ':' || *hex == ',') hex++;
        if (!hex[0] || !hex[1]) break;
        unsigned int v = 0;
        if (sscanf(hex, "%2x", &v) != 1) break;
        out[n++] = (uint8_t)v;
        hex += 2;
    }
    return (int)n;
}

static void bytes_to_hex(const uint8_t *in, size_t len, char *out, size_t out_sz) {
    static const char h[] = "0123456789abcdef";
    size_t pos = 0;
    for (size_t i = 0; i < len && pos + 2 < out_sz; i++) {
        out[pos++] = h[(in[i] >> 4) & 0xF];
        out[pos++] = h[in[i] & 0xF];
    }
    out[pos] = '\0';
}

static void delayed_reboot_task(void *arg) {
    uint32_t ms = (uint32_t)(uintptr_t)arg;
    vTaskDelay(pdMS_TO_TICKS(ms ? ms : 500));
    esp_restart();
}

static void delayed_tailnet_restart_task(void *arg) {
    (void)arg;
    vTaskDelay(pdMS_TO_TICKS(400));
    aguja_net_restart_tailnet();
    vTaskDelete(NULL);
}

static void delayed_sleep_task(void *arg) {
    uint32_t sec = (uint32_t)(uintptr_t)arg;
    vTaskDelay(pdMS_TO_TICKS(500));
    ESP_LOGW(TAG, "Entering deep sleep for %lu s", (unsigned long)sec);
    esp_deep_sleep((uint64_t)sec * 1000000ULL);
}

static bool uri_is(const char *uri, const char *path) {
    size_t pl = strlen(path);
    return strncmp(uri, path, pl) == 0 && (uri[pl] == '\0' || uri[pl] == '?');
}

static bool guard(httpd_req_t *req, bool require_auth) {
    if (!check_interface_allowed(req)) {
        send_err(req, 403, "tailnet_only");
        return false;
    }
    if (require_auth && !check_auth(req)) {
        httpd_resp_set_hdr(req, "WWW-Authenticate", "Basic realm=\"Aguja-IoT\"");
        send_err(req, 401, "unauthorized");
        return false;
    }
    return true;
}

/* ============================================================================
 * Web UI Handler (GET /)
 * ========================================================================== */

static esp_err_t handle_root(httpd_req_t *req) {
    if (!check_interface_allowed(req)) return send_err(req, 403, "tailnet_only");
    httpd_resp_set_type(req, "text/html; charset=utf-8");
    return httpd_resp_send(req, AGUJA_WEBUI_HTML, HTTPD_RESP_USE_STRLEN);
}

/* ============================================================================
 * GET /api/v1/ endpoints
 * ========================================================================== */

static esp_err_t handle_api_get(httpd_req_t *req) {
    const char *u = req->uri;

    if (uri_is(u, "/api/v1/health")) {
        if (!guard(req, false)) return ESP_OK;
        char host[48] = {0};
        aguja_config_get_hostname(host, sizeof(host));
        cJSON *j = cJSON_CreateObject();
        cJSON_AddBoolToObject(j, "ok", true);
        cJSON_AddStringToObject(j, "hostname", host);
        cJSON_AddNumberToObject(j, "uptime_s", (double)(esp_timer_get_time() / 1000000LL));
        return send_json(req, 200, j);
    }

    if (!guard(req, true)) return ESP_OK;

    if (uri_is(u, "/api/v1/status")) {
        char host[48] = {0};
        aguja_config_get_hostname(host, sizeof(host));
        cJSON *root = cJSON_CreateObject();

        cJSON *sys = cJSON_AddObjectToObject(root, "sys");
        const esp_app_desc_t *app = esp_app_get_description();
        const esp_partition_t *part = esp_ota_get_running_partition();
        esp_chip_info_t ci;
        esp_chip_info(&ci);
        uint8_t mac[6] = {0};
        esp_read_mac(mac, ESP_MAC_WIFI_STA);
        char mac_s[18];
        snprintf(mac_s, sizeof(mac_s), "%02x:%02x:%02x:%02x:%02x:%02x",
                 mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
        float temp_c = 0;
        aguja_hw_read_temp_c(&temp_c);

        cJSON_AddStringToObject(sys, "hostname", host);
        cJSON_AddStringToObject(sys, "board", "Seeed Studio XIAO ESP32-C6");
        cJSON_AddStringToObject(sys, "chip", "ESP32-C6");
        cJSON_AddNumberToObject(sys, "chip_rev", ci.revision);
        cJSON_AddStringToObject(sys, "mac", mac_s);
        cJSON_AddStringToObject(sys, "fw_version", app->version);
        cJSON_AddStringToObject(sys, "build_date", app->date);
        cJSON_AddStringToObject(sys, "partition", part ? part->label : "?");
        cJSON_AddNumberToObject(sys, "uptime_s", (double)(esp_timer_get_time() / 1000000LL));
        cJSON_AddNumberToObject(sys, "temp_c", temp_c);
        cJSON_AddNumberToObject(sys, "cpu_mhz", aguja_hw_get_cpu_mhz());
        cJSON_AddNumberToObject(sys, "heap_free", esp_get_free_heap_size());
        cJSON_AddNumberToObject(sys, "heap_min", esp_get_minimum_free_heap_size());
        cJSON_AddNumberToObject(sys, "heap_largest", heap_caps_get_largest_free_block(MALLOC_CAP_8BIT));
        cJSON_AddNumberToObject(sys, "reset_reason", esp_reset_reason());

        cJSON_AddItemToObject(root, "net", aguja_net_status_json());

        cJSON *hw = cJSON_AddObjectToObject(root, "hw");
        cJSON_AddStringToObject(hw, "antenna", aguja_hw_get_antenna_external() ? "external_ufl" : "internal_ceramic");
        aguja_led_mode_t lm; uint8_t lp; uint16_t lb;
        aguja_hw_get_led(&lm, &lp, &lb);
        cJSON_AddNumberToObject(hw, "led_mode", lm);
        cJSON_AddNumberToObject(hw, "led_pwm_pct", lp);
        cJSON_AddNumberToObject(hw, "led_blink_ms", lb);
        cJSON_AddItemToObject(hw, "gpios", aguja_hw_gpio_dump_json());
        cJSON_AddItemToObject(hw, "adc", aguja_hw_adc_dump_json());

        return send_json(req, 200, root);
    }

    if (uri_is(u, "/api/v1/peers")) {
        cJSON *j = cJSON_CreateObject();
        cJSON_AddItemToObject(j, "peers", aguja_net_peers_json());
        return send_json(req, 200, j);
    }

    if (uri_is(u, "/api/v1/config")) {
        bool inc = (strstr(u, "secrets=1") != NULL);
        return send_json(req, 200, aguja_config_to_json(inc));
    }

    if (uri_is(u, "/api/v1/hw/gpio")) {
        cJSON *j = cJSON_CreateObject();
        cJSON_AddItemToObject(j, "gpios", aguja_hw_gpio_dump_json());
        return send_json(req, 200, j);
    }

    if (uri_is(u, "/api/v1/hw/adc")) {
        cJSON *j = cJSON_CreateObject();
        cJSON_AddItemToObject(j, "adc", aguja_hw_adc_dump_json());
        return send_json(req, 200, j);
    }

    if (uri_is(u, "/api/v1/hw/i2c/scan")) {
        cJSON *j = cJSON_CreateObject();
        cJSON_AddItemToObject(j, "devices", aguja_hw_i2c_scan());
        return send_json(req, 200, j);
    }

    if (uri_is(u, "/api/v1/hw/uart/rx")) {
        uint8_t buf[256];
        int n = aguja_hw_uart_rx(buf, sizeof(buf), 150);
        cJSON *j = cJSON_CreateObject();
        if (n > 0) {
            char hex[513];
            bytes_to_hex(buf, (size_t)n, hex, sizeof(hex));
            cJSON_AddNumberToObject(j, "len", n);
            cJSON_AddStringToObject(j, "hex", hex);
            char txt[257];
            memcpy(txt, buf, (size_t)n);
            txt[n] = '\0';
            cJSON_AddStringToObject(j, "text", txt);
        } else {
            cJSON_AddNumberToObject(j, "len", 0);
            cJSON_AddStringToObject(j, "hex", "");
            cJSON_AddStringToObject(j, "text", "");
        }
        return send_json(req, 200, j);
    }

    if (uri_is(u, "/api/v1/wifi/scan")) {
        cJSON *j = cJSON_CreateObject();
        cJSON_AddItemToObject(j, "aps", aguja_net_wifi_scan_json());
        return send_json(req, 200, j);
    }

    if (uri_is(u, "/api/v1/net/clients")) {
        cJSON *j = cJSON_CreateObject();
        cJSON_AddItemToObject(j, "ap_clients", aguja_net_clients_json());
        return send_json(req, 200, j);
    }

    if (uri_is(u, "/api/v1/logs")) {
        char *buf = malloc(AGUJA_LOG_RING_SIZE);
        if (!buf) return send_err(req, 500, "oom");
        size_t n = aguja_log_read(buf, AGUJA_LOG_RING_SIZE);
        cJSON *j = cJSON_CreateObject();
        cJSON_AddNumberToObject(j, "bytes", (double)n);
        cJSON_AddStringToObject(j, "logs", buf);
        free(buf);
        return send_json(req, 200, j);
    }

    if (uri_is(u, "/api/v1/rules")) {
        cJSON *j = cJSON_CreateObject();
        cJSON_AddItemToObject(j, "rules", aguja_config_rules_to_json());
        return send_json(req, 200, j);
    }

    return send_err(req, 404, "not_found");
}

/* ============================================================================
 * OTA Upload Handler (POST /api/v1/ota)
 * ========================================================================== */

static esp_err_t handle_ota_upload(httpd_req_t *req) {
    size_t total = req->content_len;
    if (total < 65536 || total > 1920 * 1024) {
        return send_err(req, 400, "invalid_ota_size");
    }
    const esp_partition_t *upd = esp_ota_get_next_update_partition(NULL);
    if (!upd) return send_err(req, 500, "no_ota_partition");

    esp_ota_handle_t oh = 0;
    esp_err_t err = esp_ota_begin(upd, OTA_WITH_SEQUENTIAL_WRITES, &oh);
    if (err != ESP_OK) return send_err(req, 500, esp_err_to_name(err));

    uint8_t *buf = malloc(4096);
    if (!buf) {
        esp_ota_abort(oh);
        return send_err(req, 500, "oom");
    }

    size_t written = 0;
    while (written < total) {
        size_t want = total - written;
        if (want > 4096) want = 4096;
        int r = httpd_req_recv(req, (char *)buf, want);
        if (r <= 0) {
            if (r == HTTPD_SOCK_ERR_TIMEOUT) continue;
            free(buf);
            esp_ota_abort(oh);
            return send_err(req, 500, "recv_failed");
        }
        err = esp_ota_write(oh, buf, (size_t)r);
        if (err != ESP_OK) {
            free(buf);
            esp_ota_abort(oh);
            return send_err(req, 500, esp_err_to_name(err));
        }
        written += (size_t)r;
    }
    free(buf);

    err = esp_ota_end(oh);
    if (err != ESP_OK) return send_err(req, 400, esp_err_to_name(err));

    err = esp_ota_set_boot_partition(upd);
    if (err != ESP_OK) return send_err(req, 500, esp_err_to_name(err));

    ESP_LOGW(TAG, "OTA flashed %u bytes to '%s'. Rebooting (auto-rollback armed)...",
             (unsigned)written, upd->label);
    cJSON *j = cJSON_CreateObject();
    cJSON_AddBoolToObject(j, "ok", true);
    cJSON_AddStringToObject(j, "partition", upd->label);
    cJSON_AddNumberToObject(j, "bytes", (double)written);
    cJSON_AddBoolToObject(j, "rebooting", true);
    send_json(req, 200, j);

    xTaskCreate(delayed_reboot_task, "ota_reb", 2048, (void *)600, 3, NULL);
    return ESP_OK;
}

/* ============================================================================
 * POST / PUT / DELETE /api/v1/ endpoints
 * ========================================================================== */

static esp_err_t handle_api_write(httpd_req_t *req) {
    if (!guard(req, true)) return ESP_OK;
    const char *u = req->uri;

    if (req->method == HTTP_DELETE && uri_is(u, "/api/v1/logs")) {
        aguja_log_clear();
        return send_ok(req, "logs_cleared");
    }

    if (req->method == HTTP_POST && uri_is(u, "/api/v1/ota")) {
        return handle_ota_upload(req);
    }

    cJSON *body = read_json_body(req);
    if (!body && req->content_len > 0) {
        return send_err(req, 400, "invalid_json");
    }
    if (!body) body = cJSON_CreateObject();

    /* PUT /api/v1/config */
    if (uri_is(u, "/api/v1/config")) {
        bool net_r = false, tn_r = false;
        esp_err_t err = aguja_config_apply_json(body, &net_r, &tn_r);
        cJSON_Delete(body);
        if (err != ESP_OK) return send_err(req, 400, esp_err_to_name(err));

        aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
        if (cfg) {
            aguja_config_get(cfg);
            aguja_hw_set_antenna(cfg->antenna_external);
            aguja_hw_set_led((aguja_led_mode_t)cfg->led_mode, cfg->led_pwm_pct, cfg->led_blink_ms);
            aguja_hw_set_cpu_mhz(cfg->cpu_mhz);
            free(cfg);
        }
        aguja_net_apply_wifi_rf();
        if (net_r) aguja_net_apply_ap();

        cJSON *res = cJSON_CreateObject();
        cJSON_AddBoolToObject(res, "ok", true);
        cJSON_AddBoolToObject(res, "needs_net_restart", net_r);
        cJSON_AddBoolToObject(res, "needs_tailnet_restart", tn_r);
        return send_json(req, 200, res);
    }

    /* PUT /api/v1/rules */
    if (uri_is(u, "/api/v1/rules")) {
        const cJSON *arr = cJSON_IsArray(body) ? body : cJSON_GetObjectItem(body, "rules");
        esp_err_t err = aguja_config_set_rules_json(arr);
        cJSON_Delete(body);
        return err == ESP_OK ? send_ok(req, "rules_saved") : send_err(req, 400, "invalid_rules");
    }

    /* Hardware: Antenna */
    if (uri_is(u, "/api/v1/hw/antenna")) {
        const cJSON *ext = cJSON_GetObjectItem(body, "external");
        const cJSON *per = cJSON_GetObjectItem(body, "persist");
        bool is_ext = cJSON_IsTrue(ext);
        aguja_hw_set_antenna(is_ext);
        if (cJSON_IsTrue(per)) aguja_config_set_antenna(is_ext);
        cJSON_Delete(body);
        cJSON *j = cJSON_CreateObject();
        cJSON_AddBoolToObject(j, "ok", true);
        cJSON_AddStringToObject(j, "antenna", is_ext ? "external_ufl" : "internal_ceramic");
        return send_json(req, 200, j);
    }

    /* Hardware: LED */
    if (uri_is(u, "/api/v1/hw/led")) {
        const cJSON *m = cJSON_GetObjectItem(body, "mode");
        const cJSON *p = cJSON_GetObjectItem(body, "pwm_pct");
        const cJSON *b = cJSON_GetObjectItem(body, "blink_ms");
        const cJSON *per = cJSON_GetObjectItem(body, "persist");
        aguja_led_mode_t lm = AGUJA_LED_STATUS;
        if (cJSON_IsString(m)) {
            if (strcmp(m->valuestring, "off") == 0) lm = AGUJA_LED_OFF;
            else if (strcmp(m->valuestring, "on") == 0) lm = AGUJA_LED_ON;
            else if (strcmp(m->valuestring, "blink") == 0) lm = AGUJA_LED_BLINK;
            else if (strcmp(m->valuestring, "pwm") == 0) lm = AGUJA_LED_PWM;
        } else if (cJSON_IsNumber(m)) {
            lm = (aguja_led_mode_t)m->valueint;
        }
        uint8_t pct = cJSON_IsNumber(p) ? (uint8_t)p->valueint : 50;
        uint16_t bms = cJSON_IsNumber(b) ? (uint16_t)b->valueint : 300;
        aguja_hw_set_led(lm, pct, bms);
        if (cJSON_IsTrue(per)) {
            aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
            if (cfg) {
                aguja_config_get(cfg);
                cfg->led_mode = (uint8_t)lm;
                cfg->led_pwm_pct = pct;
                cfg->led_blink_ms = bms;
                aguja_config_set(cfg);
                free(cfg);
            }
        }
        cJSON_Delete(body);
        return send_ok(req, "led_updated");
    }

    /* Hardware: GPIO */
    if (uri_is(u, "/api/v1/hw/gpio")) {
        const cJSON *pin = cJSON_GetObjectItem(body, "pin");
        if (!cJSON_IsNumber(pin)) { cJSON_Delete(body); return send_err(req, 400, "missing_pin"); }
        int p = pin->valueint;
        bool force = cJSON_IsTrue(cJSON_GetObjectItem(body, "force"));
        const cJSON *mode = cJSON_GetObjectItem(body, "mode");
        const cJSON *pull = cJSON_GetObjectItem(body, "pull");
        const cJSON *level = cJSON_GetObjectItem(body, "level");
        const cJSON *pulse = cJSON_GetObjectItem(body, "pulse_ms");

        esp_err_t err = ESP_OK;
        if (cJSON_IsNumber(pulse) && pulse->valueint > 0) {
            err = aguja_hw_gpio_pulse(p, cJSON_IsNumber(level) ? level->valueint : 1,
                                      (uint32_t)pulse->valueint, force);
        } else {
            if (cJSON_IsString(mode) || cJSON_IsString(pull)) {
                err = aguja_hw_gpio_config(p, cJSON_IsString(mode) ? mode->valuestring : "in",
                                           cJSON_IsString(pull) ? pull->valuestring : "none", force);
            }
            if (err == ESP_OK && cJSON_IsNumber(level)) {
                err = aguja_hw_gpio_write(p, level->valueint, force);
            }
        }
        cJSON_Delete(body);
        if (err != ESP_OK) return send_err(req, 400, esp_err_to_name(err));
        cJSON *j = cJSON_CreateObject();
        cJSON_AddBoolToObject(j, "ok", true);
        cJSON_AddNumberToObject(j, "pin", p);
        cJSON_AddNumberToObject(j, "level", aguja_hw_gpio_read(p));
        return send_json(req, 200, j);
    }

    /* Hardware: PWM */
    if (uri_is(u, "/api/v1/hw/pwm")) {
        int ch = cJSON_IsNumber(cJSON_GetObjectItem(body, "channel")) ? cJSON_GetObjectItem(body, "channel")->valueint : 0;
        int pin = cJSON_IsNumber(cJSON_GetObjectItem(body, "pin")) ? cJSON_GetObjectItem(body, "pin")->valueint : -1;
        uint32_t freq = cJSON_IsNumber(cJSON_GetObjectItem(body, "freq_hz")) ? (uint32_t)cJSON_GetObjectItem(body, "freq_hz")->valueint : 1000;
        float duty = cJSON_IsNumber(cJSON_GetObjectItem(body, "duty_pct")) ? (float)cJSON_GetObjectItem(body, "duty_pct")->valuedouble : 50.0f;
        bool stop = cJSON_IsTrue(cJSON_GetObjectItem(body, "stop"));
        cJSON_Delete(body);
        esp_err_t err = aguja_hw_pwm_set(ch, pin, freq, duty, stop);
        return err == ESP_OK ? send_ok(req, "pwm_updated") : send_err(req, 400, esp_err_to_name(err));
    }

    /* Hardware: I2C config / xfer */
    if (uri_is(u, "/api/v1/hw/i2c/config")) {
        int sda = cJSON_IsNumber(cJSON_GetObjectItem(body, "sda")) ? cJSON_GetObjectItem(body, "sda")->valueint : XIAO_PIN_D4_SDA;
        int scl = cJSON_IsNumber(cJSON_GetObjectItem(body, "scl")) ? cJSON_GetObjectItem(body, "scl")->valueint : XIAO_PIN_D5_SCL;
        uint32_t hz = cJSON_IsNumber(cJSON_GetObjectItem(body, "freq_hz")) ? (uint32_t)cJSON_GetObjectItem(body, "freq_hz")->valueint : 100000;
        cJSON_Delete(body);
        esp_err_t err = aguja_hw_i2c_config(sda, scl, hz);
        return err == ESP_OK ? send_ok(req, "i2c_configured") : send_err(req, 400, esp_err_to_name(err));
    }

    if (uri_is(u, "/api/v1/hw/i2c/xfer")) {
        const cJSON *ja = cJSON_GetObjectItem(body, "addr");
        if (!cJSON_IsNumber(ja)) { cJSON_Delete(body); return send_err(req, 400, "missing_addr"); }
        uint8_t addr = (uint8_t)ja->valueint;
        uint8_t tx[64], rx[64];
        int tx_len = 0;
        const cJSON *jtx = cJSON_GetObjectItem(body, "tx_hex");
        if (cJSON_IsString(jtx)) tx_len = parse_hex_str(jtx->valuestring, tx, sizeof(tx));
        int rx_len = cJSON_IsNumber(cJSON_GetObjectItem(body, "rx_len")) ? cJSON_GetObjectItem(body, "rx_len")->valueint : 0;
        if (rx_len < 0) rx_len = 0;
        if (rx_len > (int)sizeof(rx)) rx_len = sizeof(rx);
        cJSON_Delete(body);

        esp_err_t err = aguja_hw_i2c_xfer(addr, tx_len > 0 ? tx : NULL, (size_t)tx_len,
                                          rx_len > 0 ? rx : NULL, (size_t)rx_len, 250);
        if (err != ESP_OK) return send_err(req, 500, esp_err_to_name(err));
        cJSON *j = cJSON_CreateObject();
        cJSON_AddBoolToObject(j, "ok", true);
        char rhex[129] = "";
        if (rx_len > 0) bytes_to_hex(rx, (size_t)rx_len, rhex, sizeof(rhex));
        cJSON_AddStringToObject(j, "rx_hex", rhex);
        return send_json(req, 200, j);
    }

    /* Hardware: UART */
    if (uri_is(u, "/api/v1/hw/uart/config")) {
        int tx = cJSON_IsNumber(cJSON_GetObjectItem(body, "tx")) ? cJSON_GetObjectItem(body, "tx")->valueint : XIAO_PIN_D6_TX;
        int rx = cJSON_IsNumber(cJSON_GetObjectItem(body, "rx")) ? cJSON_GetObjectItem(body, "rx")->valueint : XIAO_PIN_D7_RX;
        int baud = cJSON_IsNumber(cJSON_GetObjectItem(body, "baud")) ? cJSON_GetObjectItem(body, "baud")->valueint : 115200;
        cJSON_Delete(body);
        esp_err_t err = aguja_hw_uart_config(tx, rx, baud);
        return err == ESP_OK ? send_ok(req, "uart_configured") : send_err(req, 400, esp_err_to_name(err));
    }

    if (uri_is(u, "/api/v1/hw/uart/tx")) {
        const cJSON *jh = cJSON_GetObjectItem(body, "hex");
        const cJSON *jt = cJSON_GetObjectItem(body, "text");
        int sent = 0;
        if (cJSON_IsString(jh)) {
            uint8_t buf[256];
            int n = parse_hex_str(jh->valuestring, buf, sizeof(buf));
            sent = aguja_hw_uart_tx(buf, (size_t)n);
        } else if (cJSON_IsString(jt)) {
            sent = aguja_hw_uart_tx((const uint8_t *)jt->valuestring, strlen(jt->valuestring));
        }
        cJSON_Delete(body);
        cJSON *j = cJSON_CreateObject();
        cJSON_AddBoolToObject(j, "ok", sent >= 0);
        cJSON_AddNumberToObject(j, "sent", sent);
        return send_json(req, 200, j);
    }

    /* Hardware: SPI */
    if (uri_is(u, "/api/v1/hw/spi/xfer")) {
        int sck = cJSON_IsNumber(cJSON_GetObjectItem(body, "sck")) ? cJSON_GetObjectItem(body, "sck")->valueint : XIAO_PIN_D8_SCK;
        int miso = cJSON_IsNumber(cJSON_GetObjectItem(body, "miso")) ? cJSON_GetObjectItem(body, "miso")->valueint : XIAO_PIN_D9_MISO;
        int mosi = cJSON_IsNumber(cJSON_GetObjectItem(body, "mosi")) ? cJSON_GetObjectItem(body, "mosi")->valueint : XIAO_PIN_D10_MOSI;
        int cs = cJSON_IsNumber(cJSON_GetObjectItem(body, "cs")) ? cJSON_GetObjectItem(body, "cs")->valueint : XIAO_PIN_D3;
        uint32_t hz = cJSON_IsNumber(cJSON_GetObjectItem(body, "clock_hz")) ? (uint32_t)cJSON_GetObjectItem(body, "clock_hz")->valueint : 1000000;
        uint8_t tx[128], rx[128] = {0};
        const cJSON *jtx = cJSON_GetObjectItem(body, "tx_hex");
        int len = cJSON_IsString(jtx) ? parse_hex_str(jtx->valuestring, tx, sizeof(tx)) : 0;
        cJSON_Delete(body);
        if (len <= 0) return send_err(req, 400, "missing_tx_hex");
        esp_err_t err = aguja_hw_spi_xfer(sck, miso, mosi, cs, hz, tx, rx, (size_t)len);
        if (err != ESP_OK) return send_err(req, 400, esp_err_to_name(err));
        char rhex[257];
        bytes_to_hex(rx, (size_t)len, rhex, sizeof(rhex));
        cJSON *j = cJSON_CreateObject();
        cJSON_AddBoolToObject(j, "ok", true);
        cJSON_AddStringToObject(j, "rx_hex", rhex);
        return send_json(req, 200, j);
    }

    /* WiFi SoftAP & RF */
    if (uri_is(u, "/api/v1/wifi/ap")) {
        const cJSON *en = cJSON_GetObjectItem(body, "enabled");
        const cJSON *ss = cJSON_GetObjectItem(body, "ssid");
        const cJSON *pw = cJSON_GetObjectItem(body, "pass");
        const cJSON *ch = cJSON_GetObjectItem(body, "channel");
        aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
        if (cfg) {
            aguja_config_get(cfg);
            aguja_config_set_ap(cJSON_IsBool(en) ? cJSON_IsTrue(en) : cfg->ap_enabled,
                                cJSON_IsString(ss) ? ss->valuestring : NULL,
                                cJSON_IsString(pw) ? pw->valuestring : NULL,
                                cJSON_IsNumber(ch) ? (uint8_t)ch->valueint : cfg->ap_channel);
            free(cfg);
        }
        cJSON_Delete(body);
        aguja_net_apply_ap();
        return send_ok(req, "ap_updated");
    }

    if (uri_is(u, "/api/v1/wifi/rf")) {
        aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
        if (cfg) {
            aguja_config_get(cfg);
            const cJSON *tx = cJSON_GetObjectItem(body, "tx_power_dbm");
            const cJSON *ps = cJSON_GetObjectItem(body, "ps_mode");
            if (cJSON_IsNumber(tx) && tx->valueint >= 8 && tx->valueint <= 20) cfg->wifi_tx_power_dbm = (int8_t)tx->valueint;
            if (cJSON_IsNumber(ps) && ps->valueint >= 0 && ps->valueint <= 2) cfg->wifi_ps_mode = (uint8_t)ps->valueint;
            aguja_config_set(cfg);
            free(cfg);
        }
        cJSON_Delete(body);
        aguja_net_apply_wifi_rf();
        return send_ok(req, "wifi_rf_updated");
    }

    /* NetOps */
    if (uri_is(u, "/api/v1/net/ping")) {
        const cJSON *h = cJSON_GetObjectItem(body, "host");
        const cJSON *cnt = cJSON_GetObjectItem(body, "count");
        const cJSON *to = cJSON_GetObjectItem(body, "timeout_ms");
        char host[128] = "";
        if (cJSON_IsString(h)) strncpy(host, h->valuestring, sizeof(host) - 1);
        uint32_t c = cJSON_IsNumber(cnt) ? (uint32_t)cnt->valueint : 3;
        uint32_t t = cJSON_IsNumber(to) ? (uint32_t)to->valueint : 1000;
        cJSON_Delete(body);
        return send_json(req, 200, aguja_net_ping_json(host, c, t));
    }

    if (uri_is(u, "/api/v1/net/probe")) {
        const cJSON *h = cJSON_GetObjectItem(body, "host");
        const cJSON *p = cJSON_GetObjectItem(body, "port");
        const cJSON *to = cJSON_GetObjectItem(body, "timeout_ms");
        char host[128] = "";
        if (cJSON_IsString(h)) strncpy(host, h->valuestring, sizeof(host) - 1);
        uint16_t port = cJSON_IsNumber(p) ? (uint16_t)p->valueint : 80;
        uint32_t t = cJSON_IsNumber(to) ? (uint32_t)to->valueint : 1500;
        cJSON_Delete(body);
        return send_json(req, 200, aguja_net_tcp_probe_json(host, port, t));
    }

    if (uri_is(u, "/api/v1/net/dns")) {
        const cJSON *h = cJSON_GetObjectItem(body, "host");
        char host[128] = "";
        if (cJSON_IsString(h)) strncpy(host, h->valuestring, sizeof(host) - 1);
        cJSON_Delete(body);
        return send_json(req, 200, aguja_net_dns_lookup_json(host));
    }

    if (uri_is(u, "/api/v1/net/wol")) {
        const cJSON *m = cJSON_GetObjectItem(body, "mac");
        esp_err_t err = cJSON_IsString(m) ? aguja_net_send_wol(m->valuestring) : ESP_ERR_INVALID_ARG;
        cJSON_Delete(body);
        return err == ESP_OK ? send_ok(req, "wol_sent") : send_err(req, 400, "invalid_mac");
    }

    if (uri_is(u, "/api/v1/net/beacon")) {
        const cJSON *ev = cJSON_GetObjectItem(body, "event");
        aguja_net_send_beacon_now(cJSON_IsString(ev) ? ev->valuestring : "manual");
        cJSON_Delete(body);
        return send_ok(req, "beacon_sent");
    }

    /* Logs level */
    if (uri_is(u, "/api/v1/logs/level")) {
        const cJSON *tag = cJSON_GetObjectItem(body, "tag");
        const cJSON *lvl = cJSON_GetObjectItem(body, "level");
        esp_err_t err = aguja_log_set_level(cJSON_IsString(tag) ? tag->valuestring : "*",
                                            cJSON_IsString(lvl) ? lvl->valuestring : "info");
        cJSON_Delete(body);
        return err == ESP_OK ? send_ok(req, "log_level_set") : send_err(req, 400, "invalid_level");
    }

    /* System controls */
    if (uri_is(u, "/api/v1/system/cpu")) {
        const cJSON *mhz = cJSON_GetObjectItem(body, "mhz");
        uint16_t m = cJSON_IsNumber(mhz) ? (uint16_t)mhz->valueint : 160;
        bool per = cJSON_IsTrue(cJSON_GetObjectItem(body, "persist"));
        cJSON_Delete(body);
        esp_err_t err = aguja_hw_set_cpu_mhz(m);
        if (err == ESP_OK && per) {
            aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
            if (cfg) {
                aguja_config_get(cfg);
                cfg->cpu_mhz = m;
                aguja_config_set(cfg);
                free(cfg);
            }
        }
        return err == ESP_OK ? send_ok(req, "cpu_freq_updated") : send_err(req, 400, "invalid_mhz");
    }

    if (uri_is(u, "/api/v1/system/sleep")) {
        uint32_t sec = cJSON_IsNumber(cJSON_GetObjectItem(body, "seconds")) ?
                       (uint32_t)cJSON_GetObjectItem(body, "seconds")->valueint : 30;
        cJSON_Delete(body);
        if (sec < 5 || sec > 86400) return send_err(req, 400, "seconds_out_of_range");
        send_ok(req, "entering_deep_sleep");
        xTaskCreate(delayed_sleep_task, "sleep_t", 2048, (void *)(uintptr_t)sec, 3, NULL);
        return ESP_OK;
    }

    if (uri_is(u, "/api/v1/system/restart-tailnet")) {
        cJSON_Delete(body);
        send_ok(req, "restarting_tailnet");
        xTaskCreate(delayed_tailnet_restart_task, "tn_rst", 4096, NULL, 3, NULL);
        return ESP_OK;
    }

    if (uri_is(u, "/api/v1/system/reboot")) {
        cJSON_Delete(body);
        send_ok(req, "rebooting");
        xTaskCreate(delayed_reboot_task, "reb_t", 2048, (void *)400, 3, NULL);
        return ESP_OK;
    }

    if (uri_is(u, "/api/v1/system/factory-reset")) {
        bool confirm = cJSON_IsTrue(cJSON_GetObjectItem(body, "confirm"));
        cJSON_Delete(body);
        if (!confirm) return send_err(req, 400, "set_confirm_true");
        aguja_config_reset_defaults();
        microlink_factory_reset();
        send_ok(req, "factory_reset_rebooting");
        xTaskCreate(delayed_reboot_task, "fr_t", 2048, (void *)500, 3, NULL);
        return ESP_OK;
    }

    cJSON_Delete(body);
    return send_err(req, 404, "not_found");
}

esp_err_t aguja_http_start(void) {
    if (s_httpd) return ESP_OK;

    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
    cfg.server_port = 80;
    cfg.stack_size = 6144;
    cfg.max_uri_handlers = 8;
    cfg.max_open_sockets = 5;
    cfg.lru_purge_enable = true;
    cfg.uri_match_fn = httpd_uri_match_wildcard;

    esp_err_t err = httpd_start(&s_httpd, &cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "httpd_start failed: %s", esp_err_to_name(err));
        return err;
    }

    const httpd_uri_t uris[] = {
        { .uri = "/",        .method = HTTP_GET,    .handler = handle_root },
        { .uri = "/api/v1/*", .method = HTTP_GET,    .handler = handle_api_get },
        { .uri = "/api/v1/*", .method = HTTP_POST,   .handler = handle_api_write },
        { .uri = "/api/v1/*", .method = HTTP_PUT,    .handler = handle_api_write },
        { .uri = "/api/v1/*", .method = HTTP_DELETE, .handler = handle_api_write },
    };
    for (size_t i = 0; i < sizeof(uris) / sizeof(uris[0]); i++) {
        httpd_register_uri_handler(s_httpd, &uris[i]);
    }

    ESP_LOGI(TAG, "Aguja-IoT Agent Ops HTTP server listening on :80 (Tailnet-only by default)");
    return ESP_OK;
}

void aguja_http_stop(void) {
    if (s_httpd) {
        httpd_stop(s_httpd);
        s_httpd = NULL;
    }
}
