#pragma once

#include <stddef.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define AGUJA_LOG_RING_SIZE 4096

void aguja_log_init(void);
size_t aguja_log_read(char *out, size_t max_len);
void aguja_log_clear(void);
esp_err_t aguja_log_set_level(const char *tag, const char *level_str);

#ifdef __cplusplus
}
#endif
