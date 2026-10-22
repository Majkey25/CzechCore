#include "broker_identity.h"
#include "pipe_io.h"

#include <iostream>
#include <future>
#include <cstdlib>
#include <memory>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}

std::wstring executable_path() {
  std::wstring executable(32768, L'\0');
  const DWORD length = GetModuleFileNameW(nullptr, executable.data(),
                                        static_cast<DWORD>(executable.size()));
  require(length != 0 && length < executable.size(), "executable path failed");
  executable.resize(length);
  return executable;
}

using Handle = std::unique_ptr<void, decltype(&CloseHandle)>;

Handle start_peer(const wchar_t* mode, HANDLE ready, HANDLE stop) {
  std::wstring command = L"\"" + executable_path() + L"\" " + mode + L" "
      + std::to_wstring(reinterpret_cast<uintptr_t>(ready)) + L" "
      + std::to_wstring(reinterpret_cast<uintptr_t>(stop));
  STARTUPINFOW startup{};
  startup.cb = sizeof(startup);
  PROCESS_INFORMATION process{};
  require(CreateProcessW(nullptr, command.data(), nullptr, nullptr, TRUE,
                        CREATE_NO_WINDOW, nullptr, nullptr, &startup, &process) != 0,
          "peer start failed");
  CloseHandle(process.hThread);
  return Handle(process.hProcess, CloseHandle);
}

void wait_peer(HANDLE process) {
  require(WaitForSingleObject(process, 10000) == WAIT_OBJECT_0, "peer exit timed out");
  DWORD code = 1;
  require(GetExitCodeProcess(process, &code) != 0 && code == 0, "peer failed");
}

int run_peer(std::wstring_view mode, HANDLE ready, HANDLE stop) {
  if (mode == L"probe") {
    return czechcore::broker_pipe_name().empty() ? 1 : 0;
  }
  czechcore::broker_security_attributes();
  Handle server(nullptr, CloseHandle);
  Handle endpoint(nullptr, CloseHandle);
  if (mode == L"holder") {
    const std::wstring name = czechcore::new_broker_pipe_name();
    server.reset(CreateNamedPipeW(
        name.c_str(), PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE,
        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
        1, 4096, 4096, 0, czechcore::broker_security_attributes()));
    require(server.get() != INVALID_HANDLE_VALUE, "holder pipe creation failed");
    endpoint.reset(czechcore::publish_broker_pipe_name(name));
  }
  require(SetEvent(ready) != 0, "peer readiness failed");
  require(WaitForSingleObject(stop, 10000) == WAIT_OBJECT_0, "peer stop timed out");
  return 0;
}

void test_namespace_creator_exit() {
  SECURITY_ATTRIBUTES attributes{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
  Handle ready(CreateEventW(&attributes, TRUE, FALSE, nullptr), CloseHandle);
  Handle stop_creator(CreateEventW(&attributes, TRUE, FALSE, nullptr), CloseHandle);
  Handle stop_holder(CreateEventW(&attributes, TRUE, FALSE, nullptr), CloseHandle);
  require(ready && stop_creator && stop_holder, "coordination event creation failed");
  const auto creator = start_peer(L"creator", ready.get(), stop_creator.get());
  require(WaitForSingleObject(ready.get(), 10000) == WAIT_OBJECT_0, "creator readiness failed");
  ResetEvent(ready.get());
  const auto holder = start_peer(L"holder", ready.get(), stop_holder.get());
  require(WaitForSingleObject(ready.get(), 10000) == WAIT_OBJECT_0, "holder readiness failed");
  SetEvent(stop_creator.get());
  wait_peer(creator.get());
  const auto probe = start_peer(L"probe", ready.get(), stop_holder.get());
  wait_peer(probe.get());
  SetEvent(stop_holder.get());
  wait_peer(holder.get());
}

}  // namespace

int wmain(int argument_count, wchar_t** arguments) {
  try {
    if (argument_count == 4) {
      return run_peer(arguments[1],
          reinterpret_cast<HANDLE>(static_cast<uintptr_t>(std::wcstoull(arguments[2], nullptr, 10))),
          reinterpret_cast<HANDLE>(static_cast<uintptr_t>(std::wcstoull(arguments[3], nullptr, 10))));
    }
    test_namespace_creator_exit();
    const std::wstring name = czechcore::new_broker_pipe_name();
    require(name != czechcore::new_broker_pipe_name(), "endpoint nonce was reused");
    const HANDLE raw = CreateNamedPipeW(
        name.c_str(), PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE | FILE_FLAG_OVERLAPPED,
        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
        1, 4096, 4096, 0, czechcore::broker_security_attributes());
    require(raw != INVALID_HANDLE_VALUE, "pipe creation failed");
    const std::unique_ptr<void, decltype(&CloseHandle)> server(raw, CloseHandle);
    {
      const std::unique_ptr<void, decltype(&CloseHandle)> endpoint(
          czechcore::publish_broker_pipe_name(name), CloseHandle);
      require(czechcore::broker_pipe_name() == name, "protected endpoint discovery failed");
      const std::wstring executable = executable_path();
      for (int index = 0; index < 2; ++index) {
        auto connection = std::async(std::launch::async, [&server] {
          return czechcore::connect_pipe(server.get(), 1000);
        });
        require(WaitNamedPipeW(name.c_str(), 1000) != 0, "pipe readiness failed");
        const HANDLE client_raw = CreateFileW(name.c_str(), GENERIC_READ | GENERIC_WRITE,
            0, nullptr, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, nullptr);
        require(client_raw != INVALID_HANDLE_VALUE, "client connection failed");
        const std::unique_ptr<void, decltype(&CloseHandle)> client(client_raw, CloseHandle);
        require(connection.get(), "server connection failed");
        require(czechcore::expected_broker(client.get(), executable), "valid peer rejected");
        require(!czechcore::expected_broker(client.get(), executable + L".wrong"),
                "wrong executable accepted");
        const uint8_t sent = 7;
        uint8_t received = 0;
        require(czechcore::write_pipe_exact(client.get(), &sent, sizeof(sent)), "write failed");
        require(czechcore::read_pipe_exact(server.get(), &received, sizeof(received))
                && received == sent, "read failed");
        require(DisconnectNamedPipe(server.get()) != 0, "disconnect failed");
      }
    }
    require(czechcore::broker_pipe_name().empty(), "stale endpoint survived broker exit");
    std::cout << "protected discovery, peer identity, reconnect, and cleanup passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
