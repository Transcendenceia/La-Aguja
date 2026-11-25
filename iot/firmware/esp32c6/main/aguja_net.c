#include "aguja_net.h"
#include "aguja_config.h"
#include "aguja_hw.h"
#include "microlink.h"
#include "microlink_internal.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_mac.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "lwip/inet.h"
#include "ping/ping_sock.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/semphr.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

static const char *TAG = "aguja_net";

static esp_netif_t *s_sta_netif = NULL;
static esp_netif_t *s_ap_netif = NULL;
static EventGroupHandle_t s_wifi_ev = NULL;
#define WIFI_GOT_IP_BIT BIT0

static volatile bool s_wifi_connected = false;
static volatile bool s_wifi_scanning = false;
static uint32_t s_sta_ip = 0;       /* network byte order */
static uint32_t s_sta_mask = 0;     /* network byte order */
static uint32_t s_sta_gw = 0;       /* network byte order */
static char s_sta_cidr[32] = "";
static char s_active_routes[256] = "";
static char s_ml_auth_key[128] = "";
static char s_ml_hostname[48] = "";
static char s_ml_ctrl_host[64] = "";
static int s_wifi_idx = 0;
static int s_wifi_retry = 0;

static microlink_t *s_ml = NULL;
static microlink_udp_socket_t *s_dns_sock = NULL;
static microlink_udp_socket_t *s_beacon_sock = NULL;
static SemaphoreHandle_t s_ml_mtx = NULL;
static uint32_t s_dns_queries = 0;
static uint32_t s_beacon_count = 0;
static bool s_beacon_task_started = false;

static int hex_to_bytes(const char *hex, uint8_t *out, size_t out_len) {
    if (!hex || strlen(hex) != out_len * 2) return -1;
    for (size_t i = 0; i < out_len; i++) {
        unsigned int v = 0;
        if (sscanf(hex + i * 2, "%2x", &v) != 1) return -1;
        out[i] = (uint8_t)v;
    }
    return 0;
}

static int mask_to_prefix(uint32_t mask_nbo) {
    uint32_t m = ntohl(mask_nbo);
    int bits = 0;
    while (m & 0x80000000U) {
        bits++;
        m <<= 1;
    }
    return bits;
}

static void refresh_tailnet_task(void *arg) {
    (void)arg;
    vTaskDelay(pdMS_TO_TICKS(500));
    aguja_net_restart_tailnet();
    vTaskDelete(NULL);
}

static void wifi_connect_profile(int idx) {
    char ssid[33] = {0}, pass[65] = {0};
    uint8_t cnt = aguja_config_get_wifi_profile(idx, ssid, sizeof(ssid), pass, sizeof(pass));
    if (cnt == 0 || !ssid[0]) {
        ESP_LOGW(TAG, "No WiFi profiles configured");
        return;
    }
    s_wifi_idx = idx % cnt;

    wifi_config_t wc = {0};
    strncpy((char *)wc.sta.ssid, ssid, sizeof(wc.sta.ssid) - 1);
    strncpy((char *)wc.sta.password, pass, sizeof(wc.sta.password) - 1);
    wc.sta.threshold.authmode = pass[0] ? WIFI_AUTH_WPA_PSK : WIFI_AUTH_OPEN;
    wc.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;
    wc.sta.sort_method = WIFI_CONNECT_AP_BY_SIGNAL;
    wc.sta.pmf_cfg.capable = true;
    wc.sta.pmf_cfg.required = false;

    ESP_LOGI(TAG, "WiFi STA connecting to [%d] '%s'...", s_wifi_idx, wc.sta.ssid);
    aguja_hw_set_net_stage(AGUJA_NET_STAGE_WIFI_CONNECTING);
    esp_wifi_set_config(WIFI_IF_STA, &wc);
    esp_wifi_connect();
}

static void wifi_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data) {
    (void)arg;
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        wifi_connect_profile(0);
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_event_sta_disconnected_t *ev = (wifi_event_sta_disconnected_t *)data;
        ESP_LOGW(TAG, "WiFi STA disconnected (reason=%d)", ev ? (int)ev->reason : -1);
        s_wifi_connected = false;
        xEventGroupClearBits(s_wifi_ev, WIFI_GOT_IP_BIT);
        aguja_hw_set_net_stage(AGUJA_NET_STAGE_WIFI_CONNECTING);
        if (s_wifi_scanning) return;
        s_wifi_retry++;
        uint8_t cnt = aguja_config_get_wifi_profile(0, NULL, 0, NULL, 0);
        if (cnt > 1 && s_wifi_retry >= 3) {
            s_wifi_retry = 0;
            s_wifi_idx = (s_wifi_idx + 1) % cnt;
        }
        wifi_connect_profile(s_wifi_idx);
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *ev = (ip_event_got_ip_t *)data;
        s_wifi_connected = true;
        s_wifi_retry = 0;
        s_sta_ip = ev->ip_info.ip.addr;
        s_sta_mask = ev->ip_info.netmask.addr;
        s_sta_gw = ev->ip_info.gw.addr;

        uint32_t net = s_sta_ip & s_sta_mask;
        int pfx = mask_to_prefix(s_sta_mask);
        struct in_addr na = { .s_addr = net };
        char net_str[16];
        inet_ntoa_r(na, net_str, sizeof(net_str));
        snprintf(s_sta_cidr, sizeof(s_sta_cidr), "%s/%u", net_str, (unsigned)(pfx & 0x3F));

        ESP_LOGI(TAG, "WiFi STA IP=" IPSTR " mask=" IPSTR " gw=" IPSTR " subnet=%s",
                 IP2STR(&ev->ip_info.ip), IP2STR(&ev->ip_info.netmask),
                 IP2STR(&ev->ip_info.gw), s_sta_cidr);
        xEventGroupSetBits(s_wifi_ev, WIFI_GOT_IP_BIT);
        /* If MicroLink already started before STA had a subnet, refresh advertised routes */
        if (s_ml && s_sta_cidr[0] && strstr(s_active_routes, s_sta_cidr) == NULL) {
            ESP_LOGI(TAG, "New upstream subnet %s detected; refreshing Tailnet routes", s_sta_cidr);
            xTaskCreate(refresh_tailnet_task, "tn_ref", 4096, NULL, 3, NULL);
        }
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_AP_STACONNECTED) {
        wifi_event_ap_staconnected_t *ev = (wifi_event_ap_staconnected_t *)data;
        ESP_LOGI(TAG, "SoftAP station joined: " MACSTR " (AID=%d)", MAC2STR(ev->mac), ev->aid);
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_AP_STADISCONNECTED) {
        wifi_event_ap_stadisconnected_t *ev = (wifi_event_ap_stadisconnected_t *)data;
        ESP_LOGI(TAG, "SoftAP station left: " MACSTR, MAC2STR(ev->mac));
    }
}

