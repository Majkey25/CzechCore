package cz.czechcore.app;

enum CorrectionMode {
    OFF("off"),
    UNDERLINE("underline"),
    CONFIRM("confirm"),
    AUTOMATIC("automatic");

    static final String PREFERENCES = "czechcore_ime";
    static final String PREFERENCE_KEY = "correction_mode";

    private final String storedValue;

    CorrectionMode(String storedValue) {
        this.storedValue = storedValue;
    }

    String storedValue() {
        return storedValue;
    }

    CorrectionMode next() {
        CorrectionMode[] modes = values();
        return modes[(ordinal() + 1) % modes.length];
    }

    static CorrectionMode fromStored(String value) {
        for (CorrectionMode mode : values()) {
            if (mode.storedValue.equals(value)) {
                return mode;
            }
        }
        return UNDERLINE;
    }
}
