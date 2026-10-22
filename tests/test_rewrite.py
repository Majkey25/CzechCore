from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.error import HTTPError

import pytest

from czechcore.core import CorrectionResult
from czechcore.rewrite import HybridRewriter, LocalChatRewriteBackend


class IdentityProofreader:
    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult:
        return CorrectionResult(text, text, text, ())


@dataclass(frozen=True)
class StaticRewriteBackend:
    candidate: str

    def rewrite(self, source: str, proofread: str) -> str:
        return self.candidate


class DroppingMarkerProofreader:
    def __init__(self) -> None:
        self._calls = 0

    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult:
        self._calls += 1
        suggestion = (
            text.replace("https://czechcore.invalid/protected/0", "") if self._calls == 1 else text
        )
        return CorrectionResult(text, suggestion, text, ())


class PostcheckChangingProofreader:
    def __init__(self) -> None:
        self._calls = 0

    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult:
        self._calls += 1
        suggestion = text if self._calls == 1 else text.replace("dobrý", "výborný")
        return CorrectionResult(text, suggestion, text, ())


def test_hybrid_rewriter_returns_explicit_whole_sentence_suggestion() -> None:
    candidate = (
        "Jako jo, je to prakticky nejpoužívanější nástroj, má širší záběr než pip "
        "a je hodně zaměřený na AI."
    )
    rewriter = HybridRewriter(IdentityProofreader(), StaticRewriteBackend(candidate))

    result = rewriter.suggest(
        "jako jo je to prakticky nejpouzivanejsi nastroj na sirsi obsah nez co ma pip "
        "a hodne na ai zamereny",
        protected=("pip",),
    )

    assert result.suggested_text == candidate
    assert result.requires_review
    assert result.warnings == ()


def test_hybrid_rewriter_falls_back_when_number_changes() -> None:
    rewriter = HybridRewriter(
        IdentityProofreader(),
        StaticRewriteBackend("Objednal jsem čtyři kusy za 999 Kč."),
    )
    source = "Objednal jsem 3 kusy za 1 299 Kč."

    result = rewriter.suggest(source)

    assert result.suggested_text == source
    assert result.warnings == ("rewrite_changed_number",)


def test_hybrid_rewriter_preserves_numeric_sign() -> None:
    rewriter = HybridRewriter(
        IdentityProofreader(),
        StaticRewriteBackend("Teplota byla 5 °C."),
    )

    result = rewriter.suggest("Teplota byla -5 °C.")

    assert result.suggested_text == result.original_text
    assert result.warnings == ("rewrite_changed_number",)


def test_hybrid_rewriter_rejects_chat_template_token() -> None:
    rewriter = HybridRewriter(
        IdentityProofreader(),
        StaticRewriteBackend("Opraveno. <|END_OF_TURN_TOKEN|>"),
    )

    result = rewriter.suggest("Opravit.")

    assert result.suggested_text == result.proofread_text
    assert result.warnings == ("rewrite_added_special_token",)


def test_hybrid_rewriter_requires_literal_token_boundary() -> None:
    rewriter = HybridRewriter(
        IdentityProofreader(),
        StaticRewriteBackend("Nástroj pipA funguje."),
    )

    result = rewriter.suggest("Nástroj pip funguje.", protected=("pip",))

    assert result.suggested_text == result.proofread_text
    assert result.warnings == ("rewrite_changed_protected_literal",)


def test_hybrid_rewriter_falls_back_when_explicit_literal_disappears() -> None:
    rewriter = HybridRewriter(
        IdentityProofreader(),
        StaticRewriteBackend("Je to nástroj s širším záběrem."),
    )

    result = rewriter.suggest("Má širší záběr než pip.", protected=("pip",))

    assert result.suggested_text == result.proofread_text
    assert result.warnings == ("rewrite_changed_protected_literal",)


def test_safe_rewrite_can_recover_from_unsafe_proofread_candidate() -> None:
    candidate = "Je to širší nástroj než pip."
    context = DroppingMarkerProofreader()
    rewriter = HybridRewriter(
        IdentityProofreader(),
        StaticRewriteBackend(candidate),
        context_proofreader=context,
    )

    result = rewriter.suggest("Je to nástroj jako pip.", protected=("pip",))

    assert result.suggested_text == candidate
    assert result.warnings == ("context_changed_protected_literal",)


def test_uncalibrated_postcheck_does_not_overwrite_rewrite() -> None:
    candidate = "To je dobrý nástroj."
    rewriter = HybridRewriter(
        PostcheckChangingProofreader(),
        StaticRewriteBackend(candidate),
        context_proofreader=IdentityProofreader(),
    )

    result = rewriter.suggest("to je dobry nastroj")

    assert result.suggested_text == candidate
    assert result.warnings == ("postcheck_disagrees",)


def test_rewrite_endpoint_must_be_local() -> None:
    with pytest.raises(ValueError, match="local HTTP"):
        LocalChatRewriteBackend("https://example.com/v1/chat/completions")


@contextmanager
def _rewrite_server(redirect: str = "") -> Generator[tuple[int, list[bytes]]]:
    requests: list[bytes] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            requests.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(302 if redirect else 200)
            if redirect:
                self.send_header("Location", redirect)
            self.end_headers()
            self.wfile.write(b'{"choices":[{"message":{"content":"Opraveno."}}]}')

        def log_message(self, format: str, *args: object) -> None:
            pass

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield server.server_port, requests
        finally:
            server.shutdown()
            thread.join(timeout=5)


@pytest.mark.parametrize("redirect", [False, True])
def test_loopback_rewrite_bypasses_ambient_proxies_and_refuses_redirects(
    monkeypatch: pytest.MonkeyPatch, redirect: bool
) -> None:
    with _rewrite_server() as (proxy_port, proxy_requests):
        proxy = f"http://127.0.0.1:{proxy_port}"
        for variable in ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
            monkeypatch.setenv(variable, proxy)
        monkeypatch.setenv("NO_PROXY", "")
        monkeypatch.setenv("no_proxy", "")
        with _rewrite_server(proxy if redirect else "") as (port, local_requests):
            backend = LocalChatRewriteBackend(f"http://127.0.0.1:{port}", timeout_seconds=2)
            if redirect:
                with pytest.raises(HTTPError, match="302"):
                    backend.rewrite("Soukromý text.", "Návrh.")
            else:
                assert backend.rewrite("Soukromý text.", "Návrh.") == "Opraveno."
            assert len(local_requests) == 1
            assert "Soukromý text.".encode() in local_requests[0]
            assert "Návrh.".encode() in local_requests[0]
        assert proxy_requests == []
