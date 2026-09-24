# ADR 0007: Hardware-aware local model evaluation

- Status: Accepted
- Date: 2026-09-24

## Context

The development machine is an Apple M2 system with 8 GB unified memory and Ollama installed. Running a large generator, a large multilingual embedder, PostgreSQL, Redis, MinIO, the API, the worker, and the frontend concurrently can create memory pressure. The project still needs a free/open-weight path and reproducible CI.

## Decision

Keep embedding, reranking, and generation behind application ports. Use deterministic in-process fake providers in CI and for end-to-end contract tests. Establish a 384-dimensional multilingual embedding baseline suitable for constrained local hardware, then compare a small multilingual E5-family candidate with BGE-M3 using the versioned evaluation set before accepting a production profile.

Evaluate a quantized small Qwen-family instruct model through Ollama for generation. Record exact model tag/digest, quantization, context limit, memory use, latency, and Persian/English/cross-lingual quality. Do not run embedding and generation models concurrently by default on this machine until measured memory use proves it safe.

## Alternatives considered

- Defaulting immediately to BGE-M3 and a 9B generator: stronger headline capability, but unlikely to provide a stable local developer experience within 8 GB.
- Hosted proprietary APIs: operationally simple, but do not meet the free local baseline and introduce data-transfer and cost concerns.
- Embedding inside PostgreSQL extensions: reduces application code, but limits model/runtime flexibility and reproducibility.

## Consequences

Schema and CI can progress without downloading model weights. The first real model is a measured baseline rather than a marketing choice. A future accepted embedding dimension/model change requires versioned storage and migration planning. Model weights and caches remain outside Git.

## Sprint 1 measured evidence

The accepted 384-dimensional retrieval baseline is
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, executed by FastEmbed from the
ONNX source repository `qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q` at exact commit
`faf4aa4225822f3bc6376869cb1164e8e3feedd0`. The source commit is enforced at runtime rather than
merely written into metadata. On the 40-question bilingual fixture it measured Recall@6 `0.944444`
and MRR `0.859722`.

BGE-M3 is not the default on the M2/8 GB machine. Its larger runtime footprint would compete with
PostgreSQL, Redis, MinIO, Next.js, the worker, and the generator; Sprint 1 has no measured quality
gain that justifies that operational cost. It remains a future controlled comparison, not a claim
that MiniLM is universally better.

The complete Qwen 2.5 0.5B baseline is operationally light but measured only `0.10` groundedness
proxy and is rejected for public use. The 1.5B pull was unstable under Ollama 0.15.5, and the locally
available 7.6B coder required about 4.81 GB VRAM with a 67-second cold load. Therefore Sprint 1 keeps
`qwen2.5:1.5b` as the next evaluation candidate rather than silently promoting either measured
extreme. Operational attempts are recorded separately from quality results.

Provider generation is intentionally buffered before SSE deltas: this delays first output but
prevents control syntax from leaking and lets the adapter parse citations before the application
validates them. True token streaming is a future experiment and may not weaken citation validation.
