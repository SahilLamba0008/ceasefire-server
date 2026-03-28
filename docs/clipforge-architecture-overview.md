# ClipForge — Architecture Overview

> **System Goal:** User provides a URL (YouTube video, podcast, or article) → System automatically generates multiple short-form videos (Shorts / Reels) with captions, hooks, and metadata.

---

## 1. Tech Stack Decision

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | Next.js (App Router) | SSR, file-based routing, server actions for form submissions |
| **API / Orchestrator** | Java 21 + Spring Boot 3 | Type-safe REST + WebSocket APIs, robust job orchestration, mature ecosystem for queues and DB |
| **Message Broker** | RabbitMQ (Docker) | Native AMQP support in Spring, dead-letter queues, per-queue concurrency — better Java interop than BullMQ |
| **Worker Services** | Python 3.12 | Best ecosystem for AI/ML (Whisper, ffmpeg-python, Ollama client) |
| **Database** | PostgreSQL 16 (Docker) | JSONB for flexible metadata, strong transactional guarantees |
| **Object Storage** | Local filesystem (MVP) → S3 (prod) | Docker volume mount for $0 MVP; interface-based swap to S3 later |
| **Transcription** | faster-whisper (local, free) | OpenAI Whisper-compatible, runs on CPU, no API key |
| **LLM** | Ollama + llama3.1:8b (local, free) | OpenAI-compatible API, runs in Docker, swap to GPT-4o later |
| **Cache / Pub-Sub** | Dropped for MVP | Use DB polling; add Redis when needed for WebSocket push |

### Why Java for Backend + Python for Workers?

```
Java Backend (Spring Boot)                 Python Workers
┌──────────────────────────┐              ┌──────────────────────────┐
│ • REST API surface       │              │ • faster-whisper (local)  │
│ • Auth / rate limiting   │  RabbitMQ    │ • Ollama (local LLM)     │
│ • Job orchestration      │◄────────────►│ • ffmpeg-python (video)  │
│ • DB transactions        │              │ • face-detection (dlib)  │
│ • WebSocket / SSE        │              │ • PIL / moviepy          │
│ • File serving (MVP)     │              │                          │
└──────────────────────────┘              └──────────────────────────┘
       Strengths:                                Strengths:
  Strong typing, concurrency,              AI/ML libraries, rapid
  enterprise patterns, thread pools        prototyping, ffmpeg bindings
```

> **Rule of thumb:** Java owns the request lifecycle and state machine. Python owns compute-heavy AI and video work. They communicate exclusively through RabbitMQ + shared filesystem (never direct HTTP between them in the hot path). Swap filesystem → S3 later with a config flag.

---

## 2. High-Level Architecture

```
                                    ┌─────────────────┐
                                    │   Next.js App    │
                                    │  (App Router)    │
                                    └────────┬────────┘
                                             │ HTTPS
                                             ▼
                              ┌──────────────────────────────┐
                              │     Java API Gateway         │
                              │      (Spring Boot)           │
                              │                              │
                              │  • POST /api/jobs            │
                              │  • GET  /api/jobs/:id        │
                              │  • GET  /api/jobs/:id/clips  │
                              │  • WS   /ws/progress         │
                              └──────┬───────────┬───────────┘
                                     │           │
                              ┌──────┘           └──────┐
                              ▼                         ▼
                     ┌─────────────┐          ┌──────────────┐
                     │ PostgreSQL  │          │   RabbitMQ   │
                     │             │          │              │
                     │ • jobs      │          │ Exchanges:   │
                     │ • clips     │          │  pipeline.x  │
                     │ • users     │          │              │
                     │ • assets    │          │ Queues:      │
                     └─────────────┘          │  ingest.q    │
                                              │  transcribe.q│
                                              │  analyze.q   │
                                              │  render.q    │
                                              │  finalize.q  │
                                              └──────┬───────┘
                                                     │
                            ┌────────────────────────┼────────────────────────┐
                            │                        │                        │
                            ▼                        ▼                        ▼
                   ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
                   │  Ingest      │        │  AI Service   │        │  Video       │
                   │  Worker (Py) │        │  Worker (Py)  │        │  Worker (Py) │
                   │              │        │               │        │              │
                   │ • yt-dlp     │        │ • Whisper     │        │ • FFmpeg     │
                   │ • trafilatura│        │ • OpenAI LLM  │        │ • face-det.  │
                   │ • metadata   │        │ • segment ID  │        │ • captions   │
                   └──────┬───────┘        └──────┬────────┘        └──────┬───────┘
                          │                       │                        │
                          └───────────────────────┼────────────────────────┘
                                                  ▼
                                         ┌──────────────────┐
                                         │  Storage Layer   │
                                         │                  │
                                         │ MVP: local fs    │
                                         │ Prod: AWS S3     │
                                         │                  │
                                         │ /raw/            │
                                         │ /transcripts/    │
                                         │ /clips/          │
                                         │ /outputs/        │
                                         └──────────────────┘
```