/* ============================================================================
 * Exit-Node DNS Relay (UDP 53 on Tailscale VPN IP -> upstream DNS)
 * ========================================================================== */

static void on_dns_udp_rx(microlink_udp_socket_t *sock, uint32_t src_ip, uint16_t src_port,
                          const uint8_t *data, size_t len, void *user_data) {
    (void)user_data;
    if (!data || len < 12 || len > 512) return;

    bool dns_en = false;
    char upstream_buf[20] = "1.1.1.1";
    aguja_config_get_dns(&dns_en, upstream_buf, sizeof(upstream_buf));
    if (!dns_en) return;

    s_dns_queries++;
    const char *upstream = upstream_buf[0] ? upstream_buf : "1.1.1.1";

    int fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (fd < 0) return;

    struct timeval tv = { .tv_sec = 2, .tv_usec = 0 };
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    struct sockaddr_in dst = {
        .sin_family = AF_INET,
        .sin_port = htons(53),
    };
    inet_aton(upstream, &dst.sin_addr);

    if (sendto(fd, data, len, 0, (struct sockaddr *)&dst, sizeof(dst)) > 0) {
        uint8_t resp[512];
        ssize_t rlen = recvfrom(fd, resp, sizeof(resp), 0, NULL, NULL);
        if (rlen > 0) {
            microlink_udp_send(sock, src_ip, src_port, resp, (size_t)rlen);
        }
    }
    close(fd);
}

/* ============================================================================
 * Agent Check-In Beacon over Tailscale UDP
 * ========================================================================== */

void aguja_net_send_beacon_now(const char *event_tag) {
    if (!s_ml || microlink_get_vpn_ip(s_ml) == 0 || !s_beacon_sock) return;
    bool en = false;
    char bip[20] = {0}, host[48] = {0};
    uint16_t bport = 0;
    aguja_config_get_beacon(&en, bip, sizeof(bip), &bport, NULL);
    if (!en || !bip[0] || bport == 0) return;

    uint32_t dst_ip = microlink_parse_ip(bip);
    if (dst_ip == 0) return;
    aguja_config_get_hostname(host, sizeof(host));

    char vpn_ip[16] = "0.0.0.0", sta_ip[16] = "0.0.0.0";
    aguja_net_get_vpn_ip_str(vpn_ip, sizeof(vpn_ip));
    aguja_net_get_sta_ip_str(sta_ip, sizeof(sta_ip));

    wifi_ap_record_t ap_info = {0};
    int rssi = 0;
    char ssid[33] = "";
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        rssi = ap_info.rssi;
        memcpy(ssid, ap_info.ssid, 32);
        ssid[32] = '\0';
    }
    float temp_c = 0;
    aguja_hw_read_temp_c(&temp_c);

    char msg[384];
    int n = snprintf(msg, sizeof(msg),
        "{\"event\":\"%s\",\"host\":\"%s\",\"vpn_ip\":\"%s\",\"sta_ip\":\"%s\","
        "\"subnet\":\"%s\",\"ssid\":\"%s\",\"rssi\":%d,\"temp_c\":%.1f,"
        "\"heap_free\":%u,\"uptime_s\":%lld,\"routes\":\"%s\"}",
        event_tag ? event_tag : "heartbeat",
        host, vpn_ip, sta_ip, s_sta_cidr, ssid, rssi, temp_c,
        (unsigned)esp_get_free_heap_size(),
        (long long)(esp_timer_get_time() / 1000000LL),
        s_active_routes);

    if (n > 0) {
        if (microlink_udp_send(s_beacon_sock, dst_ip, bport, msg, (size_t)n) == ESP_OK) {
            s_beacon_count++;
        }
    }
}

