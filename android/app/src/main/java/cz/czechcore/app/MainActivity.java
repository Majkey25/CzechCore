package cz.czechcore.app;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.view.inputmethod.InputMethodManager;
import java.io.File;

public final class MainActivity extends Activity {
    private final LocalCorrectionEngine engine = new LocalCorrectionEngine();

    private Button correctButton;
    private Button enableKeyboardButton;
    private Button selectKeyboardButton;
    private Button modeButton;
    private EditText inputText;
    private TextView outputText;
    private TextView statusText;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        correctButton = findViewById(R.id.correct_button);
        enableKeyboardButton = findViewById(R.id.enable_keyboard_button);
        selectKeyboardButton = findViewById(R.id.select_keyboard_button);
        modeButton = findViewById(R.id.mode_button);
        inputText = findViewById(R.id.input_text);
        outputText = findViewById(R.id.output_text);
        statusText = findViewById(R.id.status_text);

        String suppliedText = getIntent().getStringExtra("text");
        inputText.setText(
                suppliedText == null ? "Když přišel domů šel spát." : suppliedText);
        correctButton.setOnClickListener(view -> correct());
        enableKeyboardButton.setOnClickListener(view ->
                startActivity(new Intent(Settings.ACTION_INPUT_METHOD_SETTINGS)));
        selectKeyboardButton.setOnClickListener(view -> {
            InputMethodManager manager = getSystemService(InputMethodManager.class);
            if (manager != null) {
                manager.showInputMethodPicker();
            }
        });
        modeButton.setOnClickListener(view -> cycleMode());
        updateModelStatus();
        updateModeButton();

        if (getIntent().getBooleanExtra("run", false)) {
            correctButton.post(this::correct);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateModeButton();
    }

    @Override
    protected void onDestroy() {
        engine.close();
        super.onDestroy();
    }

    private void correct() {
        File modelDirectory = modelDirectory();
        if (!LocalCorrectionEngine.hasModel(modelDirectory)) {
            statusText.setText(R.string.model_missing);
            return;
        }

        String source = inputText.getText().toString();
        correctButton.setEnabled(false);
        statusText.setText(R.string.running);
        engine.correct(modelDirectory, source, new LocalCorrectionEngine.Listener() {
            @Override
            public void onCorrected(String corrected) {
                runOnUiThread(() -> showResult(corrected));
            }

            @Override
            public void onRejected() {
                runOnUiThread(() -> showRejected(source));
            }

            @Override
            public void onError() {
                runOnUiThread(MainActivity.this::showError);
            }
        });
    }

    private void showResult(String corrected) {
        outputText.setText(corrected);
        statusText.setText(R.string.complete);
        correctButton.setEnabled(true);
    }

    private void showError() {
        outputText.setText(R.string.failed);
        statusText.setText(R.string.failed);
        correctButton.setEnabled(true);
    }

    private void showRejected(String source) {
        outputText.setText(source);
        statusText.setText(R.string.candidate_rejected);
        correctButton.setEnabled(true);
    }

    private void updateModelStatus() {
        statusText.setText(
                LocalCorrectionEngine.hasModel(modelDirectory())
                        ? R.string.model_ready
                        : R.string.model_missing);
    }

    private void cycleMode() {
        CorrectionMode current = CorrectionMode.fromStored(
                getSharedPreferences(CorrectionMode.PREFERENCES, MODE_PRIVATE)
                        .getString(
                                CorrectionMode.PREFERENCE_KEY,
                                CorrectionMode.UNDERLINE.storedValue()));
        getSharedPreferences(CorrectionMode.PREFERENCES, MODE_PRIVATE)
                .edit()
                .putString(CorrectionMode.PREFERENCE_KEY, current.next().storedValue())
                .apply();
        updateModeButton();
    }

    private void updateModeButton() {
        CorrectionMode current = CorrectionMode.fromStored(
                getSharedPreferences(CorrectionMode.PREFERENCES, MODE_PRIVATE)
                        .getString(
                                CorrectionMode.PREFERENCE_KEY,
                                CorrectionMode.UNDERLINE.storedValue()));
        int name = switch (current) {
            case OFF -> R.string.ime_mode_off;
            case UNDERLINE -> R.string.ime_mode_underline;
            case CONFIRM -> R.string.ime_mode_confirm;
            case AUTOMATIC -> R.string.ime_mode_automatic;
        };
        modeButton.setText(getString(R.string.mode_format, getString(name)));
    }

    private File modelDirectory() {
        File files = getExternalFilesDir(null);
        if (files == null) {
            throw new IllegalStateException("external app storage is unavailable");
        }
        return new File(files, "model");
    }

}