---

## 3. Data Flow — Step by Step

```
Step  Who              Action                                          Queue / Storage
─────────────────────────────────────────────────────────────────────────────────────
 1    User → API       POST /api/jobs { url }                          → DB: job CREATED
 2    API              Validates URL, creates job row                  → publishes to ingest.q
 3    Ingest Worker    Picks up message                                ← ingest.q
      │                Downloads video/audio via yt-dlp                → S3: /raw/{jobId}/
      │                Extracts metadata (title, duration, thumbnail)  → DB: job INGESTED
      └──              Publishes next step                             → transcribe.q
 4    AI Worker        Picks up message                                ← transcribe.q
      │                Downloads audio from S3
      │                Runs Whisper → timestamped transcript           → S3: /transcripts/{jobId}.json
      │                Updates DB                                      → DB: job TRANSCRIBED
      └──              Publishes next step                             → analyze.q
 5    AI Worker        Picks up message                                ← analyze.q
      │                Sends transcript to LLM with prompt:
      │                  "Identify top 5 viral segments (30-60s)"
      │                  "For each: hook text, caption, hashtags"
      │                Parses structured LLM response                  → DB: clips[] ANALYZED
      └──              Publishes one message PER clip                  → render.q (×N)
 6    Video Worker     Picks up ONE clip message                       ← render.q
      │                Downloads source video segment from S3
      │                FFmpeg pipeline:
      │                  → Trim to segment timestamps
      │                  → Crop 9:16 (center or face-tracked)
      │                  → Burn in captions (ASS subtitle overlay)
      │                  → Optional: background music mix
      │                Uploads rendered clip                           → S3: /outputs/{jobId}/{clipId}.mp4
      └──              Updates clip status                             → DB: clip RENDERED
 7    API (listener)   When ALL clips for a job are RENDERED           → DB: job COMPLETED
                       Notifies frontend via WebSocket / SSE
 8    User ← Frontend  Previews clips, downloads, copies metadata
```

### Key Design Choices

- **Fan-out at step 5→6:** One analyze message produces N render messages. This lets multiple video workers process clips in parallel.
- **Each step is idempotent:** Workers check current state before processing. If a clip is already RENDERED, skip it. This makes retries safe.
- **Storage as the data bus:** Workers never send large payloads through RabbitMQ. They write to storage (local fs or S3) and pass only the file path/key in the message.
- **Ollama is OpenAI-compatible:** The AI worker uses the `openai` Python SDK pointed at Ollama's URL. Switching to GPT-4o later means changing one env var (`LLM_BASE_URL`).

---

## 4. Component Breakdown

### 4.1 Java API Gateway (Spring Boot)

```
src/main/java/com/clipforge/
├── controller/
│   ├── JobController.java          # REST endpoints
│   └── ProgressWebSocketHandler.java
├── service/
│   ├── JobService.java             # Business logic, state machine
│   ├── StorageService.java         # Interface: LocalStorage (MVP) or S3 (prod)
│   └── QueuePublisher.java         # RabbitMQ message publishing
├── model/
│   ├── Job.java                    # JPA entity
│   ├── Clip.java                   # JPA entity
│   └── enums/JobStatus.java
├── config/
│   ├── RabbitConfig.java           # Exchange, queue, binding setup
│   ├── SecurityConfig.java         # JWT auth
│   └── S3Config.java
└── listener/
    └── ClipCompletionListener.java # Listens for clip.rendered events
```

**Responsibilities:** Auth, validation, job state machine, file serving (MVP) or presigned URLs (prod), WebSocket push, dead-letter monitoring.