esp_err_t aguja_net_send_udp_alert(const char *rule_name, const char *msg_text, int value) {
    if (!s_ml || !microlink_is_connected(s_ml) || !s_beacon_sock) return ESP_ERR_INVALID_STATE;
    char bip[20] = {0}, host[48] = {0};
    uint16_t bport = 0;
    aguja_config_get_beacon(NULL, bip, sizeof(bip), &bport, NULL);
    uint32_t dst_ip = microlink_parse_ip(bip);
    if (dst_ip == 0 || bport == 0) return ESP_ERR_INVALID_ARG;
    aguja_config_get_hostname(host, sizeof(host));

    char buf[256];
    int n = snprintf(buf, sizeof(buf),
        "{\"event\":\"rule_alert\",\"host\":\"%s\",\"rule\":\"%s\",\"msg\":\"%s\",\"value\":%d}",
        host, rule_name ? rule_name : "", msg_text ? msg_text : "", value);
    if (n <= 0) return ESP_FAIL;
    return microlink_udp_send(s_beacon_sock, dst_ip, bport, buf, (size_t)n);
}

static void beacon_task(void *arg) {
    (void)arg;
    while (1) {
        bool en = false;
        uint16_t interval_s = 60;
        aguja_config_get_beacon(&en, NULL, 0, NULL, &interval_s);
        if (interval_s < 5) interval_s = 60;
        vTaskDelay(pdMS_TO_TICKS(interval_s * 1000));
        if (s_ml && microlink_is_connected(s_ml) && en) {
            aguja_net_send_beacon_now("heartbeat");
        }
    }
}

/* ============================================================================
 * MicroLink Callbacks & Lifecycle
 * ========================================================================== */

static void on_ml_state(microlink_t *ml, microlink_state_t state, void *user_data) {
    (void)user_data;
    static const char *names[] = {
        "IDLE", "WIFI_WAIT", "CONNECTING", "REGISTERING",
        "CONNECTED", "RECONNECTING", "ERROR", "AUTH_FAILED", "NEEDS_LOGIN"
    };
    const char *sn = (state < sizeof(names) / sizeof(names[0])) ? names[state] : "UNKNOWN";
    ESP_LOGI(TAG, "Tailnet state -> %s", sn);

    if (state == ML_STATE_CONNECTED) {
        aguja_hw_set_net_stage(AGUJA_NET_STAGE_CONNECTED);
        char ip_str[16];
        microlink_ip_to_str(microlink_get_vpn_ip(ml), ip_str);
        ESP_LOGI(TAG, "AGUJA-IOT ONLINE ON TAILNET! VPN IP: %s | Routes: %s", ip_str, s_active_routes);

        /* Open Exit-Node DNS relay socket (UDP 53 on VPN IP) & beacon socket */
        if (!s_dns_sock) {
            s_dns_sock = microlink_udp_create(ml, 53);
            if (s_dns_sock) {
                microlink_udp_set_rx_callback(s_dns_sock, on_dns_udp_rx, NULL);
                ESP_LOGI(TAG, "Exit-node DNS relay listening on %s:53", ip_str);
            }
        }
        if (!s_beacon_sock) {
            s_beacon_sock = microlink_udp_create(ml, 9421);
        }
        aguja_net_send_beacon_now("online");
    } else if (state == ML_STATE_AUTH_FAILED || state == ML_STATE_ERROR) {
        aguja_hw_set_net_stage(AGUJA_NET_STAGE_ERROR);
    } else if (state == ML_STATE_CONNECTING || state == ML_STATE_REGISTERING || state == ML_STATE_RECONNECTING) {
        aguja_hw_set_net_stage(AGUJA_NET_STAGE_TAILNET_CONNECTING);
    } else if (state == ML_STATE_NEEDS_LOGIN) {
        char url[MICROLINK_AUTH_URL_MAX];
        if (microlink_get_auth_url(ml, url, sizeof(url)) == ESP_OK) {
            ESP_LOGW(TAG, "Tailnet NEEDS_LOGIN URL: %s", url);
        }
    }
}

static void on_ml_peer(microlink_t *ml, const microlink_peer_info_t *peer, void *user_data) {
    (void)ml; (void)user_data;
    char ip[16];
    microlink_ip_to_str(peer->vpn_ip, ip);
    ESP_LOGI(TAG, "Peer %s (%s) online=%d direct=%d", peer->hostname, ip, peer->online, peer->direct_path);
}

static void build_routes_string(const aguja_config_t *cfg, char *out, size_t out_sz) {
    out[0] = '\0';
    size_t pos = 0;

    if (cfg->exit_node_enabled) {
        pos += (size_t)snprintf(out + pos, out_sz - pos, "0.0.0.0/0");
    }
    if (cfg->advertise_upstream_subnet && s_sta_cidr[0]) {
        pos += (size_t)snprintf(out + pos, out_sz - pos, "%s%s", pos ? "," : "", s_sta_cidr);
    }
    if (cfg->ap_enabled && cfg->advertise_ap_subnet) {
        /* Avoid duplicate if upstream is also 192.168.4.0/24 */
        if (strcmp(s_sta_cidr, "192.168.4.0/24") != 0) {
            pos += (size_t)snprintf(out + pos, out_sz - pos, "%s192.168.4.0/24", pos ? "," : "");
        }
    }
    if (cfg->extra_routes[0]) {
        snprintf(out + pos, out_sz - pos, "%s%s", pos ? "," : "", cfg->extra_routes);
    }
}

