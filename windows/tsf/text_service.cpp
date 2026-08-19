#include "tsf.h"

#include "engine_client.h"
#include "text.h"

#include <oleauto.h>

#include <cwctype>
#include <memory>
#include <new>
#include <optional>
#include <utility>
#include <vector>

namespace {

constexpr LONG kContextCharacters = 512;
constexpr TF_PRESERVEDKEY kApplyKey = {VK_RETURN, TF_MOD_CONTROL | TF_MOD_ALT};
constexpr TF_PRESERVEDKEY kCheckKey = {'G', TF_MOD_CONTROL | TF_MOD_ALT};
constexpr TF_PRESERVEDKEY kModeKey = {'M', TF_MOD_CONTROL | TF_MOD_ALT};

template <typename Interface>
void release(Interface*& value) {
  if (value != nullptr) {
    value->Release();
    value = nullptr;
  }
}

bool get_range_text(ITfRange* range, TfEditCookie cookie, std::wstring& output) {
  ITfRange* reader = nullptr;
  if (FAILED(range->Clone(&reader))) {
    return false;
  }
  wchar_t buffer[kContextCharacters + 1]{};
  ULONG fetched = 0;
  const HRESULT result = reader->GetText(
      cookie, TF_TF_MOVESTART, buffer, static_cast<ULONG>(std::size(buffer) - 1), &fetched);
  reader->Release();
  if (FAILED(result)) {
    return false;
  }
  output.assign(buffer, fetched);
  return true;
}

bool read_current_sentence(
    ITfContext* context,
    TfEditCookie cookie,
    bool require_terminator,
    ITfRange** output_range,
    std::wstring& output_text) {
  *output_range = nullptr;
  TF_SELECTION selection{};
  ULONG fetched = 0;
  if (FAILED(context->GetSelection(cookie, TF_DEFAULT_SELECTION, 1, &selection, &fetched))
      || fetched != 1) {
    return false;
  }
  BOOL empty = FALSE;
  if (FAILED(selection.range->IsEmpty(cookie, &empty)) || empty == FALSE) {
    selection.range->Release();
    return false;
  }
  if (FAILED(selection.range->Collapse(cookie, TF_ANCHOR_START))) {
    selection.range->Release();
    return false;
  }
  LONG shifted = 0;
  if (FAILED(selection.range->ShiftStart(cookie, -kContextCharacters, &shifted, nullptr))) {
    selection.range->Release();
    return false;
  }

  std::wstring context_text;
  if (!get_range_text(selection.range, cookie, context_text)) {
    selection.range->Release();
    return false;
  }
  size_t end = context_text.size();
  while (end > 0 && std::iswspace(context_text[end - 1]) != 0) {
    --end;
  }
  if (end == 0) {
    selection.range->Release();
    return false;
  }
  const wchar_t terminal = context_text[end - 1];
  if (require_terminator && terminal != L'.' && terminal != L'!' && terminal != L'?') {
    selection.range->Release();
    return false;
  }
  size_t start = 0;
  if (end > 1) {
    for (size_t index = end - 1; index-- > 0;) {
      const wchar_t value = context_text[index];
      if (value == L'.' || value == L'!' || value == L'?' || value == L'\n') {
        start = index + 1;
        break;
      }
    }
  }
  while (start < end && std::iswspace(context_text[start]) != 0) {
    ++start;
  }
  if (end - start < 2) {
    selection.range->Release();
    return false;
  }
  LONG actual = 0;
  if ((start != 0
       && FAILED(selection.range->ShiftStart(
           cookie, static_cast<LONG>(start), &actual, nullptr)))
      || (context_text.size() != end
          && FAILED(selection.range->ShiftEnd(
              cookie,
              -static_cast<LONG>(context_text.size() - end),
              &actual,
              nullptr)))) {
    selection.range->Release();
    return false;
  }
  output_text = context_text.substr(start, end - start);
  *output_range = selection.range;
  return true;
}

bool has_text_updates(ITfEditRecord* record) {
  IEnumTfRanges* ranges = nullptr;
  if (FAILED(record->GetTextAndPropertyUpdates(TF_GTP_INCL_TEXT, nullptr, 0, &ranges))
      || ranges == nullptr) {
    return false;
  }
  ITfRange* range = nullptr;
  ULONG fetched = 0;
  const bool updated = ranges->Next(1, &range, &fetched) == S_OK && fetched == 1;
  if (range != nullptr) {
    range->Release();
  }
  ranges->Release();
  return updated;
}

class EditSessionBase : public ITfEditSession {
 public:
  explicit EditSessionBase(CzechCoreTextService* service) : service_(service) {
    service_->AddRef();
  }
  virtual ~EditSessionBase() { service_->Release(); }

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
  CzechCoreTextService* service_;

