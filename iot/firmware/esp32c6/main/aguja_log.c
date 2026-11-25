#include "aguja_log.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <strings.h>

static char s_ring[AGUJA_LOG_RING_SIZE];
static size_t s_head = 0;
static size_t s_count = 0;
static portMUX_TYPE s_lock = portMUX_INITIALIZER_UNLOCKED;
static vprintf_like_t s_orig_vprintf = NULL;

static int aguja_vprintf(const char *fmt, va_list args) {
    char tmp[384];
    va_list copy;
    va_copy(copy, args);
    int n = vsnprintf(tmp, sizeof(tmp), fmt, copy);
    va_end(copy);

    if (n > 0) {
        size_t len = (size_t)n;
        if (len >= sizeof(tmp)) len = sizeof(tmp) - 1;
        portENTER_CRITICAL(&s_lock);
        for (size_t i = 0; i < len; i++) {
            s_ring[s_head] = tmp[i];
            s_head = (s_head + 1) % AGUJA_LOG_RING_SIZE;
            if (s_count < AGUJA_LOG_RING_SIZE) {
                s_count++;
            }
        }
        portEXIT_CRITICAL(&s_lock);
    }

    if (s_orig_vprintf) {
        return s_orig_vprintf(fmt, args);
    }
    return vprintf(fmt, args);
}

void aguja_log_init(void) {
    if (!s_orig_vprintf) {
        s_orig_vprintf = esp_log_set_vprintf(aguja_vprintf);
    }
}

size_t aguja_log_read(char *out, size_t max_len) {
    if (!out || max_len == 0) return 0;
    portENTER_CRITICAL(&s_lock);
    size_t avail = s_count;
    size_t to_copy = avail;
    if (to_copy > max_len - 1) {
        to_copy = max_len - 1;
    }
    size_t start = (s_head + AGUJA_LOG_RING_SIZE - to_copy) % AGUJA_LOG_RING_SIZE;
    size_t first = AGUJA_LOG_RING_SIZE - start;
    if (first > to_copy) first = to_copy;
    memcpy(out, s_ring + start, first);
    if (to_copy > first) {
        memcpy(out + first, s_ring, to_copy - first);
    }
    portEXIT_CRITICAL(&s_lock);
    out[to_copy] = '\0';
    return to_copy;
}

void aguja_log_clear(void) {
    portENTER_CRITICAL(&s_lock);
    s_head = 0;
    s_count = 0;
    portEXIT_CRITICAL(&s_lock);
}

esp_err_t aguja_log_set_level(const char *tag, const char *level_str) {
    if (!tag || !tag[0] || !level_str) return ESP_ERR_INVALID_ARG;
    esp_log_level_t lvl = ESP_LOG_INFO;
    if (strcasecmp(level_str, "none") == 0) lvl = ESP_LOG_NONE;
    else if (strcasecmp(level_str, "error") == 0) lvl = ESP_LOG_ERROR;
    else if (strcasecmp(level_str, "warn") == 0) lvl = ESP_LOG_WARN;
    else if (strcasecmp(level_str, "info") == 0) lvl = ESP_LOG_INFO;
    else if (strcasecmp(level_str, "debug") == 0) lvl = ESP_LOG_DEBUG;
    else if (strcasecmp(level_str, "verbose") == 0) lvl = ESP_LOG_VERBOSE;
    else return ESP_ERR_INVALID_ARG;

    esp_log_level_set(tag, lvl);
    return ESP_OK;
}
