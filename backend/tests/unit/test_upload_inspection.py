from io import BytesIO
from typing import BinaryIO

import pytest

from app.modules.documents.application.upload import inspect_upload
from app.platform.errors import UnsupportedDocumentError


class MemoryUpload:
    def __init__(self, content: bytes, *, filename: str, content_type: str) -> None:
        self.filename: str | None = filename
        self.content_type: str | None = content_type
        self.file: BinaryIO = BytesIO(content)

    async def read(self, size: int = -1) -> bytes:
        return self.file.read(size)

    async def seek(self, offset: int) -> None:
        self.file.seek(offset)


@pytest.mark.asyncio
async def test_text_upload_is_checked_incrementally_and_rewound() -> None:
    upload = MemoryUpload("متن فارسی".encode(), filename="../guide.txt", content_type="text/plain")

    result = await inspect_upload(upload, max_bytes=1024)

    assert result.filename == "guide.txt"
    assert result.media_type == "text/plain"
    assert result.size_bytes == len("متن فارسی".encode())
    assert upload.file.tell() == 0


@pytest.mark.asyncio
async def test_binary_content_cannot_hide_behind_text_mime() -> None:
    upload = MemoryUpload(b"abc\x00def", filename="unsafe.txt", content_type="text/plain")

    with pytest.raises(UnsupportedDocumentError) as caught:
        await inspect_upload(upload, max_bytes=1024)

    assert caught.value.code == "unsupported_file_type"
