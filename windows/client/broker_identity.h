#pragma once

#include <windows.h>

#include <filesystem>
#include <string>

namespace czechcore {

inline constexpr wchar_t kBrokerMutexName[] = L"CzechCoreBroker\\Mutex.v2";
inline constexpr wchar_t kPipeReadyEventName[] = L"CzechCoreBroker\\Ready.v2";

SECURITY_ATTRIBUTES* broker_security_attributes();
std::wstring new_broker_pipe_name();
std::wstring broker_pipe_name();
HANDLE publish_broker_pipe_name(const std::wstring& name);
bool expected_broker(HANDLE pipe, const std::filesystem::path& executable);

}  // namespace czechcore
