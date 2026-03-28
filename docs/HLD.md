# 🧠 High level Flow Diagram :

                             ┌──────────────────────────┐
                             │       Frontend           │
                             │     Next.js (App)        │
                             │   http://localhost:3000  │
                             └─────────────┬────────────┘
                                           │ HTTPS
                                           ▼
                          ┌────────────────────────────────┐
                          │        Java API Layer          │
                          │      Spring Boot (REST)        │
                          │                                │
                          │  POST /api/jobs                │
                          │  GET  /api/jobs/{id}           │
                          │  GET  /api/jobs/{id}/clips     │
                          │                                │
                          └─────────────┬──────────────────┘
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 │                                             │
                 ▼                                             ▼
        ┌──────────────────┐                          ┌──────────────────┐
        │   PostgreSQL     │                          │    RabbitMQ      │
        │                  │                          │                  │
        │ • users          │                          │ Exchanges:       │
        │ • jobs           │                          │  pipeline.x      │
        │ • clips          │                          │                  │
        │ • assets         │                          │ Queues:          │
        └──────────────────┘                          │  ingest.q        │
                                                      │  transcribe.q    │
                                                      │  analyze.q       │
                                                      │  render.q        │
                                                      │  finalize.q *    │
                                                      └────────┬─────────┘
                                                               │
                                                               ▼
                                     ┌────────────────────────────────────┐
                                     │        Python Worker Service       │
                                     │                                    │
                                     │  Ingest Stage                      │
                                     │   • yt-dlp                         │
                                     │   • metadata extraction            │
                                     │                                    │
                                     │  Transcription Stage               │
                                     │   • faster-whisper                 │
                                     │                                    │
                                     │  Analysis Stage                    │
                                     │   • LLM (Ollama / OpenAI)          │
                                     │   • segment detection              │
                                     │                                    │
                                     │  Rendering Stage                   │
                                     │   • FFmpeg                         │
                                     │   • captions (ASS)                 │
                                     │   • 9:16 crop                      │
                                     │                                    │
                                     │  Finalization Step                 │
                                     │   • publish → finalize.q           │
                                     └─────────────┬──────────────────────┘
                                                   │
                                                   ▼
                                     ┌──────────────────────────┐
                                     │     Storage Layer        │
                                     │                          │
                                     │  MVP: Local Filesystem   │
                                     │  ./data/                 │
                                     │   ├── raw/               │
                                     │   ├── transcripts/       │
                                     │   └── outputs/           │
                                     │                          │
                                     │  Future: AWS S3          │
                                     └──────────────────────────┘

                                                   │
                                                   ▼
                          ┌────────────────────────────────────────┐
                          │     Java API Listener (Consumer)       │
                          │                                        │
                          │  • listens to finalize.q               │
                          │  • verifies all clips rendered         │
                          │  • updates job status → COMPLETED      │
                          │  • optional: notify frontend (WS/SSE)  │
                          └─────────────┬──────────────────────────┘
                                        │
                                        ▼
                                ┌──────────────┐
                                │ PostgreSQL   │
                                │ job:COMPLETE │
                                └──────────────┘

# Processing Flow :

1. User submits URL
2. API creates job → status = CREATED
3. API publishes → ingest.q

4. Worker pipeline:
   ingest → transcribe → analyze

5. analyze step:
   → creates N clips
   → publishes N messages → render.q

6. render step (parallel):
   → generates clips
   → updates clip status = RENDERED

7. AFTER all clips done:
   → worker publishes → finalize.q

8. Java API (listener):
   → consumes finalize event
   → verifies all clips rendered
   → updates job status = COMPLETED

9. Frontend:
   → polls or receives update
   → shows clips

# 🚀 Future Evolution (Already Supported)

Current (MVP)
→ Single Python Worker

Next
→ Split into: - ingest-worker - ai-worker - video-worker

Scale
→ multiple replicas per queue
