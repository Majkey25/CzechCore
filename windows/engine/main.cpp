#include "text.h"
#include "pipe_io.h"
#include "broker_identity.h"

#include <windows.h>

#include <ctranslate2/translator.h>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace {

constexpr DWORD kIdleTimeoutMilliseconds = 10 * 60 * 1000;

std::string read_file(const std::filesystem::path& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("required model file is unavailable");
  }
  return std::string(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
}

class Corrector final {
 public:
  explicit Corrector(const std::filesystem::path& model_directory)
      : tokenizer_(czechcore::WordPieceTokenizer::from_json(
            read_file(model_directory / "shared_vocabulary.json"))),
        translator_(
            model_directory.string(),
            ctranslate2::Device::CPU,
            ctranslate2::ComputeType::FLOAT32) {}

  std::string correct(std::string_view source) {
    if (const auto repair = czechcore::remove_adjacent_duplicate(source); repair.has_value()) {
      return *repair;
    }

    ctranslate2::TranslationOptions options;
    options.beam_size = 4;
    options.num_hypotheses = 1;
    options.max_input_length = 0;
    options.max_decoding_length = 255;
    const auto results = translator_.translate_batch({tokenizer_.encode(source)}, options);
    if (results.empty()) {
      throw std::runtime_error("model returned no translation");
    }
    const std::string candidate = tokenizer_.decode(results.front().output());
    return czechcore::preserves_protected_text(source, candidate)
        ? candidate
        : std::string(source);
  }

 private:
  czechcore::WordPieceTokenizer tokenizer_;
  ctranslate2::Translator translator_;
};

void serve(const std::filesystem::path& model_directory, HANDLE ready_event) {
  Corrector corrector(model_directory);
  const std::wstring pipe_name = czechcore::new_broker_pipe_name();
  const HANDLE pipe_raw = CreateNamedPipeW(
        pipe_name.c_str(),
        PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE | FILE_FLAG_OVERLAPPED,
        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
        1,
        czechcore::kMaxPipeMessageBytes,
        czechcore::kMaxPipeMessageBytes,
        0,
        czechcore::broker_security_attributes());
  if (pipe_raw == INVALID_HANDLE_VALUE) {
    throw std::runtime_error("named pipe creation failed");
  }
  const std::unique_ptr<void, decltype(&CloseHandle)> pipe(pipe_raw, CloseHandle);
  const std::unique_ptr<void, decltype(&CloseHandle)> endpoint(
      czechcore::publish_broker_pipe_name(pipe_name), CloseHandle);
  SetEvent(ready_event);
  while (true) {
    if (!czechcore::connect_pipe(pipe.get(), kIdleTimeoutMilliseconds)) {
      if (GetLastError() == ERROR_SEM_TIMEOUT) {
        return;
      }
      DisconnectNamedPipe(pipe.get());
      continue;
    }
    bool response_sent = false;
    try {
      uint32_t request_size = 0;
      if (!czechcore::read_pipe_exact(pipe.get(), &request_size, sizeof(request_size))
          || request_size == 0 || request_size > czechcore::kMaxPipeMessageBytes) {
        throw std::runtime_error("invalid named pipe request size");
      }
      std::string request(request_size, '\0');
      if (!czechcore::read_pipe_exact(pipe.get(), request.data(), request_size)) {
        throw std::runtime_error("named pipe read failed");
      }
      std::string response = corrector.correct(request);
      if (response.empty() || response.size() > czechcore::kMaxPipeMessageBytes) {
        throw std::runtime_error("invalid named pipe response size");
      }
      const uint32_t response_size = static_cast<uint32_t>(response.size());
      if (!czechcore::write_pipe_exact(pipe.get(), &response_size, sizeof(response_size))
          || !czechcore::write_pipe_exact(pipe.get(), response.data(), response_size)) {
        throw std::runtime_error("named pipe write failed");
      }
      response_sent = true;
      uint8_t acknowledgement = 0;
      if (!czechcore::read_pipe_exact(pipe.get(), &acknowledgement, sizeof(acknowledgement))
          || acknowledgement != 1) {
        throw std::runtime_error("named pipe acknowledgement failed");
      }
    } catch (const std::exception& error) {
      std::cerr << "CzechCore request error: " << error.what() << '\n';
      if (!response_sent) {
        const uint32_t empty = 0;
        czechcore::write_pipe_exact(pipe.get(), &empty, sizeof(empty));
      }
    }
    DisconnectNamedPipe(pipe.get());
  }
}

