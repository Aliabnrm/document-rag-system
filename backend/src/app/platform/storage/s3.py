from functools import partial
from tempfile import SpooledTemporaryFile
from typing import Any, BinaryIO, cast

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from starlette.concurrency import run_in_threadpool

from app.core.settings import Settings


class S3SourceStorage:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )

    async def ensure_bucket(self) -> None:
        def ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError as error:
                code = str(error.response.get("Error", {}).get("Code", ""))
                if code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
                self._client.create_bucket(Bucket=self._bucket)

        await run_in_threadpool(ensure)

    async def is_ready(self) -> bool:
        await run_in_threadpool(partial(self._client.head_bucket, Bucket=self._bucket))
        return True

    async def put_file(self, *, key: str, file: BinaryIO, media_type: str) -> None:
        await run_in_threadpool(
            partial(
                self._client.upload_fileobj,
                file,
                self._bucket,
                key,
                ExtraArgs={"ContentType": media_type},
            )
        )

    async def download_file(self, *, key: str) -> BinaryIO:
        """Download into a bounded-memory spool that rolls large sources to disk."""
        # Ownership transfers to the caller, which closes the spool after extraction.
        target = cast(
            BinaryIO,
            SpooledTemporaryFile(  # noqa: SIM115
                max_size=8 * 1024 * 1024,
                mode="w+b",
            ),
        )
        try:
            await run_in_threadpool(
                partial(self._client.download_fileobj, self._bucket, key, target)
            )
            target.seek(0)
            return target
        except Exception:
            target.close()
            raise

    async def delete(self, *, key: str) -> None:
        await run_in_threadpool(partial(self._client.delete_object, Bucket=self._bucket, Key=key))
