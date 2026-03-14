"""Tests for the custom intent classifier (embedding similarity).

TDD: Tests written FIRST.
"""
from __future__ import annotations

import math
from unittest.mock import AsyncMock

import pytest

from bsgateway.rules.intent import IntentClassifier, IntentDefinition


class TestIntentClassifier:
    """Test embedding-based intent classification."""

    @pytest.fixture
    def mock_embedder(self) -> AsyncMock:
        """Mock that returns deterministic embeddings based on text."""
        embedder = AsyncMock()

        # Simple mock: hash-based pseudo-embeddings for testing
        async def fake_embed(text: str) -> list[float]:
            # Create a simple 4-dim embedding based on keywords
            vec = [0.0, 0.0, 0.0, 0.0]
            text_lower = text.lower()
            if "추천" in text_lower or "recommend" in text_lower:
                vec[0] = 0.9
            if "주문" in text_lower or "order" in text_lower:
                vec[1] = 0.9
            if "코드" in text_lower or "code" in text_lower:
                vec[2] = 0.9
            if "번역" in text_lower or "translat" in text_lower:
                vec[3] = 0.9
            # Normalize
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            return [x / norm for x in vec]

        embedder.side_effect = fake_embed
        return embedder

    @pytest.fixture
    def intents(self) -> list[IntentDefinition]:
        return [
            IntentDefinition(
                name="product_recommendation",
                description="상품 추천 요청",
                example_embeddings=[
                    [0.9, 0.0, 0.0, 0.0],  # "추천" dominant
                ],
            ),
            IntentDefinition(
                name="order_status",
                description="주문 상태 확인",
                example_embeddings=[
                    [0.0, 0.9, 0.0, 0.0],  # "주문" dominant
                ],
            ),
            IntentDefinition(
                name="code_generation",
                description="코드 생성",
                example_embeddings=[
                    [0.0, 0.0, 0.9, 0.0],  # "코드" dominant
                ],
            ),
        ]

    async def test_classify_matches_correct_intent(
        self, mock_embedder: AsyncMock, intents: list[IntentDefinition],
    ):
        classifier = IntentClassifier(
            embed_fn=mock_embedder, intents=intents, threshold=0.5,
        )
        result = await classifier.classify("상품 추천해줘")
        assert result == "product_recommendation"

    async def test_classify_different_intent(
        self, mock_embedder: AsyncMock, intents: list[IntentDefinition],
    ):
        classifier = IntentClassifier(
            embed_fn=mock_embedder, intents=intents, threshold=0.5,
        )
        result = await classifier.classify("주문 상태 확인")
        assert result == "order_status"

    async def test_classify_returns_none_below_threshold(
        self, mock_embedder: AsyncMock, intents: list[IntentDefinition],
    ):
        classifier = IntentClassifier(
            embed_fn=mock_embedder, intents=intents, threshold=0.99,
        )
        # "hello" doesn't match any intent well
        result = await classifier.classify("hello world")
        assert result is None

    async def test_classify_empty_text(
        self, mock_embedder: AsyncMock, intents: list[IntentDefinition],
    ):
        classifier = IntentClassifier(
            embed_fn=mock_embedder, intents=intents, threshold=0.5,
        )
        result = await classifier.classify("")
        assert result is None

    async def test_classify_no_intents(self, mock_embedder: AsyncMock):
        classifier = IntentClassifier(
            embed_fn=mock_embedder, intents=[], threshold=0.5,
        )
        result = await classifier.classify("anything")
        assert result is None

    async def test_cosine_similarity_basic(self):
        from bsgateway.rules.intent import cosine_similarity

        # Identical vectors
        assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)
        # Orthogonal vectors
        assert cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)
        # Opposite vectors
        assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    async def test_multiple_examples_best_match(self, mock_embedder: AsyncMock):
        """Intent with multiple examples should use the best (max) similarity."""
        intents = [
            IntentDefinition(
                name="recommendation",
                description="추천",
                example_embeddings=[
                    [0.9, 0.0, 0.0, 0.0],
                    [0.7, 0.3, 0.0, 0.0],  # also partially matches
                ],
            ),
        ]
        classifier = IntentClassifier(
            embed_fn=mock_embedder, intents=intents, threshold=0.5,
        )
        result = await classifier.classify("상품 추천해줘")
        assert result == "recommendation"
