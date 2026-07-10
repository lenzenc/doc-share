.PHONY: up down logs restart dev migrate revision psql fmt clean audit-verify

up: ## Start Postgres + MinIO (infra only; API runs locally, see `make dev`)
	docker compose up -d

down: ## Stop infra, keep volumes
	docker compose down

logs: ## Tail infra logs
	docker compose logs -f

restart: ## Restart infra
	docker compose restart

dev: ## Run migrations, then start the API locally with autoreload (Ctrl-C stops it cleanly)
	uv run alembic upgrade head
	exec uv run uvicorn app.main:app --reload

migrate: ## Run alembic migrations against the running infra
	uv run alembic upgrade head

revision: ## Autogenerate a new migration: make revision m="add x"
	uv run alembic revision --autogenerate -m "$(m)"

psql: ## Open a psql shell against the postgres container
	docker compose exec postgres psql -U doc_share -d doc_share

fmt: ## Format the codebase (requires uv add --dev ruff)
	uv run ruff format .

clean: ## Tear down containers and volumes (destructive: wipes db + minio data)
	docker compose down -v

audit-verify: ## Verify the audit event hash chain is intact (exits non-zero on tamper)
	uv run python -m app.audit_verify
