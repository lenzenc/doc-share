from functools import lru_cache

import boto3
from botocore.client import Config as BotoConfig

from app.config import get_settings


def _build_client(endpoint_url: str):
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name=settings.minio_region,
        config=BotoConfig(signature_version="s3v4"),
    )


@lru_cache
def get_s3_client():
    """Client used for server-side operations (upload), reaching MinIO over
    the docker network."""
    return _build_client(get_settings().minio_endpoint)


@lru_cache
def get_presigning_client():
    """Client used only to sign download URLs. Uses the publicly-reachable
    endpoint since the resulting URL is followed by the client's browser,
    not the API container."""
    return _build_client(get_settings().minio_public_endpoint)


def upload_fileobj(fileobj, bucket: str, object_key: str, content_type: str) -> None:
    client = get_s3_client()
    client.upload_fileobj(
        fileobj, bucket, object_key, ExtraArgs={"ContentType": content_type}
    )


def presigned_download_url(bucket: str, object_key: str, expires_in: int) -> str:
    client = get_presigning_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=expires_in,
    )
