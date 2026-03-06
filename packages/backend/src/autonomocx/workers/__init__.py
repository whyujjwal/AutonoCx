"""AutonoCX background workers.

Workers handle long-running, asynchronous tasks such as document
ingestion, embedding generation, and analytics aggregation.  They
are designed to be run as separate processes or consumed by a task
queue (e.g., Celery, ARQ, or a simple asyncio loop).
"""

from .analytics_aggregator import AnalyticsAggregator
from .document_processor import DocumentProcessor
from .embedding_worker import EmbeddingWorker

__all__ = [
    "AnalyticsAggregator",
    "DocumentProcessor",
    "EmbeddingWorker",
]
