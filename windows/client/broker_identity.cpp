#include "broker_identity.h"

#include <bcrypt.h>
#include <sddl.h>

#include <array>
#include <cstring>
#include <cwchar>
#include <memory>
#include <stdexcept>
#include <vector>

namespace czechcore {
namespace {

constexpr wchar_t kNamespace[] = L"CzechCoreBroker";
constexpr wchar_t kMappingName[] = L"CzechCoreBroker\\Endpoint.v2";
constexpr wchar_t kPipePrefix[] = LR"(\\.\pipe\CzechCore.Engine.v2.)";
constexpr size_t kEndpointCharacters = 128;

std::vector<unsigned char> token_information(HANDLE token, TOKEN_INFORMATION_CLASS kind) {
  DWORD size = 0;
  GetTokenInformation(token, kind, nullptr, 0, &size);
  if (size == 0) {
    throw std::runtime_error("broker token information is unavailable");
  }
  std::vector<unsigned char> data(size);
  if (GetTokenInformation(token, kind, data.data(), size, &size) == 0) {
    throw std::runtime_error("broker token information failed");
  }
  return data;
}

PSID logon_sid(std::vector<unsigned char>& data) {
  const auto* groups = reinterpret_cast<const TOKEN_GROUPS*>(data.data());
  if (groups->GroupCount != 1) {
    throw std::runtime_error("broker requires an interactive logon SID");
  }
  return groups->Groups[0].Sid;
}

class BrokerNamespace final {
 public:
  BrokerNamespace() {
    try {
      HANDLE token_raw = nullptr;
      if (OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token_raw) == 0) {
        throw std::runtime_error("broker user token is unavailable");
      }
      const std::unique_ptr<void, decltype(&CloseHandle)> token(token_raw, CloseHandle);
      auto user = token_information(token.get(), TokenUser);
      auto logon = token_information(token.get(), TokenLogonSid);
      PSID user_sid = reinterpret_cast<const TOKEN_USER*>(user.data())->User.Sid;
      LPWSTR sid_raw = nullptr;
      if (ConvertSidToStringSidW(user_sid, &sid_raw) == 0) {
        throw std::runtime_error("broker user SID conversion failed");
      }
      const std::unique_ptr<void, decltype(&LocalFree)> sid(sid_raw, LocalFree);
      const std::wstring sddl = L"D:P(A;;GA;;;SY)(A;;GA;;;" + std::wstring(sid_raw) + L")";
      if (ConvertStringSecurityDescriptorToSecurityDescriptorW(
              sddl.c_str(), SDDL_REVISION_1, &descriptor_, nullptr) == 0) {
        throw std::runtime_error("broker security descriptor failed");
      }
      attributes_ = {static_cast<DWORD>(sizeof(attributes_)), descriptor_, FALSE};
      boundary_ = CreateBoundaryDescriptorW(kNamespace, 0);
      if (boundary_ == nullptr || AddSIDToBoundaryDescriptor(&boundary_, user_sid) == 0
          || AddSIDToBoundaryDescriptor(&boundary_, logon_sid(logon)) == 0) {
        throw std::runtime_error("broker namespace boundary failed");
      }
      namespace_ = CreatePrivateNamespaceW(&attributes_, boundary_, kNamespace);
      if (namespace_ == nullptr && GetLastError() == ERROR_ALREADY_EXISTS) {
        namespace_ = OpenPrivateNamespaceW(boundary_, kNamespace);
      }
      if (namespace_ == nullptr) {
        throw std::runtime_error("broker private namespace is unavailable");
      }
    } catch (...) {
      close();
      throw;
    }
  }

  ~BrokerNamespace() { close(); }
  BrokerNamespace(const BrokerNamespace&) = delete;
  BrokerNamespace& operator=(const BrokerNamespace&) = delete;
  SECURITY_ATTRIBUTES* attributes() { return &attributes_; }

