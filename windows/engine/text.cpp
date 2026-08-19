#include "text.h"

#include <windows.h>

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cwctype>
#include <regex>
#include <stdexcept>
#include <utility>

namespace czechcore {
namespace {

constexpr size_t kMaxModelTokens = 256;
constexpr size_t kMaxWordCodePoints = 100;

void append_utf8(std::string& output, uint32_t code_point) {
  if (code_point <= 0x7f) {
    output.push_back(static_cast<char>(code_point));
  } else if (code_point <= 0x7ff) {
    output.push_back(static_cast<char>(0xc0 | (code_point >> 6)));
    output.push_back(static_cast<char>(0x80 | (code_point & 0x3f)));
  } else if (code_point <= 0xffff) {
    output.push_back(static_cast<char>(0xe0 | (code_point >> 12)));
    output.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3f)));
    output.push_back(static_cast<char>(0x80 | (code_point & 0x3f)));
  } else if (code_point <= 0x10ffff) {
    output.push_back(static_cast<char>(0xf0 | (code_point >> 18)));
    output.push_back(static_cast<char>(0x80 | ((code_point >> 12) & 0x3f)));
    output.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3f)));
    output.push_back(static_cast<char>(0x80 | (code_point & 0x3f)));
  } else {
    throw std::invalid_argument("invalid Unicode code point");
  }
}

class JsonStringArrayParser final {
 public:
  explicit JsonStringArrayParser(std::string_view input) : input_(input) {}

  std::vector<std::string> parse() {
    skip_space();
    expect('[');
    skip_space();
    std::vector<std::string> values;
    if (consume(']')) {
      return values;
    }
    while (true) {
      values.push_back(parse_string());
      skip_space();
      if (consume(']')) {
        break;
      }
      expect(',');
      skip_space();
    }
    skip_space();
    if (position_ != input_.size()) {
      throw std::invalid_argument("trailing vocabulary JSON data");
    }
    return values;
  }

 private:
  std::string parse_string() {
    expect('"');
    std::string output;
    while (position_ < input_.size()) {
      const unsigned char value = static_cast<unsigned char>(input_[position_++]);
      if (value == '"') {
        return output;
      }
      if (value < 0x20) {
        throw std::invalid_argument("control character in vocabulary JSON");
      }
      if (value != '\\') {
        output.push_back(static_cast<char>(value));
        continue;
      }
      if (position_ >= input_.size()) {
        throw std::invalid_argument("incomplete vocabulary JSON escape");
      }
      const char escaped = input_[position_++];
      switch (escaped) {
        case '"':
        case '\\':
        case '/':
          output.push_back(escaped);
          break;
        case 'b':
          output.push_back('\b');
          break;
        case 'f':
          output.push_back('\f');
          break;
        case 'n':
          output.push_back('\n');
          break;
        case 'r':
          output.push_back('\r');
          break;
        case 't':
          output.push_back('\t');
          break;
        case 'u':
          append_utf8(output, parse_hex_quad());
          break;
        default:
          throw std::invalid_argument("invalid vocabulary JSON escape");
      }
    }
    throw std::invalid_argument("unterminated vocabulary JSON string");
  }

  uint32_t parse_hex_quad() {
    if (position_ + 4 > input_.size()) {
      throw std::invalid_argument("incomplete vocabulary Unicode escape");
    }
    uint32_t value = 0;
    for (int index = 0; index < 4; ++index) {
      const char digit = input_[position_++];
      value <<= 4;
      if (digit >= '0' && digit <= '9') {
        value += static_cast<uint32_t>(digit - '0');
      } else if (digit >= 'a' && digit <= 'f') {
        value += static_cast<uint32_t>(digit - 'a' + 10);
      } else if (digit >= 'A' && digit <= 'F') {
        value += static_cast<uint32_t>(digit - 'A' + 10);
      } else {
        throw std::invalid_argument("invalid vocabulary Unicode escape");
      }
    }
    return value;
  }

  void skip_space() {
    while (position_ < input_.size()
           && std::isspace(static_cast<unsigned char>(input_[position_])) != 0) {
      ++position_;
    }
  }

  bool consume(char value) {
    if (position_ < input_.size() && input_[position_] == value) {
      ++position_;
      return true;
    }
    return false;
  }

  void expect(char value) {
    if (!consume(value)) {
      throw std::invalid_argument("invalid vocabulary JSON array");
    }
  }

  std::string_view input_;
  size_t position_ = 0;
};

