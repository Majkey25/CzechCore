#include "engine_client.h"
#include "broker_identity.h"
#include "pipe_io.h"

#include <windows.h>

#include <filesystem>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <thread>

namespace {

constexpr wchar_t kRegistryPath[] = L"Software\\CzechCore";

class RegistryRoot final {
 public:
  explicit RegistryRoot(const std::wstring& value) {
    DWORD bytes = 0;
    if (RegGetValueW(
            HKEY_CURRENT_USER,
            kRegistryPath,
            L"InstallRoot",
            RRF_RT_REG_SZ,
            nullptr,
            nullptr,
            &bytes)
        == ERROR_SUCCESS) {
      std::wstring previous(bytes / sizeof(wchar_t), L'\0');
      if (RegGetValueW(
              HKEY_CURRENT_USER,
              kRegistryPath,
              L"InstallRoot",
              RRF_RT_REG_SZ,
              nullptr,
              previous.data(),
              &bytes)
          == ERROR_SUCCESS) {
        previous.resize(wcsnlen_s(previous.c_str(), previous.size()));
        previous_ = std::move(previous);
      }
    }
    valid_ = RegSetKeyValueW(
        HKEY_CURRENT_USER,
        kRegistryPath,
        L"InstallRoot",
        REG_SZ,
        value.c_str(),
        static_cast<DWORD>((value.size() + 1) * sizeof(wchar_t)))
        == ERROR_SUCCESS;
  }

  ~RegistryRoot() {
    if (previous_.has_value()) {
      RegSetKeyValueW(
          HKEY_CURRENT_USER,
          kRegistryPath,
          L"InstallRoot",
          REG_SZ,
          previous_->c_str(),
          static_cast<DWORD>((previous_->size() + 1) * sizeof(wchar_t)));
    } else {
      RegDeleteKeyValueW(HKEY_CURRENT_USER, kRegistryPath, L"InstallRoot");
    }
  }

  bool valid() const { return valid_; }

 private:
  std::optional<std::wstring> previous_;
  bool valid_ = false;
};

}  // namespace

int wmain(int argument_count, wchar_t** arguments) {
  if (argument_count != 2) {
    std::wcerr << L"usage: czechcore-client-security-test ENGINE_DIRECTORY\n";
    return 2;
  }
  const std::filesystem::path root(arguments[1]);
  if (!std::filesystem::is_regular_file(root / "czechcore-engine.exe")) {
    std::wcerr << L"engine executable is missing\n";
    return 2;
  }
  RegistryRoot registry(root.wstring());
  if (!registry.valid()) {
    std::wcerr << L"registry setup failed\n";
    return 1;
  }
  const std::wstring pipe_name = czechcore::new_broker_pipe_name();
  const HANDLE pipe = CreateNamedPipeW(
      pipe_name.c_str(),
      PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE | FILE_FLAG_OVERLAPPED,
      PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
      1,
      4096,
      4096,
      0,
      czechcore::broker_security_attributes());
  if (pipe == INVALID_HANDLE_VALUE) {
    std::wcerr << L"test pipe creation failed\n";
    return 1;
  }
  const std::unique_ptr<void, decltype(&CloseHandle)> endpoint(
      czechcore::publish_broker_pipe_name(pipe_name), CloseHandle);
  bool sent_to_untrusted_peer = false;
  std::thread server([pipe, &sent_to_untrusted_peer] {
    if (czechcore::connect_pipe(pipe, 1000)) {
      uint8_t received = 0;
      sent_to_untrusted_peer = czechcore::read_pipe_exact(pipe, &received, sizeof(received));
      DisconnectNamedPipe(pipe);
    }
  });
  const auto response = czechcore::request_engine(L"To je problém.");
  server.join();
  CloseHandle(pipe);
  if (response.has_value() || sent_to_untrusted_peer) {
    std::wcerr << L"untrusted pipe server was accepted\n";
    return 1;
  }
  std::wcout << L"untrusted pipe server rejected\n";
  return 0;
}
