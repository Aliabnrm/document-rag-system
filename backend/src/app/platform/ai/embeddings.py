import hashlib
import math
import re
from importlib import import_module
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.modules.ingestion.application import EmbeddingBatch

_FEATURE = re.compile(r"\w+(?:\u200c\w+)*", flags=re.UNICODE)
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class DeterministicEmbeddingProvider:
    """Stable local test provider; it is not a quality production model."""

    def __init__(self, *, dimensions: int = 384) -> None:
        self._dimensions = dimensions

    async def embed(self, texts: tuple[str, ...]) -> EmbeddingBatch:
        vectors = tuple(self._vector(text) for text in texts)
        return EmbeddingBatch(
            vectors=vectors,
            model_id="deterministic-hash-embedding",
            revision="v1",
            dimensions=self._dimensions,
            maximum_input_tokens=8192,
            runtime="python",
        )

    def _vector(self, text: str) -> tuple[float, ...]:
        values = [0.0] * self._dimensions
        features = [match.group(0).casefold() for match in _FEATURE.finditer(text)]
        if not features:
            features = [text.casefold() or "empty"]
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=16).digest()
            first_index = int.from_bytes(digest[:8], "big") % self._dimensions
            second_index = int.from_bytes(digest[8:], "big") % self._dimensions
            values[first_index] += 1.0 if digest[0] & 1 else -1.0
            values[second_index] += 0.5 if digest[8] & 1 else -0.5
        magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
        return tuple(value / magnitude for value in values)


class FastEmbedProvider:
    """Optional real multilingual embedding adapter loaded only when selected."""

    def __init__(
        self,
        *,
        model_id: str,
        source_repo: str,
        revision: str,
        dimensions: int,
    ) -> None:
        if not _COMMIT_SHA.fullmatch(revision):
            raise ValueError("fastembed_revision_must_be_an_exact_commit_sha")
        try:
            text_embedding: Any = import_module("fastembed").TextEmbedding
            snapshot_download: Any = import_module("huggingface_hub").snapshot_download
        except ImportError as error:
            raise RuntimeError(
                "The 'models' optional dependency is required for fastembed"
            ) from error
        model_path = snapshot_download(repo_id=source_repo, revision=revision)
        self._model = text_embedding(
            model_name=model_id,
            specific_model_path=model_path,
        )
        self._model_id = model_id
        self._revision = revision
        self._dimensions = dimensions

    async def embed(self, texts: tuple[str, ...]) -> EmbeddingBatch:
        raw_vectors = await run_in_threadpool(
            lambda: list(self._model.embed(list(texts), batch_size=32))
        )
        vectors = tuple(tuple(float(value) for value in vector) for vector in raw_vectors)
        return EmbeddingBatch(
            vectors=vectors,
            model_id=self._model_id,
            revision=self._revision,
            dimensions=self._dimensions,
            maximum_input_tokens=512,
            runtime="fastembed-onnx",
        )
