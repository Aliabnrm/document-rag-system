from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from app.modules.ingestion.domain import PermanentIngestionError
from app.modules.ingestion.infrastructure.extraction import PdfTxtExtractor


def test_pdf_extraction_preserves_page_numbers() -> None:
    source = make_text_pdf(("First page policy text.", "Second page evidence text."))

    result = PdfTxtExtractor().extract(source=BytesIO(source), media_type="application/pdf")

    assert [page.page_number for page in result.pages] == [1, 2]
    assert "First page" in result.pages[0].text
    assert "Second page" in result.pages[1].text
    assert result.diagnostics["page_count"] == 2


def test_encrypted_pdf_has_actionable_permanent_failure() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)

    with pytest.raises(PermanentIngestionError) as caught:
        PdfTxtExtractor().extract(source=BytesIO(output.getvalue()), media_type="application/pdf")

    assert caught.value.code == "encrypted_pdf"


def make_text_pdf(page_texts: tuple[str, ...]) -> bytes:
    writer = PdfWriter()
    for text in page_texts:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_reference = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
        )
        stream = StreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