esp_err_t aguja_net_init(void) {
    if (!s_ml_mtx) s_ml_mtx = xSemaphoreCreateMutex();
    if (!s_wifi_ev) s_wifi_ev = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    s_sta_netif = esp_netif_create_default_wifi_sta();
    s_ap_netif = esp_netif_create_default_wifi_ap();

    wifi_init_config_t init_cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init_cfg));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));
    return ESP_OK;
}

esp_err_t aguja_net_apply_wifi_rf(void) {
    aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
    if (!cfg) return ESP_ERR_NO_MEM;
    aguja_config_get(cfg);
    int8_t dbm = cfg->wifi_tx_power_dbm;
    if (dbm < 8 || dbm > 20) dbm = 20;
    esp_wifi_set_max_tx_power(dbm * 4);
    wifi_ps_type_t ps = (cfg->wifi_ps_mode == 1) ? WIFI_PS_MIN_MODEM :
                        (cfg->wifi_ps_mode == 2) ? WIFI_PS_MAX_MODEM : WIFI_PS_NONE;
    esp_wifi_set_ps(ps);
    free(cfg);
    return ESP_OK;
}

esp_err_t aguja_net_apply_ap(void) {
    aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
    if (!cfg) return ESP_ERR_NO_MEM;
    aguja_config_get(cfg);
    if (cfg->ap_enabled) {
        esp_wifi_set_mode(WIFI_MODE_APSTA);
        wifi_config_t ap_cfg = {0};
        strncpy((char *)ap_cfg.ap.ssid, cfg->ap_ssid, sizeof(ap_cfg.ap.ssid) - 1);
        ap_cfg.ap.ssid_len = (uint8_t)strlen((char *)ap_cfg.ap.ssid);
        strncpy((char *)ap_cfg.ap.password, cfg->ap_pass, sizeof(ap_cfg.ap.password) - 1);
        ap_cfg.ap.channel = cfg->ap_channel ? cfg->ap_channel : 6;
        ap_cfg.ap.max_connection = cfg->ap_max_conn ? cfg->ap_max_conn : 4;
        ap_cfg.ap.authmode = (strlen(cfg->ap_pass) >= 8) ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
        esp_wifi_set_config(WIFI_IF_AP, &ap_cfg);
        esp_netif_napt_enable(s_ap_netif);
        ESP_LOGI(TAG, "SoftAP NAT enabled: SSID='%s' ch=%u subnet=192.168.4.0/24",
                 cfg->ap_ssid, ap_cfg.ap.channel);
    } else {
        esp_netif_napt_disable(s_ap_netif);
        esp_wifi_set_mode(WIFI_MODE_STA);
        ESP_LOGI(TAG, "SoftAP disabled (STA-only mode)");
    }
    free(cfg);
    return ESP_OK;
}

esp_err_t aguja_net_start_wifi(void) {
    aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
    if (!cfg) return ESP_ERR_NO_MEM;
    aguja_config_get(cfg);

    bool ap_en = cfg->ap_enabled;
    if (ap_en) {
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
        wifi_config_t ap_cfg = {0};
        strncpy((char *)ap_cfg.ap.ssid, cfg->ap_ssid, sizeof(ap_cfg.ap.ssid) - 1);
        ap_cfg.ap.ssid_len = (uint8_t)strlen((char *)ap_cfg.ap.ssid);
        strncpy((char *)ap_cfg.ap.password, cfg->ap_pass, sizeof(ap_cfg.ap.password) - 1);
        ap_cfg.ap.channel = cfg->ap_channel ? cfg->ap_channel : 6;
        ap_cfg.ap.max_connection = cfg->ap_max_conn ? cfg->ap_max_conn : 4;
        ap_cfg.ap.authmode = (strlen(cfg->ap_pass) >= 8) ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_cfg));
    } else {
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    }
    free(cfg);

    ESP_ERROR_CHECK(esp_wifi_start());
    aguja_net_apply_wifi_rf();
    if (ap_en) {
        esp_netif_napt_enable(s_ap_netif);
    }

    ESP_LOGI(TAG, "Waiting for WiFi STA IP...");
    xEventGroupWaitBits(s_wifi_ev, WIFI_GOT_IP_BIT, pdFALSE, pdTRUE, pdMS_TO_TICKS(20000));
    return ESP_OK;
}

