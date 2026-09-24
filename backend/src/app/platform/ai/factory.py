from app.core.settings import Settings
from app.modules.ingestion.application import EmbeddingProvider
from app.platform.ai.embeddings import DeterministicEmbeddingProvider, FastEmbedProvider


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "fastembed":
        return FastEmbedProvider(
            model_id=settings.embedding_model,
            source_repo=settings.embedding_source_repo,
            revision=settings.embedding_revision,
            dimensions=settings.embedding_dimensions,
        )
    return DeterministicEmbeddingProvider(dimensions=settings.embedding_dimensions)
