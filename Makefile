-include .docker-env
-include .env
export TAG
export GEMINI_API_KEY
export YOUTUBE_API_KEY
TAG ?= latest

COMPOSE     = docker-compose -f infra/docker-compose.yml
COMPOSE_DEV = $(COMPOSE) -f infra/docker-compose.dev.yml
REGISTRY    = dushyantpant
API_IMG     = $(REGISTRY)/clipforge-api
WORKER_IMG  = $(REGISTRY)/clipforge-worker

.PHONY: dev dev-java dev-full dev-local build down logs migration migrate migrate-info migrate-to check check-java check-python check-db

dev:          ## Python dev: pull images for current TAG, start all (worker gets live code mount)
	$(COMPOSE_DEV) pull
	$(COMPOSE_DEV) up

dev-java:     ## Java dev: start infra + registry worker, then run API on host with ./gradlew bootRun
	$(COMPOSE) up postgres rabbitmq worker

dev-full:     ## Python + Java dev: live worker mount + infra only (run API on host with ./gradlew bootRun)
	$(COMPOSE_DEV) up postgres rabbitmq worker

build:        ## Build images locally (tagged :local — registry :latest is never touched)
	docker build -t $(API_IMG):local services/api
	docker build -t $(WORKER_IMG):local services/worker

dev-local-windows: build  ## Integration test: build :local images and start all services in Docker (no mounts)
	set TAG=local&& $(COMPOSE) up

dev-local-linux: build  ## Integration test: build :local images and start all services in Docker (no mounts)	
	set TAG=local $(COMPOSE) up

down:         ## Stop all services
	$(COMPOSE) down

logs:         ## Follow logs from all services
	$(COMPOSE) logs -f

migration:    ## Create a new Flyway migration file
	@python scripts/new_migration.py

migrate-info: ## Show migration status without applying anything (safe to run anytime)
	docker run --rm \
	  --network host \
	  -v "$(PWD)/services/api/src/main/resources/db/migration:/flyway/sql" \
	  flyway/flyway:10 \
	  -url=jdbc:postgresql://localhost:$${DB_PORT:-5432}/$${DB_NAME:-clipforge} \
	  -user=$${DB_USER:-postgres} \
	  -password=$${DB_PASSWORD:-postgres} \
	  info

migrate:      ## Apply pending Flyway migrations to local DB (run after git pull)
	docker run --rm \
	  --network host \
	  -v "$(PWD)/services/api/src/main/resources/db/migration:/flyway/sql" \
	  flyway/flyway:10 \
	  -url=jdbc:postgresql://localhost:$${DB_PORT:-5432}/$${DB_NAME:-clipforge} \
	  -user=$${DB_USER:-postgres} \
	  -password=$${DB_PASSWORD:-postgres} \
	  migrate

migrate-to:   ## Apply migrations up to a specific version: make migrate-to VERSION=3
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required. Usage: make migrate-to VERSION=3" && exit 1)
	docker run --rm \
	  --network host \
	  -v "$(PWD)/services/api/src/main/resources/db/migration:/flyway/sql" \
	  flyway/flyway:10 \
	  -url=jdbc:postgresql://localhost:$${DB_PORT:-5432}/$${DB_NAME:-clipforge} \
	  -user=$${DB_USER:-postgres} \
	  -password=$${DB_PASSWORD:-postgres} \
	  -target=$(VERSION) \
	  migrate

# ── Local CI checks ───────────────────────────────────────────────────────────

check-java:   ## Run Java CI checks locally (compile, test, docker build)
	cd services/api && gradle test
	docker build -t $(API_IMG):local services/api

check-python: ## Run Python CI checks locally (lint, docker build)
	pip install ruff
	cd services/worker && ruff check .
	docker build -t $(WORKER_IMG):local services/worker

check-db:     ## Run DB checks locally (naming, duplicates, SQL security)
	python scripts/validate_migrations.py

check: check-java check-python check-db  ## Run all CI checks locally
