#include "tsf.h"

#include <objbase.h>

#include <filesystem>
#include <memory>
#include <new>
#include <string>
#include <type_traits>

HINSTANCE g_module = nullptr;
long g_module_references = 0;

const CLSID CLSID_CzechCoreTextService = {
    0xf293cf7c, 0x0b9e, 0x4d85, {0xa6, 0x98, 0x0c, 0x78, 0x7b, 0x53, 0x9c, 0xd4}};
const GUID GUID_CzechCoreProfile = {
    0x34ea17ce, 0x4666, 0x4b39, {0xa7, 0x28, 0x86, 0xb4, 0xb2, 0x27, 0x13, 0xd9}};
const GUID GUID_CzechCoreDisplayAttribute = {
    0xb1cb7d65, 0x866e, 0x4a68, {0xbb, 0xb0, 0x03, 0x0b, 0xda, 0x8a, 0x6e, 0x2d}};
const GUID GUID_CzechCoreApplyKey = {
    0x52ab526f, 0xb166, 0x4013, {0x86, 0x9a, 0x98, 0x61, 0xbd, 0x13, 0x39, 0x04}};
const GUID GUID_CzechCoreCheckKey = {
    0x7f7b55f4, 0xed74, 0x44af, {0xbc, 0x86, 0xdf, 0x60, 0xea, 0x27, 0x6e, 0x91}};
const GUID GUID_CzechCoreModeKey = {
    0xac7dc284, 0x0d4b, 0x4391, {0x9d, 0xc4, 0x88, 0x38, 0xf9, 0xa4, 0x9e, 0x40}};

namespace {

constexpr LANGID kCzechLanguage = MAKELANGID(LANG_CZECH, SUBLANG_DEFAULT);
constexpr wchar_t kDescription[] = L"CzechCore – česká korekce";

class ClassFactory final : public IClassFactory {
 public:
  ClassFactory() { module_add_ref(); }
  ~ClassFactory() { module_release(); }

  STDMETHODIMP QueryInterface(REFIID interface_id, void** output) override {
    if (output == nullptr) {
      return E_POINTER;
    }
    *output = nullptr;
    if (interface_id == IID_IUnknown || interface_id == IID_IClassFactory) {
      *output = static_cast<IClassFactory*>(this);
      AddRef();
      return S_OK;
    }
    return E_NOINTERFACE;
  }

  STDMETHODIMP_(ULONG) AddRef() override {
    return static_cast<ULONG>(InterlockedIncrement(&references_));
  }

  STDMETHODIMP_(ULONG) Release() override {
    const long remaining = InterlockedDecrement(&references_);
    if (remaining == 0) {
      delete this;
    }
    return static_cast<ULONG>(remaining);
  }

  STDMETHODIMP CreateInstance(
      IUnknown* outer, REFIID interface_id, void** output) override {
    return CzechCoreTextService::create_instance(outer, interface_id, output);
  }

  STDMETHODIMP LockServer(BOOL lock) override {
    lock != FALSE ? module_add_ref() : module_release();
    return S_OK;
  }

