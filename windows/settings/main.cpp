#include <windows.h>
#include <commctrl.h>

#include <iterator>

namespace {

enum class Mode : DWORD { Off = 0, Underline = 1, Automatic = 2 };

Mode read_mode() {
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
    return Mode::Underline;
  }
  return static_cast<Mode>(value);
}

bool write_mode(Mode mode) {
  const DWORD value = static_cast<DWORD>(mode);
  return RegSetKeyValueW(
             HKEY_CURRENT_USER,
             L"Software\\CzechCore",
             L"Mode",
             REG_DWORD,
             &value,
             sizeof(value))
      == ERROR_SUCCESS;
}

}  // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int) {
  const TASKDIALOG_BUTTON choices[] = {
      {100, L"Vypnuto\nCzechCore text nečte ani neopravuje."},
      {101, L"Podtržení\nNávrhy zobrazí, text změní až po potvrzení."},
      {102, L"Automaticky\nAutomaticky použije jen přesně vymezené bezpečné opravy."}};
  const int selected = 100 + static_cast<int>(read_mode());
  TASKDIALOGCONFIG dialog{};
  dialog.cbSize = sizeof(dialog);
  dialog.hInstance = instance;
  dialog.dwFlags = TDF_USE_COMMAND_LINKS | TDF_ALLOW_DIALOG_CANCELLATION;
  dialog.dwCommonButtons = TDCBF_OK_BUTTON | TDCBF_CANCEL_BUTTON;
  dialog.pszWindowTitle = L"CzechCore";
  dialog.pszMainInstruction = L"Režim korekce při psaní";
  dialog.pszContent =
      L"Korekce běží pouze lokálně. Neurální opravy se bez kalibrace nikdy nepoužijí tiše.";
  dialog.cRadioButtons = static_cast<UINT>(std::size(choices));
  dialog.pRadioButtons = choices;
  dialog.nDefaultRadioButton = selected;
  dialog.pszFooter =
      L"Ctrl+Alt+G: zkontrolovat větu    Ctrl+Alt+Enter: použít návrh";

  int button = 0;
  int radio = selected;
  if (FAILED(TaskDialogIndirect(&dialog, &button, &radio, nullptr)) || button != IDOK) {
    return 0;
  }
  const Mode mode = radio >= 100 && radio <= 102
      ? static_cast<Mode>(radio - 100)
      : Mode::Underline;
  if (!write_mode(mode)) {
    MessageBoxW(
        nullptr,
        L"Nastavení se nepodařilo uložit.",
        L"CzechCore",
        MB_OK | MB_ICONERROR);
    return 1;
  }
  MessageBoxW(
      nullptr,
      L"Nastavení bylo uloženo a platí při další kontrole textu.",
      L"CzechCore",
      MB_OK | MB_ICONINFORMATION);
  return 0;
}
