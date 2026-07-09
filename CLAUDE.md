# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**doc-share** — an MVP portal for a financial advisor's clients to upload documents (statements, tax forms, IDs) used to set up a retirement plan. Clients identify themselves with a **household ID**; all uploads and lookups are scoped to that ID. There is intentionally **no authentication** in this MVP — treat the domain (client financial documents) as sensitive when extending it, and don't add auth-adjacent shortcuts (e.g. trusting a client-supplied household ID for anything beyond scoping reads/writes) without discussing the security model first.

## Environment

- Python **3.14+** (`requires-python = ">=3.14"`, pinned via `.python-version`).
- Tooling is **uv**. Use `uv run` (not bare `python`), `uv add` (not `pip install`), and `uv remove`. Do not activate the venv manually.

## Commands

Infra (Postgres + MinIO) runs in Docker; the API itself runs directly on the host via `uv run` — there is no API container or Dockerfile.

- `make up` — start Postgres + MinIO (+ one-shot bucket creation) via `docker compose`
- `make dev` — run `alembic upgrade head` then start the API locally with `uvicorn --reload`
- `make migrate` — run migrations against the running infra (without starting the API)
- `make revision m="message"` — autogenerate a new Alembic migration from model changes
- `make psql` — psql shell into the Postgres container
- `make down` / `make logs` / `make restart` — infra lifecycle
- `make clean` — `docker compose down -v` (destroys Postgres + MinIO volumes)

`cp .env.example .env` first — the API reads config from `.env` via `pydantic-settings`.

No test suite exists yet. When adding tests, prefer `uv add --dev pytest` and run with `uv run pytest`.

## Architecture

- **`app/main.py`** — FastAPI app. Mounts `frontend/` as static files at `/` and includes the documents router. `/` redirects to `/upload.html`.
- **`app/routers/documents.py`** — the entire API surface: `POST /api/documents` (multipart upload, one or more files + `household_id`), `GET /api/documents?household_id=` (list, newest first), `GET /api/documents/{id}/download` (302 to a presigned MinIO URL).
- **`app/storage.py`** — boto3 S3 client wrapper. There are two separate clients/endpoints — `get_s3_client()` (`MINIO_ENDPOINT`, used for actual upload operations) and `get_presigning_client()` (`MINIO_PUBLIC_ENDPOINT`, used only to sign download URLs). Since the API now runs on the host, both default to `localhost:9000` and are equivalent today — the split exists because a presigned URL is followed directly by the client's *browser*, so if the API is ever containerized again while MinIO's internal hostname differs from what's browser-reachable, only `MINIO_PUBLIC_ENDPOINT` needs to change.
- **`app/models.py` / `app/database.py`** — one table, `documents` (household_id, original_filename, content_type, size_bytes, bucket, object_key, uploaded_at). Sync SQLAlchemy engine/session (not async) — path operations are plain `def`, letting FastAPI run them in a threadpool.
- **`app/config.py`** — `pydantic-settings` `Settings`, sourced from `.env`. Includes the upload allowlist (`allowed_content_types_set`) and the 25 MB size cap enforced in the upload router.
- **`alembic/`** — `env.py` is wired to `app.config.get_settings().database_url` and `app.database.Base.metadata`; migrations are written by hand in this repo rather than always relying on autogenerate (see `0001_create_documents.py`, which also creates the `pgcrypto` extension for `gen_random_uuid()`).
- **`frontend/`** — two static pages (`upload.html`, `documents.html`) sharing `css/styles.css`; each has its own vanilla-JS file (`js/upload.js`, `js/documents.js`) that calls the API via `fetch`. No build step.

## Conventions worth preserving

- Upload validation (content-type allowlist + 25 MB cap) happens server-side in `_validate_upload` (`app/routers/documents.py`) — the client-side `accept` attribute on the file input is a UX hint only, not a security boundary.
- New object storage or DB config should go through `app/config.py`'s `Settings`, not hardcoded, and should be reflected in `.env.example`.
- Migrations are additive/hand-written to date; if you add a model field, add a corresponding Alembic revision rather than relying purely on `create_all`.
