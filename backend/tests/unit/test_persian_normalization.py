# ruff: noqa: RUF001

from app.modules.ingestion.domain import normalize_for_retrieval


def test_persian_normalization_changes_only_retrieval_copy() -> None:
    source = "  كتاب\u200c هاى   خوب  \n\n\n  مُدیر  "

    normalized = normalize_for_retrieval(source)

    assert normalized == "کتاب\u200cهای خوب\n\nمدیر"
    assert source == "  كتاب\u200c هاى   خوب  \n\n\n  مُدیر  "


def test_normalization_is_idempotent() -> None:
    value = "می \u200c روم\r\nبا   فاصله"

    once = normalize_for_retrieval(value)

    assert normalize_for_retrieval(once) == once
    assert once == "می\u200cروم\nبا فاصله"
