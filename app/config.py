from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://doc_share:doc_share@localhost:5432/doc_share"
    )

    # Used by the API container to talk to MinIO over the docker network.
    minio_endpoint: str = "http://localhost:9000"
    # Used when generating presigned URLs, which are followed by the client's
    # browser and therefore must resolve outside the docker network.
    minio_public_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "doc-share"
    minio_region: str = "us-east-1"

    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB
    allowed_content_types: str = (
        "application/pdf,"
        "image/png,"
        "image/jpeg,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    presigned_url_expiry_seconds: int = 300

    @property
    def allowed_content_types_set(self) -> set[str]:
        return {ct.strip() for ct in self.allowed_content_types.split(",") if ct.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