### 4.2 Python Workers (Shared Structure)

```
workers/
├── common/
│   ├── rabbit.py          # Pika connection, ack/nack helpers
│   ├── storage.py         # Local fs (MVP) or boto3 S3 (prod) — same interface
│   ├── db.py              # SQLAlchemy (lightweight, status updates only)
│   └── config.py          # Env-based config (STORAGE_TYPE=local|s3, LLM_BASE_URL, etc.)
├── ingest/
│   ├── handler.py         # yt-dlp download, metadata extraction
│   └── Dockerfile
├── ai/
│   ├── transcribe.py      # faster-whisper (local, free) — or OpenAI Whisper API for prod
│   ├── analyze.py         # Ollama (local, free) — or GPT-4o for prod. Same openai SDK.
│   └── Dockerfile
├── video/
│   ├── render.py          # FFmpeg pipeline orchestration
│   ├── face_track.py      # Optional dlib/mediapipe face detection
│   ├── captions.py        # ASS subtitle generation
│   └── Dockerfile
└── docker-compose.workers.yml
```

### 4.3 RabbitMQ Topology

```
Exchange: pipeline.topic (type: topic)
  │
  ├── routing_key: job.ingest      → Queue: ingest.q       → Ingest Worker
  ├── routing_key: job.transcribe  → Queue: transcribe.q    → AI Worker
  ├── routing_key: job.analyze     → Queue: analyze.q       → AI Worker
  ├── routing_key: clip.render     → Queue: render.q        → Video Worker (×N)
  └── routing_key: clip.finalize   → Queue: finalize.q      → Java Listener

Dead Letter Exchange: pipeline.dlx
  └── All failed messages → Queue: dead-letter.q → Monitoring / Manual retry
```

Each queue has:
- **Prefetch = 1** (one message at a time per worker, critical for heavy video work)
- **TTL = 30 min** on render.q (kill stuck jobs)
- **Max retries = 3** via `x-death` header counting, then route to DLX

---

## 5. Database Schema (PostgreSQL)

```sql
-- Users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    plan            VARCHAR(20) DEFAULT 'free',  -- free | pro | team
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Jobs (one per submitted URL)
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    source_url      TEXT NOT NULL,
    source_type     VARCHAR(20),                 -- youtube | podcast | article
    status          VARCHAR(20) DEFAULT 'created',
    -- Statuses: created → ingesting → transcribing → analyzing → rendering → completed | failed
    title           TEXT,                         -- extracted from source
    duration_sec    INTEGER,
    raw_asset_key   TEXT,                         -- S3 key for downloaded source
    transcript_key  TEXT,                         -- S3 key for transcript JSON
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_jobs_user_status ON jobs(user_id, status);

-- Clips (multiple per job)
CREATE TABLE clips (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID REFERENCES jobs(id) ON DELETE CASCADE,
    clip_index      INTEGER NOT NULL,            -- ordering within job
    status          VARCHAR(20) DEFAULT 'pending',
    -- Statuses: pending → rendering → rendered | failed
    start_time_ms   INTEGER NOT NULL,
    end_time_ms     INTEGER NOT NULL,
    hook_text       TEXT,                         -- LLM-generated hook (first 3s)
    title           TEXT,                         -- LLM-generated title
    caption         TEXT,                         -- LLM-generated description
    hashtags        TEXT[],                       -- LLM-generated
    output_key      TEXT,                         -- S3 key for rendered clip
    thumbnail_key   TEXT,
    metadata        JSONB DEFAULT '{}',           -- extensible (virality score, etc.)
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_clips_job ON clips(job_id);
```

### Entity Relationship

```
┌──────────┐       1:N        ┌──────────┐
│  users   │──────────────────│   jobs   │
└──────────┘                  └────┬─────┘
                                   │ 1:N
                              ┌────┴─────┐
                              │  clips   │
                              └──────────┘
```

---

