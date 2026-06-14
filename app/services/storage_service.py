"""
StorageService — MinIO wrapper with correct presigned URL generation.

ROOT CAUSE OF 403s
------------------
Presigned URLs embed the host in the HMAC signature (via X-Amz-SignedHeaders=host).
The upload client uses the Docker-internal "minio:9000" — correct for TCP inside
Docker, wrong for signing URLs that Flutter fetches from outside.

THE FIX
-------
• _upload_client  — "minio:9000"  — used for put_object / bucket ops only.
• Presigning      — done with boto3's generate_presigned_url, pointed at
                    MINIO_PUBLIC_ENDPOINT ("localhost:9000" or LAN IP).
                    boto3 computes the signature locally (pure crypto, no HTTP
                    connection made) so it works even though the public endpoint
                    isn't reachable from inside Docker.

boto3 is already a transitive dependency of most Python ML stacks; if it isn't
in your requirements.txt, add: boto3>=1.26
"""

import io
import uuid
from datetime import timedelta
from urllib.parse import urlparse

import boto3
from botocore.config import Config as BotoConfig
from minio import Minio

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        # ── Upload client (internal Docker network) ──────────────────────────
        # Used for put_object, bucket_exists, make_bucket.
        # "minio:9000" resolves correctly inside the Docker network.
        self._upload_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        # ── Presign client (public hostname) ────────────────────────────────
        # boto3 generate_presigned_url is pure crypto — it computes the HMAC
        # signature locally and never opens a TCP connection to the endpoint.
        # This means it works fine even though MINIO_PUBLIC_ENDPOINT
        # ("localhost:9000") is not reachable from inside the container.
        scheme = "https" if settings.MINIO_SECURE else "http"
        self._presign_s3 = boto3.client(
            "s3",
            endpoint_url=f"{scheme}://{settings.MINIO_PUBLIC_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            region_name="us-east-1",           # MinIO ignores region but boto3 requires one
            config=BotoConfig(
                signature_version="s3v4",
                # Disable any boto3 connectivity checks / retries —
                # we never want this client to make real HTTP calls.
                retries={"max_attempts": 0},
            ),
        )

        self.bucket = settings.MINIO_BUCKET_NAME
        self._ensure_bucket()

    # ── Bucket bootstrap ──────────────────────────────────────────────────────

    def _ensure_bucket(self) -> None:
        try:
            if not self._upload_client.bucket_exists(self.bucket):
                self._upload_client.make_bucket(self.bucket)
        except Exception as exc:
            print(f"[StorageService] bucket check: {exc}")

    # ── Public API ────────────────────────────────────────────────────────────

    def upload_image(self, file_data: bytes, content_type: str) -> dict:
        """
        Upload bytes to MinIO and return a presigned GET URL valid for 7 days.
        The URL is signed for MINIO_PUBLIC_ENDPOINT, ready for Flutter to use
        directly with no hostname rewriting.
        """
        ext = ".jpg" if "jpeg" in content_type else ".png"
        image_id = str(uuid.uuid4())
        filename = f"{image_id}{ext}"

        self._upload_client.put_object(
            bucket_name=self.bucket,
            object_name=filename,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )

        url = self._presign(filename)
        return {"image_id": image_id, "filename": filename, "url": url, "size": len(file_data)}

    def get_fresh_url(self, stored_url: str) -> str:
        """
        Re-sign a stored URL.  Only the object name matters — the old host,
        old signature, and old expiry are all discarded.
        """
        try:
            object_name = urlparse(stored_url).path.rstrip("/").split("/")[-1]
            if not object_name:
                return stored_url
            return self._presign(object_name)
        except Exception as exc:
            print(f"[StorageService] get_fresh_url failed: {exc}")
            return stored_url

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _presign(self, object_name: str, expires_seconds: int = 7 * 24 * 3600) -> str:
        """
        Generate a presigned GET URL using boto3 (pure local computation,
        no HTTP connection).  Signed for MINIO_PUBLIC_ENDPOINT so Flutter
        can fetch it directly.
        """
        return self._presign_s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_name},
            ExpiresIn=expires_seconds,
        )


# Singleton
storage_service = StorageService()
