#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t aguja_http_start(void);
void aguja_http_stop(void);

#ifdef __cplusplus
}
#endif
