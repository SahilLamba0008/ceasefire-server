# Docker Setup Guide

## Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git access to this repository

---

## First-time Setup

**1. Clone the repository**
```bash
git clone https://github.com/SahilLamba0008/ceasefire-server.git
cd ceasefire-server
```

**2. Set up environment variables**
```bash
cp .env.example .env
cp .docker-env.example .docker-env
```
Edit `.env` if needed (defaults work for local development out of the box).
Edit `.docker-env` to pin a specific image tag (default is `latest`).

**3. Pull the latest images and start everything**
```bash
make dev
```

That's it. All 4 services are now running:
- API → http://localhost:8080
- RabbitMQ UI → http://localhost:15672 (guest / guest)
- PostgreSQL → localhost:5432
- Worker → running in background

---

## Daily Commands

| Command | When to use |
|---|---|
| `make dev` | **Python dev** — pulls latest registry images, starts all services, mounts `services/worker/` live |
| `make dev-java` | **Java dev** — starts infra + registry worker (stable, no mount), run API on host |
| `make dev-full` | **Working on both** — starts infra + live worker mount, run API on host |
| `make dev-local` | **Integration test** — builds `:local` images and starts everything in Docker (no mounts) |
| `make build` | Build images locally (tagged `:local`, never touches registry `:latest`) |
| `make down` | Stop all services |
| `make logs` | Follow logs from all services |
| `make migrate-info` | Check which migrations are applied / pending (read-only, safe anytime) |
| `make migrate` | Apply pending migrations to local DB (run after `git pull`) |

---

## Development Workflows

### Working on Python Worker only
```bash
make dev
```
Your local `services/worker/` is mounted into the container and `watchfiles` watches for `.py` changes — the worker restarts automatically on every save. The API runs from the latest registry image; you don't need to build it.

**When you need to rebuild the worker image** (e.g. added a new dependency to `requirements.txt`):
```bash
cd infra && docker compose build --no-cache worker && docker compose up -d --force-recreate worker
```

### Working on Java API only
```bash
make dev-java
```
Starts postgres, rabbitmq, and the **registry** worker image (stable, no local mount). Then run the API on your host:
```bash
cd services/api
./gradlew bootRun
```
Spring Boot DevTools will hot-reload on file changes.

### Working on both Python Worker and Java API
```bash
make dev-full
```
Starts postgres, rabbitmq, and the worker with your **live local code mounted**. Then run the API on your host:
```bash
cd services/api
./gradlew bootRun
```
Changes to either service are reflected immediately without rebuilding images.

### Integration Testing (all services in Docker)
When you want to test your local changes with everything running inside Docker:
```bash
make dev-local
```
Builds `:local` images from your source and starts all 4 services. No volume mounts — tests the actual built image.

---

## Pinning to a specific commit snapshot

CI/CD tags every image with two tags on each merge to `develop`:
- `:latest` — always the newest build
- `:<commit-sha>` — a frozen snapshot of that exact commit (e.g. `a1b2c3d`)

To pin your local environment to a specific snapshot, edit `.docker-env`:
```bash
TAG=a1b2c3d
```
Then `make dev` will pull and run that exact build. Switch back to `TAG=latest` anytime.

---

## How Images Are Updated

**Developers never push Docker images manually.**

Images are only updated via CI/CD when a Pull Request is approved and merged into the `develop` branch. When you run `make dev`, it pulls whichever tag is set in `.docker-env` (default: `latest`).

If you notice your changes aren't reflected after `make dev`, check that your PR has been merged.

---

## Running Migrations After `git pull`

When you pull changes that include new migration scripts, apply them to your local DB before running the API.

**Step 1 — Make sure Postgres is running**
```bash
make dev-java
# or just the DB container alone:
docker-compose --env-file .env -f infra/docker-compose.yml up postgres
```

**Step 2 — Check what's pending (read-only, no DB changes)**
```bash
make migrate-info
```
Example output:
```
+-----------+---------+---------------------+------+---------------------+---------+
| Category  | Version | Description         | Type | Installed On        | State   |
+-----------+---------+---------------------+------+---------------------+---------+
| Versioned | 1       | init schema         | SQL  | 2026-04-10 12:00:00 | Success |
| Versioned | 2       | add users table     | SQL  |                     | Pending |
+-----------+---------+---------------------+------+---------------------+---------+
```
- `Success` — already applied, will not be touched
- `Pending` — will be applied by `make migrate`

**Step 3 — Apply pending migrations**
```bash
make migrate
```

> **Note:** You may see the following warnings in the output — these are harmless and can be ignored:
> ```
> WARNING: Storing migrations in 'sql' is not recommended...
> A more recent version of Flyway is available...
> ```
> The first is a deprecation notice for a future Flyway release (not yet in effect). The second is just an upgrade nudge. Neither affects functionality.

---

## Troubleshooting

**Services not starting / port already in use**
```bash
make down
make dev
```

**Want to see logs for a specific service**
```bash
docker-compose -f infra/docker-compose.yml logs -f worker
docker-compose -f infra/docker-compose.yml logs -f api
```

**Postgres data needs to be reset**
```bash
make down
docker volume rm ceasefire-server_postgres_data
make dev
```
