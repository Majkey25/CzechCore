cmake_minimum_required(VERSION 3.22.1)
project(czechcore_android LANGUAGES CXX)

if(NOT CT2_INCLUDE_DIR OR NOT EXISTS "${CT2_INCLUDE_DIR}/ctranslate2/translator.h")
  message(FATAL_ERROR "CT2_INCLUDE_DIR must contain the pinned CTranslate2 headers")
endif()

set(CT2_LIBRARY "${CT2_LIBRARY_DIR}/${ANDROID_ABI}/libctranslate2.so")
if(NOT EXISTS "${CT2_LIBRARY}")
  message(FATAL_ERROR "Missing prebuilt CTranslate2 library: ${CT2_LIBRARY}")
endif()

add_library(ctranslate2 SHARED IMPORTED)
set_target_properties(ctranslate2 PROPERTIES IMPORTED_LOCATION "${CT2_LIBRARY}")

add_library(czechcore_jni SHARED native_bridge.cpp)
target_compile_features(czechcore_jni PRIVATE cxx_std_17)
target_include_directories(czechcore_jni PRIVATE "${CT2_INCLUDE_DIR}")
target_link_libraries(czechcore_jni PRIVATE ctranslate2 log)