std::string request(std::string_view text) {
  const std::wstring pipe_name = czechcore::broker_pipe_name();
  if (pipe_name.empty() || !WaitNamedPipeW(pipe_name.c_str(), 5000)) {
    throw std::runtime_error("CzechCore engine pipe is unavailable");
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
    throw std::runtime_error("CzechCore engine connection failed");
  }
  const std::unique_ptr<void, decltype(&CloseHandle)> pipe(pipe_raw, CloseHandle);
  std::wstring executable(32768, L'\0');
  const DWORD length = GetModuleFileNameW(nullptr, executable.data(),
                                        static_cast<DWORD>(executable.size()));
  if (length == 0 || length >= executable.size()) {
    throw std::runtime_error("CzechCore executable path is unavailable");
  }
  executable.resize(length);
  if (!czechcore::expected_broker(pipe.get(), executable)) {
    throw std::runtime_error("CzechCore engine identity mismatch");
  }
  const uint32_t request_size = static_cast<uint32_t>(text.size());
  if (request_size == 0 || request_size > czechcore::kMaxPipeMessageBytes
      || !czechcore::write_pipe_exact(pipe.get(), &request_size, sizeof(request_size))
      || !czechcore::write_pipe_exact(pipe.get(), text.data(), request_size)) {
    throw std::runtime_error("CzechCore engine request failed");
  }
  uint32_t response_size = 0;
  if (!czechcore::read_pipe_exact(pipe.get(), &response_size, sizeof(response_size))) {
    throw std::runtime_error(
        "CzechCore engine response header failed (" + std::to_string(GetLastError()) + ")");
  }
  if (response_size == 0 || response_size > czechcore::kMaxPipeMessageBytes) {
    throw std::runtime_error("CzechCore engine returned an invalid response");
  }
  std::string response(response_size, '\0');
  if (!czechcore::read_pipe_exact(pipe.get(), response.data(), response_size)) {
    throw std::runtime_error(
        "CzechCore engine response body failed (" + std::to_string(GetLastError()) + ")");
  }
  const uint8_t acknowledgement = 1;
  czechcore::write_pipe_exact(pipe.get(), &acknowledgement, sizeof(acknowledgement));
  return response;
}

}  // namespace

int wmain(int argument_count, wchar_t** arguments) {
  try {
    SetConsoleOutputCP(CP_UTF8);
    std::filesystem::path model_directory;
    std::optional<std::string> check_text;
    std::optional<std::string> request_text;
    for (int index = 1; index < argument_count; ++index) {
      const std::wstring_view argument(arguments[index]);
      if (argument == L"--model" && index + 1 < argument_count) {
        model_directory = arguments[++index];
      } else if (argument == L"--check" && index + 1 < argument_count) {
        check_text = czechcore::utf16_to_utf8(arguments[++index]);
      } else if (argument == L"--request" && index + 1 < argument_count) {
        request_text = czechcore::utf16_to_utf8(arguments[++index]);
      } else {
        throw std::invalid_argument("usage: czechcore-engine --model PATH [--check TEXT]");
      }
    }
    if (request_text.has_value()) {
      std::cout << request(*request_text) << '\n';
      return 0;
    }
    if (model_directory.empty()) {
      throw std::invalid_argument("--model is required");
    }
    if (check_text.has_value()) {
      Corrector corrector(model_directory);
      std::cout << corrector.correct(*check_text) << '\n';
      return 0;
    }
    SECURITY_ATTRIBUTES* security = czechcore::broker_security_attributes();
    const HANDLE mutex_raw = CreateMutexW(security, FALSE, czechcore::kBrokerMutexName);
    if (mutex_raw == nullptr) {
      throw std::runtime_error("CzechCore engine mutex failed");
    }
    const std::unique_ptr<void, decltype(&CloseHandle)> mutex(mutex_raw, CloseHandle);
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
      return 0;
    }
    const HANDLE event_raw = CreateEventW(
        security, TRUE, FALSE, czechcore::kPipeReadyEventName);
    if (event_raw == nullptr) {
      throw std::runtime_error("CzechCore engine ready event failed");
    }
    const std::unique_ptr<void, decltype(&CloseHandle)> event(event_raw, CloseHandle);
    ResetEvent(event.get());
    serve(model_directory, event.get());
  } catch (const std::exception& error) {
    std::cerr << "CzechCore engine error: " << error.what() << '\n';
    return 1;
  }
  return 0;
}