 private:
  long references_ = 1;
};

}  // namespace

class SuggestionEditSession final : public EditSessionBase {
 public:
  enum class Action { Mark, Apply, Clear };

  SuggestionEditSession(
      CzechCoreTextService* service,
      ITfContext* context,
      ITfRange* range,
      std::wstring source,
      std::wstring replacement,
      Action action)
      : EditSessionBase(service),
        context_(context),
        range_(range),
        source_(std::move(source)),
        replacement_(std::move(replacement)),
        action_(action) {
    context_->AddRef();
    range_->AddRef();
  }

  ~SuggestionEditSession() {
    range_->Release();
    context_->Release();
  }

  STDMETHODIMP DoEditSession(TfEditCookie cookie) override {
    std::wstring current;
    if (!get_range_text(range_, cookie, current) || current != source_) {
      return S_OK;
    }
    if (action_ == Action::Apply) {
      const HRESULT result = range_->SetText(
          cookie,
          0,
          replacement_.c_str(),
          static_cast<LONG>(replacement_.size()));
      if (SUCCEEDED(result)) {
        service_->last_analyzed_ = replacement_;
        service_->clear_candidate(false);
      }
      return result;
    }

    ITfProperty* property = nullptr;
    if (FAILED(context_->GetProperty(GUID_PROP_ATTRIBUTE, &property))) {
      return E_FAIL;
    }
    HRESULT result = S_OK;
    if (action_ == Action::Clear) {
      result = property->Clear(cookie, range_);
    } else {
      VARIANT value{};
      value.vt = VT_I4;
      value.lVal = service_->display_atom_;
      result = property->SetValue(cookie, range_, &value);
    }
    property->Release();
    return result;
  }

 private:
  ITfContext* context_;
  ITfRange* range_;
  std::wstring source_;
  std::wstring replacement_;
  Action action_;
};

class AnalyzeEditSession final : public EditSessionBase {
 public:
  AnalyzeEditSession(CzechCoreTextService* service, ITfContext* context)
      : EditSessionBase(service), context_(context) {
    context_->AddRef();
  }
  ~AnalyzeEditSession() { context_->Release(); }

  STDMETHODIMP DoEditSession(TfEditCookie cookie) override {
    service_->analyze(context_, cookie, false);
    return S_OK;
  }

 private:
  ITfContext* context_;
};

CzechCoreTextService::CzechCoreTextService() {
  module_add_ref();
}

CzechCoreTextService::~CzechCoreTextService() {
  clear_candidate(false);
  module_release();
}

HRESULT CzechCoreTextService::create_instance(
    IUnknown* outer, REFIID interface_id, void** output) {
  if (output == nullptr) {
    return E_POINTER;
  }
  *output = nullptr;
  if (outer != nullptr) {
    return CLASS_E_NOAGGREGATION;
  }
  auto* service = new (std::nothrow) CzechCoreTextService();
  if (service == nullptr) {
    return E_OUTOFMEMORY;
  }
  const HRESULT result = service->QueryInterface(interface_id, output);
  service->Release();
  return result;
}

STDMETHODIMP CzechCoreTextService::QueryInterface(REFIID interface_id, void** output) {
  if (output == nullptr) {
    return E_POINTER;
  }
  *output = nullptr;
  if (interface_id == IID_IUnknown || interface_id == IID_ITfTextInputProcessor) {
    *output = static_cast<ITfTextInputProcessor*>(this);
  } else if (interface_id == IID_ITfThreadMgrEventSink) {
    *output = static_cast<ITfThreadMgrEventSink*>(this);
  } else if (interface_id == IID_ITfTextEditSink) {
    *output = static_cast<ITfTextEditSink*>(this);
  } else if (interface_id == IID_ITfKeyEventSink) {
    *output = static_cast<ITfKeyEventSink*>(this);
  } else if (interface_id == IID_ITfDisplayAttributeProvider) {
    *output = static_cast<ITfDisplayAttributeProvider*>(this);
  }
  if (*output == nullptr) {
    return E_NOINTERFACE;
  }
  AddRef();
  return S_OK;
}

