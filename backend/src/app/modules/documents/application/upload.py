import codecs
import hashlib
import os
import unicodedata
from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID, uuid4

from app.modules.documents.domain import PendingDocumentUpload
from app.platform.errors import FieldError, UnsupportedDocumentError

READ_CHUNK_BYTES = 64 * 1024


class UploadStream(Protocol):
    filename: str | None
    content_type: str | None
    file: BinaryIO

    async def read(self, size: int = -1) -> bytes: ...

    async def seek(self, offset: int) -> None: ...


class SourceStorage(Protocol):
    async def ensure_bucket(self) -> None: ...

    async def put_file(self, *, key: str, file: BinaryIO, media_type: str) -> None: ...

    async def download_file(self, *, key: str) -> BinaryIO: ...

    async def delete(self, *, key: str) -> None: ...


class JobDispatcher(Protocol):
    async def dispatch(self, *, job_id: UUID, document_version_id: UUID) -> None: ...


class DocumentUploadRepository(Protocol):
    async def create_pending(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        document_version_id: UUID,
        job_id: UUID,
        display_name: str,
        inspection: "FileInspection",
        storage_key: str,
        pipeline_version: str,
    ) -> PendingDocumentUpload: ...

    async def mark_dispatched(
        self,
        *,
        owner_id: UUID,
        document_version_id: UUID,
        job_id: UUID,
    ) -> PendingDocumentUpload: ...

    async def mark_dispatch_failed(
        self,
        *,
        owner_id: UUID,
        document_version_id: UUID,
        job_id: UUID,
    ) -> PendingDocumentUpload: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


@dataclass(frozen=True, slots=True)
class FileInspection:
    filename: str
    media_type: str
    extension: str
    size_bytes: int
    sha256: str


class CreateDocumentUpload:
    def __init__(
        self,
        *,
        repository: DocumentUploadRepository,
        storage: SourceStorage,
        dispatcher: JobDispatcher,
        max_upload_bytes: int,
        pipeline_version: str,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._dispatcher = dispatcher
        self._max_upload_bytes = max_upload_bytes
        self._pipeline_version = pipeline_version

    async def execute(
        self,
        *,
        owner_id: UUID,
        collection_id: UUID,
        upload: UploadStream,
    ) -> PendingDocumentUpload:
        inspection = await inspect_upload(upload, max_bytes=self._max_upload_bytes)
        document_id = uuid4()
        document_version_id = uuid4()
        job_id = uuid4()
        storage_key = _storage_key(
            owner_id=owner_id,
            collection_id=collection_id,
            document_id=document_id,
            document_version_id=document_version_id,
            extension=inspection.extension,
        )

        await upload.seek(0)
        await self._storage.put_file(
            key=storage_key,
            file=upload.file,
            media_type=inspection.media_type,
        )
        try:
            await self._repository.create_pending(
                owner_id=owner_id,
                collection_id=collection_id,
                document_id=document_id,
                document_version_id=document_version_id,
                job_id=job_id,
                display_name=inspection.filename,
                inspection=inspection,
                storage_key=storage_key,
                pipeline_version=self._pipeline_version,
            )
            await self._repository.commit()
        except Exception:
            await self._repository.rollback()
            await self._storage.delete(key=storage_key)
            raise

        queued = await self._repository.mark_dispatched(
            owner_id=owner_id,
            document_version_id=document_version_id,
            job_id=job_id,
        )
        await self._repository.commit()
        try:
            await self._dispatcher.dispatch(job_id=job_id, document_version_id=document_version_id)
            return queued
        except Exception:
            await self._repository.rollback()
            failed = await self._repository.mark_dispatch_failed(
                owner_id=owner_id,
                document_version_id=document_version_id,
                job_id=job_id,
            )
            await self._repository.commit()
            return failed


async def inspect_upload(upload: UploadStream, *, max_bytes: int) -> FileInspection:
    filename = _safe_filename(upload.filename)
    hasher = hashlib.sha256()
    size_bytes = 0
    prefix = bytearray()
    utf8_decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
    text_candidate = True

    await upload.seek(0)
    while chunk := await upload.read(READ_CHUNK_BYTES):
        size_bytes += len(chunk)
        if size_bytes > max_bytes:
            raise UnsupportedDocumentError("file_too_large", "errors.file_too_large")
        hasher.update(chunk)
        if len(prefix) < 8:
            prefix.extend(chunk[: 8 - len(prefix)])
        if text_candidate and not prefix.startswith(b"%PDF-"):
            if b"\x00" in chunk:
                text_candidate = False
            else:
                try:
                    utf8_decoder.decode(chunk, final=False)
                except UnicodeDecodeError:
                    text_candidate = False

    if size_bytes == 0:
        raise UnsupportedDocumentError("empty_file", "errors.empty_file")

    supplied_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if prefix.startswith(b"%PDF-"):
        media_type = "application/pdf"
        extension = "pdf"
        allowed_types = {"", "application/pdf", "application/octet-stream"}
    elif text_candidate:
        try:
            utf8_decoder.decode(b"", final=True)
        except UnicodeDecodeError as error:
            raise UnsupportedDocumentError(
                "invalid_text_encoding",
                "errors.invalid_text_encoding",
            ) from error
        media_type = "text/plain"
        extension = "txt"
        allowed_types = {"", "text/plain", "application/octet-stream"}
    else:
        raise UnsupportedDocumentError("unsupported_file_type", "errors.unsupported_file_type")

    if supplied_type not in allowed_types:
        mismatch_error = UnsupportedDocumentError("mime_mismatch", "errors.mime_mismatch")
        mismatch_error.field_errors = (FieldError(field="file", code="mime_mismatch"),)
        raise mismatch_error

    filename_extension = os.path.splitext(filename)[1].lower().lstrip(".")
    if filename_extension and filename_extension != extension:
        raise UnsupportedDocumentError("extension_mismatch", "errors.extension_mismatch")

    await upload.seek(0)
    return FileInspection(
        filename=filename,
        media_type=media_type,
        extension=extension,
        size_bytes=size_bytes,
        sha256=hasher.hexdigest(),
    )


def _safe_filename(value: str | None) -> str:
    candidate = os.path.basename(value or "document").strip()
    candidate = "".join(
        character
        for character in unicodedata.normalize("NFC", candidate)
        if character.isprintable()
    )
    if not candidate:
        candidate = "document"
    return candidate[:255]


def _storage_key(
    *,
    owner_id: UUID,
    collection_id: UUID,
    document_id: UUID,
    document_version_id: UUID,
    extension: str,
) -> str:
    return (
        f"owners/{owner_id}/collections/{collection_id}/documents/{document_id}/"
        f"versions/{document_version_id}/source.{extension}"
    )
