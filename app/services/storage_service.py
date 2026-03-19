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
# """
# StorageService — MinIO wrapper with correct presigned URL generation.

# ROOT CAUSE OF 403s
# ------------------
# Presigned URLs embed the host in both the Credential scope and the signature
# itself (via X-Amz-SignedHeaders=host). When the Minio client is initialised
# with the Docker-internal hostname "minio:9000", every URL it generates carries
# that host in the signature.  Flutter rewrites the URL string to "localhost:9000"
# before making the HTTP request, but the Host header it sends is "localhost:9000"
# while the signature was computed for "minio:9000" → MinIO rejects with 403.

# THE FIX
# -------
# Two separate Minio client instances:
#   • _upload_client  — uses MINIO_ENDPOINT ("minio:9000")
#                       Used only for put_object / bucket ops that stay inside Docker.
#   • _presign_client — uses MINIO_PUBLIC_ENDPOINT ("localhost:9000" or LAN IP)
#                       Used only for get_presigned_url.
#                       Generates a URL already containing the public host, so no
#                       hostname rewriting is needed in Flutter at all.

# The two clients share credentials.  The only difference is the endpoint.
# """

# import io
# import uuid
# from datetime import timedelta
# from urllib.parse import urlparse

# from minio import Minio

# from app.core.config import settings


# class StorageService:
#     def __init__(self) -> None:
#         shared_kwargs = dict(
#             access_key=settings.MINIO_ACCESS_KEY,
#             secret_key=settings.MINIO_SECRET_KEY,
#             secure=settings.MINIO_SECURE,
#         )

#         # Internal client — for uploads and bucket management inside Docker
#         self._upload_client = Minio(settings.MINIO_ENDPOINT, **shared_kwargs) # type: ignore

#         # Public client — for presigning only.
#         # Generates URLs with MINIO_PUBLIC_ENDPOINT in the host + credential,
#         # so the signature is valid when the client fetches the URL directly.
#         self._presign_client = Minio(settings.MINIO_PUBLIC_ENDPOINT, **shared_kwargs) # type: ignore

#         self.bucket = settings.MINIO_BUCKET_NAME
#         self._ensure_bucket()

#     # ------------------------------------------------------------------
#     # Bucket bootstrap
#     # ------------------------------------------------------------------

#     def _ensure_bucket(self) -> None:
#         """Create the bucket if it doesn't exist yet."""
#         try:
#             if not self._upload_client.bucket_exists(self.bucket):
#                 self._upload_client.make_bucket(self.bucket)
#         except Exception as exc:
#             # Non-fatal on startup — the bucket probably already exists
#             print(f"[StorageService] bucket check: {exc}")

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------

#     def upload_image(self, file_data: bytes, content_type: str) -> dict:
#         """
#         Upload bytes to MinIO and return a presigned URL valid for 7 days.

#         The URL is signed with MINIO_PUBLIC_ENDPOINT so it can be fetched
#         directly by Flutter without any hostname rewriting.
#         """
#         ext = ".jpg" if "jpeg" in content_type else ".png"
#         image_id = str(uuid.uuid4())
#         filename = f"{image_id}{ext}"

#         # Upload via internal client (resolves "minio:9000" inside Docker)
#         self._upload_client.put_object(
#             bucket_name=self.bucket,
#             object_name=filename,
#             data=io.BytesIO(file_data),
#             length=len(file_data),
#             content_type=content_type,
#         )

#         url = self._presign(filename)
#         return {"image_id": image_id, "filename": filename, "url": url, "size": len(file_data)}

#     def get_fresh_url(self, stored_url: str) -> str:
#         """
#         Generate a fresh presigned URL for an object identified by its stored URL.

#         The stored URL may contain the old internal hostname — we only need the
#         object name (last path segment), then re-sign with the public client.
#         """
#         try:
#             path_parts = urlparse(stored_url).path.rstrip("/").split("/")
#             object_name = path_parts[-1]
#             if not object_name:
#                 return stored_url
#             return self._presign(object_name)
#         except Exception as exc:
#             print(f"[StorageService] get_fresh_url failed: {exc}")
#             return stored_url

#     # ------------------------------------------------------------------
#     # Internal helpers
#     # ------------------------------------------------------------------

#     def _presign(self, object_name: str, expires: timedelta = timedelta(days=7)) -> str:
#         """
#         Sign a GET URL using the PUBLIC client.

#         7-day expiry (S3/MinIO max for non-STS credentials) means history
#         thumbnails stay valid across typical app sessions without needing
#         constant re-signing.
#         """
#         return self._presign_client.get_presigned_url(
#             "GET",
#             self.bucket,
#             object_name,
#             expires=expires,
#         )


# # Singleton — imported everywhere as `from app.services.storage_service import storage_service`
# storage_service = StorageService()
# # import uuid
# # import io
# # from minio import Minio
# # from datetime import timedelta
# # from urllib.parse import urlparse
# # from app.core.config import settings

# # class StorageService:
# #     def __init__(self):
# #         self.client = Minio(
# #             settings.MINIO_ENDPOINT,
# #             access_key=settings.MINIO_ACCESS_KEY,
# #             secret_key=settings.MINIO_SECRET_KEY,
# #             secure=settings.MINIO_SECURE
# #         )
# #         self.bucket = settings.MINIO_BUCKET_NAME

# #     def upload_image(self, file_data: bytes, content_type: str) -> dict:
# #         """
# #         Uploads bytes to MinIO and returns metadata + presigned URL.
# #         """
# #         # 1. Generate unique filename (UUID)
# #         ext = ".jpg" if "jpeg" in content_type else ".png"
# #         image_id = str(uuid.uuid4())
# #         filename = f"{image_id}{ext}"
        
# #         # 2. Prepare stream
# #         file_stream = io.BytesIO(file_data)
# #         file_size = len(file_data)

# #         # 3. Upload to MinIO
# #         self.client.put_object(
# #             bucket_name=self.bucket,
# #             object_name=filename,
# #             data=file_stream,
# #             length=file_size,
# #             content_type=content_type
# #         )

# #         # 4. Generate Presigned URL (Valid for 1 hour)
# #         # This allows the frontend to display the image even if the bucket is private
# #         url = self.client.get_presigned_url(
# #             "GET",
# #             self.bucket,
# #             filename,
# #             expires=timedelta(hours=1)
# #         )

# #         return {
# #             "image_id": image_id,
# #             "filename": filename,
# #             "url": url,
# #             "size": file_size
# #         }
    
# #     def get_fresh_url(self, expired_url: str) -> str:
# #         """
# #         Extracts filename from an old URL and generates a new presigned URL.
# #         """
# #         try:
# #             # 1. Parse the URL to get the path
# #             parsed = urlparse(expired_url)
# #             path_parts = parsed.path.split('/')
            
# #             # 2. Extract object name (last part of path)
# #             # URL is usually /bucket_name/filename.jpg
# #             if not path_parts:
# #                 return expired_url
                
# #             object_name = path_parts[-1]
            
# #             # 3. Generate new signed URL (valid for 1 hour from NOW)
# #             return self.client.get_presigned_url(
# #                 "GET",
# #                 self.bucket,
# #                 object_name,
# #                 expires=timedelta(hours=1)
# #             )
# #         except Exception as e:
# #             print(f"Failed to refresh URL: {e}")
# #             return expired_url

# # # Singleton instance
# # storage_service = StorageService()