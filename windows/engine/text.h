#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

namespace czechcore {

std::wstring utf8_to_utf16(std::string_view value);
std::string utf16_to_utf8(std::wstring_view value);
std::optional<std::string> remove_adjacent_duplicate(std::string_view source);
bool preserves_protected_text(std::string_view source, std::string_view candidate);

class WordPieceTokenizer final {
 public:
  static WordPieceTokenizer from_json(std::string_view json);

  std::vector<std::string> encode(std::string_view text) const;
  std::string decode(const std::vector<std::string>& tokens) const;

 private:
  explicit WordPieceTokenizer(std::unordered_set<std::string> vocabulary);

  std::vector<std::string> word_pieces(std::wstring_view word) const;
  bool is_punctuation_token(std::string_view token) const;

  std::unordered_set<std::string> vocabulary_;
};

}  // namespace czechcore
