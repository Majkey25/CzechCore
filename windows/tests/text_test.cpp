#include "text.h"

#include <stdexcept>
#include <string>
#include <vector>

namespace {

void require(bool condition) {
  if (!condition) {
    throw std::runtime_error("Windows text test failed");
  }
}

}  // namespace

int main() {
  using czechcore::WordPieceTokenizer;

  const std::string unicode = "Příliš 👨‍👩‍👧";
  require(czechcore::utf16_to_utf8(czechcore::utf8_to_utf16(unicode)) == unicode);

  const auto repair = czechcore::remove_adjacent_duplicate("To je je problém.");
  require(repair.has_value());
  require(*repair == "To je problém.");
  require(!czechcore::remove_adjacent_duplicate("Když přišel domů.").has_value());

  const auto tokenizer = WordPieceTokenizer::from_json(
      R"(["[PAD]","[CLS]","[SEP]","[UNK]","Když","přišel","domů","šel","spát",".",",","pro","##blém"])");
  require(tokenizer.encode("Když přišel domů šel spát.") ==
          std::vector<std::string>({"[CLS]", "Když", "přišel", "domů", "šel", "spát", ".", "[SEP]"}));
  require(tokenizer.encode("problém, neznámé") ==
          std::vector<std::string>({"[CLS]", "pro", "##blém", ",", "[UNK]", "[SEP]"}));
  require(tokenizer.decode({"Když", "přišel", "domů", ",", "šel", "spát", "."}) ==
          "Když přišel domů, šel spát.");

  require(czechcore::preserves_protected_text(
      "Kontakt majkey25@example.cz, verze v1.2.3.",
      "Kontakt majkey25@example.cz, verze v1.2.3."));
  require(!czechcore::preserves_protected_text(
      "Kontakt majkey25@example.cz, verze v1.2.3.",
      "Kontakt majkey25@ example. cz, verze v1. 2. 3."));

  return 0;
}
