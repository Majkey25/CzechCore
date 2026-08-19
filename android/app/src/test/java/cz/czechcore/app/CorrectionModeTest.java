package cz.czechcore.app;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public final class CorrectionModeTest {
    @Test
    public void unknownStoredValueFallsBackToUnderline() {
        assertEquals(CorrectionMode.UNDERLINE, CorrectionMode.fromStored("invalid"));
        assertEquals(CorrectionMode.AUTOMATIC, CorrectionMode.fromStored("automatic"));
    }

    @Test
    public void cyclesThroughEveryUserMode() {
        assertEquals(CorrectionMode.CONFIRM, CorrectionMode.UNDERLINE.next());
        assertEquals(CorrectionMode.AUTOMATIC, CorrectionMode.CONFIRM.next());
        assertEquals(CorrectionMode.OFF, CorrectionMode.AUTOMATIC.next());
        assertEquals(CorrectionMode.UNDERLINE, CorrectionMode.OFF.next());
    }
}
