package cz.czechcore.app;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class ProtectedTextTest {
    @Test
    public void acceptsCorrectionThatKeepsTechnicalLiterals() {
        assertTrue(ProtectedText.isSafe(
                "Projekt CzechCore použival verzi v1.2.3.",
                "Projekt CzechCore používal verzi v1.2.3."));
    }

    @Test
    public void rejectsChangedEmailAndVersion() {
        assertFalse(ProtectedText.isSafe(
                "Kontakt majkey25@example.cz, verze v1.2.3.",
                "Kontakt majkey25@ example. cz, verze v1. 2. 3."));
    }
}