esp_err_t aguja_net_start_tailnet(void) {
    xSemaphoreTake(s_ml_mtx, portMAX_DELAY);
    if (s_ml) {
        xSemaphoreGive(s_ml_mtx);
        return ESP_OK;
    }

    aguja_config_t *cfg = malloc(sizeof(aguja_config_t));
    if (!cfg) {
        xSemaphoreGive(s_ml_mtx);
        return ESP_ERR_NO_MEM;
    }
    aguja_config_get(cfg);
    build_routes_string(cfg, s_active_routes, sizeof(s_active_routes));

    uint8_t noise_key[32];
    const uint8_t *noise_key_ptr = NULL;
    if (hex_to_bytes(cfg->ctrl_noise_pubkey_hex, noise_key, 32) == 0) {
        noise_key_ptr = noise_key;
    }

    /* Persist string storage so pointers in microlink_config_t remain valid forever */
    snprintf(s_ml_auth_key, sizeof(s_ml_auth_key), "%s", cfg->auth_key);
    snprintf(s_ml_hostname, sizeof(s_ml_hostname), "%s", cfg->hostname[0] ? cfg->hostname : "aguja-iot");
    snprintf(s_ml_ctrl_host, sizeof(s_ml_ctrl_host), "%s", cfg->ctrl_host);

    microlink_config_t ml_cfg = {
        .auth_key = s_ml_auth_key[0] ? s_ml_auth_key : NULL,
        .device_name = s_ml_hostname,
        .enable_derp = true,
        .enable_stun = true,
        .enable_disco = true,
        .max_peers = cfg->max_peers ? cfg->max_peers : 16,
        .wifi_tx_power_dbm = cfg->wifi_tx_power_dbm,
        .priority_peer_ip = cfg->priority_peer_ip[0] ? microlink_parse_ip(cfg->priority_peer_ip) : 0,
        .disco_heartbeat_ms = cfg->disco_heartbeat_ms ? cfg->disco_heartbeat_ms : 3000,
        .ctrl_host = s_ml_ctrl_host[0] ? s_ml_ctrl_host : NULL,
        .ctrl_noise_pubkey = noise_key_ptr,
        .streaming_map_fetch = true,
        .advertise_routes = s_active_routes[0] ? s_active_routes : NULL,
    };

    ESP_LOGI(TAG, "Starting MicroLink: host='%s' ctrl='%s' derp=%u routes='%s'",
             ml_cfg.device_name,
             ml_cfg.ctrl_host ? ml_cfg.ctrl_host : "default",
             (unsigned)cfg->derp_region,
             s_active_routes);

    s_ml = microlink_init(&ml_cfg);
    free(cfg);
    if (!s_ml) {
        ESP_LOGE(TAG, "microlink_init failed! free_heap=%u", (unsigned)esp_get_free_heap_size());
        xSemaphoreGive(s_ml_mtx);
        return ESP_FAIL;
    }
    microlink_set_state_callback(s_ml, on_ml_state, NULL);
    microlink_set_peer_callback(s_ml, on_ml_peer, NULL);

    aguja_hw_set_net_stage(AGUJA_NET_STAGE_TAILNET_CONNECTING);
    esp_err_t err = microlink_start(s_ml);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "microlink_start failed: %s", esp_err_to_name(err));
    }

    if (!s_beacon_task_started) {
        s_beacon_task_started = true;
        xTaskCreate(beacon_task, "aguja_bcn", 3072, NULL, 2, NULL);
    }

    xSemaphoreGive(s_ml_mtx);
    return err;
}

esp_err_t aguja_net_restart_tailnet(void) {
    xSemaphoreTake(s_ml_mtx, portMAX_DELAY);
    if (s_dns_sock) { microlink_udp_close(s_dns_sock); s_dns_sock = NULL; }
    if (s_beacon_sock) { microlink_udp_close(s_beacon_sock); s_beacon_sock = NULL; }
    if (s_ml) {
        microlink_destroy(s_ml);
        s_ml = NULL;
    }
    xSemaphoreGive(s_ml_mtx);
    vTaskDelay(pdMS_TO_TICKS(300));
    return aguja_net_start_tailnet();
}

microlink_t *aguja_net_get_ml(void) { return s_ml; }
bool aguja_net_is_wifi_connected(void) { return s_wifi_connected; }
bool aguja_net_is_tailnet_connected(void) { return s_ml && microlink_is_connected(s_ml); }

void aguja_net_get_sta_ip_str(char *out, size_t out_sz) {
    struct in_addr a = { .s_addr = s_sta_ip };
    char tmp[16] = "0.0.0.0";
    if (s_sta_ip) inet_ntoa_r(a, tmp, sizeof(tmp));
    snprintf(out, out_sz, "%s", tmp);
}

void aguja_net_get_sta_subnet_cidr(char *out, size_t out_sz) {
    snprintf(out, out_sz, "%s", s_sta_cidr);
}

void aguja_net_get_active_routes(char *out, size_t out_sz) {
    snprintf(out, out_sz, "%s", s_active_routes);
}

void aguja_net_get_vpn_ip_str(char *out, size_t out_sz) {
    char tmp[16] = "0.0.0.0";
    if (s_ml) {
        uint32_t ip = microlink_get_vpn_ip(s_ml);
        if (ip) microlink_ip_to_str(ip, tmp);
    }
    snprintf(out, out_sz, "%s", tmp);
}

/* ============================================================================
 * Status & Network Ops JSON Builders
 * ========================================================================== */

