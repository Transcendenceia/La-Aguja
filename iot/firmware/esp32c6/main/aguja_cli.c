#include "aguja_cli.h"
#include "aguja_config.h"
#include "aguja_hw.h"
#include "aguja_net.h"
#include "aguja_log.h"
#include "driver/usb_serial_jtag.h"
#include "esp_system.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static const char *TAG = "aguja_cli";

static void cli_exec(char *line) {
    while (*line == ' ' || *line == '\t') line++;
    size_t n = strlen(line);
    while (n > 0 && (line[n - 1] == '\r' || line[n - 1] == '\n' || line[n - 1] == ' ')) line[--n] = '\0';
    if (n == 0) return;

    if (strcmp(line, "help") == 0) {
        printf("\n=== Aguja-IoT Serial CLI ===\n"
               "  status                       - Show WiFi, Tailnet, Heap, Temp\n"
               "  token                        - Print API Bearer token\n"
               "  config                       - Dump JSON config (redacted)\n"
               "  wifi <ssid> <pass>           - Set primary WiFi & reboot\n"
               "  authkey <key>                - Set Headscale pre-auth key & restart tailnet\n"
               "  antenna <ceramic|ufl>        - Switch XIAO RF antenna\n"
               "  led <status|on|off|blink>    - Control user LED\n"
               "  lan <on|off>                 - Allow/deny HTTP API on LAN\n"
               "  reboot                       - Reboot ESP32-C6\n"
               "  factory-reset                - Wipe NVS config + Tailscale keys & reboot\n\n");
    } else if (strcmp(line, "status") == 0) {
        cJSON *j = aguja_net_status_json();
        float tc = 0;
        aguja_hw_read_temp_c(&tc);
        cJSON_AddNumberToObject(j, "temp_c", tc);
        cJSON_AddNumberToObject(j, "heap_free", esp_get_free_heap_size());
        cJSON_AddNumberToObject(j, "heap_min", esp_get_minimum_free_heap_size());
        cJSON_AddStringToObject(j, "antenna", aguja_hw_get_antenna_external() ? "ufl" : "ceramic");
        char *s = cJSON_PrintUnformatted(j);
        if (s) { printf("%s\n", s); free(s); }
        cJSON_Delete(j);
    } else if (strcmp(line, "scan") == 0) {
        cJSON *j = aguja_net_wifi_scan_json();
        char *s = cJSON_PrintUnformatted(j);
        if (s) { printf("%s\n", s); free(s); }
        cJSON_Delete(j);
    } else if (strcmp(line, "token") == 0) {
        char tok[65] = {0};
        aguja_config_get_token(tok, sizeof(tok));
        printf("API_TOKEN=%s\n", tok);
    } else if (strcmp(line, "config") == 0) {
        cJSON *j = aguja_config_to_json(false);
        char *s = cJSON_PrintUnformatted(j);
        if (s) { printf("%s\n", s); free(s); }
        cJSON_Delete(j);
    } else if (strncmp(line, "wifi ", 5) == 0) {
        char *ssid = line + 5;
        char *sp = strchr(ssid, ' ');
        char *pass = "";
        if (sp) { *sp = '\0'; pass = sp + 1; }
        aguja_config_set_wifi_primary(ssid, pass);
        printf("WiFi primary set to '%s'. Rebooting...\n", ssid);
        vTaskDelay(pdMS_TO_TICKS(300));
        esp_restart();
    } else if (strncmp(line, "authkey ", 8) == 0) {
        aguja_config_set_auth_key(line + 8);
        printf("Auth key saved. Restarting tailnet...\n");
        aguja_net_restart_tailnet();
    } else if (strncmp(line, "antenna ", 8) == 0) {
        bool ext = (strcmp(line + 8, "ufl") == 0 || strcmp(line + 8, "ext") == 0);
        aguja_hw_set_antenna(ext);
        aguja_config_set_antenna(ext);
        printf("Antenna switched to %s\n", ext ? "EXTERNAL u.FL" : "INTERNAL ceramic");
    } else if (strncmp(line, "led ", 4) == 0) {
        const char *m = line + 4;
        if (strcmp(m, "on") == 0) aguja_hw_set_led(AGUJA_LED_ON, 100, 500);
        else if (strcmp(m, "off") == 0) aguja_hw_set_led(AGUJA_LED_OFF, 0, 500);
        else if (strcmp(m, "blink") == 0) aguja_hw_set_led(AGUJA_LED_BLINK, 50, 300);
        else aguja_hw_set_led(AGUJA_LED_STATUS, 50, 500);
        printf("LED mode updated: %s\n", m);
    } else if (strncmp(line, "lan ", 4) == 0) {
        aguja_config_t *c = malloc(sizeof(aguja_config_t));
        if (c) {
            aguja_config_get(c);
            c->http_allow_lan = (strcmp(line + 4, "on") == 0);
            aguja_config_set(c);
            printf("HTTP LAN access: %s\n", c->http_allow_lan ? "ENABLED" : "TAILNET-ONLY");
            free(c);
        }
    } else if (strcmp(line, "reboot") == 0) {
        printf("Rebooting...\n");
        vTaskDelay(pdMS_TO_TICKS(200));
        esp_restart();
    } else if (strcmp(line, "factory-reset") == 0) {
        printf("Factory reset: wiping config & Tailscale keys...\n");
        aguja_config_reset_defaults();
        microlink_factory_reset();
        vTaskDelay(pdMS_TO_TICKS(300));
        esp_restart();
    } else {
        printf("Unknown command: '%s' (type 'help')\n", line);
    }
}

static void cli_task(void *arg) {
    (void)arg;
    usb_serial_jtag_driver_config_t cfg = {
        .rx_buffer_size = 512,
        .tx_buffer_size = 512,
    };
    if (usb_serial_jtag_driver_install(&cfg) != ESP_OK) {
        ESP_LOGW(TAG, "USB Serial/JTAG CLI driver already installed or unavailable");
        vTaskDelete(NULL);
        return;
    }

    char line[256];
    size_t pos = 0;
    uint8_t ch;
    while (1) {
        int n = usb_serial_jtag_read_bytes(&ch, 1, pdMS_TO_TICKS(200));
        if (n <= 0) continue;
        if (ch == '\r' || ch == '\n') {
            line[pos] = '\0';
            if (pos > 0) cli_exec(line);
            pos = 0;
        } else if (ch == 0x7F || ch == '\b') {
            if (pos > 0) pos--;
        } else if (pos + 1 < sizeof(line)) {
            line[pos++] = (char)ch;
        }
    }
}

void aguja_cli_start(void) {
    xTaskCreate(cli_task, "aguja_cli", 3072, NULL, 2, NULL);
}
