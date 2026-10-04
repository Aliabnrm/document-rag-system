# ADR 0011: Measured generator acceptance gate

- Status: Accepted
- Date: 2026-09-26

## Context

The 0.5B Qwen Sprint 1 run fit the local machine but failed groundedness and relevance proxies. The
1.5B download did not complete under Ollama 0.15.5, and a local 7B coder competed heavily with the
8 GiB stack. Model popularity or open weights do not prove product quality or zero operating cost.

## Decision

Keep deterministic generation for CI contracts. Compare at least two license-compatible,
hardware-appropriate multilingual generators on one versioned 80–100 question corpus. Begin with
the recorded `qwen2.5:1.5b` candidate and select another candidate only after checking its current
license and runtime fit.

Record exact digest/revision, quantization, hardware, loaded memory, cold load, TTFT, total latency,
throughput, failures, Persian/English/cross-lingual quality, citation support, prompt-injection
behavior, abstention, and practical concurrency. Human review is required; automated term overlap is
only a regression proxy. No generator becomes a beta default until comparable results and acceptance
thresholds are recorded.

## Alternatives considered

- Promote the 0.5B model because it is fast: rejected by measured quality.
- Default to the available 7B coder: rejected without task fit and a stable operating envelope.
- Use an unmeasured hosted API: rejected because it hides cost, privacy, and availability decisions.

## Consequences

Beta readiness may remain blocked even when orchestration tests pass. Model weights and
caches stay outside Git, and local-development and deployed-inference profiles may legitimately use
different hardware while sharing the same evaluation contract.
