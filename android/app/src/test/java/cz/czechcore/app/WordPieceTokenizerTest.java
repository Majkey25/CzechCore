package cz.czechcore.app;

import static org.junit.Assert.assertEquals;

import java.util.Collections;
import java.util.List;
import org.junit.Test;

public final class WordPieceTokenizerTest {
    private static final List<String> VOCABULARY = List.of(
            "[PAD]", "[CLS]", "[SEP]", "[UNK]", "Když", "přišel", "domů",
            "šel", "spát", ".", ",", "pro", "##blém");

    @Test
    public void encodesCzechWordsPunctuationAndSpecialTokens() {
        WordPieceTokenizer tokenizer = new WordPieceTokenizer(VOCABULARY);

        assertEquals(
                List.of("[CLS]", "Když", "přišel", "domů", "šel", "spát", ".", "[SEP]"),
                tokenizer.encode("Když přišel domů šel spát."));
    }

    @Test
    public void usesLongestWordPieceAndDecodesPunctuation() {
        WordPieceTokenizer tokenizer = new WordPieceTokenizer(VOCABULARY);

        assertEquals(
                List.of("[CLS]", "pro", "##blém", ",", "[UNK]", "[SEP]"),
                tokenizer.encode("problém, neznámé"));
        assertEquals(
                "Když přišel domů, šel spát.",
                tokenizer.decode(List.of("Když", "přišel", "domů", ",", "šel", "spát", ".")));
    }

    @Test(expected = IllegalArgumentException.class)
    public void rejectsInputAboveModelPositionLimit() {
        WordPieceTokenizer tokenizer = new WordPieceTokenizer(VOCABULARY);

        tokenizer.encode(String.join(" ", Collections.nCopies(255, "Když")));
    }
}
