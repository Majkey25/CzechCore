#pragma once

#include <windows.h>
#include <inputscope.h>
#include <msctf.h>

#include <string>

extern HINSTANCE g_module;
extern long g_module_references;

extern const CLSID CLSID_CzechCoreTextService;
extern const GUID GUID_CzechCoreProfile;
extern const GUID GUID_CzechCoreDisplayAttribute;
extern const GUID GUID_CzechCoreApplyKey;
extern const GUID GUID_CzechCoreCheckKey;
extern const GUID GUID_CzechCoreModeKey;

void module_add_ref();
void module_release();

HRESULT create_display_attribute_info(ITfDisplayAttributeInfo** output);
HRESULT create_display_attribute_enum(IEnumTfDisplayAttributeInfo** output);

class SuggestionEditSession;
class AnalyzeEditSession;

class CzechCoreTextService final : public ITfTextInputProcessor,
                                   public ITfThreadMgrEventSink,
                                   public ITfTextEditSink,
                                   public ITfKeyEventSink,
                                   public ITfDisplayAttributeProvider {
 public:
  CzechCoreTextService();
  ~CzechCoreTextService();

  static HRESULT create_instance(IUnknown* outer, REFIID interface_id, void** output);

  STDMETHODIMP QueryInterface(REFIID interface_id, void** output) override;
  STDMETHODIMP_(ULONG) AddRef() override;
  STDMETHODIMP_(ULONG) Release() override;

  STDMETHODIMP Activate(ITfThreadMgr* thread_manager, TfClientId client_id) override;
  STDMETHODIMP Deactivate() override;

  STDMETHODIMP OnInitDocumentMgr(ITfDocumentMgr* document_manager) override;
  STDMETHODIMP OnUninitDocumentMgr(ITfDocumentMgr* document_manager) override;
  STDMETHODIMP OnSetFocus(
      ITfDocumentMgr* focused_document, ITfDocumentMgr* previous_document) override;
  STDMETHODIMP OnPushContext(ITfContext* context) override;
  STDMETHODIMP OnPopContext(ITfContext* context) override;

  STDMETHODIMP OnEndEdit(
      ITfContext* context, TfEditCookie read_cookie, ITfEditRecord* edit_record) override;

  STDMETHODIMP OnSetFocus(BOOL foreground) override;
  STDMETHODIMP OnTestKeyDown(
      ITfContext* context, WPARAM key, LPARAM flags, BOOL* eaten) override;
  STDMETHODIMP OnKeyDown(
      ITfContext* context, WPARAM key, LPARAM flags, BOOL* eaten) override;
  STDMETHODIMP OnTestKeyUp(
      ITfContext* context, WPARAM key, LPARAM flags, BOOL* eaten) override;
  STDMETHODIMP OnKeyUp(
      ITfContext* context, WPARAM key, LPARAM flags, BOOL* eaten) override;
  STDMETHODIMP OnPreservedKey(ITfContext* context, REFGUID key_guid, BOOL* eaten) override;

  STDMETHODIMP EnumDisplayAttributeInfo(IEnumTfDisplayAttributeInfo** output) override;
  STDMETHODIMP GetDisplayAttributeInfo(
      REFGUID guid, ITfDisplayAttributeInfo** output) override;

 private:
  friend class SuggestionEditSession;
  friend class AnalyzeEditSession;

  enum class Mode : DWORD { Off = 0, Underline = 1, Automatic = 2 };

  bool advise_thread_manager_sink();
  void unadvise_thread_manager_sink();
  bool advise_key_sink();
  void unadvise_key_sink();
  bool preserve_keys();
  void unpreserve_keys();
  bool advise_text_edit_sink(ITfDocumentMgr* document_manager);
  void unadvise_text_edit_sink();
  void analyze(ITfContext* context, TfEditCookie read_cookie, bool require_terminator);
  void queue_suggestion(
      ITfContext* context,
      ITfRange* range,
      std::wstring source,
      std::wstring replacement,
      bool automatic);
  void apply_candidate();
  void clear_candidate(bool clear_attribute);
  void cycle_mode();
  void load_mode();
  void save_mode() const;
  bool sensitive_scope(ITfContext* context, ITfRange* range, TfEditCookie cookie) const;

  long references_ = 1;
  ITfThreadMgr* thread_manager_ = nullptr;
  TfClientId client_id_ = TF_CLIENTID_NULL;
  DWORD thread_manager_cookie_ = TF_INVALID_COOKIE;
  DWORD text_edit_cookie_ = TF_INVALID_COOKIE;
  ITfContext* text_edit_context_ = nullptr;
  TfGuidAtom display_atom_ = TF_INVALID_GUIDATOM;
  Mode mode_ = Mode::Underline;
  std::wstring last_analyzed_;
  ITfContext* candidate_context_ = nullptr;
  ITfRange* candidate_range_ = nullptr;
  std::wstring candidate_source_;
  std::wstring candidate_replacement_;
};

bool register_server();
void unregister_server();
HRESULT register_profiles();
void unregister_profiles();
HRESULT register_categories();
void unregister_categories();
