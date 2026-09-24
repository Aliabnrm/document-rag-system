# ADR 0006: pypdf for the first PDF extraction baseline

- Status: Accepted
- Date: 2026-09-24

## Context

Sprint 1 supports text-based Persian and English PDFs with page-aware citations. The extractor must have a permissive license, detect encrypted/empty documents, and preserve page boundaries. Full layout, table, image, and OCR understanding is outside this sprint.

## Decision

Use pypdf as the initial PDF adapter and Python's explicit UTF-8 decoding path for TXT. Return page-numbered source text plus extraction diagnostics through an application port. Detect encrypted PDFs, pages with no extractable text, and likely scanned documents. Preserve original extracted text for citations and normalize a separate retrieval copy.

Benchmark representative Persian and English fixtures before treating extraction quality as sufficient. Keep the extractor replaceable so a later layout-aware or OCR pipeline does not change ingestion use cases.

## Alternatives considered

- PyMuPDF: fast and capable, but its AGPL/commercial licensing requires a product-level licensing decision.
- pdfplumber/pdfminer: useful for layout inspection, but heavier than required for the first text baseline.
- Cloud document intelligence services: stronger on OCR/layout, but add variable cost, data-transfer/privacy concerns, and vendor coupling before the baseline is measured.

## Consequences

The first release has a clear permissive baseline and page citations. Some Persian fonts, multi-column layouts, tables, and scanned files will fail or extract poorly; diagnostics and explicit unsupported states are part of the contract rather than hidden limitations.
