set(aguja_reqs
    microlink
    nvs_flash
    esp_wifi
    esp_netif
    esp_event
    esp_timer
    esp_http_server
    esp_adc
    esp_pm
    app_update
    esp_app_format
    driver
    esp_driver_gpio
    esp_driver_ledc
    esp_driver_i2c
    esp_driver_uart
    esp_driver_spi
    lwip
    json
    mbedtls
)

if(NOT IDF_TARGET STREQUAL "esp32")
    list(APPEND aguja_reqs esp_driver_tsens)
endif()

if(IDF_TARGET STREQUAL "esp32c6" OR IDF_TARGET STREQUAL "esp32c3" OR IDF_TARGET STREQUAL "esp32s3")
    list(APPEND aguja_reqs esp_driver_usb_serial_jtag)
endif()

idf_component_register(
    SRCS
        "main.c"
        "aguja_log.c"
        "aguja_config.c"
        "aguja_hw.c"
        "aguja_net.c"
        "aguja_http.c"
        "aguja_cli.c"
    INCLUDE_DIRS "."
    REQUIRES ${aguja_reqs}
)
