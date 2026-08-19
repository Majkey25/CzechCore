package cz.czechcore.app;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

final class LocalCorrectionEngine implements AutoCloseable {
    interface Listener {
        void onCorrected(String corrected);

        void onRejected();

        void onError();
    }

    private static final long MAX_CONFIG_BYTES = 64 * 1024;
    private static final long MAX_VOCABULARY_BYTES = 8 * 1024 * 1024;
    private static final long MAX_MODEL_BYTES = 512 * 1024 * 1024;

    private final ThreadPoolExecutor executor = new ThreadPoolExecutor(
            1,
            1,
            0,
            TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(1),
            new ThreadPoolExecutor.DiscardOldestPolicy());
    private WordPieceTokenizer tokenizer;

    void correct(File modelDirectory, String source, Listener listener) {
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
                    listener.onCorrected(corrected);
                } else {
                    listener.onRejected();
                }
            } catch (Exception ignored) {
                listener.onError();
            }
        });
    }

    static boolean hasModel(File directory) {
        return validFile(new File(directory, "config.json"), MAX_CONFIG_BYTES)
                && validFile(new File(directory, "model.bin"), MAX_MODEL_BYTES)
                && validFile(
                        new File(directory, "shared_vocabulary.json"),
                        MAX_VOCABULARY_BYTES);
    }

    @Override
    public void close() {
        executor.shutdownNow();
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

    private static boolean validFile(File file, long maximumBytes) {
        long bytes = file.length();
        return file.isFile() && bytes > 0 && bytes <= maximumBytes;
    }
}