## 6. Async Processing — How It Fits Together

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SYNCHRONOUS BOUNDARY                        │
│                                                                    │
│  User → Next.js → Java API → Validate → Insert DB → Publish msg   │
│                             ← Return jobId (HTTP 202 Accepted) ←   │
└─────────────────────────────────────────────────────────────────────┘
        │
        │  RabbitMQ
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       ASYNCHRONOUS BOUNDARY                        │
│                                                                    │
│  ingest.q → transcribe.q → analyze.q → render.q (×N) → finalize.q │
│                                                                    │
│  Each step:                                                        │
│    1. Consume message                                              │
│    2. Download assets from S3                                      │
│    3. Process                                                      │
│    4. Upload results to S3                                         │
│    5. Update DB status                                             │
│    6. Publish next message (or ack done)                           │
└─────────────────────────────────────────────────────────────────────┘
        │
        │  WebSocket / SSE
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend polls or receives push updates on job progress           │
└─────────────────────────────────────────────────────────────────────┘
```

### Progress Updates

Workers publish status changes to Redis Pub/Sub on channel `job:{jobId}:progress`. The Java API subscribes and forwards to connected WebSocket clients. This keeps the frontend live without polling.

```
Video Worker → Redis PUBLISH job:abc:progress '{"clip":2,"of":5,"status":"rendering"}'
                            │
Java WebSocket Handler ←────┘  → pushes to connected browser sessions
```

---

## 7. Scaling Strategy

### Horizontal Scaling Map (Production — not needed for MVP)

```
Component          Scale Axis           How
──────────────────────────────────────────────────────────
Next.js            Requests             Vercel / k8s replicas (stateless)
Java API           Requests             k8s replicas behind LB (stateless)
Ingest Workers     Download concurrency More pods (bound by network I/O)
AI Workers         Whisper + LLM calls  More pods (API rate limits or CPU)
Video Workers      FFmpeg rendering     More pods (CPU-bound, most expensive)
PostgreSQL         Read load            Read replicas
RabbitMQ           Message throughput   Cluster mode (rarely the bottleneck)
S3                 Storage              Infinite (managed service)
```

> **MVP:** All workers run as single containers on one machine. Scaling = buying a bigger box or spinning up a second one.

### Cost Optimization Priorities

```
 ┌────────────────────────────────────────────────────────────────┐
 │              COST RANKING (highest → lowest)                   │
 │                                                                │
 │  1. VIDEO RENDERING (FFmpeg CPU time)                          │
 │     → Use spot/preemptible instances for video workers         │
 │     → GPU instances only if doing face detection               │
 │     → Cache common operations (crop templates)                 │
 │                                                                │
 │  2. AI API CALLS (Whisper + GPT)                               │
 │     → Local Whisper (faster-whisper) for MVP to avoid API cost │
 │     → Batch LLM calls: one call for all segments, not per clip │
 │     → Cache transcripts (same URL = same transcript)           │
 │                                                                │
 │  3. STORAGE (S3)                                               │
 │     → Lifecycle policy: delete raw assets after 7 days         │
 │     → Keep only rendered outputs long-term                     │
 │     → Use S3 Intelligent Tiering                               │
 │                                                                │
 │  4. COMPUTE (API + Workers)                                    │
 │     → Auto-scale workers to zero when queue is empty           │
 │     → Right-size: ingest workers need network, not CPU         │
 └────────────────────────────────────────────────────────────────┘
```

---

## 8. Failure Handling & Retries

```
                    Message arrives at worker
                              │
                              ▼
                    ┌───────────────────┐
                    │  Process message  │
                    └────────┬──────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
              Success                  Failure
                 │                       │
                 ▼                       ▼
          ACK message          Check x-death count
          Update DB status              │
          Publish next step    ┌────────┴────────┐
                               │                 │
                          count < 3          count >= 3
                               │                 │
                               ▼                 ▼
                         NACK + requeue    Route to DLX
                         (exponential       Mark job FAILED
                          backoff via        Alert monitoring
                          message TTL)
```

### Per-Stage Failure Modes

| Stage | Common Failures | Mitigation |
|---|---|---|
| Ingest | URL blocked, rate limited, geo-restricted | Retry with backoff; proxy rotation; fail fast with clear error |
| Transcribe | Whisper timeout, OOM on long audio | Chunk audio into 10-min segments; retry with smaller chunks |
| Analyze | LLM rate limit, malformed response | Retry with backoff; validate JSON schema; fallback prompt |
| Render | FFmpeg crash, corrupt source, OOM | Retry once; if codec issue, re-encode source first |

### Idempotency Contract

Every worker checks the DB status before processing. If the expected state doesn't match, the message is acknowledged without work. This means duplicate messages (from retries or redelivery) are harmless.

```python
# Example: render worker
def handle_render(msg):
    clip = db.get_clip(msg.clip_id)
    if clip.status != 'pending':
        channel.basic_ack(msg.delivery_tag)  # already processed
        return
    # ... proceed with rendering
