# Sprint 1 evaluation

## Method

`evals/datasets/sprint-1-v1.jsonl` contains 40 controlled questions over four versioned Persian and
English fixtures. Categories include direct facts, semantic paraphrases, exact names/dates,
multi-passage support, Persian/English, cross-lingual retrieval, ambiguity, unanswerable questions,
and adversarial instructions embedded in a document.

The runner uses the production normalization, chunker, deterministic RRF, context packing,
citation validator, embedding port, and answer-generator port. Its portable lexical score is token
overlap rather than PostgreSQL full-text search; production SQL behavior is covered separately by
integration tests. `citation support` and `groundedness proxy` are automated term checks, not human
judgments.

Run the reproducible fake baseline:

```bash
cd backend
uv run python ../evals/run_baseline.py
```

Run the exact real multilingual embedder:

```bash
cd backend
uv run --extra models python ../evals/run_baseline.py \
  --embedding-provider fastembed \
  --answer-provider deterministic \
  --output ../evals/reports/sprint-1-multilingual-minilm.json
```

## Measured retrieval baseline

Hardware: Apple M2, 8 CPU cores, 8 GiB unified memory, Python 3.13.14. The real model runs through
FastEmbed 0.8.1 and ONNX Runtime 1.30.0.

| Metric | Deterministic fake | Multilingual MiniLM |
|---|---:|---:|
| Recall@6 | 0.916667 | **0.944444** |
| MRR | 0.831019 | **0.859722** |
| Citation ID validity | 1.000000 | 1.000000 |
| Citation support proxy | 0.775000 | 0.775000 |
| Groundedness proxy | 0.775000 | 0.775000 |
| Answer relevance | 0.625000 | 0.625000 |
| Abstention accuracy | 0.925000 | 0.925000 |
| Fixture embedding throughput | 17,132.675 chunks/s | 55.118 chunks/s |

Generation metrics are identical in this comparison because both runs deliberately use the same
deterministic answer provider; this isolates retrieval. The real embedder is the better Sprint 1
baseline on these fixtures, but the dataset is too small to claim universal superiority.

Exact real embedding provenance:

- Logical model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- ONNX source: `qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q`
- Source commit: `faf4aa4225822f3bc6376869cb1164e8e3feedd0`
- Dimension: 384; maximum input: 512 tokens

## Generator evaluation

`qwen2.5:0.5b` Q4_K_M completed all 40 questions through Ollama 0.15.5. It used approximately
730 MB reported VRAM with a 2,048-token runtime context.

| Metric | MiniLM + deterministic answer | MiniLM + Qwen 2.5 0.5B |
|---|---:|---:|
| Citation ID validity | 1.000 | 1.000 |
| Citation support proxy | 0.775 | **0.100** |
| Groundedness proxy | 0.775 | **0.100** |
| Answer relevance | 0.625 | **0.325** |
| Abstention accuracy | 0.925 | **0.850** |
| Median TTFT | 0.291 ms | 431.615 ms |
| Median total generation latency | 0.315 ms | 431.630 ms |

Its exact digest is `a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67`.
The model is operationally light but fails the evidence-following quality needed for public use, so
it is a measured rejected baseline rather than the default production answer model.

`qwen2.5:1.5b` remains the next constrained-hardware candidate. Repeated Ollama 0.15.5 multipart
downloads terminated before registration, so no quality number is fabricated. An existing
`qwen2.5-coder:7b` Q4_K_M smoke test loaded at roughly 4.81 GB VRAM; cold load took 67.345 seconds
and the first two-token response took 91.761 seconds. A 40-question run exceeded the ordinary
60-second provider timeout on its first cold request and did not produce a report. It is neither a
general-purpose ideal nor an acceptable always-on baseline for this 8 GB machine.

The complete 0.5B report is `sprint-1-multilingual-minilm-qwen2.5-0.5b.json`; operational failures
are separated in `sprint-1-generator-operational-attempts.json`. The application remains usable in
development through the deterministic provider, which proves orchestration and citation safety,
not natural-language quality. A public deployment must complete the 1.5B (or hosted open-weight)
comparison before inviting external users.

## Interpretation and next experiments

- No release threshold is invented from the first baseline.
- Exact identifiers benefit from lexical retrieval; semantic/cross-lingual questions benefit from
  dense retrieval. Their RRF combination is justified by category behavior.
- Citation support/relevance are the largest current gaps. Human-labeled claim-level support and a
  stable real-generator report are required before a public quality promise.
- BGE-M3 and reranking remain experiments. Compare them on the same data, hardware, latency, and
  memory envelope before changing defaults.
- Add real page-aware PDFs and harder Persian typography/table fixtures in Sprint 2.