bool is_punctuation(wchar_t value) {
  if ((value >= L'!' && value <= L'/') || (value >= L':' && value <= L'@')
      || (value >= L'[' && value <= L'`') || (value >= L'{' && value <= L'~')) {
    return true;
  }
  WORD type = 0;
  return GetStringTypeW(CT_CTYPE1, &value, 1, &type) != 0 && (type & C1_PUNCT) != 0;
}

bool is_control(wchar_t value) {
  if (value == L'\t' || value == L'\n' || value == L'\r') {
    return false;
  }
  WORD type = 0;
  return value == L'\0'
      || (GetStringTypeW(CT_CTYPE1, &value, 1, &type) != 0 && (type & C1_CNTRL) != 0);
}

size_t code_point_count(std::wstring_view value) {
  size_t count = 0;
  for (size_t index = 0; index < value.size(); ++index) {
    if (IS_HIGH_SURROGATE(value[index]) && index + 1 < value.size()
        && IS_LOW_SURROGATE(value[index + 1])) {
      ++index;
    }
    ++count;
  }
  return count;
}

size_t previous_code_point(std::wstring_view value, size_t index) {
  --index;
  if (index > 0 && IS_LOW_SURROGATE(value[index]) && IS_HIGH_SURROGATE(value[index - 1])) {
    --index;
  }
  return index;
}

std::vector<std::wstring> basic_tokens(std::wstring_view text) {
  std::vector<std::wstring> tokens;
  std::wstring current;
  const auto flush = [&tokens, &current]() {
    if (!current.empty()) {
      tokens.push_back(std::move(current));
      current.clear();
    }
  };
  for (size_t index = 0; index < text.size(); ++index) {
    const wchar_t value = text[index];
    if (is_control(value)) {
      continue;
    }
    if (std::iswspace(value) != 0) {
      flush();
      continue;
    }
    if (is_punctuation(value)) {
      flush();
      tokens.emplace_back(1, value);
      continue;
    }
    current.push_back(value);
    if (IS_HIGH_SURROGATE(value) && index + 1 < text.size()
        && IS_LOW_SURROGATE(text[index + 1])) {
      current.push_back(text[++index]);
    }
  }
  flush();
  return tokens;
}

}  // namespace

std::wstring utf8_to_utf16(std::string_view value) {
  if (value.empty()) {
    return {};
  }
  const int size = MultiByteToWideChar(
      CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0);
  if (size <= 0) {
    throw std::invalid_argument("invalid UTF-8 text");
  }
  std::wstring result(static_cast<size_t>(size), L'\0');
  if (MultiByteToWideChar(
          CP_UTF8,
          MB_ERR_INVALID_CHARS,
          value.data(),
          static_cast<int>(value.size()),
          result.data(),
          size)
      != size) {
    throw std::runtime_error("UTF-8 conversion failed");
  }
  return result;
}

std::string utf16_to_utf8(std::wstring_view value) {
  if (value.empty()) {
    return {};
  }
  const int size = WideCharToMultiByte(
      CP_UTF8,
      WC_ERR_INVALID_CHARS,
      value.data(),
      static_cast<int>(value.size()),
      nullptr,
      0,
      nullptr,
      nullptr);
  if (size <= 0) {
    throw std::invalid_argument("invalid UTF-16 text");
  }
  std::string result(static_cast<size_t>(size), '\0');
  if (WideCharToMultiByte(
          CP_UTF8,
          WC_ERR_INVALID_CHARS,
          value.data(),
          static_cast<int>(value.size()),
          result.data(),
          size,
          nullptr,
          nullptr)
      != size) {
    throw std::runtime_error("UTF-16 conversion failed");
  }
  return result;
}

std::optional<std::string> remove_adjacent_duplicate(std::string_view source) {
  struct Span {
    size_t start;
    size_t end;
  };
  std::vector<Span> words;
  size_t position = 0;
  while (position < source.size()) {
    while (position < source.size()
           && std::isspace(static_cast<unsigned char>(source[position])) != 0) {
      ++position;
    }
    const size_t start = position;
    while (position < source.size()
           && std::isspace(static_cast<unsigned char>(source[position])) == 0) {
      ++position;
    }
    if (start != position) {
      words.push_back({start, position});
    }
  }

  std::optional<std::string> repaired;
  for (size_t index = 1; index < words.size(); ++index) {
    const auto first = source.substr(words[index - 1].start, words[index - 1].end - words[index - 1].start);
    const auto second = source.substr(words[index].start, words[index].end - words[index].start);
    if (first != second) {
      continue;
    }
    if (repaired.has_value()) {
      return std::nullopt;
    }
    repaired = std::string(source.substr(0, words[index - 1].end))
        + std::string(source.substr(words[index].end));
  }
  return repaired;
}

