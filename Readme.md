# ClipForge Backend

Minimal backend monorepo with:
- `services/api` (Spring Boot API)
- `services/worker` (Python worker)
- `infra/docker-compose.yml` (Postgres + RabbitMQ + services)

## Start All Services (Recommended)
```bash
make dev
```

## Stop / Logs
```bash
make down
make logs
```

## Start Only Specific Services (Docker)
```bash
docker-compose -f infra/docker-compose.yml up -d postgres rabbitmq
docker-compose -f infra/docker-compose.yml up --build api
docker-compose -f infra/docker-compose.yml up --build worker
```

## Local Run (Without Docker for API/Worker)
1. Start dependencies first:
```bash
docker-compose -f infra/docker-compose.yml up -d postgres rabbitmq
```
2. Run API locally:
```powershell
cd services/api
$env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/clipforge"
$env:SPRING_DATASOURCE_USERNAME="postgres"
$env:SPRING_DATASOURCE_PASSWORD="postgres"
$env:SPRING_RABBITMQ_HOST="localhost"
mvn spring-boot:run
```
3. Run Worker locally:
```powershell
cd services/worker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:DB_HOST="localhost"
$env:RABBITMQ_HOST="localhost"
python main.py
```

## Install Requirements
- Docker flow: no manual install needed (images install dependencies).
- API local: Maven downloads dependencies during `mvn spring-boot:run` or `mvn clean package`.
- Worker local: run `pip install -r services/worker/requirements.txt`.

## Quick Checks
- API health: `http://localhost:8080/api/health`
- RabbitMQ UI: `http://localhost:15672`
- Worker logs should show:
  - `Worker started...`
  - `Polling for jobs...`

## File Status
- `services/api/Dockerfile`: correct for containerized API build/run.
- `services/worker/Dockerfile`: correct for worker install/run.
- `infra/docker-compose.yml`: correct for this minimal setup.
- `Makefile`: correct (`dev`, `down`, `logs`) and no change required.
