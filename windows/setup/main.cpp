#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>

#include <filesystem>
#include <memory>
#include <string>
#include <type_traits>
#include <vector>

namespace {

using RegistrationFunction = HRESULT(__stdcall*)();

std::filesystem::path executable_path() {
  std::wstring path(32768, L'\0');
  const DWORD length = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
  if (length == 0 || length >= path.size()) {
    return {};
  }
  path.resize(length);
  return path;
}

bool elevated() {
  HANDLE token_raw = nullptr;
  if (OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token_raw) == 0) {
    return false;
  }
  const std::unique_ptr<void, decltype(&CloseHandle)> token(token_raw, CloseHandle);
  TOKEN_ELEVATION elevation{};
  DWORD bytes = 0;
  return GetTokenInformation(
             token.get(), TokenElevation, &elevation, sizeof(elevation), &bytes)
          != 0
      && elevation.TokenIsElevated != 0;
}

bool verify_payload_shape(const std::filesystem::path& root) {
  const std::filesystem::path files[] = {
      root / "czechcore-engine.exe",
      root / "czechcore-settings.exe",
      root / "x64" / "CzechCoreTsf.dll",
      root / "x86" / "CzechCoreTsf.dll",
      root / "model" / "config.json",
      root / "model" / "shared_vocabulary.json",
      root / "model" / "model.bin"};
  for (const auto& file : files) {
    std::error_code error;
    if (!std::filesystem::is_regular_file(file, error)
        || std::filesystem::file_size(file, error) == 0 || error) {
      return false;
    }
  }
  return true;
}

std::filesystem::path program_files_root() {
  PWSTR raw = nullptr;
  if (FAILED(SHGetKnownFolderPath(FOLDERID_ProgramFiles, KF_FLAG_DEFAULT, nullptr, &raw))) {
    return {};
  }
  const std::filesystem::path result(raw);
  CoTaskMemFree(raw);
  return result;
}

bool copy_payload(const std::filesystem::path& source, const std::filesystem::path& target) {
  std::error_code error;
  std::filesystem::create_directories(target / "model", error);
  std::filesystem::create_directories(target / "x64", error);
  std::filesystem::create_directories(target / "x86", error);
  if (error) {
    return false;
  }
  const std::filesystem::path relative_files[] = {
      "czechcore-engine.exe",
      "czechcore-settings.exe",
      std::filesystem::path("x64") / "CzechCoreTsf.dll",
      std::filesystem::path("x86") / "CzechCoreTsf.dll",
      std::filesystem::path("model") / "config.json",
      std::filesystem::path("model") / "shared_vocabulary.json",
      std::filesystem::path("model") / "model.bin"};
  for (const auto& relative : relative_files) {
    error.clear();
    std::filesystem::copy_file(
        source / relative,
        target / relative,
        std::filesystem::copy_options::overwrite_existing,
        error);
    if (error) {
      return false;
    }
  }
  return true;
}

