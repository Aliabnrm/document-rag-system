import pytest

from app.platform.ai.embeddings import FastEmbedProvider


def test_fastembed_requires_exact_source_commit() -> None:
    with pytest.raises(ValueError, match="exact_commit_sha"):
        FastEmbedProvider(
            model_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            source_repo="qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q",
            revision="main",
            dimensions=384,
        )
