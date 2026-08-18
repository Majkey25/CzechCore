package cz.czechcore.app;

import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    private Button correctButton;
    private EditText inputText;
    private TextView outputText;
    private TextView statusText;
    private WordPieceTokenizer tokenizer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        correctButton = findViewById(R.id.correct_button);
        inputText = findViewById(R.id.input_text);
        outputText = findViewById(R.id.output_text);
        statusText = findViewById(R.id.status_text);

        String suppliedText = getIntent().getStringExtra("text");
        inputText.setText(
                suppliedText == null ? "Když přišel domů šel spát." : suppliedText);
        correctButton.setOnClickListener(view -> correct());
        updateModelStatus();

        if (getIntent().getBooleanExtra("run", false)) {
            correctButton.post(this::correct);
        }
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    private void correct() {
        File modelDirectory = modelDirectory();
        if (!hasModel(modelDirectory)) {
            statusText.setText(R.string.model_missing);
            return;
        }

        String source = inputText.getText().toString();
        correctButton.setEnabled(false);
        statusText.setText(R.string.running);
        executor.execute(() -> {
            try {
                if (tokenizer == null) {
                    tokenizer = WordPieceTokenizer.fromJson(
                            readUtf8(new File(modelDirectory, "shared_vocabulary.json")));
                }
                String[] input = tokenizer.encode(source).toArray(new String[0]);
                String[] output = NativeBridge.correct(modelDirectory.getAbsolutePath(), input);
                String corrected = tokenizer.decode(Arrays.asList(output));
                if (ProtectedText.isSafe(source, corrected)) {
                    runOnUiThread(() -> showResult(corrected));
                } else {
                    runOnUiThread(() -> showRejected(source));
                }
            } catch (Exception error) {
                runOnUiThread(() -> showError(error));
            }
        });
    }

    private void showResult(String corrected) {
        outputText.setText(corrected);
        statusText.setText(R.string.complete);
        correctButton.setEnabled(true);
    }

    private void showError(Exception error) {
        outputText.setText(error.getMessage());
        statusText.setText(R.string.failed);
        correctButton.setEnabled(true);
    }

    private void showRejected(String source) {
        outputText.setText(source);
        statusText.setText(R.string.candidate_rejected);
        correctButton.setEnabled(true);
    }

    private void updateModelStatus() {
        statusText.setText(hasModel(modelDirectory()) ? R.string.model_ready : R.string.model_missing);
    }

    private File modelDirectory() {
        File files = getExternalFilesDir(null);
        if (files == null) {
            throw new IllegalStateException("external app storage is unavailable");
        }
        return new File(files, "model");
    }

    private static boolean hasModel(File directory) {
        return new File(directory, "config.json").isFile()
                && new File(directory, "model.bin").isFile()
                && new File(directory, "shared_vocabulary.json").isFile();
    }

    private static String readUtf8(File file) throws IOException {
        try (InputStream input = new FileInputStream(file);
                ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) {
                output.write(buffer, 0, count);
            }
            return new String(output.toByteArray(), StandardCharsets.UTF_8);
        }
    }
}