 private:
  long references_ = 1;
};

std::wstring module_path() {
  std::wstring path(32768, L'\0');
  const DWORD length = GetModuleFileNameW(g_module, path.data(), static_cast<DWORD>(path.size()));
  if (length == 0 || length >= path.size()) {
    return {};
  }
  path.resize(length);
  return path;
}

std::wstring guid_string(REFGUID guid) {
  wchar_t value[39]{};
  return StringFromGUID2(guid, value, static_cast<int>(std::size(value))) > 0
      ? std::wstring(value)
      : std::wstring();
}

bool set_string(HKEY root, const std::wstring& path, const wchar_t* name, const std::wstring& value) {
  HKEY key_raw = nullptr;
  if (RegCreateKeyExW(
          root, path.c_str(), 0, nullptr, 0, KEY_SET_VALUE, nullptr, &key_raw, nullptr)
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

bool initialize_com(bool& should_uninitialize) {
  const HRESULT result = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
  should_uninitialize = result == S_OK || result == S_FALSE;
  return SUCCEEDED(result) || result == RPC_E_CHANGED_MODE;
}

}  // namespace

void module_add_ref() {
  InterlockedIncrement(&g_module_references);
}

void module_release() {
  InterlockedDecrement(&g_module_references);
}

bool register_server() {
  const std::wstring path = module_path();
  const std::wstring clsid = guid_string(CLSID_CzechCoreTextService);
  if (path.empty() || clsid.empty()) {
    return false;
  }
  const std::wstring base = L"Software\\Classes\\CLSID\\" + clsid;
  std::filesystem::path install_root = std::filesystem::path(path).parent_path();
  if (install_root.filename() == L"x64" || install_root.filename() == L"x86") {
    install_root = install_root.parent_path();
  }
  return set_string(HKEY_CURRENT_USER, base, nullptr, kDescription)
      && set_string(HKEY_CURRENT_USER, base + L"\\InprocServer32", nullptr, path)
      && set_string(
          HKEY_CURRENT_USER, base + L"\\InprocServer32", L"ThreadingModel", L"Apartment")
      && set_string(
          HKEY_CURRENT_USER,
          L"Software\\CzechCore",
          L"InstallRoot",
          install_root.wstring());
}

void unregister_server() {
  const std::wstring clsid = guid_string(CLSID_CzechCoreTextService);
  if (!clsid.empty()) {
    RegDeleteTreeW(HKEY_CURRENT_USER, (L"Software\\Classes\\CLSID\\" + clsid).c_str());
  }
}

HRESULT register_profiles() {
  ITfInputProcessorProfileMgr* profiles = nullptr;
  if (FAILED(CoCreateInstance(
          CLSID_TF_InputProcessorProfiles,
          nullptr,
          CLSCTX_INPROC_SERVER,
          IID_ITfInputProcessorProfileMgr,
          reinterpret_cast<void**>(&profiles)))) {
    return E_FAIL;
  }
  const std::unique_ptr<ITfInputProcessorProfileMgr, decltype([](ITfInputProcessorProfileMgr* value) {
                          if (value != nullptr) {
                            value->Release();
                          }
                        })>
      owner(profiles);
  HRESULT result = profiles->RegisterProfile(
      CLSID_CzechCoreTextService,
      kCzechLanguage,
      GUID_CzechCoreProfile,
      kDescription,
      static_cast<ULONG>(std::size(kDescription) - 1),
      nullptr,
      0,
      0,
      nullptr,
      0,
      TRUE,
      0);
  if (FAILED(result)) {
    return MAKE_HRESULT(SEVERITY_ERROR, FACILITY_ITF, 0x211);
  }
  result = profiles->ActivateProfile(
      TF_PROFILETYPE_INPUTPROCESSOR,
      kCzechLanguage,
      CLSID_CzechCoreTextService,
      GUID_CzechCoreProfile,
      nullptr,
      TF_IPPMF_FORSESSION | TF_IPPMF_DONTCARECURRENTINPUTLANGUAGE);
  return FAILED(result) ? MAKE_HRESULT(SEVERITY_ERROR, FACILITY_ITF, 0x212) : S_OK;
}

void unregister_profiles() {
  ITfInputProcessorProfileMgr* profiles = nullptr;
  if (SUCCEEDED(CoCreateInstance(
          CLSID_TF_InputProcessorProfiles,
          nullptr,
          CLSCTX_INPROC_SERVER,
          IID_ITfInputProcessorProfileMgr,
          reinterpret_cast<void**>(&profiles)))) {
    profiles->UnregisterProfile(
        CLSID_CzechCoreTextService, kCzechLanguage, GUID_CzechCoreProfile, 0);
    profiles->Release();
  }
}

HRESULT register_categories() {
  ITfCategoryMgr* manager = nullptr;
  if (FAILED(CoCreateInstance(
          CLSID_TF_CategoryMgr,
          nullptr,
          CLSCTX_INPROC_SERVER,
          IID_ITfCategoryMgr,
          reinterpret_cast<void**>(&manager)))) {
    return E_FAIL;
  }
  const GUID categories[] = {GUID_TFCAT_TIP_KEYBOARD, GUID_TFCAT_DISPLAYATTRIBUTEPROVIDER};
  HRESULT result = S_OK;
  for (const GUID& category : categories) {
    result = manager->RegisterCategory(
        CLSID_CzechCoreTextService, category, CLSID_CzechCoreTextService);
    if (FAILED(result)) {
      break;
    }
  }
  manager->Release();
  return result;
}

void unregister_categories() {
  ITfCategoryMgr* manager = nullptr;
  if (SUCCEEDED(CoCreateInstance(
          CLSID_TF_CategoryMgr,
          nullptr,
          CLSCTX_INPROC_SERVER,
          IID_ITfCategoryMgr,
          reinterpret_cast<void**>(&manager)))) {
    manager->UnregisterCategory(
        CLSID_CzechCoreTextService,
        GUID_TFCAT_TIP_KEYBOARD,
        CLSID_CzechCoreTextService);
    manager->UnregisterCategory(
        CLSID_CzechCoreTextService,
        GUID_TFCAT_DISPLAYATTRIBUTEPROVIDER,
        CLSID_CzechCoreTextService);
    manager->Release();
  }
}

extern "C" BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, void*) {
  if (reason == DLL_PROCESS_ATTACH) {
    g_module = instance;
    DisableThreadLibraryCalls(instance);
  }
  return TRUE;
}

extern "C" HRESULT __stdcall DllGetClassObject(
    REFCLSID class_id, REFIID interface_id, void** output) {
  if (class_id != CLSID_CzechCoreTextService || output == nullptr) {
    return CLASS_E_CLASSNOTAVAILABLE;
  }
  auto* factory = new (std::nothrow) ClassFactory();
  if (factory == nullptr) {
    return E_OUTOFMEMORY;
  }
  const HRESULT result = factory->QueryInterface(interface_id, output);
  factory->Release();
  return result;
}

extern "C" HRESULT __stdcall DllCanUnloadNow() {
  return g_module_references == 0 ? S_OK : S_FALSE;
}

extern "C" HRESULT __stdcall DllRegisterServer() {
  bool uninitialize = false;
  if (!initialize_com(uninitialize)) {
    return E_FAIL;
  }
  HRESULT result = S_OK;
  if (!register_server()) {
    result = MAKE_HRESULT(SEVERITY_ERROR, FACILITY_ITF, 0x101);
  } else if constexpr (sizeof(void*) == 8) {
    if (const HRESULT profile_result = register_profiles(); FAILED(profile_result)) {
      result = profile_result;
    } else if (const HRESULT category_result = register_categories(); FAILED(category_result)) {
      result = category_result;
    }
  }
  if (FAILED(result)) {
    if constexpr (sizeof(void*) == 8) {
      unregister_categories();
      unregister_profiles();
    }
    unregister_server();
  }
  if (uninitialize) {
    CoUninitialize();
  }
  return result;
}

extern "C" HRESULT __stdcall DllUnregisterServer() {
  bool uninitialize = false;
  if (initialize_com(uninitialize)) {
    if constexpr (sizeof(void*) == 8) {
      unregister_categories();
      unregister_profiles();
    }
    if (uninitialize) {
      CoUninitialize();
    }
  }
  unregister_server();
  return S_OK;
}