cJSON *aguja_net_status_json(void) {
    cJSON *o = cJSON_CreateObject();
    aguja_config_t *cp = malloc(sizeof(aguja_config_t));
    if (!cp) return o;
    aguja_config_get(cp);
#define cfg (*cp)

    /* WiFi STA */
    cJSON *wifi = cJSON_AddObjectToObject(o, "wifi");
    cJSON_AddBoolToObject(wifi, "connected", s_wifi_connected);
    char sta_ip[16], gw_ip[16] = "0.0.0.0";
    aguja_net_get_sta_ip_str(sta_ip, sizeof(sta_ip));
    if (s_sta_gw) {
        struct in_addr g = { .s_addr = s_sta_gw };
        inet_ntoa_r(g, gw_ip, sizeof(gw_ip));
    }
    cJSON_AddStringToObject(wifi, "ip", sta_ip);
    cJSON_AddStringToObject(wifi, "gateway", gw_ip);
    cJSON_AddStringToObject(wifi, "subnet", s_sta_cidr);

    wifi_ap_record_t ap = {0};
    if (s_wifi_connected && esp_wifi_sta_get_ap_info(&ap) == ESP_OK) {
        char ssid[33];
        memcpy(ssid, ap.ssid, 32);
        ssid[32] = '\0';
        char bssid[18];
        snprintf(bssid, sizeof(bssid), "%02x:%02x:%02x:%02x:%02x:%02x",
                 ap.bssid[0], ap.bssid[1], ap.bssid[2], ap.bssid[3], ap.bssid[4], ap.bssid[5]);
        cJSON_AddStringToObject(wifi, "ssid", ssid);
        cJSON_AddStringToObject(wifi, "bssid", bssid);
        cJSON_AddNumberToObject(wifi, "rssi", ap.rssi);
        cJSON_AddNumberToObject(wifi, "channel", ap.primary);
    }
    int8_t tx_q = 0;
    if (esp_wifi_get_max_tx_power(&tx_q) == ESP_OK) {
        cJSON_AddNumberToObject(wifi, "tx_power_dbm", tx_q / 4.0);
    }

    /* SoftAP */
    cJSON *softap = cJSON_AddObjectToObject(o, "ap");
    cJSON_AddBoolToObject(softap, "enabled", cfg.ap_enabled);
    cJSON_AddStringToObject(softap, "ssid", cfg.ap_ssid);
    cJSON_AddStringToObject(softap, "subnet", "192.168.4.0/24");
    wifi_sta_list_t stas = {0};
    if (cfg.ap_enabled && esp_wifi_ap_get_sta_list(&stas) == ESP_OK) {
        cJSON_AddNumberToObject(softap, "clients", stas.num);
    } else {
        cJSON_AddNumberToObject(softap, "clients", 0);
    }

    /* Tailnet */
    cJSON *tn = cJSON_AddObjectToObject(o, "tailnet");
    char vpn_ip[16];
    aguja_net_get_vpn_ip_str(vpn_ip, sizeof(vpn_ip));
    cJSON_AddStringToObject(tn, "hostname", cfg.hostname);
    cJSON_AddStringToObject(tn, "ctrl_host", cfg.ctrl_host);
    cJSON_AddStringToObject(tn, "vpn_ip", vpn_ip);
    cJSON_AddBoolToObject(tn, "connected", aguja_net_is_tailnet_connected());
    cJSON_AddStringToObject(tn, "advertised_routes", s_active_routes);
    cJSON_AddBoolToObject(tn, "exit_node", cfg.exit_node_enabled);
    cJSON_AddBoolToObject(tn, "dns_relay", cfg.dns_relay_enabled);
    cJSON_AddNumberToObject(tn, "dns_queries", s_dns_queries);
    cJSON_AddNumberToObject(tn, "beacons_sent", s_beacon_count);
    if (s_ml) {
        static const char *st_names[] = {
            "IDLE", "WIFI_WAIT", "CONNECTING", "REGISTERING",
            "CONNECTED", "RECONNECTING", "ERROR", "AUTH_FAILED", "NEEDS_LOGIN"
        };
        int st = microlink_get_state(s_ml);
        cJSON_AddStringToObject(tn, "state", (st >= 0 && st < 9) ? st_names[st] : "UNKNOWN");
        cJSON_AddNumberToObject(tn, "peer_count", microlink_get_peer_count(s_ml));
        cJSON_AddNumberToObject(tn, "derp_home_region", s_ml->derp_home_region);
        char stun_ip[16] = "";
        if (s_ml->stun_public_ip) {
            microlink_ip_to_str(s_ml->stun_public_ip, stun_ip);
        }
        cJSON_AddStringToObject(tn, "stun_public_ip", stun_ip);
        cJSON_AddNumberToObject(tn, "stun_public_port", s_ml->stun_public_port);
        cJSON_AddBoolToObject(tn, "symmetric_nat", s_ml->nat_mapping_varies);
    }
#undef cfg
    free(cp);
    return o;
}

cJSON *aguja_net_peers_json(void) {
    cJSON *arr = cJSON_CreateArray();
    if (!s_ml) return arr;
    int n = microlink_get_peer_count(s_ml);
    for (int i = 0; i < n; i++) {
        microlink_peer_info_t p;
        if (microlink_get_peer_info(s_ml, i, &p) == ESP_OK) {
            cJSON *o = cJSON_CreateObject();
            char ip[16];
            microlink_ip_to_str(p.vpn_ip, ip);
            cJSON_AddStringToObject(o, "hostname", p.hostname);
            cJSON_AddStringToObject(o, "vpn_ip", ip);
            cJSON_AddBoolToObject(o, "online", p.online);
            cJSON_AddBoolToObject(o, "direct", p.direct_path);
            cJSON_AddItemToArray(arr, o);
        }
    }
    return arr;
}

