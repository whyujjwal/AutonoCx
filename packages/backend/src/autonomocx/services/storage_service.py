"""File storage service -- local filesystem for dev, S3 for production."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog

from autonomocx.core.config import get_settings

logger = structlog.get_logger(__name__)

_UPLOAD_DIR = Path("uploads")


class StorageService:
    """Abstract file storage that works locally or with S3."""

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.s3_bucket_name
        self._use_s3 = bool(self._bucket)
        self._s3_client: Any | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upload_file(self, key: str, content: bytes, content_type: str = "") -> str:
        """Upload *content* under *key*.  Returns the storage path."""
        if self._use_s3:
            return await self._s3_upload(key, content, content_type)
        return await self._local_upload(key, content)

    async def download_file(self, key: str) -> bytes:
        """Download file content by *key*."""
        if self._use_s3:
            return await self._s3_download(key)
        return await self._local_download(key)

    async def delete_file(self, key: str) -> None:
        """Delete file by *key*."""
        if self._use_s3:
            await self._s3_delete(key)
        else:
            await self._local_delete(key)

    # ------------------------------------------------------------------
    # Local filesystem
    # ------------------------------------------------------------------

    async def _local_upload(self, key: str, content: bytes) -> str:
        path = _UPLOAD_DIR / key
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, content)
        logger.debug("local_file_uploaded", key=key, size=len(content))
        return str(path)

    async def _local_download(self, key: str) -> bytes:
        path = _UPLOAD_DIR / key
        data: bytes = await asyncio.to_thread(path.read_bytes)
        return data

    async def _local_delete(self, key: str) -> None:
        path = _UPLOAD_DIR / key
        await asyncio.to_thread(path.unlink, missing_ok=True)

    # ------------------------------------------------------------------
    # S3
    # ------------------------------------------------------------------

    def _get_s3_client(self) -> Any:
        if self._s3_client is None:
            import boto3

            settings = get_settings()
            kwargs: dict[str, Any] = {"region_name": settings.s3_region}
            if settings.s3_access_key_id:
                kwargs["aws_access_key_id"] = settings.s3_access_key_id.get_secret_value()
            if settings.s3_secret_access_key:
                kwargs["aws_secret_access_key"] = settings.s3_secret_access_key.get_secret_value()
            if settings.s3_endpoint_url:
                kwargs["endpoint_url"] = settings.s3_endpoint_url
            self._s3_client = boto3.client("s3", **kwargs)
        return self._s3_client

    async def _s3_upload(self, key: str, content: bytes, content_type: str) -> str:
        client = self._get_s3_client()
        extra: dict[str, str] = {}
        if content_type:
            extra["ContentType"] = content_type
        await asyncio.to_thread(
            client.put_object, Bucket=self._bucket, Key=key, Body=content, **extra
        )
        logger.debug("s3_file_uploaded", bucket=self._bucket, key=key, size=len(content))
        return f"s3://{self._bucket}/{key}"

    async def _s3_download(self, key: str) -> bytes:
        client = self._get_s3_client()
        resp = await asyncio.to_thread(client.get_object, Bucket=self._bucket, Key=key)
        data: bytes = await asyncio.to_thread(resp["Body"].read)
        return data

    async def _s3_delete(self, key: str) -> None:
        client = self._get_s3_client()
        await asyncio.to_thread(client.delete_object, Bucket=self._bucket, Key=key)


# Module-level singleton
storage_service = StorageService()