bool preserves_protected_text(std::string_view source, std::string_view candidate) {
  static const std::vector<std::regex> patterns = {
      std::regex(R"(https?://[^\s<>()\[\]{}]+)"),
      std::regex(R"([A-Za-z0-9_.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)"),
      std::regex(R"(v?[0-9]+(?:\.[0-9]+){2,})")};
  const std::string source_text(source);
  const std::string candidate_text(candidate);
  for (const std::regex& pattern : patterns) {
    for (std::sregex_iterator match(source_text.begin(), source_text.end(), pattern), end;
         match != end;
         ++match) {
      std::string literal = match->str();
      while (!literal.empty()
             && std::string_view(".,;:!?").find(literal.back()) != std::string_view::npos) {
        literal.pop_back();
      }
      if (literal.empty()) {
        continue;
      }
      size_t source_count = 0;
      size_t candidate_count = 0;
      for (size_t offset = 0; (offset = source_text.find(literal, offset)) != std::string::npos;
           offset += literal.size()) {
        ++source_count;
      }
      for (size_t offset = 0;
           (offset = candidate_text.find(literal, offset)) != std::string::npos;
           offset += literal.size()) {
        ++candidate_count;
      }
      if (candidate_count < source_count) {
        return false;
      }
    }
  }
  return true;
}

WordPieceTokenizer WordPieceTokenizer::from_json(std::string_view json) {
  std::vector<std::string> values = JsonStringArrayParser(json).parse();
  return WordPieceTokenizer(std::unordered_set<std::string>(values.begin(), values.end()));
}

WordPieceTokenizer::WordPieceTokenizer(std::unordered_set<std::string> vocabulary)
    : vocabulary_(std::move(vocabulary)) {
  for (const std::string_view required : {"[CLS]", "[SEP]", "[UNK]"}) {
    if (!vocabulary_.contains(std::string(required))) {
      throw std::invalid_argument("missing required vocabulary token");
    }
  }
}

std::vector<std::string> WordPieceTokenizer::encode(std::string_view text) const {
  std::vector<std::string> output{"[CLS]"};
  for (const std::wstring& word : basic_tokens(utf8_to_utf16(text))) {
    std::vector<std::string> pieces = word_pieces(word);
    if (output.size() + pieces.size() + 1 > kMaxModelTokens) {
      throw std::invalid_argument("input exceeds model position limit");
    }
    output.insert(output.end(), pieces.begin(), pieces.end());
  }
  output.emplace_back("[SEP]");
  return output;
}

std::string WordPieceTokenizer::decode(const std::vector<std::string>& tokens) const {
  std::string output;
  for (const std::string& token : tokens) {
    if (token == "[PAD]" || token == "[CLS]" || token == "[SEP]" || token == "[MASK]") {
      continue;
    }
    if (token.starts_with("##")) {
      output += token.substr(2);
    } else if (is_punctuation_token(token)) {
      output += token;
    } else {
      if (!output.empty()) {
        output.push_back(' ');
      }
      output += token;
    }
  }
  return output;
}

std::vector<std::string> WordPieceTokenizer::word_pieces(std::wstring_view word) const {
  const std::string whole = utf16_to_utf8(word);
  if (vocabulary_.contains(whole)) {
    return {whole};
  }
  if (code_point_count(word) > kMaxWordCodePoints) {
    return {"[UNK]"};
  }

  std::vector<std::string> pieces;
  size_t start = 0;
  while (start < word.size()) {
    std::optional<std::pair<std::string, size_t>> matched;
    size_t end = word.size();
    while (end > start) {
      std::string candidate = utf16_to_utf8(word.substr(start, end - start));
      if (start != 0) {
        candidate.insert(0, "##");
      }
      if (vocabulary_.contains(candidate)) {
        matched = std::pair(std::move(candidate), end);
        break;
      }
      end = previous_code_point(word, end);
    }
    if (!matched.has_value()) {
      return {"[UNK]"};
    }
    pieces.push_back(std::move(matched->first));
    start = matched->second;
  }
  return pieces;
}

bool WordPieceTokenizer::is_punctuation_token(std::string_view token) const {
  const std::wstring value = utf8_to_utf16(token);
  return code_point_count(value) == 1 && is_punctuation(value.front());
}

}  // namespace czechcore