 private:
  void close() {
    if (namespace_ != nullptr) ClosePrivateNamespace(namespace_, 0);
    if (boundary_ != nullptr) DeleteBoundaryDescriptor(boundary_);
    if (descriptor_ != nullptr) LocalFree(descriptor_);
  }
  HANDLE namespace_ = nullptr;
  HANDLE boundary_ = nullptr;
  PSECURITY_DESCRIPTOR descriptor_ = nullptr;
  SECURITY_ATTRIBUTES attributes_{};
};

bool same_logon(HANDLE process) {
  HANDLE peer_raw = nullptr;
  HANDLE own_raw = nullptr;
  if (OpenProcessToken(process, TOKEN_QUERY, &peer_raw) == 0) return false;
  const std::unique_ptr<void, decltype(&CloseHandle)> peer(peer_raw, CloseHandle);
  if (OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &own_raw) == 0) return false;
  const std::unique_ptr<void, decltype(&CloseHandle)> own(own_raw, CloseHandle);
  auto peer_user = token_information(peer.get(), TokenUser);
  auto own_user = token_information(own.get(), TokenUser);
  auto peer_logon = token_information(peer.get(), TokenLogonSid);
  auto own_logon = token_information(own.get(), TokenLogonSid);
  return EqualSid(reinterpret_cast<const TOKEN_USER*>(peer_user.data())->User.Sid,
                  reinterpret_cast<const TOKEN_USER*>(own_user.data())->User.Sid) != 0
      && EqualSid(logon_sid(peer_logon), logon_sid(own_logon)) != 0;
}

}  // namespace

SECURITY_ATTRIBUTES* broker_security_attributes() {
  static BrokerNamespace identity;
  return identity.attributes();
}

std::wstring new_broker_pipe_name() {
  std::array<unsigned char, 16> nonce{};
  if (BCryptGenRandom(nullptr, nonce.data(), static_cast<ULONG>(nonce.size()),
                      BCRYPT_USE_SYSTEM_PREFERRED_RNG) != 0) {
    throw std::runtime_error("broker endpoint randomness failed");
  }
  constexpr wchar_t digits[] = L"0123456789abcdef";
  std::wstring name(kPipePrefix);
  for (const auto byte : nonce) {
    name += digits[byte >> 4];
    name += digits[byte & 15];
  }
  return name;
}

HANDLE publish_broker_pipe_name(const std::wstring& name) {
  if (name.size() >= kEndpointCharacters || !name.starts_with(kPipePrefix)) {
    throw std::runtime_error("invalid broker endpoint");
  }
  const HANDLE mapping = CreateFileMappingW(
      INVALID_HANDLE_VALUE, broker_security_attributes(), PAGE_READWRITE, 0,
      static_cast<DWORD>(kEndpointCharacters * sizeof(wchar_t)), kMappingName);
  if (mapping == nullptr) throw std::runtime_error("broker endpoint publication failed");
  if (GetLastError() == ERROR_ALREADY_EXISTS) {
    CloseHandle(mapping);
    throw std::runtime_error("broker endpoint is already published");
  }
  void* view = MapViewOfFile(mapping, FILE_MAP_WRITE, 0, 0, kEndpointCharacters * sizeof(wchar_t));
  if (view == nullptr) {
    CloseHandle(mapping);
    throw std::runtime_error("broker endpoint mapping failed");
  }
  wcscpy_s(static_cast<wchar_t*>(view), kEndpointCharacters, name.c_str());
  UnmapViewOfFile(view);
  return mapping;
}

std::wstring broker_pipe_name() {
  broker_security_attributes();
  const HANDLE raw = OpenFileMappingW(FILE_MAP_READ, FALSE, kMappingName);
  if (raw == nullptr) return {};
  const std::unique_ptr<void, decltype(&CloseHandle)> mapping(raw, CloseHandle);
  const void* view = MapViewOfFile(mapping.get(), FILE_MAP_READ, 0, 0,
                                  kEndpointCharacters * sizeof(wchar_t));
  if (view == nullptr) return {};
  std::array<wchar_t, kEndpointCharacters> snapshot{};
  memcpy(snapshot.data(), view, sizeof(snapshot));
  UnmapViewOfFile(view);
  const size_t length = wcsnlen_s(snapshot.data(), snapshot.size());
  if (length == snapshot.size()) return {};
  const std::wstring name(snapshot.data(), length);
  return name.starts_with(kPipePrefix) && name.size() == std::size(kPipePrefix) - 1 + 32
      ? name : std::wstring();
}

bool expected_broker(HANDLE pipe, const std::filesystem::path& executable) {
  try {
    ULONG process_id = 0;
    if (GetNamedPipeServerProcessId(pipe, &process_id) == 0) return false;
    const HANDLE raw = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, process_id);
    if (raw == nullptr) return false;
    const std::unique_ptr<void, decltype(&CloseHandle)> process(raw, CloseHandle);
    if (!same_logon(process.get())) return false;
    std::wstring path(32768, L'\0');
    DWORD length = static_cast<DWORD>(path.size());
    if (QueryFullProcessImageNameW(process.get(), 0, path.data(), &length) == 0) return false;
    path.resize(length);
    std::error_code error;
    return std::filesystem::equivalent(executable, path, error) && !error;
  } catch (...) {
    return false;
  }
}

}  // namespace czechcore
