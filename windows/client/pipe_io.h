#pragma once

#include <windows.h>

#include <cstdint>

namespace czechcore {

constexpr uint32_t kMaxPipeMessageBytes = 16 * 1024;
constexpr DWORD kPipeIoTimeoutMilliseconds = 5000;

bool connect_pipe(HANDLE pipe, DWORD timeout_milliseconds);
bool read_pipe_exact(HANDLE pipe, void* output, uint32_t bytes);
bool write_pipe_exact(HANDLE pipe, const void* input, uint32_t bytes);

}  // namespace czechcore
