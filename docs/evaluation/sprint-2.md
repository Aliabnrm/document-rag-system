# Sprint 2 generator evaluation

- Status: Automated comparison complete; independent human review pending
- Measured: 2026-09-26
- Dataset: `evals/datasets/sprint-2-v1.json` (80 controlled questions)
- Hardware: Apple M2, 8 CPU cores, 8 GiB unified memory
- Runtime: Ollama 0.15.5, FastEmbed 0.8.1, ONNX Runtime 1.30.0

## Method

Both candidates used the same extracted fixtures, multilingual embedding revision, chunking,
retrieval depths, RRF fusion, context budget, prompt contract, 384-token output ceiling,
deterministic seed/temperature, and true Ollama streaming path. Model thinking was disabled because
hidden reasoning consumed the bounded answer budget without helping this short grounded-answer
contract. The corpus includes Persian, English, cross-lingual, exact-value, multi-passage,
unanswerable, ambiguous, and adversarial-document questions. Two four-page PDFs use the production
extractor and have versioned checksums.

Automated citation support, groundedness, and relevance values are regression proxies based on the
controlled expected terms and validated citation structure. They are not human quality scores.
The runner exports an 80-row JSONL packet with answer, evidence, and empty reviewer fields; a human
must score groundedness, citation support, relevance, language quality, and abstention correctness
before a beta model can be accepted.

The human packet is deliberately not presented as a completed report. Regenerate it from the
versioned dataset and candidate with `--review-output <path>`, have an independent reviewer fill the
five empty score fields for every row, and archive the reviewed artifact only after checking that it
contains no private user documents. The current 80-row Qwen 3 packet has empty human score fields.

### Human review rubric

Use integer scores `0`, `1`, or `2` for groundedness, citation support, relevance, and language
quality: `0` means failed or unsupported, `1` means partially correct with a material defect, and `2`
means fully acceptable for the controlled question. `abstention_correct` is boolean: true only when
the answer/abstention behavior matches the fixture's answerability. Reviewers must inspect the quoted
evidence rather than infer from memory, record a note for every `0` or `1`, and must not edit the
model answer or evidence. A second reviewer should resolve disagreements before any aggregate human
score or release decision is reported.

## Comparable measured results

| Metric | Qwen 2.5 1.5B | Qwen 3 1.7B |
|---|---:|---:|
| Ollama digest | `65ec06548149…` | `8f68893c685c…` |
| Quantization | Q4_K_M | Q4_K_M |
| Weight size | 986 MB | 1.36 GB |
| Loaded memory | 1.41 GB | 1.89 GB |
| License | Apache-2.0 | Apache-2.0 |
| Recall@8 | 0.891892 | 0.891892 |
| MRR | 0.796734 | 0.796734 |
| Correct PDF document + page | 1.0 | 1.0 |
| Generation success | 1.0 | 1.0 |
| Citation-ID validity | 1.0 | 1.0 |
| Citation support proxy | 0.1875 | 0.7500 |
| Groundedness proxy | 0.1875 | 0.7500 |
| Relevance proxy | 0.3875 | 0.6000 |
| Abstention accuracy | 0.6500 | 0.9125 |
| Median TTFT | 1980 ms | 2008 ms |
| Median total latency | 2328 ms | 2354 ms |
| Provider failures | 0 | 0 |

Retrieval metrics match because both candidates received the same retrieved evidence. Qwen 3 is
materially stronger on the automated grounding, relevance, and abstention proxies while its median
TTFT and total latency remain within about 2% of Qwen 2.5 on this run. This makes it the stronger
automated candidate, but proxy values cannot establish natural language quality or factual support
without independent human review.

## Failure history

The first Qwen 2.5 run generated many answers and then exceeded the original three-minute process
limit. The runner now caps output, applies a per-request timeout, and records provider failures
without discarding the complete comparison. An initial Qwen 3 run completed all 80 prompts but had
an `8246ms` median TTFT because Ollama thinking was enabled and the adapter buffered the complete
answer. The final comparable runs disable thinking, consume Ollama's real stream, withhold control
markers from the UI, and parse the citation footer before backend validation. Both candidates were
rerun through that same path; the table contains only those final measurements.

Gemma 3 1B was downloaded locally but excluded from evaluation because its hosted artifact required
explicit acceptance of custom terms. Downloaded weights and caches remain outside Git.

## Decision

Neither candidate is the beta default yet. Qwen 2.5 is rejected on automated grounding quality.
Qwen 3 is the leading candidate, but remains blocked on independent human review and an explicitly
accepted quality/latency gate. Deterministic generation remains the CI provider and must not be
presented as end-user AI quality.

Canonical machine-readable reports:

- `evals/reports/sprint-2-qwen2.5-1.5b.json`
- `evals/reports/sprint-2-qwen3-1.7b.json`
- `evals/reports/sprint-2-deterministic.json`