cJSON *aguja_net_wifi_scan_json(void) {
    cJSON *arr = cJSON_CreateArray();
    bool was_connected = s_wifi_connected;
    s_wifi_scanning = true;
    if (!was_connected) {
        esp_wifi_disconnect();
        vTaskDelay(pdMS_TO_TICKS(150));
    }
    wifi_scan_config_t sc = { .show_hidden = true };
    esp_err_t err = esp_wifi_scan_start(&sc, true);
    if (err == ESP_OK) {
        uint16_t count = 20;
        wifi_ap_record_t *recs = calloc(count, sizeof(wifi_ap_record_t));
        if (recs) {
            if (esp_wifi_scan_get_ap_records(&count, recs) == ESP_OK) {
                for (uint16_t i = 0; i < count; i++) {
                    cJSON *o = cJSON_CreateObject();
                    char ssid[33];
                    memcpy(ssid, recs[i].ssid, 32);
                    ssid[32] = '\0';
                    char bssid[18];
                    snprintf(bssid, sizeof(bssid), "%02x:%02x:%02x:%02x:%02x:%02x",
                             recs[i].bssid[0], recs[i].bssid[1], recs[i].bssid[2],
                             recs[i].bssid[3], recs[i].bssid[4], recs[i].bssid[5]);
                    cJSON_AddStringToObject(o, "ssid", ssid);
                    cJSON_AddStringToObject(o, "bssid", bssid);
                    cJSON_AddNumberToObject(o, "rssi", recs[i].rssi);
                    cJSON_AddNumberToObject(o, "channel", recs[i].primary);
                    cJSON_AddNumberToObject(o, "authmode", recs[i].authmode);
                    cJSON_AddItemToArray(arr, o);
                }
            }
            free(recs);
        }
    }
    s_wifi_scanning = false;
    if (!was_connected) {
        esp_wifi_connect();
    }
    return arr;
}

cJSON *aguja_net_clients_json(void) {
    cJSON *arr = cJSON_CreateArray();
    wifi_sta_list_t stas = {0};
    if (esp_wifi_ap_get_sta_list(&stas) == ESP_OK) {
        for (int i = 0; i < stas.num; i++) {
            cJSON *o = cJSON_CreateObject();
            char mac[18];
            snprintf(mac, sizeof(mac), "%02x:%02x:%02x:%02x:%02x:%02x",
                     stas.sta[i].mac[0], stas.sta[i].mac[1], stas.sta[i].mac[2],
                     stas.sta[i].mac[3], stas.sta[i].mac[4], stas.sta[i].mac[5]);
            cJSON_AddStringToObject(o, "mac", mac);
            cJSON_AddNumberToObject(o, "rssi", stas.sta[i].rssi);
            cJSON_AddItemToArray(arr, o);
        }
    }
    return arr;
}

typedef struct {
    SemaphoreHandle_t done;
    uint32_t rx;
    uint32_t tx;
    uint32_t min_ms;
    uint32_t max_ms;
    uint32_t sum_ms;
} ping_res_t;

static void ping_on_success(esp_ping_handle_t hdl, void *args) {
    ping_res_t *r = (ping_res_t *)args;
    uint32_t elapsed = 0;
    esp_ping_get_profile(hdl, ESP_PING_PROF_TIMEGAP, &elapsed, sizeof(elapsed));
    r->rx++;
    r->sum_ms += elapsed;
    if (r->rx == 1 || elapsed < r->min_ms) r->min_ms = elapsed;
    if (elapsed > r->max_ms) r->max_ms = elapsed;
}

static void ping_on_end(esp_ping_handle_t hdl, void *args) {
    ping_res_t *r = (ping_res_t *)args;
    esp_ping_get_profile(hdl, ESP_PING_PROF_REQUEST, &r->tx, sizeof(r->tx));
    xSemaphoreGive(r->done);
}

cJSON *aguja_net_ping_json(const char *host, uint32_t count, uint32_t timeout_ms) {
    cJSON *o = cJSON_CreateObject();
    if (!host || !host[0]) {
        cJSON_AddStringToObject(o, "error", "missing host");
        return o;
    }
    if (count == 0 || count > 10) count = 4;
    if (timeout_ms < 200 || timeout_ms > 5000) timeout_ms = 1000;

    struct addrinfo hints = { .ai_family = AF_INET };
    struct addrinfo *res = NULL;
    if (getaddrinfo(host, NULL, &hints, &res) != 0 || !res) {
        cJSON_AddStringToObject(o, "host", host);
        cJSON_AddStringToObject(o, "error", "dns_failed");
        return o;
    }

    ip_addr_t target;
    memset(&target, 0, sizeof(target));
    struct sockaddr_in *sa = (struct sockaddr_in *)res->ai_addr;
    target.type = IPADDR_TYPE_V4;
    target.u_addr.ip4.addr = sa->sin_addr.s_addr;
    char ip_str[16];
    inet_ntoa_r(sa->sin_addr, ip_str, sizeof(ip_str));
    freeaddrinfo(res);

    ping_res_t pr = { .done = xSemaphoreCreateBinary() };
    esp_ping_config_t pcfg = ESP_PING_DEFAULT_CONFIG();
    pcfg.target_addr = target;
    pcfg.count = count;
    pcfg.timeout_ms = timeout_ms;
    pcfg.interval_ms = 250;

    esp_ping_callbacks_t cbs = {
        .cb_args = &pr,
        .on_ping_success = ping_on_success,
        .on_ping_end = ping_on_end,
    };
    esp_ping_handle_t hdl = NULL;
    if (esp_ping_new_session(&pcfg, &cbs, &hdl) == ESP_OK) {
        esp_ping_start(hdl);
        xSemaphoreTake(pr.done, pdMS_TO_TICKS((count * (timeout_ms + 300)) + 2000));
        esp_ping_stop(hdl);
        esp_ping_delete_session(hdl);
    }
    vSemaphoreDelete(pr.done);

    cJSON_AddStringToObject(o, "host", host);
    cJSON_AddStringToObject(o, "ip", ip_str);
    cJSON_AddNumberToObject(o, "tx", pr.tx ? pr.tx : count);
    cJSON_AddNumberToObject(o, "rx", pr.rx);
    cJSON_AddNumberToObject(o, "loss_pct", pr.tx ? (100.0 * (pr.tx - pr.rx) / pr.tx) : 100.0);
    if (pr.rx > 0) {
        cJSON_AddNumberToObject(o, "min_ms", pr.min_ms);
        cJSON_AddNumberToObject(o, "avg_ms", (double)pr.sum_ms / pr.rx);
        cJSON_AddNumberToObject(o, "max_ms", pr.max_ms);
    }
    return o;
}

