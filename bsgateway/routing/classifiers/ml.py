from __future__ import annotations

import structlog

from bsgateway.routing.classifiers.base import ClassificationResult, ClassifierProtocol

logger = structlog.get_logger(__name__)


class MLClassifier:
    """ML-based classifier placeholder.

    No trained model is available yet. Always delegates to the fallback
    classifier (typically StaticClassifier) and logs the delegation so
    operators can track how often ML routing *would* have been used.
    """

    def __init__(self, fallback: ClassifierProtocol) -> None:
        self.fallback = fallback

    async def classify(self, data: dict) -> ClassificationResult:
        logger.debug("ml_classifier_not_available", reason="no trained model loaded")
        return await self.fallback.classify(data)
