#include "aguja_log.h"
#include "aguja_config.h"
#include "aguja_hw.h"
#include "aguja_net.h"
#include "aguja_http.h"
#include "aguja_cli.h"
#include "nvs_flash.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_app_desc.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "aguja_main";

static void on_rule_alert(const char *rule_name, const char *msg, int value) {
    ESP_LOGW(TAG, "Rule '%s' triggered (val=%d): %s", rule_name, value, msg);
    aguja_net_send_udp_alert(rule_name, msg, value);
}

void app_main(void) {
    /* 1. Capture logs into RAM ring buffer immediately */
    aguja_log_init();

    const esp_app_desc_t *app = esp_app_get_description();
    const esp_partition_t *part = esp_ota_get_running_partition();
    ESP_LOGI(TAG, "=== AGUJA-IOT Mobile Ops Center (%s) ===", AGUJA_BOARD_NAME);
    ESP_LOGI(TAG, "FW %s (%s %s) running on partition '%s'",
             app->version, app->date, app->time, part ? part->label : "?");

    /* 2. Init NVS */
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    /* 3. Load ultra-editable NVS config */
    ESP_ERROR_CHECK(aguja_config_init());

    /* 4. Init XIAO hardware (RF antenna switch MUST run before WiFi!) */
    ESP_ERROR_CHECK(aguja_hw_init());
    aguja_hw_start_tasks(on_rule_alert);

    /* 5. Start interactive USB Serial/JTAG CLI */
    aguja_cli_start();

    /* 6. Init WiFi STA + optional SoftAP NAT gateway */
    ESP_ERROR_CHECK(aguja_net_init());
    ESP_ERROR_CHECK(aguja_net_start_wifi());

    /* 7. Start Tailscale/Headscale VPN (MicroLink: Exit Node + Subnet Router + DNS Relay) */
    aguja_net_start_tailnet();

    /* 8. Start Agent Ops HTTP Server (REST JSON API + Dark Web UI + Tailnet OTA) */
    ESP_ERROR_CHECK(aguja_http_start());

    /* Print initial status summary */
    ESP_LOGI(TAG, "Boot complete. Free heap: %u bytes (min: %u)",
             (unsigned)esp_get_free_heap_size(),
             (unsigned)esp_get_minimum_free_heap_size());

    /* Keep watchdog / periodic health log calm */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(60000));
        char vpn[16], sta[16];
        aguja_net_get_vpn_ip_str(vpn, sizeof(vpn));
        aguja_net_get_sta_ip_str(sta, sizeof(sta));
        float tc = 0;
        aguja_hw_read_temp_c(&tc);
        ESP_LOGI(TAG, "[HEALTH] sta=%s vpn=%s peers=%d temp=%.1fC heap=%u min=%u",
                 sta, vpn,
                 aguja_net_get_ml() ? microlink_get_peer_count(aguja_net_get_ml()) : 0,
                 tc,
                 (unsigned)esp_get_free_heap_size(),
                 (unsigned)esp_get_minimum_free_heap_size());
    }
}
