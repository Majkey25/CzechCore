#include "engine_client.h"

#include "broker_identity.h"
#include "pipe_io.h"
#include "text.h"

#include <windows.h>

#include <filesystem>
#include <memory>
#include <string>
#include <type_traits>
#include <vector>

namespace czechcore {
namespace {

constexpr size_t kMaxTextCharacters = 512;

std::optional<std::filesystem::path> install_root() {
  HKEY key_raw = nullptr;
  if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\CzechCore", 0, KEY_QUERY_VALUE, &key_raw)
      != ERROR_SUCCESS) {
    return std::nullopt;
  }
  const std::unique_ptr<std::remove_pointer_t<HKEY>, decltype(&RegCloseKey)> key(
      key_raw, RegCloseKey);
  DWORD type = 0;
  DWORD bytes = 0;
  if (RegQueryValueExW(key.get(), L"InstallRoot", nullptr, &type, nullptr, &bytes)
          != ERROR_SUCCESS
      || type != REG_SZ || bytes < sizeof(wchar_t) || bytes % sizeof(wchar_t) != 0) {
    return std::nullopt;
  }
  std::wstring value(bytes / sizeof(wchar_t), L'\0');
  if (RegQueryValueExW(
          key.get(),
          L"InstallRoot",
          nullptr,
          &type,
          reinterpret_cast<BYTE*>(value.data()),
          &bytes)
      != ERROR_SUCCESS) {
    return std::nullopt;
  }
  if (value.back() != L'\0') {
    return std::nullopt;
  }
  value.resize(value.size() - 1);
  return value.empty() ? std::nullopt : std::optional(std::filesystem::path(value));
}

bool start_engine(const std::filesystem::path& root) {
  const std::filesystem::path executable = root / "czechcore-engine.exe";
  const std::filesystem::path model = root / "model";
  if (!std::filesystem::is_regular_file(executable)
      || !std::filesystem::is_regular_file(model / "model.bin")) {
    return false;
  }

  std::wstring command = L"\"" + executable.wstring() + L"\" --model \""
      + model.wstring() + L"\"";
  std::vector<wchar_t> mutable_command(command.begin(), command.end());
  mutable_command.push_back(L'\0');
  STARTUPINFOW startup{};
  startup.cb = sizeof(startup);
  PROCESS_INFORMATION process{};
  if (CreateProcessW(
          nullptr,
          mutable_command.data(),
          nullptr,
          nullptr,
          FALSE,
          CREATE_NO_WINDOW | DETACHED_PROCESS,
          nullptr,
          root.c_str(),
          &startup,
          &process)
      == 0) {
    return false;
  }
  CloseHandle(process.hThread);
  CloseHandle(process.hProcess);
  return true;
}

bool wait_for_engine(const std::filesystem::path& root) {
  const HANDLE event_raw = CreateEventW(
      broker_security_attributes(), TRUE, FALSE, kPipeReadyEventName);
  if (event_raw == nullptr) {
    return false;
  }
  const std::unique_ptr<void, decltype(&CloseHandle)> event(event_raw, CloseHandle);
  return start_engine(root)
      && WaitForSingleObject(event.get(), 15000) == WAIT_OBJECT_0
      && WaitNamedPipeW(broker_pipe_name().c_str(), 0) != 0;
}

}  // namespace

void preload_engine() {
  try {
    const auto root = install_root();
    if (root.has_value() && WaitNamedPipeW(broker_pipe_name().c_str(), 0) == 0) {
      start_engine(*root);
    }
  } catch (...) {
  }
}

std::optional<std::wstring> request_engine(std::wstring_view text) {
  try {
    if (text.empty() || text.size() > kMaxTextCharacters) {
      return std::nullopt;
    }
    const auto root = install_root();
    if (!root.has_value()) {
      return std::nullopt;
    }
    const std::filesystem::path executable = *root / "czechcore-engine.exe";
    std::wstring pipe_name = broker_pipe_name();
    if (pipe_name.empty() || WaitNamedPipeW(pipe_name.c_str(), 0) == 0) {
      if (!wait_for_engine(*root)) {
        return std::nullopt;
      }
      pipe_name = broker_pipe_name();
    }
    const HANDLE pipe_raw = CreateFileW(
        pipe_name.c_str(),
        GENERIC_READ | GENERIC_WRITE,
        0,
        nullptr,
        OPEN_EXISTING,
        FILE_FLAG_OVERLAPPED,
        nullptr);
    if (pipe_raw == INVALID_HANDLE_VALUE) {
      return std::nullopt;
    }
    const std::unique_ptr<void, decltype(&CloseHandle)> pipe(pipe_raw, CloseHandle);
    if (!expected_broker(pipe.get(), executable)) {
      return std::nullopt;
    }
    const std::string request = utf16_to_utf8(text);
    if (request.empty() || request.size() > kMaxPipeMessageBytes) {
      return std::nullopt;
    }
    const uint32_t request_size = static_cast<uint32_t>(request.size());
    if (!write_pipe_exact(pipe.get(), &request_size, sizeof(request_size))
        || !write_pipe_exact(pipe.get(), request.data(), request_size)) {
      return std::nullopt;
    }
    uint32_t response_size = 0;
    if (!read_pipe_exact(pipe.get(), &response_size, sizeof(response_size))
        || response_size == 0 || response_size > kMaxPipeMessageBytes) {
      return std::nullopt;
    }
    std::string response(response_size, '\0');
    if (!read_pipe_exact(pipe.get(), response.data(), response_size)) {
      return std::nullopt;
    }
    const uint8_t acknowledgement = 1;
    write_pipe_exact(pipe.get(), &acknowledgement, sizeof(acknowledgement));
    return utf8_to_utf16(response);
  } catch (...) {
    return std::nullopt;
  }
}

}  // namespace czechcore
