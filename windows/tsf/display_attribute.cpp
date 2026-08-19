#include "tsf.h"

#include <oleauto.h>

#include <new>

namespace {

TF_DISPLAYATTRIBUTE default_attribute() {
  TF_DISPLAYATTRIBUTE value{};
  value.crText.type = TF_CT_NONE;
  value.crBk.type = TF_CT_NONE;
  value.lsStyle = TF_LS_SQUIGGLE;
  value.fBoldLine = FALSE;
  value.crLine.type = TF_CT_COLORREF;
  value.crLine.cr = RGB(210, 34, 45);
  value.bAttr = TF_ATTR_TARGET_NOTCONVERTED;
  return value;
}

class DisplayAttributeInfo final : public ITfDisplayAttributeInfo {
 public:
  DisplayAttributeInfo() { module_add_ref(); }
  ~DisplayAttributeInfo() { module_release(); }

  STDMETHODIMP QueryInterface(REFIID interface_id, void** output) override {
    if (output == nullptr) {
      return E_POINTER;
    }
    *output = nullptr;
    if (interface_id == IID_IUnknown || interface_id == IID_ITfDisplayAttributeInfo) {
      *output = static_cast<ITfDisplayAttributeInfo*>(this);
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

  STDMETHODIMP GetGUID(GUID* guid) override {
    if (guid == nullptr) {
      return E_POINTER;
    }
    *guid = GUID_CzechCoreDisplayAttribute;
    return S_OK;
  }

  STDMETHODIMP GetDescription(BSTR* description) override {
    if (description == nullptr) {
      return E_POINTER;
    }
    *description = SysAllocString(L"CzechCore návrh opravy");
    return *description == nullptr ? E_OUTOFMEMORY : S_OK;
  }

  STDMETHODIMP GetAttributeInfo(TF_DISPLAYATTRIBUTE* attribute) override {
    if (attribute == nullptr) {
      return E_POINTER;
    }
    *attribute = attribute_;
    return S_OK;
  }

  STDMETHODIMP SetAttributeInfo(const TF_DISPLAYATTRIBUTE* attribute) override {
    if (attribute == nullptr) {
      return E_POINTER;
    }
    attribute_ = *attribute;
    return S_OK;
  }

  STDMETHODIMP Reset() override {
    attribute_ = default_attribute();
    return S_OK;
  }

 private:
  long references_ = 1;
  TF_DISPLAYATTRIBUTE attribute_ = default_attribute();
};

class DisplayAttributeEnum final : public IEnumTfDisplayAttributeInfo {
 public:
  DisplayAttributeEnum() { module_add_ref(); }
  ~DisplayAttributeEnum() { module_release(); }

  STDMETHODIMP QueryInterface(REFIID interface_id, void** output) override {
    if (output == nullptr) {
      return E_POINTER;
    }
    *output = nullptr;
    if (interface_id == IID_IUnknown || interface_id == IID_IEnumTfDisplayAttributeInfo) {
      *output = static_cast<IEnumTfDisplayAttributeInfo*>(this);
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

  STDMETHODIMP Clone(IEnumTfDisplayAttributeInfo** output) override {
    if (output == nullptr) {
      return E_POINTER;
    }
    auto* clone = new (std::nothrow) DisplayAttributeEnum();
    if (clone == nullptr) {
      return E_OUTOFMEMORY;
    }
    clone->used_ = used_;
    *output = clone;
    return S_OK;
  }

  STDMETHODIMP Next(
      ULONG requested, ITfDisplayAttributeInfo** output, ULONG* fetched) override {
    if (output == nullptr || (requested != 1 && fetched == nullptr)) {
      return E_POINTER;
    }
    if (fetched != nullptr) {
      *fetched = 0;
    }
    if (requested == 0 || used_) {
      return S_FALSE;
    }
    const HRESULT result = create_display_attribute_info(output);
    if (FAILED(result)) {
      return result;
    }
    used_ = true;
    if (fetched != nullptr) {
      *fetched = 1;
    }
    return S_OK;
  }

  STDMETHODIMP Reset() override {
    used_ = false;
    return S_OK;
  }

  STDMETHODIMP Skip(ULONG count) override {
    if (count == 0) {
      return S_OK;
    }
    if (!used_) {
      used_ = true;
      return count == 1 ? S_OK : S_FALSE;
    }
    return S_FALSE;
  }

 private:
  long references_ = 1;
  bool used_ = false;
};

}  // namespace

HRESULT create_display_attribute_info(ITfDisplayAttributeInfo** output) {
  if (output == nullptr) {
    return E_POINTER;
  }
  *output = new (std::nothrow) DisplayAttributeInfo();
  return *output == nullptr ? E_OUTOFMEMORY : S_OK;
}

HRESULT create_display_attribute_enum(IEnumTfDisplayAttributeInfo** output) {
  if (output == nullptr) {
    return E_POINTER;
  }
  *output = new (std::nothrow) DisplayAttributeEnum();
  return *output == nullptr ? E_OUTOFMEMORY : S_OK;
}