STDMETHODIMP_(ULONG) CzechCoreTextService::AddRef() {
  return static_cast<ULONG>(InterlockedIncrement(&references_));
}

STDMETHODIMP_(ULONG) CzechCoreTextService::Release() {
  const long remaining = InterlockedDecrement(&references_);
  if (remaining == 0) {
    delete this;
  }
  return static_cast<ULONG>(remaining);
}

STDMETHODIMP CzechCoreTextService::Activate(
    ITfThreadMgr* thread_manager, TfClientId client_id) {
  thread_manager_ = thread_manager;
  thread_manager_->AddRef();
  client_id_ = client_id;
  load_mode();
  czechcore::preload_engine();

  ITfCategoryMgr* category = nullptr;
  if (SUCCEEDED(CoCreateInstance(
          CLSID_TF_CategoryMgr,
          nullptr,
          CLSCTX_INPROC_SERVER,
          IID_ITfCategoryMgr,
          reinterpret_cast<void**>(&category)))) {
    category->RegisterGUID(GUID_CzechCoreDisplayAttribute, &display_atom_);
    category->Release();
  }
  if (!advise_thread_manager_sink()) {
    Deactivate();
    return MAKE_HRESULT(SEVERITY_ERROR, FACILITY_ITF, 0x301);
  }
  if (advise_key_sink()) {
    preserve_keys();
  }
  ITfDocumentMgr* focused = nullptr;
  if (thread_manager_->GetFocus(&focused) == S_OK && focused != nullptr) {
    advise_text_edit_sink(focused);
    focused->Release();
  }
  return S_OK;
}

STDMETHODIMP CzechCoreTextService::Deactivate() {
  clear_candidate(false);
  unadvise_text_edit_sink();
  unpreserve_keys();
  unadvise_key_sink();
  unadvise_thread_manager_sink();
  release(thread_manager_);
  client_id_ = TF_CLIENTID_NULL;
  return S_OK;
}

bool CzechCoreTextService::advise_thread_manager_sink() {
  ITfSource* source = nullptr;
  if (FAILED(thread_manager_->QueryInterface(IID_ITfSource, reinterpret_cast<void**>(&source)))) {
    return false;
  }
  const HRESULT result = source->AdviseSink(
      IID_ITfThreadMgrEventSink, static_cast<ITfThreadMgrEventSink*>(this), &thread_manager_cookie_);
  source->Release();
  return SUCCEEDED(result);
}

void CzechCoreTextService::unadvise_thread_manager_sink() {
  if (thread_manager_ == nullptr || thread_manager_cookie_ == TF_INVALID_COOKIE) {
    return;
  }
  ITfSource* source = nullptr;
  if (SUCCEEDED(thread_manager_->QueryInterface(IID_ITfSource, reinterpret_cast<void**>(&source)))) {
    source->UnadviseSink(thread_manager_cookie_);
    source->Release();
  }
  thread_manager_cookie_ = TF_INVALID_COOKIE;
}

bool CzechCoreTextService::advise_key_sink() {
  ITfKeystrokeMgr* manager = nullptr;
  if (FAILED(thread_manager_->QueryInterface(
          IID_ITfKeystrokeMgr, reinterpret_cast<void**>(&manager)))) {
    return false;
  }
  const HRESULT result = manager->AdviseKeyEventSink(
      client_id_, static_cast<ITfKeyEventSink*>(this), TRUE);
  manager->Release();
  return SUCCEEDED(result);
}

void CzechCoreTextService::unadvise_key_sink() {
  if (thread_manager_ == nullptr) {
    return;
  }
  ITfKeystrokeMgr* manager = nullptr;
  if (SUCCEEDED(thread_manager_->QueryInterface(
          IID_ITfKeystrokeMgr, reinterpret_cast<void**>(&manager)))) {
    manager->UnadviseKeyEventSink(client_id_);
    manager->Release();
  }
}

