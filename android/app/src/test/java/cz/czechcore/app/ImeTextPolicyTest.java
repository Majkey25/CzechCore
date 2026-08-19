package cz.czechcore.app;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import android.text.InputType;
import android.view.inputmethod.EditorInfo;
import org.junit.Test;

public final class ImeTextPolicyTest {
    @Test
    public void extractsOnlyCurrentSentenceAndKeepsTrailingSpace() {
        ImeTextPolicy.Window window =
                ImeTextPolicy.currentSentence("Dřív bylo dobře. Když přišel domů šel spát. ");

        assertEquals("Když přišel domů šel spát.", window.text());
        assertEquals(" ", window.trailing());
    }

    @Test
    public void keepsEmojiInTheExactUtf16Window() {
        ImeTextPolicy.Window window = ImeTextPolicy.currentSentence("Hotovo. 👨‍👩‍👧 přišly domů");

        assertEquals("👨‍👩‍👧 přišly domů", window.text());
        assertEquals("", window.trailing());
    }

    @Test
    public void disablesInferenceForPasswordsAndNoLearningFields() {
        assertFalse(ImeTextPolicy.allowsCorrection(
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD, 0));
        assertFalse(ImeTextPolicy.allowsCorrection(
                InputType.TYPE_CLASS_TEXT,
                EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING));
        assertFalse(ImeTextPolicy.allowsCorrection(
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI, 0));
        assertFalse(ImeTextPolicy.allowsCorrection(
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS, 0));
        assertTrue(ImeTextPolicy.allowsCorrection(
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES, 0));
    }

    @Test
    public void automaticModeOnlyAcceptsExactAdjacentDuplicateRemoval() {
        assertEquals("To je problém.", ImeTextPolicy.automaticRepair("To je je problém."));
        assertNull(ImeTextPolicy.automaticRepair("Když přišel domů šel spát."));
        assertTrue(ImeTextPolicy.isAutoSafe("To je je problém.", "To je problém."));
        assertFalse(ImeTextPolicy.isAutoSafe(
                "Když přišel domů šel spát.", "Když přišel domů, šel spát."));
        assertFalse(ImeTextPolicy.isAutoSafe("Muži přišly domů.", "Muži přišli domů."));
    }

    @Test
    public void staleSourceMustStillMatchBeforeCursor() {
        ImeTextPolicy.Window window = new ImeTextPolicy.Window("Muži přišly domů.", " ");

        assertTrue(ImeTextPolicy.matches("Text. Muži přišly domů. ", window));
        assertFalse(ImeTextPolicy.matches("Text. Muži přišly rychle domů. ", window));
    }
}
