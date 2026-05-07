# API Service (Spring Boot)

## 🚀 Run with Docker

From the repo root:

```bash
docker-compose -f infra/docker-compose.yml up --build api
```

**Note:** This also starts `postgres` and `rabbitmq`.

---

## 🧑‍💻 Run Locally

### Prerequisites

- Java 21

---

### Start required services

From the repo root:

```bash
docker-compose -f infra/docker-compose.yml up -d postgres rabbitmq
cd services/api
```

---

### Run the application

#### PowerShell (Windows)

```powershell
$env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/clipforge"
$env:SPRING_DATASOURCE_USERNAME="postgres"
$env:SPRING_DATASOURCE_PASSWORD="postgres"
$env:SPRING_RABBITMQ_HOST="localhost"

.\gradlew bootRun
```

---

#### macOS / Linux

```bash
export SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/clipforge
export SPRING_DATASOURCE_USERNAME=postgres
export SPRING_DATASOURCE_PASSWORD=postgres
export SPRING_RABBITMQ_HOST=localhost

./gradlew bootRun
```

> If you get a permission error:

```bash
chmod +x gradlew
```

---

## 📦 Dependencies

- No manual installation required
- All dependencies are managed via `build.gradle`

---

## ✅ Health Check

Verify the API is running:

```
http://localhost:8080/api/health
```

Expected response:

```
API is running
```

---

## 🏗️ Build Commands

```bash
# macOS / Linux
./gradlew build

# Windows
.\gradlew build
# OR
gradlew build
```

---

## 🗄️ Database Migration

```bash
make migration
```

---

## 📁 Gradle Project Structure

### Required Files

- `build.gradle` → Defines dependencies and build logic
- `settings.gradle` → Defines project name and modules

Example:

```gradle
rootProject.name = 'my-app'
```

---

### Standard Directory Structure

```
project-root/
├── src/
│   ├── main/java/
│   └── test/java/
```

Without this structure, Gradle will not detect your source code properly.

---

### Gradle Wrapper (Important)

- `gradlew` → macOS / Linux
- `gradlew.bat` → Windows

These ensure a consistent Gradle version across all environments.

---

### Full Typical Setup

```
project-root/
├── build.gradle
├── settings.gradle
├── gradlew
├── gradlew.bat
├── gradle/
│    └── wrapper/
│         ├── gradle-wrapper.jar
│         └── gradle-wrapper.properties
└── src/
```

---

## ⚠️ Missing File Impact

| File              | Impact                         |
| ----------------- | ------------------------------ |
| `build.gradle`    | Project cannot build           |
| `settings.gradle` | Limited project configuration  |
| `gradlew`         | Requires global Gradle install |
| `gradlew.bat`     | Windows execution issues       |
| `wrapper/` folder | Gradle wrapper will not work   |

---

## 🧠 Notes

- Always use `gradlew` instead of `gradle`
- Avoid relying on globally installed Gradle
- Ensures consistent builds across machines and CI/CD