```

---

## 9. MVP vs Production

### MVP — Completely Free ($0/month)

The entire MVP runs on your local machine (or any single Linux box) with zero paid services.

#### Cost Audit: What Changes

```
┌──────────────────────────────────────────────────────────────────────────┐
│  COMPONENT        │  PAID VERSION       │  FREE MVP SWAP               │
├──────────────────────────────────────────────────────────────────────────┤
│  Object Storage   │  AWS S3 ($)         │  Local filesystem            │
│                   │                     │  /data/clipforge/{raw,out}   │
│                   │                     │  (Docker volume mount)       │
│──────────────────────────────────────────────────────────────────────────│
│  Transcription    │  OpenAI Whisper ($) │  faster-whisper (local)      │
│                   │  API                │  Runs on CPU, ~10x realtime  │
│                   │                     │  Model: whisper-small or     │
│                   │                     │  whisper-medium              │
│──────────────────────────────────────────────────────────────────────────│
│  LLM (segment     │  GPT-4o / Claude    │  Ollama + llama3.1:8b or    │
│  analysis, hooks,  │  API ($)           │  mistral:7b (runs local)    │
│  captions)        │                     │  Free, no API key needed    │
│──────────────────────────────────────────────────────────────────────────│
│  Database         │  RDS / Supabase ($) │  PostgreSQL in Docker (free)│
│──────────────────────────────────────────────────────────────────────────│
│  Message Broker   │  CloudAMQP ($)      │  RabbitMQ in Docker (free)  │
│──────────────────────────────────────────────────────────────────────────│
│  Cache            │  ElastiCache ($)    │  DROP for MVP               │
│  (Redis)          │                     │  Use DB polling instead     │
│──────────────────────────────────────────────────────────────────────────│
│  Frontend         │  Vercel Pro ($)     │  localhost:3000              │
│                   │                     │  (or Vercel free tier)       │
│──────────────────────────────────────────────────────────────────────────│
│  Hosting          │  AWS / GCP ($)      │  Your machine               │
│                   │                     │  docker-compose up           │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Free MVP Architecture (Simplified)

```
                          ┌─────────────────┐
                          │   Next.js App    │
                          │  localhost:3000  │
                          └────────┬────────┘
                                   │
                                   ▼
                        ┌────────────────────┐
                        │   Java API         │
                        │   localhost:8080   │
                        └──┬──────────┬──────┘
                           │          │
                    ┌──────┘          └──────┐
                    ▼                        ▼
           ┌──────────────┐        ┌──────────────┐
           │  PostgreSQL  │        │  RabbitMQ    │
           │  (Docker)    │        │  (Docker)    │
           └──────────────┘        └──────┬───────┘
                                          │
                       ┌──────────────────┼──────────────────┐
                       ▼                  ▼                  ▼
              ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
              │ Ingest       │   │ AI Worker    │   │ Video        │
              │ Worker (Py)  │   │ (Py)         │   │ Worker (Py)  │
              │              │   │              │   │              │
              │ • yt-dlp     │   │ • faster-    │   │ • FFmpeg     │
              │              │   │   whisper    │   │ • center-crop│
              └──────┬───────┘   │ • Ollama     │   │ • ASS subs   │
                     │           │   (HTTP)     │   └──────┬───────┘
                     │           └──────┬───────┘          │
                     │                  │                   │
                     └──────────────────┼───────────────────┘
                                        ▼
                               ┌──────────────────┐
                               │  Local Filesystem│
                               │                  │
                               │  ./data/         │
                               │   ├── raw/       │
                               │   ├── transcripts│
                               │   └── outputs/   │
                               └──────────────────┘

   + ┌──────────────┐
     │  Ollama       │   ← Separate container, exposes localhost:11434
     │  (Docker)     │     API-compatible, no key needed
     │  llama3.1:8b  │
     └──────────────┘
```