cJSON *aguja_net_tcp_probe_json(const char *host, uint16_t port, uint32_t timeout_ms) {
    cJSON *o = cJSON_CreateObject();
    if (!host || !host[0] || port == 0) {
        cJSON_AddStringToObject(o, "error", "invalid host/port");
        return o;
    }
    if (timeout_ms < 200 || timeout_ms > 5000) timeout_ms = 1500;

    char pstr[8];
    snprintf(pstr, sizeof(pstr), "%u", port);
    struct addrinfo hints = { .ai_family = AF_INET, .ai_socktype = SOCK_STREAM };
    struct addrinfo *res = NULL;
    if (getaddrinfo(host, pstr, &hints, &res) != 0 || !res) {
        cJSON_AddBoolToObject(o, "open", false);
        cJSON_AddStringToObject(o, "error", "dns_failed");
        return o;
    }

    int fd = socket(AF_INET, SOCK_STREAM, 0);
    bool open = false;
    int64_t t0 = esp_timer_get_time();
    if (fd >= 0) {
        int fl = fcntl(fd, F_GETFL, 0);
        fcntl(fd, F_SETFL, fl | O_NONBLOCK);
        int rc = connect(fd, res->ai_addr, res->ai_addrlen);
        if (rc == 0) {
            open = true;
        } else if (errno == EINPROGRESS) {
            fd_set wfds;
            FD_ZERO(&wfds);
            FD_SET(fd, &wfds);
            struct timeval tv = {
                .tv_sec = timeout_ms / 1000,
                .tv_usec = (timeout_ms % 1000) * 1000,
            };
            if (select(fd + 1, NULL, &wfds, NULL, &tv) > 0) {
                int so_err = 0;
                socklen_t slen = sizeof(so_err);
                getsockopt(fd, SOL_SOCKET, SO_ERROR, &so_err, &slen);
                open = (so_err == 0);
            }
        }
        close(fd);
    }
    int64_t rtt_ms = (esp_timer_get_time() - t0) / 1000;
    freeaddrinfo(res);

    cJSON_AddStringToObject(o, "host", host);
    cJSON_AddNumberToObject(o, "port", port);
    cJSON_AddBoolToObject(o, "open", open);
    cJSON_AddNumberToObject(o, "rtt_ms", (double)rtt_ms);
    return o;
}

cJSON *aguja_net_dns_lookup_json(const char *host) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddStringToObject(o, "host", host ? host : "");
    cJSON *ips = cJSON_AddArrayToObject(o, "ips");
    if (!host || !host[0]) return o;

    struct addrinfo hints = { .ai_family = AF_INET };
    struct addrinfo *res = NULL;
    if (getaddrinfo(host, NULL, &hints, &res) == 0 && res) {
        for (struct addrinfo *p = res; p; p = p->ai_next) {
            struct sockaddr_in *sa = (struct sockaddr_in *)p->ai_addr;
            char ip[16];
            inet_ntoa_r(sa->sin_addr, ip, sizeof(ip));
            cJSON_AddItemToArray(ips, cJSON_CreateString(ip));
        }
        freeaddrinfo(res);
    }
    return o;
}

esp_err_t aguja_net_send_wol(const char *mac_str) {
    if (!mac_str) return ESP_ERR_INVALID_ARG;
    unsigned int m[6];
    if (sscanf(mac_str, "%x:%x:%x:%x:%x:%x", &m[0], &m[1], &m[2], &m[3], &m[4], &m[5]) != 6) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t pkt[102];
    memset(pkt, 0xFF, 6);
    for (int i = 0; i < 16; i++) {
        for (int j = 0; j < 6; j++) pkt[6 + i * 6 + j] = (uint8_t)m[j];
    }

    int fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (fd < 0) return ESP_FAIL;
    int bc = 1;
    setsockopt(fd, SOL_SOCKET, SO_BROADCAST, &bc, sizeof(bc));
    struct sockaddr_in dst = {
        .sin_family = AF_INET,
        .sin_port = htons(9),
        .sin_addr.s_addr = INADDR_BROADCAST,
    };
    ssize_t sent = sendto(fd, pkt, sizeof(pkt), 0, (struct sockaddr *)&dst, sizeof(dst));
    close(fd);
    return (sent == sizeof(pkt)) ? ESP_OK : ESP_FAIL;
}