bool CzechCoreTextService::preserve_keys() {
  ITfKeystrokeMgr* manager = nullptr;
  if (FAILED(thread_manager_->QueryInterface(
          IID_ITfKeystrokeMgr, reinterpret_cast<void**>(&manager)))) {
    return false;
  }
  const wchar_t apply[] = L"Použít návrh CzechCore";
  const wchar_t check[] = L"Zkontrolovat větu CzechCore";
  const wchar_t mode[] = L"Přepnout režim CzechCore";
  const bool success = SUCCEEDED(manager->PreserveKey(
                           client_id_,
                           GUID_CzechCoreApplyKey,
                           &kApplyKey,
                           apply,
                           static_cast<ULONG>(std::size(apply) - 1)))
      && SUCCEEDED(manager->PreserveKey(
          client_id_,
          GUID_CzechCoreCheckKey,
          &kCheckKey,
          check,
          static_cast<ULONG>(std::size(check) - 1)))
      && SUCCEEDED(manager->PreserveKey(
          client_id_,
          GUID_CzechCoreModeKey,
          &kModeKey,
          mode,
          static_cast<ULONG>(std::size(mode) - 1)));
  manager->Release();
  return success;
}

void CzechCoreTextService::unpreserve_keys() {
  if (thread_manager_ == nullptr) {
    return;
  }
  ITfKeystrokeMgr* manager = nullptr;
  if (SUCCEEDED(thread_manager_->QueryInterface(
          IID_ITfKeystrokeMgr, reinterpret_cast<void**>(&manager)))) {
    manager->UnpreserveKey(GUID_CzechCoreApplyKey, &kApplyKey);
    manager->UnpreserveKey(GUID_CzechCoreCheckKey, &kCheckKey);
    manager->UnpreserveKey(GUID_CzechCoreModeKey, &kModeKey);
    manager->Release();
  }
}

bool CzechCoreTextService::advise_text_edit_sink(ITfDocumentMgr* document_manager) {
  unadvise_text_edit_sink();
  if (document_manager == nullptr
      || document_manager->GetTop(&text_edit_context_) != S_OK
      || text_edit_context_ == nullptr) {
    return true;
  }
  ITfSource* source = nullptr;
  if (FAILED(text_edit_context_->QueryInterface(IID_ITfSource, reinterpret_cast<void**>(&source)))) {
    release(text_edit_context_);
    return false;
  }
  const HRESULT result = source->AdviseSink(
      IID_ITfTextEditSink, static_cast<ITfTextEditSink*>(this), &text_edit_cookie_);
  source->Release();
  if (FAILED(result)) {
    release(text_edit_context_);
  }
  return SUCCEEDED(result);
}

void CzechCoreTextService::unadvise_text_edit_sink() {
  if (text_edit_context_ != nullptr && text_edit_cookie_ != TF_INVALID_COOKIE) {
    ITfSource* source = nullptr;
    if (SUCCEEDED(text_edit_context_->QueryInterface(IID_ITfSource, reinterpret_cast<void**>(&source)))) {
      source->UnadviseSink(text_edit_cookie_);
      source->Release();
    }
  }
  text_edit_cookie_ = TF_INVALID_COOKIE;
  release(text_edit_context_);
}

STDMETHODIMP CzechCoreTextService::OnInitDocumentMgr(ITfDocumentMgr*) { return S_OK; }
STDMETHODIMP CzechCoreTextService::OnUninitDocumentMgr(ITfDocumentMgr*) { return S_OK; }
STDMETHODIMP CzechCoreTextService::OnPushContext(ITfContext*) { return S_OK; }
STDMETHODIMP CzechCoreTextService::OnPopContext(ITfContext*) { return S_OK; }

STDMETHODIMP CzechCoreTextService::OnSetFocus(
    ITfDocumentMgr* focused_document, ITfDocumentMgr*) {
  advise_text_edit_sink(focused_document);
  clear_candidate(false);
  last_analyzed_.clear();
  return S_OK;
}

STDMETHODIMP CzechCoreTextService::OnEndEdit(
    ITfContext* context, TfEditCookie read_cookie, ITfEditRecord* edit_record) {
  if (!has_text_updates(edit_record)) {
    return S_OK;
  }
  clear_candidate(true);
  analyze(context, read_cookie, true);
  return S_OK;
}

void CzechCoreTextService::analyze(
    ITfContext* context, TfEditCookie read_cookie, bool require_terminator) {
  load_mode();
  if (mode_ == Mode::Off) {
    return;
  }
  ITfRange* range = nullptr;
  std::wstring source;
  if (!read_current_sentence(context, read_cookie, require_terminator, &range, source)) {
    return;
  }
  if (sensitive_scope(context, range, read_cookie) || source == last_analyzed_) {
    range->Release();
    return;
  }
  last_analyzed_ = source;
  // ponytail: synchronous only at sentence end/manual check; move to marshaled worker if p95 exceeds 250 ms.
  const std::optional<std::wstring> replacement = czechcore::request_engine(source);
  if (!replacement.has_value() || *replacement == source) {
    range->Release();
    return;
  }
  bool automatic = false;
  if (mode_ == Mode::Automatic) {
    const auto safe = czechcore::remove_adjacent_duplicate(czechcore::utf16_to_utf8(source));
    automatic = safe.has_value()
        && czechcore::utf8_to_utf16(*safe) == *replacement;
  }
  queue_suggestion(context, range, source, *replacement, automatic);
  range->Release();
}

