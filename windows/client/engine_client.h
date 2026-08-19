#pragma once

#include <optional>
#include <string>
#include <string_view>

namespace czechcore {

void preload_engine();
std::optional<std::wstring> request_engine(std::wstring_view text);

}  // namespace czechcore
