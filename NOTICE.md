# Third-party assets

CzechCore source code does not contain the following model assets. The explicit
`czechcore download` command retrieves them for local use.

## Czech grammar correction model

- Asset: `ufal/transformer-base-geccc-mate`
- Authors: Petr Pechman, Milan Straka, Jana Straková, Jakub Náplava
- Source: <https://huggingface.co/ufal/transformer-base-geccc-mate>
- License: CC BY-NC-SA 4.0
- Pinned revision: `86338eff14fd318c3e8875c911f0778563b4b3b7`
- Paper: <https://doi.org/10.1007/978-3-032-02551-7_7>

## Czech UDPipe model

- Asset: `czech-pdt-ud-2.5-191206.udpipe`
- Source repository: <https://github.com/ufal/tsd2025-gec>
- License stated by the upstream project for UDPipe models: CC BY-NC-SA 4.0
- SHA-256: `8ced138bf1c2121cf03d2494f08c663a8b27b5218fb9c322064a7d943ba02266`

## UDPipe bindings

- Package: `ufal.udpipe`
- Source: <https://pypi.org/project/ufal.udpipe/>
- License: Mozilla Public License 2.0

The default model stack is not licensed for commercial use. Commercial
distribution requires separately licensed or replacement model assets.
