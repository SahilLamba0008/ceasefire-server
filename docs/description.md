# 🚀 ClipForge Backend

ClipForge is an AI-powered system that converts long-form content (YouTube videos, podcasts, etc.) into short-form clips (Shorts/Reels) with captions, hooks, and metadata.

This repository contains the **backend system**, built using a **monorepo + microservices architecture**.

---

# 🧠 Core Concepts

## Monorepo vs Microservices

This project uses:

- **Monorepo (Code Level)**  
  → All backend services live in a single repository

- **Microservices (Runtime Level)**  
  → Each service runs independently and communicates over network (HTTP / queues)

```
Git Level → Monorepo
Runtime Level → Microservices
```

---

# 🏗️ High-Level Architecture

Client :
→ Next.js (Frontend)

Server :
→ Java API (Spring Boot)
→ RabbitMQ (Queue)
→ Python Worker (Processing)
→ Storage (Local → S3)
→ Results returned to user

---

# 📦 Services Overview

| Service    | Tech Stack         | Responsibility                                    |
| ---------- | ------------------ | ------------------------------------------------- |
| API        | Java (Spring Boot) | Handles HTTP requests, job orchestration          |
| Worker     | Python             | Handles ingestion, AI processing, video rendering |
| PostgreSQL | Database           | Stores jobs, clips, metadata                      |
| RabbitMQ   | Message Broker     | Handles async task queues                         |

---

# ⚙️ Why This Architecture?

## 1. Separation of Concerns

- Java → request handling + orchestration
- Python → compute-heavy tasks (AI, video processing)

## 2. Scalability

- Workers can scale independently
- Queue ensures async processing
- System can handle spikes in workload

## 3. Fault Tolerance

- Jobs are retried via queues
- Services are decoupled

---

# 🧩 Why NOT Turborepo / Nx?

We are NOT using tools like Turborepo or Nx because:

- They are optimized for **JavaScript/TypeScript ecosystems**
- Our stack is **polyglot**:
  - Java (Maven/Gradle)
  - Python (pip)
- Each service already has its own:
  - build system
  - dependency manager

👉 Docker + Compose already solve orchestration better for backend systems.

---

# 🗂️ Repository Structure
```
clipforge-backend/
├── services/
│ ├── api/ # Java Spring Boot service
│ └── worker/ # Python worker service
│
├── infra/
│ └── docker-compose.yml
│
├── Makefile # Dev commands shortcut
├── .env # Environment variables
└── README.md
```
---

# 🐳 Infrastructure (Docker-Based)

We use **Docker Compose** to run all services locally.

## Why Docker?

- No need to install Java, Python, PostgreSQL manually
- Same environment for all developers
- Easy deployment later

---

# 🔄 Data Flow (Step-by-Step)

1. User submits a YouTube URL
2. API creates a job in DB
3. API pushes job to RabbitMQ
4. Worker consumes job
5. Worker:
   - Downloads video
   - Transcribes audio
   - Runs AI analysis
   - Generates clips
6. Clips stored in filesystem (later S3)
7. API returns results to frontend

---

# 🐍 Worker Design

Single Python service handles:

- `ingest.py` → video download
- `transcribe.py` → speech-to-text
- `analyze.py` → AI segmentation
- `render.py` → clip generation
- `main.py` → queue consumer

👉 This is intentional for MVP simplicity  
👉 Can be split into multiple services later

---

# 📡 Communication

- API → Worker: via RabbitMQ
- Worker → DB: direct updates
- Worker → Storage: filesystem

---

# 🧪 Local Development Setup

## Prerequisites

- Docker
- Docker Compose
- Make (optional but recommended)

---

## 🔥 Start the System

```bash
make dev
```

OR manually:

```bash
make down
```

# 📜 View Logs

```bash
make logs
```

# 🌐 Local Services

Service URL

API: http://localhost:8080

RabbitMQ UI: http://localhost:15672

PostgreSQL: http://localhost:5432

# 🧠 Makefile Explained

Makefile is just a shortcut layer.

Instead of writing long commands:

```
docker-compose -f infra/docker-compose.yml up --build
```

You run:

```
make dev
```

# ⚡ Development Workflow

### 1. Run system:

```
make dev
```

### 2. Modify code in:

- services/api
- services/worker

### 3. Restart if needed:

```
make restart
```

### 4. Debug using logs:

```
make logs
```

# 🚀 Scaling Strategy (Future)

| Stage      | Setup                             |
| ---------- | --------------------------------- |
| MVP        | Single worker                     |
| Growth     | Multiple worker replicas          |
| Scale      | Split workers (ingest, AI, video) |
| Production | Kubernetes / ECS                  |

# 💾 Storage Strategy

| Stage      | Storage                   |
| ---------- | ------------------------- |
| MVP        | Local filesystem          |
| Production | AWS S3 / Free Alternative |

# 🧠 Key Design Decisions
- Queue-based architecture → async & scalable
- Polyglot services → best tool for each job
- Docker-first → environment consistency
- Monorepo → easier team collaboration

# ⚠️ What We Are NOT Doing (Yet)
- Kubernetes
- Multiple worker services
- Redis caching
- Complex CI/CD pipelines
- Auto-scaling

> 👉 Focus is on working MVP first

# 🎯 Goals (Phase 1)
- End-to-end pipeline working
- Generate 3–5 clips per video
- Stable local setup
- First 10 users