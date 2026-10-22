cmake_minimum_required(VERSION 3.24)
project(CzechCoreWindows LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(MSVC)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

add_library(czechcore_text STATIC engine/text.cpp)
target_include_directories(czechcore_text PUBLIC engine)
target_compile_definitions(czechcore_text PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore_text PRIVATE /W4 /WX /permissive- /utf-8)

add_library(czechcore_pipe STATIC client/pipe_io.cpp client/broker_identity.cpp)
target_include_directories(czechcore_pipe PUBLIC client)
target_link_libraries(czechcore_pipe PUBLIC advapi32 bcrypt)
target_compile_definitions(czechcore_pipe PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore_pipe PRIVATE /W4 /WX /permissive- /utf-8)

add_library(czechcore_client STATIC client/engine_client.cpp)
target_include_directories(czechcore_client PUBLIC client)
target_link_libraries(czechcore_client PUBLIC czechcore_text czechcore_pipe advapi32)
target_compile_definitions(czechcore_client PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore_client PRIVATE /W4 /WX /permissive- /utf-8)

add_library(
    czechcore-tsf SHARED
    tsf/module.cpp
    tsf/text_service.cpp
    tsf/display_attribute.cpp
    tsf/inputscope_guids.cpp
    tsf/czechcore-tsf.def)
target_include_directories(czechcore-tsf PRIVATE tsf)
target_link_libraries(czechcore-tsf PRIVATE czechcore_client ole32 oleaut32 user32 uuid)
target_compile_definitions(czechcore-tsf PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore-tsf PRIVATE /W4 /WX /permissive- /utf-8)
set_target_properties(czechcore-tsf PROPERTIES OUTPUT_NAME CzechCoreTsf PREFIX "")

enable_testing()
add_executable(czechcore_text_test tests/text_test.cpp)
target_link_libraries(czechcore_text_test PRIVATE czechcore_text)
target_compile_options(czechcore_text_test PRIVATE /W4 /WX /permissive- /utf-8)
add_test(NAME czechcore_text_test COMMAND czechcore_text_test)

add_executable(czechcore-broker-identity-test tests/broker_identity_test.cpp)
target_link_libraries(czechcore-broker-identity-test PRIVATE czechcore_pipe)
target_compile_definitions(
    czechcore-broker-identity-test PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore-broker-identity-test PRIVATE /W4 /WX /permissive- /utf-8)
add_test(NAME czechcore_broker_identity_test COMMAND czechcore-broker-identity-test)

add_executable(czechcore-register-probe tests/register_probe.cpp)
target_compile_definitions(
    czechcore-register-probe PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore-register-probe PRIVATE /W4 /WX /permissive- /utf-8)

add_executable(czechcore-tsf-host-test tests/tsf_host_test.cpp)
target_link_libraries(czechcore-tsf-host-test PRIVATE ole32 user32 uuid)
target_compile_definitions(
    czechcore-tsf-host-test PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore-tsf-host-test PRIVATE /W4 /WX /permissive- /utf-8)

add_executable(czechcore-client-security-test tests/client_security_test.cpp)
target_link_libraries(czechcore-client-security-test PRIVATE czechcore_client)
target_compile_definitions(
    czechcore-client-security-test PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(
    czechcore-client-security-test PRIVATE /W4 /WX /permissive- /utf-8)

add_executable(czechcore-settings WIN32 settings/main.cpp)
target_link_libraries(czechcore-settings PRIVATE comctl32 user32)
target_compile_definitions(
    czechcore-settings PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore-settings PRIVATE /W4 /WX /permissive- /utf-8)

add_executable(czechcore-setup WIN32 setup/main.cpp)
target_link_libraries(czechcore-setup PRIVATE advapi32 ole32 shell32 user32 uuid)
target_compile_definitions(
    czechcore-setup PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(czechcore-setup PRIVATE /W4 /WX /permissive- /utf-8)

option(CZECHCORE_BUILD_ENGINE "Build the native CTranslate2 engine" OFF)
if(CZECHCORE_BUILD_ENGINE)
    if(NOT DEFINED CT2_SOURCE_DIR)
        message(FATAL_ERROR "CT2_SOURCE_DIR is required")
    endif()
    set(BUILD_CLI OFF CACHE BOOL "" FORCE)
    set(BUILD_TESTS OFF CACHE BOOL "" FORCE)
    set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
    set(WITH_ACCELERATE OFF CACHE BOOL "" FORCE)
    set(WITH_CUDA OFF CACHE BOOL "" FORCE)
    set(WITH_CUDNN OFF CACHE BOOL "" FORCE)
    set(WITH_DNNL OFF CACHE BOOL "" FORCE)
    set(WITH_MKL OFF CACHE BOOL "" FORCE)
    set(WITH_OPENBLAS OFF CACHE BOOL "" FORCE)
    set(WITH_RUY ON CACHE BOOL "" FORCE)
    set(OPENMP_RUNTIME NONE CACHE STRING "" FORCE)
    add_subdirectory("${CT2_SOURCE_DIR}" ctranslate2)

    add_executable(czechcore-engine engine/main.cpp)
    target_link_libraries(czechcore-engine PRIVATE ctranslate2 czechcore_text czechcore_pipe advapi32)
    target_compile_definitions(czechcore-engine PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
    target_compile_options(
        czechcore-engine PRIVATE /W4 /WX /permissive- /utf-8 /external:W0 /external:anglebrackets)
    add_test(
        NAME czechcore_client_security_test
        COMMAND czechcore-client-security-test $<TARGET_FILE_DIR:czechcore-engine>)
endif()
