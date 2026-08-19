#include <windows.h>

#include <iostream>
#include <string_view>

int wmain(int argument_count, wchar_t** arguments) {
  if (argument_count != 3) {
    std::wcerr << L"usage: czechcore-register-probe DLL register|unregister\n";
    return 2;
  }
  const HMODULE module = LoadLibraryW(arguments[1]);
  if (module == nullptr) {
    std::wcerr << L"LoadLibrary failed: " << GetLastError() << L'\n';
    return 1;
  }
  const std::string_view action = arguments[2] == std::wstring_view(L"register")
      ? "DllRegisterServer"
      : "DllUnregisterServer";
  const auto function = reinterpret_cast<HRESULT(__stdcall*)()>(
      GetProcAddress(module, action.data()));
  if (function == nullptr) {
    std::wcerr << L"registration export missing\n";
    FreeLibrary(module);
    return 1;
  }
  const HRESULT result = function();
  std::wcout << L"HRESULT=0x" << std::hex << static_cast<unsigned long>(result) << L'\n';
  FreeLibrary(module);
  return FAILED(result) ? 1 : 0;
}
