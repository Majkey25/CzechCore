#include "pipe_io.h"

#include <memory>

namespace czechcore {
namespace {

bool wait_for_io(HANDLE pipe, OVERLAPPED& overlap, DWORD& transferred) {
  const DWORD wait = WaitForSingleObject(overlap.hEvent, kPipeIoTimeoutMilliseconds);
  if (wait != WAIT_OBJECT_0) {
    CancelIoEx(pipe, &overlap);
    WaitForSingleObject(overlap.hEvent, INFINITE);
    SetLastError(wait == WAIT_TIMEOUT ? ERROR_TIMEOUT : ERROR_OPERATION_ABORTED);
    return false;
  }
  return GetOverlappedResult(pipe, &overlap, &transferred, FALSE) != 0;
}

bool transfer_exact(HANDLE pipe, void* buffer, uint32_t bytes, bool write) {
  auto* data = static_cast<unsigned char*>(buffer);
  uint32_t offset = 0;
  while (offset < bytes) {
    const HANDLE event_raw = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    if (event_raw == nullptr) {
      return false;
    }
    const std::unique_ptr<void, decltype(&CloseHandle)> event(event_raw, CloseHandle);
    OVERLAPPED overlap{};
    overlap.hEvent = event.get();
    const BOOL started = write
        ? WriteFile(pipe, data + offset, bytes - offset, nullptr, &overlap)
        : ReadFile(pipe, data + offset, bytes - offset, nullptr, &overlap);
    DWORD transferred = 0;
    if (started != 0) {
      if (GetOverlappedResult(pipe, &overlap, &transferred, FALSE) == 0) {
        return false;
      }
    } else if (GetLastError() != ERROR_IO_PENDING
               || !wait_for_io(pipe, overlap, transferred)) {
      return false;
    }
    if (transferred == 0) {
      return false;
    }
    offset += transferred;
  }
  return true;
}

}  // namespace

bool connect_pipe(HANDLE pipe, DWORD timeout_milliseconds) {
  const HANDLE event_raw = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  if (event_raw == nullptr) {
    return false;
  }
  const std::unique_ptr<void, decltype(&CloseHandle)> event(event_raw, CloseHandle);
  OVERLAPPED overlap{};
  overlap.hEvent = event.get();
  if (ConnectNamedPipe(pipe, &overlap) != 0 || GetLastError() == ERROR_PIPE_CONNECTED) {
    return true;
  }
  if (GetLastError() != ERROR_IO_PENDING) {
    return false;
  }
  const DWORD wait = WaitForSingleObject(overlap.hEvent, timeout_milliseconds);
  if (wait != WAIT_OBJECT_0) {
    CancelIoEx(pipe, &overlap);
    WaitForSingleObject(overlap.hEvent, INFINITE);
    SetLastError(wait == WAIT_TIMEOUT ? ERROR_SEM_TIMEOUT : ERROR_OPERATION_ABORTED);
    return false;
  }
  DWORD transferred = 0;
  return GetOverlappedResult(pipe, &overlap, &transferred, FALSE) != 0;
}

bool read_pipe_exact(HANDLE pipe, void* output, uint32_t bytes) {
  return transfer_exact(pipe, output, bytes, false);
}

bool write_pipe_exact(HANDLE pipe, const void* input, uint32_t bytes) {
  return transfer_exact(pipe, const_cast<void*>(input), bytes, true);
}

}  // namespace czechcore