#### Free MVP docker-compose (6 containers, $0)

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: clipforge
      POSTGRES_PASSWORD: localdev

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports: ["5672:5672", "15672:15672"]     # management UI free at :15672

  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: ["ollama_models:/root/.ollama"]
    # Pull model on first run: docker exec ollama ollama pull llama3.1:8b

  api:
    build: ./api                             # Java Spring Boot
    depends_on: [postgres, rabbitmq]
    ports: ["8080:8080"]
    volumes: ["./data:/data/clipforge"]      # shared filesystem

  worker-ingest:
    build: ./workers/ingest
    depends_on: [rabbitmq]
    volumes: ["./data:/data/clipforge"]

  worker-ai:
    build: ./workers/ai
    depends_on: [rabbitmq, ollama]
    volumes: ["./data:/data/clipforge"]
    # faster-whisper model downloads on first run (~500MB for 'small')

  worker-video:
    build: ./workers/video
    depends_on: [rabbitmq]
    volumes: ["./data:/data/clipforge"]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [api]

volumes:
  pgdata:
  ollama_models:
```

#### Why workers have no ports (but API does)

```
WHO CALLS WHOM?

  Browser ──HTTP──► Java API (:8080)      ← Receives requests, so needs a port
  Browser ──HTTP──► Next.js  (:3000)      ← Serves pages, so needs a port

  Workers ──AMQP──► RabbitMQ (:5672)      ← Workers PULL messages (outbound)
  Workers ──SQL───► PostgreSQL (:5432)    ← Workers WRITE status (outbound)
  Workers ──File──► ./data/clipforge/     ← Workers READ/WRITE files (local)
  AI Wrkr ──HTTP──► Ollama (:11434)       ← AI worker CALLS Ollama (outbound)

  Nobody ever calls a worker directly.
  Workers are consumers, not servers.
  No inbound traffic = no port needed.
```

This is a fundamental part of the queue-based architecture: workers are **pull-based**. They connect *outward* to RabbitMQ and ask "give me the next message." Compare this to a REST microservice where other services call *it* — that would need a port. Here, the Java API publishes a message to `ingest.q`, and the ingest worker picks it up whenever it's ready. The API doesn't know or care which worker instance handles it.

#### Worker Hosting: MVP → Production

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  MVP: YOUR MACHINE ($0)                                             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              docker-compose (single host)                   │    │
│  │                                                             │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │    │
│  │  │PostgreSQL│ │ RabbitMQ │ │  Ollama  │ │ Java API │      │    │
│  │  │  :5432   │ │  :5672   │ │  :11434  │ │  :8080   │      │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │    │
│  │                                                             │    │
│  │  ┌─────────────┐ ┌────────────┐ ┌──────────────┐          │    │
│  │  │Ingest Worker│ │ AI Worker  │ │ Video Worker │          │    │
│  │  │ (no port)   │ │ (no port)  │ │ (no port)    │          │    │
│  │  │ pulls from  │ │ pulls from │ │ pulls from   │          │    │
│  │  │ ingest.q    │ │ transcribe │ │ render.q     │          │    │
│  │  │             │ │ + analyze.q│ │              │          │    │
│  │  └─────────────┘ └────────────┘ └──────────────┘          │    │
│  │                                                             │    │
│  │  ┌─────────────────────────────────────────┐               │    │
│  │  │  ./data/clipforge/ (shared volume)      │               │    │
│  │  └─────────────────────────────────────────┘               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  All on one box. Workers share CPU/RAM. Good for 1-3 jobs/hour.    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘


                         │ scales to
                         ▼

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  PRODUCTION: KUBERNETES / ECS                                       │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Managed Services (always on)                              │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │     │
│  │  │ RDS Postgres │  │ RabbitMQ     │  │ S3 Storage   │     │     │
│  │  │ (managed)    │  │ (cluster)    │  │ (replaces    │     │     │
│  │  │              │  │              │  │  local fs)   │     │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌──────────────────────────┐  ┌────────────────────────────────┐  │
│  │  On-demand nodes         │  │  Spot nodes (60-70% cheaper)   │  │
│  │                          │  │                                │  │
│  │  ┌────────┐ ┌────────┐  │  │  ┌────────┐┌────────┐┌──────┐ │  │
│  │  │Ingest  │ │AI      │  │  │  │Video   ││Video   ││Video │ │  │
│  │  │Worker  │ │Worker  │  │  │  │Worker  ││Worker  ││Worker│ │  │
│  │  │ ×1     │ │ ×2-3   │  │  │  │ ×1     ││ ×2     ││ ×N   │ │  │
│  │  └────────┘ └────────┘  │  │  └────────┘└────────┘└──────┘ │  │
│  │                          │  │                                │  │
│  │  Light workload,         │  │  CPU-heavy FFmpeg rendering.   │  │
│  │  need reliability.       │  │  Spot is safe because:         │  │
│  │                          │  │  • Unacked msg returns to queue│  │
│  │                          │  │  • Another worker retries it   │  │
│  │                          │  │  • Idempotent = no duplicates  │  │
│  └──────────────────────────┘  └────────────────────────────────┘  │
│                                                                     │
│  KEDA watches render.q depth → auto-scales video workers 0 → N     │
│  Good for 100+ jobs/hour.                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

```
PRODUCTION PATH                          FREE MVP PATH
─────────────────────                    ─────────────────────
StorageService.java                      StorageService.java
  → S3Client.putObject()                   → Files.write(path)
  → presignedUrl()                         → /api/files/{key} (serve directly)

