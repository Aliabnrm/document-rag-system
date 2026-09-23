# Product brief

## Product promise

Document Q&A lets a person upload Persian or English documents, ask questions in either language, and receive an answer whose claims can be checked against cited passages. When the available evidence is insufficient, the product says so clearly.

## Initial audience

People who search long educational or workplace documents: students, researchers, operations teams, support teams, and knowledge workers.

## Primary user journey

1. Try a sample document or upload a PDF/TXT file.
2. See extraction and indexing progress.
3. Ask a question in Persian or English.
4. Read a concise streamed answer.
5. Open each citation at its original page and passage.
6. Ask a follow-up question or report an unhelpful answer.

## V1 scope

- Persian and English interface with correct RTL/LTR behavior.
- Text-based PDF and TXT upload.
- Document collections and processing status.
- Questions over one or more selected documents.
- Hybrid retrieval, reranking, grounded answer generation, and citations.
- Explicit insufficient-evidence behavior.
- Conversation history, document deletion, and paginated lists.
- Basic authentication, quotas, observability, and feedback for public beta.

## Deferred until evidence justifies them

- Full OCR for scanned documents.
- High-fidelity extraction from complex tables and diagrams.
- Team workspaces and granular enterprise permissions.
- Fine-tuning a generative model.

## Success measures

- Retrieval recall: the supporting passage appears in the retrieved candidate set.
- Citation correctness: cited passages support the answer's claims.
- Groundedness: material claims are supported by retrieved evidence.
- Refusal quality: unanswerable questions do not produce invented answers.
- User outcome: a test user can upload, ask, and inspect a source without help.
- Performance: upload returns quickly, processing is asynchronous, and answer latency is measured by time-to-first-token and total duration.