void CzechCoreTextService::queue_suggestion(
    ITfContext* context,
    ITfRange* range,
    std::wstring source,
    std::wstring replacement,
    bool automatic) {
  clear_candidate(false);
  candidate_context_ = context;
  candidate_context_->AddRef();
  candidate_range_ = range;
  candidate_range_->AddRef();
  candidate_source_ = source;
  candidate_replacement_ = replacement;

  auto* session = new (std::nothrow) SuggestionEditSession(
      this,
      context,
      range,
      std::move(source),
      std::move(replacement),
      automatic ? SuggestionEditSession::Action::Apply : SuggestionEditSession::Action::Mark);
  if (session == nullptr) {
    clear_candidate(false);
    return;
  }
  HRESULT session_result = S_OK;
  context->RequestEditSession(
      client_id_, session, TF_ES_READWRITE | TF_ES_ASYNCDONTCARE, &session_result);
  session->Release();
}

void CzechCoreTextService::apply_candidate() {
  if (candidate_context_ == nullptr || candidate_range_ == nullptr) {
    return;
  }
  auto* session = new (std::nothrow) SuggestionEditSession(
      this,
      candidate_context_,
      candidate_range_,
      candidate_source_,
      candidate_replacement_,
      SuggestionEditSession::Action::Apply);
  if (session == nullptr) {
    return;
  }
  HRESULT session_result = S_OK;
  candidate_context_->RequestEditSession(
      client_id_, session, TF_ES_READWRITE | TF_ES_ASYNCDONTCARE, &session_result);
  session->Release();
}

void CzechCoreTextService::clear_candidate(bool clear_attribute) {
  if (clear_attribute && candidate_context_ != nullptr && candidate_range_ != nullptr) {
    auto* session = new (std::nothrow) SuggestionEditSession(
        this,
        candidate_context_,
        candidate_range_,
        candidate_source_,
        candidate_replacement_,
        SuggestionEditSession::Action::Clear);
    if (session != nullptr) {
      HRESULT session_result = S_OK;
      candidate_context_->RequestEditSession(
          client_id_, session, TF_ES_READWRITE | TF_ES_ASYNCDONTCARE, &session_result);
      session->Release();
    }
  }
  release(candidate_range_);
  release(candidate_context_);
  candidate_source_.clear();
  candidate_replacement_.clear();
}

bool CzechCoreTextService::sensitive_scope(
    ITfContext* context, ITfRange* range, TfEditCookie cookie) const {
  ITfProperty* property = nullptr;
  if (FAILED(context->GetProperty(GUID_PROP_INPUTSCOPE, &property))) {
    return false;
  }
  VARIANT value{};
  const HRESULT result = property->GetValue(cookie, range, &value);
  property->Release();
  if (FAILED(result) || value.vt != VT_UNKNOWN || value.punkVal == nullptr) {
    VariantClear(&value);
    return false;
  }
  ITfInputScope* scope = nullptr;
  const HRESULT query = value.punkVal->QueryInterface(
      IID_ITfInputScope, reinterpret_cast<void**>(&scope));
  VariantClear(&value);
  if (FAILED(query) || scope == nullptr) {
    return false;
  }
  InputScope* scopes = nullptr;
  UINT count = 0;
  const HRESULT scopes_result = scope->GetInputScopes(&scopes, &count);
  scope->Release();
  if (FAILED(scopes_result)) {
    return false;
  }
  bool sensitive = false;
  for (UINT index = 0; index < count; ++index) {
    switch (scopes[index]) {
      case IS_URL:
      case IS_FILE_FULLFILEPATH:
      case IS_FILE_FILENAME:
      case IS_EMAIL_USERNAME:
      case IS_EMAIL_SMTPEMAILADDRESS:
      case IS_LOGINNAME:
      case IS_PASSWORD:
      case IS_EMAILNAME_OR_ADDRESS:
      case IS_PRIVATE:
      case IS_NUMERIC_PASSWORD:
      case IS_NUMERIC_PIN:
      case IS_ALPHANUMERIC_PIN:
      case IS_ALPHANUMERIC_PIN_SET:
        sensitive = true;
        break;
      default:
        break;
    }
  }
  CoTaskMemFree(scopes);
  return sensitive;
}

