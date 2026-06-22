"""S3-compatible object storage (MinIO / Railway Buckets).

Wraps synchronous ``boto3`` calls with ``asyncio.to_thread`` so that
the operations feel async to the caller without adding ``aioboto3``.
"""

from __future__ import annotations

import asyncio
import uuid

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from fastapi import UploadFile
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


class StorageService:
    """S3-compatible object storage service (MinIO / Railway Buckets)."""

    def __init__(self) -> None:
        self._config = BotoConfig(
            retries={"max_attempts": 3},
            connect_timeout=10,
            read_timeout=30,
        )
        self._client: boto3.client | None = None

    @property
    def client(self) -> boto3.client:
        """Lazily-initialised S3 client (thread-safe after creation)."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
                config=self._config,
            )
        return self._client

    @staticmethod
    async def _run(callable, *args, **kwargs):
        """Run a synchronous callable in the default thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: callable(*args, **kwargs))

    async def ensure_bucket(self) -> None:
        """Create the configured S3 bucket if it does not already exist."""
        bucket = settings.S3_BUCKET
        try:
            await self._run(self.client.head_bucket, Bucket=bucket)
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code == "404":
                await self._run(self.client.create_bucket, Bucket=bucket)
                logger.info("bucket_created", bucket=bucket)
            elif error_code == "403":
                logger.warning("bucket_access_denied", bucket=bucket)
            else:
                raise

    async def upload_bytes(
        self,
        content: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload raw *content* bytes to S3.

        Returns the S3 object key.
        """
        await self._run(
            self.client.put_object,
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        logger.info("bytes_uploaded", key=key, size=len(content))
        return key

    async def upload_file(
        self,
        file: UploadFile,
        key: str,
    ) -> str:
        """Upload a FastAPI ``UploadFile`` to S3.

        Returns the S3 object key.
        """
        content = await file.read()
        return await self.upload_bytes(content, key, file.content_type or "application/octet-stream")

    async def upload_text(
        self,
        content: str,
        key: str,
    ) -> str:
        """Upload UTF-8 text content to S3 as a markdown file.

        Returns the S3 object key.
        """
        return await self.upload_bytes(
            content.encode("utf-8"),
            key,
            content_type="text/markdown; charset=utf-8",
        )

    async def download_file(self, key: str) -> str:
        """Download a file from S3 by its object key."""
        response = await self._run(self.client.get_object, Bucket=settings.S3_BUCKET, Key=key)
        body = response["Body"].read()
        return body.decode("utf-8")

    async def get_download_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned download URL valid for *expires_in* seconds."""
        url = await self._run(
            self.client.generate_presigned_url,
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def delete_file(self, key: str) -> None:
        """Delete a single object from S3.

        Does **not** raise when the key does not exist.
        """
        try:
            await self._run(self.client.delete_object, Bucket=settings.S3_BUCKET, Key=key)
            logger.info("file_deleted", key=key)
        except ClientError:
            logger.warning("file_delete_failed", key=key)

    async def delete_files(self, paths: list[str]) -> None:
        """Delete multiple objects in a single S3 batch request."""
        if not paths:
            return
        objects = [{"Key": p} for p in paths]
        try:
            await self._run(
                self.client.delete_objects,
                Bucket=settings.S3_BUCKET,
                Delete={"Objects": objects, "Quiet": True},
            )
            logger.info("files_deleted", count=len(paths))
        except ClientError:
            logger.warning("files_delete_failed", count=len(paths))
