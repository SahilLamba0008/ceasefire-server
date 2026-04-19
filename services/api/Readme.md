# API Service (Spring Boot)

## Run In Docker

From repo root:

```bash
docker-compose -f infra/docker-compose.yml up --build api
```

Note: this also starts `postgres` and `rabbitmq` (via `depends_on`).

## Run Locally

Prerequisites:

- Java 21
- Gradle

From repo root:

```bash
docker-compose -f infra/docker-compose.yml up -d postgres rabbitmq
cd services/api
```

PowerShell env + run:

```powershell
$env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/clipforge"
$env:SPRING_DATASOURCE_USERNAME="postgres"
$env:SPRING_DATASOURCE_PASSWORD="postgres"
$env:SPRING_RABBITMQ_HOST="localhost"
gradle bootRun
```

## Dependencies

- No manual package install command needed.
- Gradle resolves dependencies from `build.gradle` automatically.

## Check

- `http://localhost:8080/api/health` should return `API is running`.

## Build Command for Java Project

```
.\gradlew build
```
## Run DB migration
```
make migration
```