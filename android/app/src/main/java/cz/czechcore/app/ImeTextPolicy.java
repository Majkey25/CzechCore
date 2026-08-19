package cz.czechcore.app;

import android.text.InputType;
import android.view.inputmethod.EditorInfo;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class ImeTextPolicy {
    private static final int MAX_CONTEXT_CHARS = 480;
    private static final Pattern ADJACENT_DUPLICATE =
            Pattern.compile("(?<!\\S)(\\S+)(\\s+)\\1(?=\\s|$)");

    private ImeTextPolicy() {}

    static Window currentSentence(String beforeCursor) {
        int end = beforeCursor.length();
        while (end > 0 && Character.isWhitespace(beforeCursor.charAt(end - 1))) {
            end--;
        }
        int start = Math.max(0, end - MAX_CONTEXT_CHARS);
        for (int index = end - 2; index >= start; index--) {
            char value = beforeCursor.charAt(index);
            if (value == '.' || value == '!' || value == '?' || value == '\n') {
                start = index + 1;
                break;
            }
        }
        if (start < end && Character.isLowSurrogate(beforeCursor.charAt(start))) {
            start++;
        }
        while (start < end && Character.isWhitespace(beforeCursor.charAt(start))) {
            start++;
        }
        return new Window(beforeCursor.substring(start, end), beforeCursor.substring(end));
    }

    static boolean allowsCorrection(int inputType, int imeOptions) {
        if ((imeOptions & EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING) != 0
                || (inputType & InputType.TYPE_MASK_CLASS) != InputType.TYPE_CLASS_TEXT) {
            return false;
        }
        int variation = inputType & InputType.TYPE_MASK_VARIATION;
        return variation != InputType.TYPE_TEXT_VARIATION_PASSWORD
                && variation != InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                && variation != InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD
                && variation != InputType.TYPE_TEXT_VARIATION_URI
                && variation != InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
                && variation != InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS;
    }

    static boolean isAutoSafe(String source, String candidate) {
        String repair = automaticRepair(source);
        return repair != null && repair.equals(candidate);
    }

    static String automaticRepair(String source) {
        Matcher matcher = ADJACENT_DUPLICATE.matcher(source);
        if (!matcher.find()) {
            return null;
        }
        String repaired = source.substring(0, matcher.start())
                + matcher.group(1)
                + source.substring(matcher.end());
        return matcher.find() ? null : repaired;
    }

    static boolean matches(String beforeCursor, Window window) {
        return beforeCursor.endsWith(window.text + window.trailing);
    }

    static final class Window {
        private final String text;
        private final String trailing;

        Window(String text, String trailing) {
            this.text = Objects.requireNonNull(text);
            this.trailing = Objects.requireNonNull(trailing);
        }

        String text() {
            return text;
        }

        String trailing() {
            return trailing;
        }
    }
}
