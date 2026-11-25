cmake_minimum_required(VERSION 3.16)

set(PROJECT_VER "1.4.0")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/components")

project(aguja_iot)
