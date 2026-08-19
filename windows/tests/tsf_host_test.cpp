#include <windows.h>
#include <msctf.h>

#include <chrono>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

namespace {

const CLSID kTextService = {
    0xf293cf7c, 0x0b9e, 0x4d85, {0xa6, 0x98, 0x0c, 0x78, 0x7b, 0x53, 0x9c, 0xd4}};
const GUID kApplyKey = {
    0x52ab526f, 0xb166, 0x4013, {0x86, 0x9a, 0x98, 0x61, 0xbd, 0x13, 0x39, 0x04}};
const GUID kCheckKey = {
    0x7f7b55f4, 0xed74, 0x44af, {0xbc, 0x86, 0xdf, 0x60, 0xea, 0x27, 0x6e, 0x91}};

using GetClassObject = HRESULT(__stdcall*)(REFCLSID, REFIID, void**);

void require(bool condition, const wchar_t* message) {
  if (!condition) {
    std::wcerr << message << L'\n';
    throw std::runtime_error("TSF context test failed");
  }
}

void pump_messages() {
  MSG message{};
  while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE) != 0) {
    TranslateMessage(&message);
    DispatchMessageW(&message);
  }
}

class SessionBase : public ITfEditSession {
 public:
  STDMETHODIMP QueryInterface(REFIID interface_id, void** output) override {
    if (output == nullptr) {
      return E_POINTER;
    }
    *output = nullptr;
    if (interface_id == IID_IUnknown || interface_id == IID_ITfEditSession) {
      *output = static_cast<ITfEditSession*>(this);
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

 protected:
  virtual ~SessionBase() = default;

 private:
  long references_ = 1;
};

class SetTextSession final : public SessionBase {
 public:
  SetTextSession(ITfContext* context, std::wstring text)
      : context_(context), text_(std::move(text)) {
    context_->AddRef();
  }
  ~SetTextSession() override { context_->Release(); }

  STDMETHODIMP DoEditSession(TfEditCookie cookie) override {
    ITfRange* range = nullptr;
    ITfRange* end = nullptr;
    if (FAILED(context_->GetStart(cookie, &range)) || FAILED(context_->GetEnd(cookie, &end))) {
      if (range != nullptr) {
        range->Release();
      }
      return E_FAIL;
    }
    HRESULT result = range->ShiftEndToRange(cookie, end, TF_ANCHOR_END);
    if (SUCCEEDED(result)) {
      result = range->SetText(cookie, 0, text_.c_str(), static_cast<LONG>(text_.size()));
    }
    end->Release();
    range->Release();
    if (FAILED(result)) {
      return result;
    }

    if (FAILED(context_->GetStart(cookie, &range)) || FAILED(context_->GetEnd(cookie, &end))) {
      if (range != nullptr) {
        range->Release();
      }
      return E_FAIL;
    }
    range->ShiftEndToRange(cookie, end, TF_ANCHOR_END);
    end->Collapse(cookie, TF_ANCHOR_END);
    TF_SELECTION selection{};
    selection.range = end;
    selection.style.ase = TF_AE_NONE;
    selection.style.fInterimChar = FALSE;
    result = context_->SetSelection(cookie, 1, &selection);
    end->Release();
    range->Release();
    return result;
  }

 private:
  ITfContext* context_;
  std::wstring text_;
};

class ReadTextSession final : public SessionBase {
 public:
  ReadTextSession(ITfContext* context, std::wstring& output)
      : context_(context), output_(output) {
    context_->AddRef();
  }
  ~ReadTextSession() override { context_->Release(); }

  STDMETHODIMP DoEditSession(TfEditCookie cookie) override {
    ITfRange* range = nullptr;
    ITfRange* end = nullptr;
    if (FAILED(context_->GetStart(cookie, &range)) || FAILED(context_->GetEnd(cookie, &end))) {
      if (range != nullptr) {
        range->Release();
      }
      return E_FAIL;
    }
    range->ShiftEndToRange(cookie, end, TF_ANCHOR_END);
    end->Release();
    wchar_t buffer[1024]{};
    ULONG fetched = 0;
    const HRESULT result = range->GetText(
        cookie, TF_TF_MOVESTART, buffer, static_cast<ULONG>(std::size(buffer) - 1), &fetched);
    range->Release();
    if (SUCCEEDED(result)) {
      output_.assign(buffer, fetched);
    }
    return result;
  }

 private:
  ITfContext* context_;
  std::wstring& output_;
};

bool request_session(
    ITfContext* context, TfClientId client_id, ITfEditSession* session, DWORD flags) {
  HRESULT session_result = E_FAIL;
  const HRESULT request = context->RequestEditSession(client_id, session, flags, &session_result);
  return SUCCEEDED(request) && SUCCEEDED(session_result);
}

bool set_text(ITfContext* context, TfClientId client_id, std::wstring text) {
  auto* session = new SetTextSession(context, std::move(text));
  const bool success = request_session(context, client_id, session, TF_ES_SYNC | TF_ES_READWRITE);
  session->Release();
  return success;
}

std::wstring read_text(ITfContext* context, TfClientId client_id) {
  std::wstring output;
  auto* session = new ReadTextSession(context, output);
  request_session(context, client_id, session, TF_ES_SYNC | TF_ES_READ);
  session->Release();
  return output;
}

bool wait_for_text(
    ITfContext* context,
    TfClientId client_id,
    std::wstring_view expected,
    std::chrono::seconds timeout) {
  const auto deadline = std::chrono::steady_clock::now() + timeout;
  while (std::chrono::steady_clock::now() < deadline) {
    pump_messages();
    if (read_text(context, client_id) == expected) {
      return true;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  return false;
}

}  // namespace

int wmain(int argument_count, wchar_t** arguments) {
  if (argument_count != 2) {
    std::wcerr << L"usage: czechcore-tsf-host-test CzechCoreTsf.dll\n";
    return 2;
  }
  try {
    require(SUCCEEDED(CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED)), L"COM init failed");
    const HMODULE module = LoadLibraryW(arguments[1]);
    require(module != nullptr, L"TSF DLL load failed");
    const auto get_class = reinterpret_cast<GetClassObject>(
        GetProcAddress(module, "DllGetClassObject"));
    require(get_class != nullptr, L"DllGetClassObject missing");

    IClassFactory* factory = nullptr;
    require(
        SUCCEEDED(get_class(kTextService, IID_IClassFactory, reinterpret_cast<void**>(&factory))),
        L"class factory failed");
    ITfTextInputProcessor* service = nullptr;
    require(
        SUCCEEDED(factory->CreateInstance(
            nullptr, IID_ITfTextInputProcessor, reinterpret_cast<void**>(&service))),
        L"text service creation failed");
    factory->Release();

    ITfThreadMgr* thread_manager = nullptr;
    require(
        SUCCEEDED(CoCreateInstance(
            CLSID_TF_ThreadMgr,
            nullptr,
            CLSCTX_INPROC_SERVER,
            IID_ITfThreadMgr,
            reinterpret_cast<void**>(&thread_manager))),
        L"TSF thread manager failed");
    TfClientId client_id = TF_CLIENTID_NULL;
    require(SUCCEEDED(thread_manager->Activate(&client_id)), L"TSF activation failed");
    const DWORD automatic = 2;
    require(
        RegSetKeyValueW(
            HKEY_CURRENT_USER,
            L"Software\\CzechCore",
            L"Mode",
            REG_DWORD,
            &automatic,
            sizeof(automatic))
            == ERROR_SUCCESS,
        L"mode setup failed");
    require(SUCCEEDED(service->Activate(thread_manager, client_id)), L"service activation failed");

    ITfDocumentMgr* document = nullptr;
    require(SUCCEEDED(thread_manager->CreateDocumentMgr(&document)), L"document manager failed");
    ITfContext* context = nullptr;
    TfEditCookie owner_cookie = 0;
    require(
        SUCCEEDED(document->CreateContext(client_id, 0, nullptr, &context, &owner_cookie)),
        L"TSF context failed");
    require(SUCCEEDED(document->Push(context)), L"context push failed");
    require(SUCCEEDED(thread_manager->SetFocus(document)), L"context focus failed");
    pump_messages();

    ITfKeyEventSink* keys = nullptr;
    require(
        SUCCEEDED(service->QueryInterface(IID_ITfKeyEventSink, reinterpret_cast<void**>(&keys))),
        L"keystroke sink missing");
    require(set_text(context, client_id, L"To je je problém."), L"automatic input failed");
    BOOL eaten = FALSE;
    require(
        SUCCEEDED(keys->OnPreservedKey(context, kCheckKey, &eaten)) && eaten != FALSE,
        L"automatic check failed");
    require(
        wait_for_text(context, client_id, L"To je problém.", std::chrono::seconds(10)),
        L"automatic flow failed");

    require(set_text(context, client_id, L"Když přišel domů šel spát."), L"neural input failed");
    eaten = FALSE;
    require(
        SUCCEEDED(keys->OnPreservedKey(context, kCheckKey, &eaten)) && eaten != FALSE,
        L"neural check failed");
    std::this_thread::sleep_for(std::chrono::seconds(2));
    pump_messages();
    eaten = FALSE;
    require(
        SUCCEEDED(keys->OnPreservedKey(context, kApplyKey, &eaten)) && eaten != FALSE,
        L"apply shortcut failed");
    require(
        wait_for_text(context, client_id, L"Když přišel domů, šel spát.", std::chrono::seconds(10)),
        L"neural confirm flow failed");

    keys->Release();
    document->Pop(TF_POPF_ALL);
    context->Release();
    document->Release();
    service->Deactivate();
    service->Release();
    thread_manager->Deactivate();
    thread_manager->Release();
    FreeLibrary(module);
    CoUninitialize();
    std::wcout << L"TSF automatic and confirm flows passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
