package cz.czechcore.app;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public final class LocalCorrectionEngineTest {
    @Rule public final TemporaryFolder temporaryFolder = new TemporaryFolder();

    @Test
    public void requiresAllThreeModelFiles() throws IOException {
        File directory = temporaryFolder.newFolder("model");
        assertFalse(LocalCorrectionEngine.hasModel(directory));

        writeByte(new File(directory, "config.json"));
        writeByte(new File(directory, "model.bin"));
        assertFalse(LocalCorrectionEngine.hasModel(directory));

        writeByte(new File(directory, "shared_vocabulary.json"));
        assertTrue(LocalCorrectionEngine.hasModel(directory));
    }

    @Test
    public void rejectsEmptyAndOversizedModelFiles() throws IOException {
        File directory = temporaryFolder.newFolder("bounded-model");
        writeByte(new File(directory, "config.json"));
        writeByte(new File(directory, "shared_vocabulary.json"));
        File model = new File(directory, "model.bin");

        assertTrue(model.createNewFile());
        assertFalse(LocalCorrectionEngine.hasModel(directory));
        try (RandomAccessFile output = new RandomAccessFile(model, "rw")) {
            output.setLength(512L * 1024 * 1024 + 1);
        }
        assertFalse(LocalCorrectionEngine.hasModel(directory));
    }

    private static void writeByte(File file) throws IOException {
        try (FileOutputStream output = new FileOutputStream(file)) {
            output.write(1);
        }
    }
}
