package cz.czechcore.app;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONException;

public final class WordPieceTokenizer {
    private static final String UNKNOWN = "[UNK]";
    private static final int MAX_WORD_CODE_POINTS = 100;
    private static final int MAX_MODEL_TOKENS = 256;

    private final Set<String> vocabulary;

    public WordPieceTokenizer(List<String> vocabulary) {
        this.vocabulary = Set.copyOf(vocabulary);
        for (String required : List.of("[CLS]", "[SEP]", UNKNOWN)) {
            if (!this.vocabulary.contains(required)) {
                throw new IllegalArgumentException("missing vocabulary token: " + required);
            }
        }
    }

    public static WordPieceTokenizer fromJson(String json) {
        try {
            JSONArray array = new JSONArray(json);
            List<String> vocabulary = new ArrayList<>(array.length());
            for (int index = 0; index < array.length(); index++) {
                vocabulary.add(array.getString(index));
            }
            return new WordPieceTokenizer(vocabulary);
        } catch (JSONException error) {
            throw new IllegalArgumentException("invalid vocabulary JSON", error);
        }
    }

    public List<String> encode(String text) {
        if (text.codePointCount(0, text.length())
                > MAX_MODEL_TOKENS * MAX_WORD_CODE_POINTS) {
            throw new IllegalArgumentException("input exceeds model position limit");
        }
        List<String> output = new ArrayList<>();
        output.add("[CLS]");
        for (String word : basicTokens(text)) {
            List<String> pieces = wordPieces(word);
            if (output.size() + pieces.size() + 1 > MAX_MODEL_TOKENS) {
                throw new IllegalArgumentException("input exceeds model position limit");
            }
            output.addAll(pieces);
        }
        output.add("[SEP]");
        return output;
    }

    public String decode(List<String> tokens) {
        StringBuilder output = new StringBuilder();
        for (String token : tokens) {
            if (token.equals("[PAD]")
                    || token.equals("[CLS]")
                    || token.equals("[SEP]")
                    || token.equals("[MASK]")) {
                continue;
            }
            if (token.startsWith("##")) {
                output.append(token.substring(2));
            } else if (isPunctuationToken(token)) {
                output.append(token);
            } else {
                if (output.length() > 0) {
                    output.append(' ');
                }
                output.append(token);
            }
        }
        return output.toString();
    }

    private List<String> wordPieces(String word) {
        if (vocabulary.contains(word)) {
            return List.of(word);
        }
        int[] codePoints = word.codePoints().toArray();
        if (codePoints.length > MAX_WORD_CODE_POINTS) {
            return List.of(UNKNOWN);
        }

        List<String> pieces = new ArrayList<>();
        int start = 0;
        while (start < codePoints.length) {
            String matched = null;
            int end = codePoints.length;
            while (end > start) {
                String value = new String(codePoints, start, end - start);
                String candidate = start == 0 ? value : "##" + value;
                if (vocabulary.contains(candidate)) {
                    matched = candidate;
                    break;
                }
                end--;
            }
            if (matched == null) {
                return List.of(UNKNOWN);
            }
            pieces.add(matched);
            start = end;
        }
        return pieces;
    }

    private static List<String> basicTokens(String text) {
        StringBuilder normalized = new StringBuilder();
        text.codePoints().forEach(codePoint -> {
            if (isControl(codePoint)) {
                return;
            }
            if (Character.isWhitespace(codePoint)) {
                normalized.append(' ');
            } else if (isPunctuation(codePoint)) {
                normalized.append(' ').appendCodePoint(codePoint).append(' ');
            } else {
                normalized.appendCodePoint(codePoint);
            }
        });
        String value = normalized.toString().trim();
        return value.isEmpty() ? List.of() : List.of(value.split("\\s+"));
    }

    private static boolean isControl(int codePoint) {
        if (codePoint == '\t' || codePoint == '\n' || codePoint == '\r') {
            return false;
        }
        int type = Character.getType(codePoint);
        return type == Character.CONTROL
                || type == Character.FORMAT
                || codePoint == 0
                || codePoint == 0xFFFD;
    }

    private static boolean isPunctuationToken(String token) {
        return token.codePointCount(0, token.length()) == 1
                && isPunctuation(token.codePointAt(0));
    }

    private static boolean isPunctuation(int codePoint) {
        if ((codePoint >= 33 && codePoint <= 47)
                || (codePoint >= 58 && codePoint <= 64)
                || (codePoint >= 91 && codePoint <= 96)
                || (codePoint >= 123 && codePoint <= 126)) {
            return true;
        }
        return switch (Character.getType(codePoint)) {
            case Character.CONNECTOR_PUNCTUATION,
                    Character.DASH_PUNCTUATION,
                    Character.START_PUNCTUATION,
                    Character.END_PUNCTUATION,
                    Character.INITIAL_QUOTE_PUNCTUATION,
                    Character.FINAL_QUOTE_PUNCTUATION,
                    Character.OTHER_PUNCTUATION -> true;
            default -> false;
        };
    }
}
