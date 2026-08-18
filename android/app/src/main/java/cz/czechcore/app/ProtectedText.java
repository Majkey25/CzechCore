package cz.czechcore.app;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class ProtectedText {
    private static final String TRAILING_PUNCTUATION = ".,;:!?";
    private static final List<Pattern> PATTERNS = List.of(
            Pattern.compile("https?://[^\\s<>()\\[\\]{}]+"),
            Pattern.compile("(?<![\\w.+-])[\\w.+-]+@[\\w-]+(?:\\.[\\w-]+)+(?![\\w-])"),
            Pattern.compile("(?<!\\w)[A-Za-z]:\\\\[^\\r\\n\\t<>\"|?*]+"),
            Pattern.compile("(?<!\\w)v?\\d+(?:\\.\\d+){2,}(?!\\w)"),
            Pattern.compile("(?<!\\d)\\d{1,2}\\.\\s?\\d{1,2}\\.\\s?\\d{4}(?!\\d)"),
            Pattern.compile("(?<!\\d)(?:\\+?\\d[\\d ]{7,}\\d)(?!\\d)"),
            Pattern.compile(
                    "(?<!\\w)[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]{2,}(?!\\w)",
                    Pattern.UNICODE_CASE),
            Pattern.compile(
                    "(?<!\\w)(?:[A-Za-z][A-Za-z0-9_]*(?:\\+\\+|#)[A-Za-z0-9_]*|"
                            + "[A-Za-z0-9_]*[a-z][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*)(?!\\w)"));

    private ProtectedText() {}

    static boolean isSafe(String source, String candidate) {
        if (!source.isEmpty() && candidate.isEmpty()) {
            return false;
        }
        for (String literal : literals(source)) {
            if (count(candidate, literal) < count(source, literal)) {
                return false;
            }
        }
        return true;
    }

    private static List<String> literals(String text) {
        List<Literal> matches = new ArrayList<>();
        for (Pattern pattern : PATTERNS) {
            Matcher matcher = pattern.matcher(text);
            while (matcher.find()) {
                String value = stripTrailingPunctuation(matcher.group());
                if (!value.isEmpty()) {
                    matches.add(new Literal(matcher.start(), matcher.start() + value.length(), value));
                }
            }
        }
        matches.sort(Comparator.comparingInt(Literal::start)
                .thenComparing(Comparator.comparingInt(Literal::end).reversed()));

        List<String> result = new ArrayList<>();
        int previousEnd = 0;
        for (Literal literal : matches) {
            if (literal.start() < previousEnd) {
                continue;
            }
            result.add(literal.value());
            previousEnd = literal.end();
        }
        return result;
    }

    private static String stripTrailingPunctuation(String value) {
        int end = value.length();
        while (end > 0 && TRAILING_PUNCTUATION.indexOf(value.charAt(end - 1)) >= 0) {
            end--;
        }
        return value.substring(0, end);
    }

    private static int count(String text, String value) {
        int matches = 0;
        int offset = 0;
        while ((offset = text.indexOf(value, offset)) >= 0) {
            matches++;
            offset += value.length();
        }
        return matches;
    }

    private static final class Literal {
        private final int start;
        private final int end;
        private final String value;

        private Literal(int start, int end, String value) {
            this.start = start;
            this.end = end;
            this.value = value;
        }

        private int start() {
            return start;
        }

        private int end() {
            return end;
        }

        private String value() {
            return value;
        }
    }
}
