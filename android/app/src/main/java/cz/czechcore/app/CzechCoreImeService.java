package cz.czechcore.app;

import android.annotation.SuppressLint;
import android.inputmethodservice.InputMethodService;
import android.inputmethodservice.Keyboard;
import android.inputmethodservice.KeyboardView;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.text.Spannable;
import android.text.SpannableString;
import android.text.SpannableStringBuilder;
import android.text.style.SuggestionSpan;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.TextView;
import java.io.File;
import java.util.Locale;

@SuppressWarnings("deprecation")
public final class CzechCoreImeService extends InputMethodService
        implements KeyboardView.OnKeyboardActionListener {
    private static final int KEYCODE_NEXT_IME = -101;
    private static final int CONTEXT_CHARS = 512;
    private static final long DEBOUNCE_MILLIS = 350;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final LocalCorrectionEngine engine = new LocalCorrectionEngine();
    private final Runnable analyzeRunnable = this::analyzeCurrentSentence;

    private KeyboardView keyboardView;
    private Keyboard lettersKeyboard;
    private Keyboard symbolsKeyboard;
    private TextView candidateText;
    private TextView statusText;
    private Button modeButton;
    private CorrectionMode mode = CorrectionMode.UNDERLINE;
    private long revision;
    private boolean sensitiveField;
    private Candidate candidate;
    private Undo undo;

    @Override
    @SuppressLint("InflateParams")
    public View onCreateInputView() {
        View view = getLayoutInflater().inflate(R.layout.ime_input, null);
        keyboardView = view.findViewById(R.id.keyboard_view);
        candidateText = view.findViewById(R.id.candidate_text);
        statusText = view.findViewById(R.id.ime_status_text);
        modeButton = view.findViewById(R.id.ime_mode_button);
        lettersKeyboard = new Keyboard(this, R.xml.keyboard_letters);
        symbolsKeyboard = new Keyboard(this, R.xml.keyboard_symbols);
        keyboardView.setKeyboard(lettersKeyboard);
        keyboardView.setOnKeyboardActionListener(this);
        keyboardView.setPreviewEnabled(false);
        candidateText.setOnClickListener(ignored -> applyCandidateOrUndo());
        modeButton.setOnClickListener(ignored -> cycleMode());
        loadMode();
        updateModeButton();
        return view;
    }

    @Override
    public void onStartInputView(EditorInfo info, boolean restarting) {
        super.onStartInputView(info, restarting);
        revision++;
        handler.removeCallbacks(analyzeRunnable);
        loadMode();
        sensitiveField = !ImeTextPolicy.allowsCorrection(info.inputType, info.imeOptions);
        keyboardView.setKeyboard(
                (info.inputType & InputType.TYPE_MASK_CLASS) == InputType.TYPE_CLASS_TEXT
                        ? lettersKeyboard
                        : symbolsKeyboard);
        clearCandidate();
        updateModeButton();
        updateIdleStatus();
    }

    @Override
    public void onFinishInput() {
        revision++;
        handler.removeCallbacks(analyzeRunnable);
        clearCandidate();
        super.onFinishInput();
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        engine.close();
        super.onDestroy();
    }

    @Override
    public void onKey(int primaryCode, int[] keyCodes) {
        InputConnection connection = getCurrentInputConnection();
        if (connection == null) {
            return;
        }
        switch (primaryCode) {
            case Keyboard.KEYCODE_DELETE -> sendDownUpKeyEvents(KeyEvent.KEYCODE_DEL);
            case Keyboard.KEYCODE_SHIFT -> toggleShift();
            case Keyboard.KEYCODE_MODE_CHANGE -> toggleSymbols();
            case Keyboard.KEYCODE_DONE -> sendEnter(connection);
            case KEYCODE_NEXT_IME -> switchInputMethod();
            default -> commitCharacter(connection, primaryCode);
        }
        if (primaryCode != Keyboard.KEYCODE_SHIFT && primaryCode != Keyboard.KEYCODE_MODE_CHANGE) {
            revision++;
            clearCandidate();
            scheduleAnalysis(primaryCode == '.' || primaryCode == '!' || primaryCode == '?');
        }
    }

    @Override
    public void onText(CharSequence text) {
        InputConnection connection = getCurrentInputConnection();
        if (connection != null) {
            connection.commitText(text, 1);
            revision++;
            clearCandidate();
            scheduleAnalysis(false);
        }
    }

    @Override
    public void onPress(int primaryCode) {}

    @Override
    public void onRelease(int primaryCode) {}

    @Override
    public void swipeLeft() {}

    @Override
    public void swipeRight() {}

    @Override
    public void swipeDown() {}

    @Override
    public void swipeUp() {}

    private void analyzeCurrentSentence() {
        if (mode == CorrectionMode.OFF || sensitiveField) {
            return;
        }
        File modelDirectory = modelDirectory();
        InputConnection connection = getCurrentInputConnection();
        if (modelDirectory == null
                || !LocalCorrectionEngine.hasModel(modelDirectory)
                || connection == null) {
            updateIdleStatus();
            return;
        }
        CharSequence before = connection.getTextBeforeCursor(CONTEXT_CHARS, 0);
        if (before == null) {
            return;
        }
        ImeTextPolicy.Window window = ImeTextPolicy.currentSentence(before.toString());
        if (window.text().length() < 2) {
            return;
        }
        if (mode == CorrectionMode.AUTOMATIC) {
            String automatic = ImeTextPolicy.automaticRepair(window.text());
            if (automatic != null) {
                candidate = new Candidate(window, automatic);
                applyCandidate();
                statusText.setText(R.string.ime_auto_applied);
                return;
            }
        }
        long requestRevision = revision;
        statusText.setText(R.string.ime_analyzing);
        engine.correct(modelDirectory, window.text(), new LocalCorrectionEngine.Listener() {
            @Override
            public void onCorrected(String corrected) {
                handler.post(() -> acceptResult(requestRevision, window, corrected));
            }

            @Override
            public void onRejected() {
                handler.post(() -> {
                    if (revision == requestRevision) {
                        statusText.setText(R.string.ime_candidate_rejected);
                    }
                });
            }

            @Override
            public void onError() {
                handler.post(() -> {
                    if (revision == requestRevision) {
                        statusText.setText(R.string.ime_correction_failed);
                    }
                });
            }
        });
    }

    private void acceptResult(
            long requestRevision, ImeTextPolicy.Window window, String corrected) {
        if (requestRevision != revision || corrected.equals(window.text())) {
            updateIdleStatus();
            return;
        }
        InputConnection connection = getCurrentInputConnection();
        CharSequence before = connection == null
                ? null
                : connection.getTextBeforeCursor(CONTEXT_CHARS, 0);
        if (before == null || !ImeTextPolicy.matches(before.toString(), window)) {
            return;
        }
        candidate = new Candidate(window, corrected);
        if (mode == CorrectionMode.AUTOMATIC
                && ImeTextPolicy.isAutoSafe(window.text(), corrected)) {
            applyCandidate();
            statusText.setText(R.string.ime_auto_applied);
            return;
        }
        markSuggestion(connection, window, corrected);
        candidateText.setText(corrected);
        candidateText.setContentDescription(getString(R.string.ime_apply_suggestion));
        statusText.setText(R.string.ime_suggestion_ready);
    }

    private void markSuggestion(
            InputConnection connection, ImeTextPolicy.Window window, String corrected) {
        SpannableString marked = new SpannableString(window.text());
        marked.setSpan(
                new SuggestionSpan(
                        this,
                        new String[] {corrected},
                        SuggestionSpan.FLAG_EASY_CORRECT),
                0,
                marked.length(),
                Spannable.SPAN_EXCLUSIVE_EXCLUSIVE);
        replaceSuffix(connection, window.text(), window.trailing(), marked, window.trailing());
    }

    private void applyCandidateOrUndo() {
        if (undo != null) {
            applyUndo();
        } else if (candidate != null) {
            applyCandidate();
        }
    }

    private void applyCandidate() {
        Candidate selected = candidate;
        InputConnection connection = getCurrentInputConnection();
        if (selected == null || connection == null || !matches(connection, selected.window)) {
            clearCandidate();
            return;
        }
        replaceSuffix(
                connection,
                selected.window.text(),
                selected.window.trailing(),
                selected.corrected,
                selected.window.trailing());
        undo = new Undo(selected.corrected, selected.window.text(), selected.window.trailing());
        candidate = null;
        revision++;
        candidateText.setText(R.string.ime_undo);
        candidateText.setContentDescription(getString(R.string.ime_undo_description));
    }

    private void applyUndo() {
        Undo current = undo;
        InputConnection connection = getCurrentInputConnection();
        if (current == null || connection == null) {
            clearCandidate();
            return;
        }
        ImeTextPolicy.Window corrected = new ImeTextPolicy.Window(current.corrected, current.trailing);
        if (!matches(connection, corrected)) {
            clearCandidate();
            return;
        }
        replaceSuffix(
                connection,
                current.corrected,
                current.trailing,
                current.original,
                current.trailing);
        revision++;
        clearCandidate();
        statusText.setText(R.string.ime_undo_complete);
    }

    private static void replaceSuffix(
            InputConnection connection,
            String source,
            String sourceTrailing,
            CharSequence replacement,
            String replacementTrailing) {
        connection.beginBatchEdit();
        connection.deleteSurroundingText(source.length() + sourceTrailing.length(), 0);
        connection.commitText(
                new SpannableStringBuilder(replacement).append(replacementTrailing), 1);
        connection.endBatchEdit();
    }

    private static boolean matches(InputConnection connection, ImeTextPolicy.Window window) {
        CharSequence before = connection.getTextBeforeCursor(CONTEXT_CHARS, 0);
        return before != null && ImeTextPolicy.matches(before.toString(), window);
    }

    private void commitCharacter(InputConnection connection, int primaryCode) {
        if (primaryCode <= 0 || !Character.isValidCodePoint(primaryCode)) {
            return;
        }
        String value = new String(Character.toChars(primaryCode));
        if (lettersKeyboard.isShifted()) {
            value = value.toUpperCase(Locale.forLanguageTag("cs-CZ"));
            lettersKeyboard.setShifted(false);
            keyboardView.invalidateAllKeys();
        }
        connection.commitText(value, 1);
    }

    private void sendEnter(InputConnection connection) {
        EditorInfo info = getCurrentInputEditorInfo();
        int action = info == null ? EditorInfo.IME_ACTION_NONE : info.imeOptions & EditorInfo.IME_MASK_ACTION;
        if (action != EditorInfo.IME_ACTION_NONE
                && action != EditorInfo.IME_ACTION_UNSPECIFIED
                && (info.imeOptions & EditorInfo.IME_FLAG_NO_ENTER_ACTION) == 0) {
            connection.performEditorAction(action);
        } else {
            connection.commitText("\n", 1);
        }
    }

    private void toggleShift() {
        lettersKeyboard.setShifted(!lettersKeyboard.isShifted());
        keyboardView.invalidateAllKeys();
    }

    private void toggleSymbols() {
        keyboardView.setKeyboard(
                keyboardView.getKeyboard() == lettersKeyboard ? symbolsKeyboard : lettersKeyboard);
    }

    private void switchInputMethod() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            switchToNextInputMethod(false);
            return;
        }
        InputMethodManager manager = getSystemService(InputMethodManager.class);
        if (manager != null) {
            manager.showInputMethodPicker();
        }
    }

    private void scheduleAnalysis(boolean immediate) {
        handler.removeCallbacks(analyzeRunnable);
        if (mode != CorrectionMode.OFF && !sensitiveField) {
            handler.postDelayed(analyzeRunnable, immediate ? 0 : DEBOUNCE_MILLIS);
        }
    }

    private void cycleMode() {
        mode = mode.next();
        getSharedPreferences(CorrectionMode.PREFERENCES, MODE_PRIVATE)
                .edit()
                .putString(CorrectionMode.PREFERENCE_KEY, mode.storedValue())
                .apply();
        revision++;
        handler.removeCallbacks(analyzeRunnable);
        clearCandidate();
        updateModeButton();
        updateIdleStatus();
    }

    private void loadMode() {
        String stored = getSharedPreferences(CorrectionMode.PREFERENCES, MODE_PRIVATE)
                .getString(CorrectionMode.PREFERENCE_KEY, CorrectionMode.UNDERLINE.storedValue());
        mode = CorrectionMode.fromStored(stored);
    }

    private void updateModeButton() {
        int label = switch (mode) {
            case OFF -> R.string.ime_mode_off;
            case UNDERLINE -> R.string.ime_mode_underline;
            case CONFIRM -> R.string.ime_mode_confirm;
            case AUTOMATIC -> R.string.ime_mode_automatic;
        };
        modeButton.setText(label);
    }

    private void updateIdleStatus() {
        if (sensitiveField) {
            statusText.setText(R.string.ime_private_field);
            return;
        }
        if (mode == CorrectionMode.OFF) {
            statusText.setText(R.string.ime_disabled);
            return;
        }
        File model = modelDirectory();
        statusText.setText(
                model != null && LocalCorrectionEngine.hasModel(model)
                        ? R.string.ime_ready
                        : R.string.model_missing);
    }

    private void clearCandidate() {
        candidate = null;
        undo = null;
        if (candidateText != null) {
            candidateText.setText(R.string.ime_no_suggestion);
            candidateText.setContentDescription(getString(R.string.ime_no_suggestion));
        }
    }

    private File modelDirectory() {
        File files = getExternalFilesDir(null);
        return files == null ? null : new File(files, "model");
    }

    private static final class Candidate {
        private final ImeTextPolicy.Window window;
        private final String corrected;

        private Candidate(ImeTextPolicy.Window window, String corrected) {
            this.window = window;
            this.corrected = corrected;
        }
    }

    private static final class Undo {
        private final String corrected;
        private final String original;
        private final String trailing;

        private Undo(String corrected, String original, String trailing) {
            this.corrected = corrected;
            this.original = original;
            this.trailing = trailing;
        }
    }
}