HRESULT register_tsf(const std::filesystem::path& dll_path) {
  const HMODULE module = LoadLibraryExW(
      dll_path.c_str(),
      nullptr,
      LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
  if (module == nullptr) {
    return HRESULT_FROM_WIN32(GetLastError());
  }
  const auto function = reinterpret_cast<RegistrationFunction>(
      GetProcAddress(module, "DllRegisterServer"));
  const HRESULT result = function == nullptr ? E_NOINTERFACE : function();
  FreeLibrary(module);
  return result;
}

bool set_x86_registry_string(
    const std::wstring& path, const wchar_t* name, const std::wstring& value) {
  HKEY key_raw = nullptr;
  if (RegCreateKeyExW(
          HKEY_CURRENT_USER,
          path.c_str(),
          0,
          nullptr,
          0,
          KEY_SET_VALUE | KEY_WOW64_32KEY,
          nullptr,
          &key_raw,
          nullptr)
      != ERROR_SUCCESS) {
    return false;
  }
  const std::unique_ptr<std::remove_pointer_t<HKEY>, decltype(&RegCloseKey)> key(
      key_raw, RegCloseKey);
  return RegSetValueExW(
             key.get(),
             name,
             0,
             REG_SZ,
             reinterpret_cast<const BYTE*>(value.c_str()),
             static_cast<DWORD>((value.size() + 1) * sizeof(wchar_t)))
      == ERROR_SUCCESS;
}

bool register_x86_tsf(const std::filesystem::path& dll_path) {
  const std::wstring base =
      L"Software\\Classes\\CLSID\\{F293CF7C-0B9E-4D85-A698-0C787B539CD4}";
  return set_x86_registry_string(base, nullptr, L"CzechCore – česká korekce")
      && set_x86_registry_string(base + L"\\InprocServer32", nullptr, dll_path.wstring())
      && set_x86_registry_string(
          base + L"\\InprocServer32", L"ThreadingModel", L"Apartment");
}

bool create_settings_shortcut(const std::filesystem::path& target) {
  PWSTR programs_raw = nullptr;
  if (FAILED(SHGetKnownFolderPath(FOLDERID_Programs, KF_FLAG_CREATE, nullptr, &programs_raw))) {
    return false;
  }
  const std::filesystem::path shortcut_path =
      std::filesystem::path(programs_raw) / "CzechCore nastavení.lnk";
  CoTaskMemFree(programs_raw);

  IShellLinkW* link = nullptr;
  if (FAILED(CoCreateInstance(
          CLSID_ShellLink,
          nullptr,
          CLSCTX_INPROC_SERVER,
          IID_IShellLinkW,
          reinterpret_cast<void**>(&link)))) {
    return false;
  }
  link->SetPath((target / "czechcore-settings.exe").c_str());
  link->SetWorkingDirectory(target.c_str());
  link->SetDescription(L"Nastavení lokální české korekce CzechCore");
  IPersistFile* persist = nullptr;
  const HRESULT query = link->QueryInterface(IID_IPersistFile, reinterpret_cast<void**>(&persist));
  link->Release();
  if (FAILED(query)) {
    return false;
  }
  const HRESULT saved = persist->Save(shortcut_path.c_str(), TRUE);
  persist->Release();
  return SUCCEEDED(saved);
}

int elevate_self(const std::filesystem::path& executable) {
  SHELLEXECUTEINFOW operation{};
  operation.cbSize = sizeof(operation);
  operation.fMask = SEE_MASK_NOCLOSEPROCESS;
  operation.lpVerb = L"runas";
  operation.lpFile = executable.c_str();
  operation.lpParameters = L"--elevated";
  operation.nShow = SW_SHOWNORMAL;
  if (ShellExecuteExW(&operation) == 0 || operation.hProcess == nullptr) {
    return 1;
  }
  WaitForSingleObject(operation.hProcess, INFINITE);
  DWORD exit_code = 1;
  GetExitCodeProcess(operation.hProcess, &exit_code);
  CloseHandle(operation.hProcess);
  return static_cast<int>(exit_code);
}

}  // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR command_line, int) {
  const std::filesystem::path executable = executable_path();
  const std::filesystem::path source = executable.parent_path();
  if (std::wstring_view(command_line) == L"--verify") {
    return verify_payload_shape(source) ? 0 : 1;
  }
  if (!verify_payload_shape(source)) {
    MessageBoxW(
        nullptr,
        L"Instalační balíček je neúplný.",
        L"CzechCore",
        MB_OK | MB_ICONERROR);
    return 1;
  }
  if (!elevated()) {
    return elevate_self(executable);
  }

  if (FAILED(CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED))) {
    return 1;
  }
  const std::filesystem::path target = program_files_root() / "CzechCore";
  if (!copy_payload(source, target) || !verify_payload_shape(target)) {
    MessageBoxW(nullptr, L"Soubory se nepodařilo nainstalovat.", L"CzechCore", MB_OK | MB_ICONERROR);
    CoUninitialize();
    return 1;
  }
  const HRESULT registration = register_tsf(target / "x64" / "CzechCoreTsf.dll");
  if (FAILED(registration)
      || !register_x86_tsf(target / "x86" / "CzechCoreTsf.dll")) {
    wchar_t message[160]{};
    swprintf_s(
        message,
        L"Textovou službu se nepodařilo zaregistrovat (0x%08lX).",
        static_cast<unsigned long>(registration));
    MessageBoxW(nullptr, message, L"CzechCore", MB_OK | MB_ICONERROR);
    CoUninitialize();
    return 1;
  }
  create_settings_shortcut(target);
  MessageBoxW(
      nullptr,
      L"CzechCore je nainstalovaný. Vyberte jej v přepínači jazyka Windows a spusťte nastavení z nabídky Start.",
      L"CzechCore",
      MB_OK | MB_ICONINFORMATION);
  CoUninitialize();
  return 0;
}