Python workers                           Python workers
  → boto3.upload_file()                    → shutil.copy() to /data/clipforge/
  → boto3.download_file()                  → open() from /data/clipforge/
```

Write a `StorageService` interface in Java so swapping to S3 later is a one-line config change:

```java
public interface StorageService {
    String upload(String key, byte[] data);
    byte[] download(String key);
    String getDownloadUrl(String key);   // presigned URL (S3) or /api/files/key (local)
}

// MVP: LocalStorageService implements StorageService
// Prod: S3StorageService implements StorageService
// Switch via: spring.profiles.active=local | spring.profiles.active=s3
```

#### Key Swap: OpenAI → Ollama

```python
# AI Worker — analyze.py
# The only change is the base_url and model name.
# Ollama exposes an OpenAI-compatible API, so the code is identical.

from openai import OpenAI

# PRODUCTION
# client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
# model = "gpt-4o"

# FREE MVP
client = OpenAI(
    base_url="http://ollama:11434/v1",   # Ollama container
    api_key="not-needed"                  # Ollama doesn't check this
)
model = "llama3.1:8b"

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)
```

#### What You Keep vs Skip (Updated)

```
┌──────────────────────────────────────────────────────────────┐
│  KEEP (FREE)                        │  SKIP FOR MVP          │
├──────────────────────────────────────────────────────────────┤
│  Java API (single instance)         │  Face tracking          │
│  RabbitMQ in Docker                 │  Background music       │
│  PostgreSQL in Docker               │  User auth              │
│  Ollama (local LLM, free)           │  WebSocket (use polling)│
│  faster-whisper (local, free)       │  Redis                  │
│  FFmpeg (free, open source)         │  S3 (use local fs)      │
│  yt-dlp (free, open source)         │  CDN                    │
│  Center-crop (no face detection)    │  Kubernetes             │
│  Basic ASS captions                 │  Monitoring stack       │
│  Next.js (localhost or Vercel free) │  Rate limiting          │
└──────────────────────────────────────────────────────────────┘

Deploy: docker-compose up -d (all 7 containers, one machine, $0)
```

#### Hardware Requirements (Your Dev Machine)

```
MINIMUM (CPU-only, works but slow):
  • 8 GB RAM (Ollama 8B model ~5GB, whisper-small ~500MB, rest ~2GB)
  • 4-core CPU
  • 20 GB free disk
  • Transcription: ~10x realtime (10 min video → ~1 min)
  • LLM analysis: ~30-60 seconds per job
  • Video render: ~2-5x realtime per clip

RECOMMENDED (still $0):
  • 16 GB RAM (lets you run whisper-medium for better accuracy)
  • 8-core CPU
  • NVIDIA GPU with 6GB+ VRAM (optional, speeds up whisper 20-50x)
  • 50 GB free disk
```

### Production (Month 2+) — When to Start Paying

```
Add in this order of ROI:

 #  Change                        Cost Impact       Why Now
