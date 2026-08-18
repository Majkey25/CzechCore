from __future__ import annotations

from tools.research.train_ranker import (
    best_precision_metrics,
    choose_threshold,
    selection_metrics,
    split_name,
)


def test_ranker_threshold_respects_precision_and_group_split() -> None:
    scores = (0.9, 0.8, 0.7, 0.6)
    labels = (1.0, 1.0, 0.0, 1.0)

    threshold = choose_threshold(scores, labels, target_precision=0.8, min_accepted=2)
    metrics = selection_metrics(scores, labels, threshold)

    assert threshold == 0.8
    assert metrics.precision == 1.0
    assert best_precision_metrics(scores, labels, 3).precision == 0.75
    assert split_name("document-1") == split_name("document-1")
