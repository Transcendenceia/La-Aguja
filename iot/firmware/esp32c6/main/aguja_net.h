#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "cJSON.h"
#include "microlink.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t aguja_net_init(void);
esp_err_t aguja_net_start_wifi(void);
esp_err_t aguja_net_start_tailnet(void);
esp_err_t aguja_net_restart_tailnet(void);
esp_err_t aguja_net_apply_wifi_rf(void);
esp_err_t aguja_net_apply_ap(void);

microlink_t *aguja_net_get_ml(void);
bool aguja_net_is_wifi_connected(void);
bool aguja_net_is_tailnet_connected(void);
void aguja_net_get_sta_ip_str(char *out, size_t out_sz);
void aguja_net_get_sta_subnet_cidr(char *out, size_t out_sz);
void aguja_net_get_active_routes(char *out, size_t out_sz);
void aguja_net_get_vpn_ip_str(char *out, size_t out_sz);

/* Telemetry & Network Ops APIs */
cJSON *aguja_net_status_json(void);
cJSON *aguja_net_peers_json(void);
cJSON *aguja_net_wifi_scan_json(void);
cJSON *aguja_net_clients_json(void);
cJSON *aguja_net_ping_json(const char *host, uint32_t count, uint32_t timeout_ms);
cJSON *aguja_net_tcp_probe_json(const char *host, uint16_t port, uint32_t timeout_ms);
cJSON *aguja_net_dns_lookup_json(const char *host);
esp_err_t aguja_net_send_wol(const char *mac_str);
esp_err_t aguja_net_send_udp_alert(const char *rule_name, const char *msg, int value);

/* Send one immediate beacon over Tailnet */
void aguja_net_send_beacon_now(const char *event_tag);

#ifdef __cplusplus
}
#endif