──────────────────────────────────────────────────────────────
 1  Switch Ollama → GPT-4o API    ~$0.01/job        Much better segment detection
 2  Switch local fs → S3          ~$5/month         Multi-machine, durability
 3  Auth + user dashboard         $0 (code only)    Unblocks multi-user
 4  WebSocket progress            $0 (code only)    Better UX
 5  Horizontal video workers      $20-50/month      Unblocks throughput
 6  Face tracking (mediapipe)     $0 (code only)    Quality jump
 7  Spot instances for workers    Saves 40-60%      Cost reduction
 8  Transcript caching            $0 (code only)    Cost reduction
 9  CDN (CloudFront)              ~$10/month        Download speed
10  Kubernetes migration          Ops cost only     Operational maturity
```

---

## 10. Deployment Topology (Production Target)

```
┌─────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                    │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Next.js  │  │ Next.js  │  │ Next.js  │  ← Vercel or k8s │
│  └──────────┘  └──────────┘  └──────────┘                  │
│        │              │              │                       │
│        └──────────────┼──────────────┘                      │
│                       ▼                                     │
│  ┌──────────────────────────────────┐                       │
│  │  Ingress / Load Balancer         │                       │
│  └──────────────┬───────────────────┘                       │
│                 ▼                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Java API │  │ Java API │  │ Java API │  ← HPA on CPU    │
│  │  :8080   │  │  :8080   │  │  :8080   │  ← PORTS: yes,   │
│  └──────────┘  └──────────┘  └──────────┘    receives HTTP  │
│        │                                                    │
│  ┌─────┴──────────────────────────────────┐                 │
│  │            RabbitMQ Cluster             │                 │
│  └─────┬──────────┬───────────┬───────────┘                 │
│        │          │           │                              │
│  ┌─────┴────┐ ┌───┴─────┐ ┌──┴──────────┐                  │
│  │ Ingest   │ │ AI      │ │ Video       │  ← KEDA scaling  │
│  │ Workers  │ │ Workers │ │ Workers     │    on queue depth │
│  │ (×1-2)   │ │ (×2-3)  │ │ (×3-10)    │                   │
│  │ NO PORTS │ │ NO PORTS│ │ NO PORTS    │  ← Pull from     │
│  │          │ │         │ │ SPOT NODES  │    RabbitMQ only  │
│  └──────────┘ └─────────┘ └─────────────┘                   │
│  on-demand     on-demand    spot/preemptible                │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐                    │
│  │ Postgres│  │  Redis  │  │    S3    │                    │
│  │ (RDS)   │  │ (Elasti-│  │ (managed)│                    │
│  │         │  │  Cache) │  │          │                    │
│  └─────────┘  └─────────┘  └──────────┘                    │
└─────────────────────────────────────────────────────────────┘

PORT SUMMARY:
  • Java API (:8080)     → Has port. Receives HTTP from frontend.
  • Next.js (:3000)      → Has port. Serves pages to browser.
  • PostgreSQL (:5432)   → Has port. Workers + API connect to it.
  • RabbitMQ (:5672)     → Has port. Workers + API connect to it.
  • Redis (:6379)        → Has port. API connects for pub/sub.
  • S3                   → AWS managed, no port to configure.
  • Python Workers       → NO PORT. They initiate all connections
                           outward (to RabbitMQ, DB, S3).
                           Nobody calls them. They pull work.
```

---

## Appendix: Message Format (RabbitMQ)

```json
// ingest.q
{
  "jobId": "uuid",
  "sourceUrl": "https://youtube.com/watch?v=...",
  "userId": "uuid",
  "attemptNumber": 1
}

// transcribe.q
{
  "jobId": "uuid",
  "rawAssetKey": "raw/uuid/video.mp4",
  "durationSec": 1800
}

// analyze.q
{
  "jobId": "uuid",
  "transcriptKey": "transcripts/uuid.json",
  "durationSec": 1800
}

// render.q (one message per clip)
{
  "jobId": "uuid",
  "clipId": "uuid",
  "clipIndex": 0,
  "rawAssetKey": "raw/uuid/video.mp4",
  "startTimeMs": 45000,
  "endTimeMs": 102000,
  "captions": [ { "start": 45.0, "end": 46.5, "text": "Here's the thing..." } ],
  "hookText": "You won't believe what happens next",
  "options": { "faceTrack": false, "bgMusic": null }
}
```
