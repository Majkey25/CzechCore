# Architecture

## Runtime flow

```text
original text
    -> UDPipe sentence spans + exact token ranges
    -> exact-adjacent-repeat rule (mechanical only)
    -> WordPiece encoding
    -> four-beam Transformer generation
    -> unchanged-sentence scoring
    -> relative confidence normalization
    -> protected-literal + rewrite-ratio safety gate
    -> Unicode diff and edit classification
    -> suggested_text / confidence-gated output_text
```

## Modules

| Module | Responsibility |
| --- | --- |
| `assets.py` | Pinned model identifiers, cache discovery, HTTPS download, UDPipe SHA-256 validation |
| `tokenizer.py` | UDPipe loading, sentence segmentation, token forms, original Unicode ranges |
| `backend.py` | Explicit WordPiece loading, Transformer inference, unchanged candidate, relative scores |
| `core.py` | Immutable result types, edit alignment/application, mechanical classification/protection |
| `engine.py` | Sentence orchestration, abstention policy, suggestion/autocorrect behavior |
| `cli.py` | User-facing download/check/version commands and one-time JSON serialization |
| `benchmark.py` | JSONL boundary validation and sentence-exact metrics |

Dependencies flow inward through typed protocols: `engine.py` consumes a sentence
tokenizer and correction backend. Unit tests can verify policy without loading a
model; release tests use the real assets.

The top-level package and CLI import the engine lazily. Version and download
commands therefore do not initialize PyTorch/Transformers; requesting
`czechcore.CzechCore` or running correction loads the ML runtime on demand.

## Why the tokenizer loader is explicit

The pinned model contains a WordPiece `tokenizer.json` but legacy metadata names
`BartTokenizer`. Under the verified Transformers version, `AutoTokenizer` selected
a byte-level backend that removed spaces and corrupted Czech characters.

`TransformerBackend` therefore loads `PreTrainedTokenizerFast` directly and fails
unless the backend model class is `WordPiece`. This is a checked invariant, not a
compatibility fallback.

## Sentence boundaries

UDPipe creates a fresh tokenizer for each call. For every sentence, CzechCore
records the first and last `TokenRange`, then joins token forms with spaces for the
neural model. Whitespace between sentences remains outside edits and is preserved.

Sentences above the model position limit are not truncated. They receive
`sentence_too_long` and remain unchanged.

## Candidate policy

The neural backend returns unique hypotheses ordered by model score. The unchanged
normalized sentence is always included. `engine.py` accepts only the top candidate
and applies these independent gates:

1. candidate differs from the original sentence;
2. relative confidence reaches `0.25` for a suggestion;
3. protected literals are present unchanged;
4. changed-character ratio is at most `0.35`;
5. autocorrect additionally reaches the caller's `min_confidence`.

All edits from one sentence share the same candidate confidence and application
state. This prevents partial neural rewrites.

## Asset lifecycle

```text
czechcore download
    -> UDPipe raw HTTPS download
    -> SHA-256 verification
    -> atomic cache replacement
    -> Hugging Face snapshot_download at pinned Git revision

CzechCore()
    -> local hash-verified UDPipe lookup
    -> local-only Transformer snapshot lookup
    -> no network access
```

Default cache locations:

- Windows UDPipe: `%LOCALAPPDATA%\CzechCore`
- Linux/macOS UDPipe: `$XDG_CACHE_HOME/czechcore` or `~/.cache/czechcore`
- Transformer: standard Hugging Face cache unless a cache directory is supplied

Model/data files are not part of the MIT-licensed wheel.

## Trust boundaries

| Boundary | Control |
| --- | --- |
| User text -> tokenizer | Unicode strings; invalid confidence rejected |
| UDPipe download -> cache | HTTPS, pinned URL, SHA-256, temporary file, atomic replace |
| Hugging Face -> runtime | Pinned revision, selected files, safetensors, local-only load, no remote code |
| Neural output -> user text | Confidence, protected literals, rewrite ratio, exact source validation |
| JSONL -> benchmark | Required non-empty string fields validated per line |

## Performance characteristics

- Model and UDPipe load once per `CzechCore` instance.
- Inference is synchronous and CPU by default.
- Four beams trade latency for candidate quality.
- Each accepted sentence uses `SequenceMatcher`; sentence sizes are bounded by the
  model position limit.
- Text with many sentences is processed sequentially in `0.1.x`.

## Platform adapters

Windows and Android integrations must remain thin consumers of the structured
API. They must not reimplement correction logic. Required adapter concerns:

- convert Python/code-point offsets to platform UTF-16 units;
- schedule blocking inference off UI threads;
- preserve sentence-atomic application;
- expose suggestions by default and autocorrect only as an explicit setting;
- bundle or provision correctly licensed model assets;
- measure device memory, startup, and latency after quantization.