void CzechCoreTextService::load_mode() {
  DWORD value = static_cast<DWORD>(Mode::Underline);
  DWORD bytes = sizeof(value);
  if (RegGetValueW(
          HKEY_CURRENT_USER,
          L"Software\\CzechCore",
          L"Mode",
          RRF_RT_REG_DWORD,
          nullptr,
          &value,
          &bytes)
          != ERROR_SUCCESS
      || value > static_cast<DWORD>(Mode::Automatic)) {
    value = static_cast<DWORD>(Mode::Underline);
  }
  mode_ = static_cast<Mode>(value);
}

void CzechCoreTextService::save_mode() const {
  const DWORD value = static_cast<DWORD>(mode_);
  RegSetKeyValueW(
      HKEY_CURRENT_USER,
      L"Software\\CzechCore",
      L"Mode",
      REG_DWORD,
      &value,
      sizeof(value));
}

void CzechCoreTextService::cycle_mode() {
  mode_ = mode_ == Mode::Off
      ? Mode::Underline
      : mode_ == Mode::Underline ? Mode::Automatic : Mode::Off;
  save_mode();
  clear_candidate(true);
  last_analyzed_.clear();
  MessageBeep(MB_OK);
}

STDMETHODIMP CzechCoreTextService::OnSetFocus(BOOL) { return S_OK; }

STDMETHODIMP CzechCoreTextService::OnTestKeyDown(
    ITfContext*, WPARAM, LPARAM, BOOL* eaten) {
  if (eaten == nullptr) {
    return E_POINTER;
  }
  *eaten = FALSE;
  return S_OK;
}

STDMETHODIMP CzechCoreTextService::OnKeyDown(
    ITfContext*, WPARAM, LPARAM, BOOL* eaten) {
  if (eaten == nullptr) {
    return E_POINTER;
  }
  *eaten = FALSE;
  return S_OK;
}

STDMETHODIMP CzechCoreTextService::OnTestKeyUp(
    ITfContext*, WPARAM, LPARAM, BOOL* eaten) {
  if (eaten == nullptr) {
    return E_POINTER;
  }
  *eaten = FALSE;
  return S_OK;
}

STDMETHODIMP CzechCoreTextService::OnKeyUp(
    ITfContext*, WPARAM, LPARAM, BOOL* eaten) {
  if (eaten == nullptr) {
    return E_POINTER;
  }
  *eaten = FALSE;
  return S_OK;
}

STDMETHODIMP CzechCoreTextService::OnPreservedKey(
    ITfContext* context, REFGUID key_guid, BOOL* eaten) {
  if (eaten == nullptr) {
    return E_POINTER;
  }
  *eaten = TRUE;
  if (key_guid == GUID_CzechCoreApplyKey) {
    apply_candidate();
  } else if (key_guid == GUID_CzechCoreModeKey) {
    cycle_mode();
  } else if (key_guid == GUID_CzechCoreCheckKey) {
    auto* session = new (std::nothrow) AnalyzeEditSession(this, context);
    if (session != nullptr) {
      HRESULT session_result = S_OK;
      const HRESULT request_result = context->RequestEditSession(
          client_id_, session, TF_ES_SYNC | TF_ES_READ, &session_result);
      if (FAILED(request_result) || FAILED(session_result)) {
        context->RequestEditSession(
            client_id_, session, TF_ES_READ | TF_ES_ASYNCDONTCARE, &session_result);
      }
      session->Release();
    }
  } else {
    *eaten = FALSE;
  }
  return S_OK;
}

STDMETHODIMP CzechCoreTextService::EnumDisplayAttributeInfo(
    IEnumTfDisplayAttributeInfo** output) {
  return create_display_attribute_enum(output);
}

STDMETHODIMP CzechCoreTextService::GetDisplayAttributeInfo(
    REFGUID guid, ITfDisplayAttributeInfo** output) {
  if (guid != GUID_CzechCoreDisplayAttribute) {
    if (output != nullptr) {
      *output = nullptr;
    }
    return E_INVALIDARG;
  }
  return create_display_attribute_info(output);
}
