from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.modules.ingestion.application import ExtractionResult
from app.modules.ingestion.domain import PermanentIngestionError, SourcePage


class PdfTxtExtractor:
    def extract(self, *, source: BinaryIO, media_type: str) -> ExtractionResult:
        source.seek(0)
        if media_type == "application/pdf":
            return self._extract_pdf(source)
        if media_type == "text/plain":
            return self._extract_text(source)
        raise PermanentIngestionError("unsupported_file_type")

    def _extract_pdf(self, source: BinaryIO) -> ExtractionResult:
        try:
            reader = PdfReader(source, strict=False)
        except PdfReadError as error:
            raise PermanentIngestionError("invalid_pdf") from error
        if reader.is_encrypted:
            raise PermanentIngestionError("encrypted_pdf")
        if not reader.pages:
            raise PermanentIngestionError("empty_document")

        pages: list[SourcePage] = []
        pages_with_text = 0
        extracted_characters = 0
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as error:
                raise PermanentIngestionError("pdf_extraction_failed") from error
            if text.strip():
                pages_with_text += 1
                extracted_characters += len(text.strip())
            pages.append(SourcePage(page_number=page_number, text=text))

        if pages_with_text == 0 or extracted_characters < max(20, len(pages) * 5):
            raise PermanentIngestionError("likely_scanned_pdf")
        return ExtractionResult(
            pages=tuple(pages),
            diagnostics={
                "extractor": "pypdf",
                "extractor_version": "v1",
                "page_count": len(pages),
                "pages_with_text": pages_with_text,
                "empty_page_count": len(pages) - pages_with_text,
                "character_count": extracted_characters,
            },
        )

    def _extract_text(self, source: BinaryIO) -> ExtractionResult:
        try:
            text = source.read().decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as error:
            raise PermanentIngestionError("invalid_text_encoding") from error
        if not text.strip():
            raise PermanentIngestionError("empty_document")
        return ExtractionResult(
            pages=(SourcePage(page_number=1, text=text),),
            diagnostics={
                "extractor": "utf-8-text",
                "extractor_version": "v1",
                "page_count": 1,
                "pages_with_text": 1,
                "empty_page_count": 0,
                "character_count": len(text),
            },
        )
