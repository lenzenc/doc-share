# doc-share

Sharing Client Financial Documents

An MVP portal that lets a financial advisor's clients upload documents (statements, tax forms, IDs, etc.) needed to set up a retirement plan. Clients identify themselves with a **household ID**; uploads and lookups are scoped to that ID. No login is required for this MVP.

## The 60-second pitch

"Let clients send us documents" sounds like a simple ask — until it turns into a six-month platform project. This MVP proves that's a false choice. It's the whole workflow — **upload, store, index, retrieve** — running end-to-end, built in a single engineering session on three boring, battle-tested pieces of technology:

| Layer | Choice | Why it's the boring choice |
|---|---|---|
| API | FastAPI | Thin, typed, fast to iterate on |
| Object storage | MinIO (S3 API) | Same API as AWS S3 — swap providers later without touching a line of app code |
| Metadata | Postgres | The most well-understood relational database there is |

No custom file-handling framework, no bespoke storage layer, no premature microservices. That's the point: **the fastest way to de-risk a document-collection feature is to build the real thing on top of standard infrastructure, not to build a platform to build it on.**

**What this de-risks for the business, today:**
- The core client workflow (upload → confirmation → retrieval) is real and demoable, not a mockup.
- The data model (documents scoped to a household) is the actual shape this needs to take in production — extending it later is additive, not a rewrite.
- The storage choice (S3-compatible) means "point it at AWS instead of MinIO" is a config change, not a migration project.

**What's intentionally deferred — by design, not oversight:**
Client authentication, virus scanning, and audit logging are the next increment, not a hidden gap. See [Out of scope for this MVP](#out-of-scope-for-this-mvp) below for the specific, named punch list. Calling this out explicitly is what makes it safe to demo now and harden deliberately before real client data ever touches it.

**The takeaway for tech leadership:** this is what "build the MVP, not the platform" looks like in practice — a working feature in days, a clear list of what's left before production, and an architecture that doesn't have to be thrown away to get there.

## Architecture

- **Frontend:** static HTML/CSS/vanilla JS (`frontend/`) served by FastAPI — an upload page and a documents list page.
- **Backend:** FastAPI (`app/`), SQLAlchemy 2.0 + Alembic migrations against Postgres, boto3 against MinIO (S3-compatible object storage).
- **Storage model:** each uploaded file is written to MinIO under `{household_id}/{uuid}-{filename}`; a row referencing it is written to the `documents` table in Postgres.
- **Orchestration:** `docker compose` runs Postgres and MinIO (plus a one-shot bucket-creation step) for local dev. The API itself runs directly on the host via `uv run uvicorn`, not in a container.

## Running locally

```
cp .env.example .env
make up      # starts Postgres + MinIO in docker
make dev     # runs migrations, then starts the API on the host with autoreload
```

Then open:
- `http://localhost:8000/upload.html` — upload documents for a household
- `http://localhost:8000/documents.html` — list/download a household's documents
- `http://localhost:9001` — MinIO console (login with the `MINIO_ROOT_USER`/`PASSWORD` from `.env`)

Run `make` (no target) or open the `Makefile` for the full list of commands (`migrate`, `revision`, `psql`, `logs`, `clean`, ...).

## Upload rules

- Allowed types: PDF, PNG, JPG, DOCX, XLSX.
- Max size: 25 MB per file.

## Out of scope for this MVP

Authentication, virus scanning, per-advisor access control, encryption-at-rest key management, and audit logging are not implemented. Given the sensitivity of client financial documents, these should be addressed before any production use.
