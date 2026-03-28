"""Tests for the ML classifier placeholder."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from bsgateway.routing.classifiers.base import ClassificationResult
from bsgateway.routing.classifiers.ml import MLClassifier


@pytest.fixture
def mock_fallback() -> AsyncMock:
    fb = AsyncMock()
    fb.classify.return_value = ClassificationResult(
        tier="medium",
        strategy="static",
        score=50,
    )
    return fb


async def test_ml_classifier_delegates_to_fallback(mock_fallback: AsyncMock) -> None:
    classifier = MLClassifier(fallback=mock_fallback)
    result = await classifier.classify({"messages": [{"role": "user", "content": "hello"}]})
    assert result.tier == "medium"
    assert result.strategy == "static"
    mock_fallback.classify.assert_awaited_once()


async def test_ml_classifier_returns_fallback_result(mock_fallback: AsyncMock) -> None:
    mock_fallback.classify.return_value = ClassificationResult(
        tier="complex",
        strategy="static",
        score=90,
    )
    classifier = MLClassifier(fallback=mock_fallback)
    result = await classifier.classify({"messages": []})
    assert result.tier == "complex"
    assert result.score == 90


async def test_ml_classifier_passes_data_to_fallback(mock_fallback: AsyncMock) -> None:
    data = {"messages": [{"role": "user", "content": "complex prompt"}], "tools": []}
    classifier = MLClassifier(fallback=mock_fallback)
    await classifier.classify(data)
    mock_fallback.classify.assert_awaited_once_with(data)
