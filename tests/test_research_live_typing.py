from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_live_typing_evidence_keeps_verified_and_blocked_gates_separate() -> None:
    evidence = json.loads(
        (ROOT / "research/evaluations/live-typing-adapters-2026-08-19.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["status"] == "source_integration_verified"
    assert "cross_app_settings_search_candidate_apply" in evidence["android"]["live_flows"]
    assert evidence["android"]["network_permission"] is False
    assert set(evidence["windows"]["tsf_context_flows"]) == {
        "automatic_apply",
        "cold_broker_preload",
        "neural_candidate_confirm",
    }
    assert evidence["android"]["resource_bounds"]["maximum_pending_inferences"] == 1
    assert evidence["windows"]["ipc_security"]["maximum_message_bytes"] == 16 * 1024
    assert evidence["windows"]["ipc_security"]["untrusted_pipe_server_test"] == "passed"
    assert evidence["windows"]["warm_broker_performance"]["p95_end_to_end_milliseconds"] < 250
    assert evidence["windows"]["elevated_profile_registration"].startswith("not_run")
    assert "code_signing_and_rollback" in evidence["release_gates_remaining"]
