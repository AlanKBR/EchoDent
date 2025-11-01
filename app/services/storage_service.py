from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

from flask import current_app


class BaseStorageDriver(ABC):
    """Abstract storage driver for media/documents.

    Contract
    - save_file: persist a binary stream under a relative path and return
      a public URL or reference
    - generate_url: return a public URL for the given path/reference
    - delete: remove the stored object if supported
    """

    @abstractmethod
    def save_file(
        self,
        file_stream: BinaryIO,
        relative_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Persist file and return a reference/URL."""
        raise NotImplementedError

    @abstractmethod
    def generate_url(self, relative_path: str, expires_in: int = 3600) -> str:
        """Generate a public URL for the stored object."""
        raise NotImplementedError

    def delete(self, relative_path: str) -> None:  # optional
        """Delete stored object if supported (no-op by default)."""
        pass


class LocalStorageDriver(BaseStorageDriver):
    """Stores files under instance/media_storage.

    The returned reference is the relative path (e.g., "1/picture.jpg").
    """

    def _abs_path(self, relative_path: str) -> str:
        base_dir = os.path.join(current_app.instance_path, "media_storage")
        return os.path.join(base_dir, relative_path)

    def save_file(
        self,
        file_stream: BinaryIO,
        relative_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        abs_path = self._abs_path(relative_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            chunk = file_stream.read()
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            f.write(chunk or b"")
        # Return the relative path; route/controller decides how to build URLs
        return relative_path

    def generate_url(self, relative_path: str, expires_in: int = 3600) -> str:
        # For local storage we typically expose via a route that resolves
        # media by id. Since we only have the relative path here, we return
        # a pseudo URL path that callers can adapt.
        # Callers can adapt or use a dedicated route if needed.
        return f"/instance/media/{relative_path}"


class S3StorageDriver(BaseStorageDriver):
    def __init__(self) -> None:
        cfg = current_app.config
        self.bucket = cfg.get("S3_BUCKET")
        self.region = cfg.get("S3_REGION")
        # optional endpoint (e.g., MinIO)
        self.endpoint_url = cfg.get("S3_ENDPOINT_URL")
        if not self.bucket:
            raise RuntimeError("S3_BUCKET not configured")

    def _client(self):
        # Lazy import to avoid hard dependency when using Local driver
        import boto3  # type: ignore

        return boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        )

    def save_file(
        self,
        file_stream: BinaryIO,
        relative_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        data = file_stream.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        extra_args = {"ContentType": content_type} if content_type else None
        self._client().put_object(
            Bucket=self.bucket,
            Key=relative_path,
            Body=data or b"",
            **(extra_args or {}),
        )
        return relative_path

    def generate_url(self, relative_path: str, expires_in: int = 3600) -> str:
        return self._client().generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": relative_path},
            ExpiresIn=expires_in,
        )

    def delete(self, relative_path: str) -> None:
        self._client().delete_object(Bucket=self.bucket, Key=relative_path)


def get_storage_service() -> BaseStorageDriver:
    driver = (current_app.config.get("STORAGE_DRIVER") or "LOCAL").upper()
    if driver == "S3":
        return S3StorageDriver()
    return LocalStorageDriver()
