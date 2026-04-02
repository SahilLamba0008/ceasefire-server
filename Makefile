-include .docker-env
export TAG
TAG ?= latest

COMPOSE     = docker-compose -f infra/docker-compose.yml
COMPOSE_DEV = $(COMPOSE) -f infra/docker-compose.dev.yml
REGISTRY    = dushyantpant
API_IMG     = $(REGISTRY)/clipforge-api
WORKER_IMG  = $(REGISTRY)/clipforge-worker

.PHONY: dev dev-java dev-full dev-local build down logs migration check check-java check-python check-db

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

dev-local: build  ## Integration test: build :local images and start all services in Docker (no mounts)
	TAG=local $(COMPOSE) up

down:         ## Stop all services
	$(COMPOSE) down

logs:         ## Follow logs from all services
	$(COMPOSE) logs -f

migration:    ## Create a new Flyway migration file
	@python scripts/new_migration.py

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
