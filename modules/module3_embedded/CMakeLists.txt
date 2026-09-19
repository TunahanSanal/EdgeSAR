cmake_minimum_required(VERSION 3.15)
project(EdgeSAR_Embedded LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Wextra -pedantic -Werror -Wstrict-prototypes -Wshadow)
endif()

include_directories(include tests/unity)

set(LIB_SOURCES
    src/cfar_detector.c
    src/hal_sar_mock.c
    src/fft_mock.c
)

add_library(edgesar_embedded STATIC ${LIB_SOURCES})

set(TEST_SOURCES
    tests/unity/unity.c
    tests/test_cfar.c
    tests/test_hal.c
    tests/test_fft.c
    tests/test_runner.c
)

add_executable(test_runner ${TEST_SOURCES})
target_link_libraries(test_runner PRIVATE edgesar_embedded)

if(UNIX)
    target_link_libraries(test_runner PRIVATE m)
endif()

enable_testing()
add_test(NAME UnityUnitTests COMMAND test_runner)
