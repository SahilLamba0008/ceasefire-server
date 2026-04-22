# ClipForge Queue Architecture

> Outbox/Inbox pattern for reliable event delivery from the Java backend to the Python ML worker via RabbitMQ.

---

## Table of Contents

1. [Why This Architecture](#why-this-architecture)
2. [High-Level Flow](#high-level-flow)
3. [The Three Services](#the-three-services)
4. [Data Model](#data-model)
5. [The Outbox Pattern](#the-outbox-pattern)
6. [The Inbox Pattern](#the-inbox-pattern)
7. [End-to-End Walkthrough](#end-to-end-walkthrough)
8. [State Machines](#state-machines)
9. [Failure Modes and Recovery](#failure-modes-and-recovery)
10. [Code Examples](#code-examples)
11. [Where Changes Happen](#where-changes-happen)
12. [Key IDs: job_id vs event_id](#key-ids-job_id-vs-event_id)
13. [Configuration Reference](#configuration-reference)
14. [FAQ](#faq)

---

## Why This Architecture

### The problem we're solving

The Java backend creates jobs. The Python ML worker processes them (calls Groq, generates clips). These two services need to communicate **reliably** across a network, with the following guarantees:

- **No lost messages** — if the backend creates a job, the Python worker must eventually see it
- **No duplicate processing** — if a message gets redelivered, Groq should not be called twice (it costs money)
- **No orphaned state** — if a crash happens mid-flow, the system should recover cleanly without manual intervention

### Why not just call RabbitMQ directly from the backend?

The naive approach looks like:

```java
@Transactional
public Job createJob(CreateJobRequest req) {
    Job job = jobRepository.save(new Job(...));     // DB write
    rabbitTemplate.send("events", "job.created", payload);  // Rabbit write
    return job;
}
```

This is broken in two failure modes:

1. **DB write succeeds, Rabbit write fails** (broker down) → job exists but Python worker never hears about it. Silent data loss.
2. **Rabbit write succeeds, DB rolls back** (exception after the send) → Python worker processes a job that doesn't exist. Phantom data.

You cannot put a Rabbit publish inside a DB transaction — they're two different systems, there's no distributed transaction. The outbox pattern solves this by making the "send" itself a DB write, which *can* be part of the transaction.

### Why not let the Python worker just poll the DB directly?

- Polling doesn't scale — every worker hammers the DB
- No natural fan-out to multiple consumers
- No message durability if the DB is briefly unreachable
- No routing — every worker sees every event type
- You're reimplementing a message broker badly

RabbitMQ handles all of this. The outbox worker is the bridge between "DB as source of truth" and "RabbitMQ as transport."

### Why the inbox pattern on top?

RabbitMQ guarantees **at-least-once** delivery, not exactly-once. A message can be redelivered if:

- The consumer crashes before acking
- The network glitches between broker and consumer
- The consumer takes too long and the broker times out the delivery

Without dedup, redelivery means Groq gets called twice for the same job. That's a real cost problem. The inbox pattern catches redeliveries at the consumer side using a DB unique constraint.

### Summary

| Pattern | Problem solved | Where it lives |
|---|---|---|
| **Outbox** | Atomic "save business data + announce event" | Producer side (Java backend + outbox worker) |
| **Inbox** | Prevent duplicate processing on redelivery | Consumer side (Python worker) |

---

## High-Level Flow

```
┌─────────────────────┐
│   Frontend          │
│   (Next.js)         │
└──────────┬──────────┘
           │ POST /jobs
           ▼
┌─────────────────────┐     writes both        ┌─────────────────────┐
│   Java Backend      │───────────────────────►│   public.jobs       │
│   (Spring Boot)     │   in one transaction   └─────────────────────┘
│                     │───────────────────────►┌─────────────────────┐
└─────────────────────┘                        │  event.job_events   │◄──┐
                                               │  (OUTBOX TABLE)     │   │
                                               └─────────────────────┘   │
                                                                         │ polls for
                                                                         │ PENDING rows
                                               ┌─────────────────────┐   │
                                               │  Outbox Worker      │───┘
                                               │  (Spring Boot)      │
                                               │                     │
                                               │  - poll             │
                                               │  - publish          │
                                               │  - update status    │
                                               └──────────┬──────────┘
                                                          │ publishes
                                                          ▼
                                               ┌─────────────────────┐
                                               │    RabbitMQ         │
                                               │  Topic Exchange:    │
                                               │  clipforge.events   │
                                               └──────────┬──────────┘
                                                          │ delivers
                                                          ▼
                                               ┌─────────────────────┐
                                               │  Python ML Worker   │
                                               │  - dedup via inbox  │
                                               │  - call Groq        │
                                               │  - save clips       │
                                               └──────────┬──────────┘
                                                          │ writes
                                   ┌──────────────────────┼──────────────────────┐
                                   ▼                      ▼                      ▼
                      ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
                      │ event.inbox_events  │  │   public.clips      │  │   public.jobs       │
                      │   (INBOX TABLE)     │  │                     │  │  (update status)    │
                      └─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## The Three Services

### 1. Java Backend (`clipforge-backend`)

- **Role:** REST API, business logic, owner of all DDL (Flyway migrations)
- **Tech:** Spring Boot, Postgres (via HikariCP), Flyway
- **Responsibilities:**
  - Accept HTTP requests from the frontend
  - Write business data (`public.jobs`) and outbox events (`event.job_events`) atomically
  - Own all schema migrations for both `public` and `event` schemas
- **Does NOT:** Talk to RabbitMQ directly. Publishing is delegated to the outbox worker.

### 2. Outbox Worker (`clipforge-outbox-worker`)

- **Role:** Bridge between the outbox table and RabbitMQ
- **Tech:** Spring Boot, Spring AMQP, JDBC
- **Responsibilities:**
  - Poll `event.job_events` for `PENDING` rows
  - Publish them to RabbitMQ with publisher confirms
  - Update row status (`SENT` / `FAILED` / `DEAD`)
  - Recover stale `PROCESSING` rows
- **Does NOT:** Own any tables. Does NOT run migrations.

### 3. Python ML Worker (`clipforge-ml-worker`)

- **Role:** Consume events, call Groq, persist clips
- **Tech:** Python, `pika`, `psycopg`, shared Postgres connection
- **Responsibilities:**
  - Consume from `clipforge.events` exchange
  - Dedup via `event.inbox_events` unique constraint
  - Call Groq API and persist results
- **Does NOT:** Own any tables. Does NOT run migrations.

**Schema ownership rule:** Only the Java backend runs Flyway. Both workers are read/write consumers of the schema but never modify it. This avoids migration-ordering conflicts.

---

## Data Model

### `public.jobs` — business entity

The actual job being tracked. Owned by the backend.

```sql
CREATE TABLE public.jobs (
    job_id         UUID PRIMARY KEY,
    youtube_url    TEXT NOT NULL,
    status         TEXT NOT NULL,    -- pending, processing, completed, failed
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `event.job_events` — the outbox

Events waiting to be published (or already published). One row per event occurrence.

```sql
CREATE TABLE event.job_events (
    event_id       UUID PRIMARY KEY,              -- unique per event, NOT the same as job_id
    aggregate_id   UUID NOT NULL,                 -- = job_id, indexed for business queries
    event_type     TEXT NOT NULL,                 -- 'job.created', 'job.clip.ready', etc.
    payload        JSONB NOT NULL,                -- full event data, includes job_id
    status         TEXT NOT NULL DEFAULT 'PENDING',
                                                  -- PENDING | PROCESSING | SENT | FAILED | DEAD
    retry_count    INT NOT NULL DEFAULT 0,
    last_error     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at   TIMESTAMPTZ,                   -- set when SENT
    CONSTRAINT valid_status CHECK (status IN ('PENDING','PROCESSING','SENT','FAILED','DEAD'))
);

CREATE INDEX idx_job_events_poll ON event.job_events (status, created_at);
CREATE INDEX idx_job_events_aggregate ON event.job_events (aggregate_id);
```

### `event.inbox_events` — the inbox

Record of messages already processed by the consumer. Prevents duplicate work on redelivery.

```sql
CREATE TABLE event.inbox_events (
    message_id     UUID PRIMARY KEY,              -- = event_id from the outbox
    event_type     TEXT NOT NULL,
    processed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

The unique constraint on `message_id` is what makes dedup atomic. We don't `SELECT then INSERT` — we just `INSERT` and catch the unique violation.

### DB Functions (stored procedures)

Defined in Flyway migrations, called by the outbox worker:

- `event.get_pending_events(batch_size, max_retries)` — atomic fetch-and-lock using `FOR UPDATE SKIP LOCKED`
- `event.mark_as_sent(event_id)` — set status to SENT
- `event.mark_as_failed(event_id, error, max_retries)` — increment retry_count, move to FAILED or DEAD
- `event.recover_stale_processing(timeout_seconds)` — reset stuck PROCESSING rows

---

## The Outbox Pattern

### The core insight

> Make the "send a message" operation itself a database write, so it can be part of the same transaction as the business data.

### How it works

**Step 1: Business service writes both rows atomically**

```java
@Transactional
public Job createJob(CreateJobRequest req) {
    // Row 1: business data
    Job job = jobRepository.save(new Job(UUID.randomUUID(), req.url(), "pending"));

    // Row 2: outbox event (in the SAME transaction)
    outboxPublisher.publish(
        "job.created",
        job.getId(),
        Map.of("job_id", job.getId(), "youtube_url", job.getUrl())
    );

    return job;
    // Both committed together. Both rolled back if anything throws.
}
```

**Step 2: Outbox worker polls for PENDING rows**

The worker calls the DB function on a schedule:

```sql
SELECT * FROM event.get_pending_events(100, 5);
```

Internally the function does:

```sql
UPDATE event.job_events
SET status = 'PROCESSING', updated_at = now()
WHERE event_id IN (
    SELECT event_id FROM event.job_events
    WHERE (status = 'PENDING')
       OR (status = 'FAILED' AND retry_count < 5)
    ORDER BY created_at ASC
    LIMIT 100
    FOR UPDATE SKIP LOCKED     -- ← key: multiple workers don't pick the same rows
)
RETURNING *;
```

`FOR UPDATE SKIP LOCKED` is what makes horizontal scaling trivial — run 3 worker instances and they each grab a disjoint batch.

**Step 3: Worker publishes to RabbitMQ, then updates status**

```java
for (OutboxEvent event : events) {
    boolean confirmed = publisher.publish(event);
    if (confirmed) {
        jdbc.update("SELECT event.mark_as_sent(?)", event.eventId());
    } else {
        jdbc.update("SELECT event.mark_as_failed(?, ?, ?)",
            event.eventId(), "publish_not_confirmed", maxRetries);
    }
}
```

### Why it works

- If the outbox insert rolls back, the event never existed, no harm done
- If the outbox insert commits but the worker crashes before publishing, the row stays `PENDING` and the next worker poll picks it up
- If the worker publishes but crashes before updating status, the row stays `PROCESSING` and the stale-processing recovery resets it to `PENDING` after 5 minutes — will be republished, deduplicated by the inbox

---

## The Inbox Pattern

### The core insight

> Use a DB unique constraint to make "have I seen this message before?" an atomic check.

### How it works

Consumer receives a message. Before doing any work:

```python
try:
    with db_conn.transaction():
        # The INSERT is the dedup check. No SELECT needed.
        db_conn.execute(
            "INSERT INTO event.inbox_events (message_id, event_type) VALUES (%s, %s)",
            (event_id, event_type)
        )
        # If we get here, this is the first time seeing this message.
        # Do the business work inside the same transaction.
        do_business_work(payload)
        # Commit.
except UniqueViolation:
    # Already processed. Skip silently.
    pass

ch.basic_ack(delivery_tag=method.delivery_tag)
```

### Why the unique constraint matters

Naive dedup:

```python
if not already_processed(event_id):    # SELECT
    do_work()
    mark_processed(event_id)           # INSERT
```

This has a race condition. Two workers could both SELECT "not processed" before either one INSERTs. Both do the work.

Using the unique constraint on INSERT avoids this — Postgres handles the atomicity. One INSERT wins, the other raises.

### Why inbox insert + business work must be in the same transaction

If they're in separate transactions:

```
Step A: INSERT inbox row (committed)
Step B: Do business work (fails partway)
```

Now the inbox says "processed" but the work didn't finish. Redelivery sees the inbox row and skips → work is **permanently lost**.

With one transaction:

```
BEGIN
  INSERT inbox row
  Do business work
  (any failure here rolls back EVERYTHING)
COMMIT
```

Either both succeed or both roll back. Clean.

### The one exception: external API calls

You can't roll back a Groq API call. If the Groq call is inside the transaction, a DB commit failure means you've paid for inference with no record.

Our approach: **call Groq outside the transaction, then do the DB work transactionally.**

```python
def on_message(payload):
    event_id = extract_event_id()

    # Step 1: Groq call (outside any DB transaction)
    clips = call_groq(payload["youtube_url"])    # might take 30s

    # Step 2: DB work (transactional)
    try:
        with db_conn.transaction():
            db_conn.execute("INSERT INTO event.inbox_events ...", (event_id,))
            for clip in clips:
                db_conn.execute("INSERT INTO public.clips ...", (clip,))
            db_conn.execute("UPDATE public.jobs SET status='completed' WHERE job_id=%s", (job_id,))
    except UniqueViolation:
        pass  # already processed, Groq call was wasted, acceptable for MVP

    ack()
```

**Tradeoff:** on redelivery where processing already succeeded, we'll call Groq again before catching the unique violation and skipping the DB work. That's a small cost for MVP. Can be optimized later by doing a pre-flight SELECT on the inbox before the Groq call.

---

## End-to-End Walkthrough

Let's trace one job from creation to completion.

### T+0s: User submits YouTube URL

Frontend calls `POST /jobs` on the backend.

### T+0.01s: Backend writes two rows atomically

```sql
BEGIN;
INSERT INTO public.jobs (job_id, youtube_url, status)
  VALUES ('J1', 'youtube.com/...', 'pending');
INSERT INTO event.job_events (event_id, aggregate_id, event_type, payload, status)
  VALUES ('E1', 'J1', 'job.created',
          '{"job_id":"J1","youtube_url":"youtube.com/..."}', 'PENDING');
COMMIT;
```

State:
- `public.jobs`: J1 / pending
- `event.job_events`: E1 / PENDING

Backend returns 201 to frontend.

### T+1s: Outbox worker polls

```java
List<OutboxEvent> events = jdbc.query("SELECT * FROM event.get_pending_events(?, ?)", ..., 100, 5);
// Returns [E1]. E1 is now PROCESSING in the DB.
```

State:
- `event.job_events`: E1 / PROCESSING

### T+1.05s: Outbox worker publishes

```
Exchange: clipforge.events
Routing key: job.created
Headers: { message_id: "E1" }
Body: {"event_id":"E1","event_type":"job.created","payload":{"job_id":"J1",...}}
```

Broker sends publisher confirm.

### T+1.06s: Outbox worker marks SENT

```java
jdbc.update("SELECT event.mark_as_sent(?)", "E1");
```

State:
- `event.job_events`: E1 / SENT / processed_at=now()

### T+1.1s: Python worker receives message

Extracts `event_id = E1` from `message_id` header.

### T+1.11s: Python worker calls Groq

```python
clips = call_groq("youtube.com/...")    # 30s call
# Returns 3 clips
```

### T+31s: Python worker does DB work

```python
with db_conn.transaction():
    db_conn.execute("INSERT INTO event.inbox_events (message_id, event_type) VALUES (%s, %s)",
                    ("E1", "job.created"))
    for clip in clips:
        db_conn.execute("INSERT INTO public.clips (clip_id, job_id, url) VALUES (%s, %s, %s)",
                        (clip.id, "J1", clip.url))
    db_conn.execute("UPDATE public.jobs SET status='completed' WHERE job_id=%s", ("J1",))
# commit
```

State:
- `event.inbox_events`: E1 / processed_at=now()
- `public.clips`: 3 rows for J1
- `public.jobs`: J1 / completed

### T+31.01s: Python worker acks

Message is removed from the queue.

### Timeline diagram

```
T+0.00s  Frontend ──POST /jobs──► Backend
T+0.01s  Backend  ──INSERT jobs + INSERT job_events (tx)──► Postgres
T+0.02s  Backend  ──201──► Frontend

T+1.00s  Outbox Worker  ──SELECT get_pending_events──► Postgres
                         ◄── [E1] (now PROCESSING)
T+1.05s  Outbox Worker  ──publish E1──► RabbitMQ
                         ◄── publisher confirm
T+1.06s  Outbox Worker  ──mark_as_sent(E1)──► Postgres

T+1.10s  RabbitMQ  ──deliver E1──► Python Worker
T+1.11s  Python Worker  ──call Groq──► Groq API
T+31.0s   Python Worker  ◄── 3 clips
T+31.0s   Python Worker  ──INSERT inbox + INSERT clips + UPDATE jobs (tx)──► Postgres
T+31.01s  Python Worker  ──ack──► RabbitMQ
```

---

## State Machines

### Outbox row lifecycle

```
          Backend inserts
               │
               ▼
           PENDING ◄──────────────────┐
               │                       │ (recover_stale_processing
               │ worker polls,         │  resets PROCESSING → PENDING
               │ FOR UPDATE SKIP LOCKED│  if stuck > 5min)
               ▼                       │
         PROCESSING ───────────────────┤
               │                       │
       ┌───────┴───────┐               │
       │               │               │
   publish         publish             │
   confirmed       failed              │
       │               │               │
       ▼               ▼               │
      SENT          FAILED ────────────┤
       │               │ (retry_count < MAX)
       │               │
       │               │ retry_count >= MAX
       │               ▼
       │             DEAD (terminal — alert on these)
       │
       ▼
    archived after N days (not in MVP)
```

### Inbox row lifecycle

Inbox rows have no state machine — they're append-only. A row either exists (message was processed) or doesn't (message not yet seen).

### Message lifecycle in RabbitMQ

```
Published by outbox worker
        │
        ▼
In queue (durable, persistent)
        │
        ▼
Delivered to Python worker (unacked)
        │
    ┌───┴────┐
    │        │
success  failure
    │        │
   ack     nack
    │        │
 removed   redelivered
          (up to N times)
             │
             ▼
         DLQ (if configured)
```

---

## Failure Modes and Recovery

| Failure | Effect | Recovery mechanism |
|---|---|---|
| Backend crashes before COMMIT | No job, no event | Transaction rollback, nothing to recover |
| Backend commits, outbox worker hasn't polled yet | Row in PENDING | Next poll picks it up |
| Outbox worker crashes mid-publish | Row stuck in PROCESSING | `recover_stale_processing` resets to PENDING after 5min |
| RabbitMQ down when worker tries to publish | Publish fails, row → FAILED | Retry on next poll (up to MAX_RETRIES) |
| Publish succeeds, status update fails | Row stuck in PROCESSING but message sent | Recovery resets to PENDING → republished → inbox dedups on consumer |
| RabbitMQ redelivers a message | Python worker receives it twice | Inbox unique constraint catches the duplicate |
| Python worker crashes mid-processing | Message nacked, requeued | Rabbit redelivers; inbox dedups if DB work had committed, otherwise reprocesses cleanly |
| Python worker commits DB but crashes before ack | Message redelivered | Inbox unique constraint catches it, skip |
| Groq API fails | Exception, DB tx rolls back, message nacked | Rabbit redelivers; retry up to DLQ threshold |
| Persistent poison message | After N redeliveries, lands in DLQ | Manual investigation (queue doesn't block) |
| All events exceed MAX_RETRIES | Rows marked DEAD | Alert fires; manual investigation |

---

## Code Examples

### Java: OutboxEventPublisher (backend)

```java
@Service
@RequiredArgsConstructor
public class OutboxEventPublisher {
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;

    @SneakyThrows
    public void publish(String eventType, UUID aggregateId, Object payload) {
        jdbc.update(
            "INSERT INTO event.job_events " +
            "(event_id, aggregate_id, event_type, payload, status) " +
            "VALUES (?, ?, ?, ?::jsonb, 'PENDING')",
            UUID.randomUUID(),
            aggregateId,
            eventType,
            mapper.writeValueAsString(payload)
        );
    }
}
```

Usage in business service:

```java
@Service
@RequiredArgsConstructor
public class JobService {
    private final JobRepository jobs;
    private final OutboxEventPublisher outbox;

    @Transactional
    public Job createJob(CreateJobRequest req) {
        Job job = jobs.save(new Job(UUID.randomUUID(), req.url(), "pending"));
        outbox.publish("job.created", job.getId(), Map.of(
            "job_id", job.getId().toString(),
            "youtube_url", job.getUrl()
        ));
        return job;
    }
}
```

### Java: OutboxPoller (outbox worker)

```java
@Component
@RequiredArgsConstructor
@Slf4j
public class OutboxPoller {
    private final JdbcTemplate jdbc;
    private final OutboxPublisher publisher;

    @Value("${outbox.batch-size:100}") int batchSize;
    @Value("${outbox.max-retries:5}") int maxRetries;

    @Scheduled(fixedDelayString = "${outbox.poll.interval-ms:1000}")
    public void poll() {
        try {
            List<OutboxEvent> events = jdbc.query(
                "SELECT * FROM event.get_pending_events(?, ?)",
                new OutboxEventRowMapper(),
                batchSize, maxRetries
            );

            if (events.isEmpty()) return;

            log.info("Polled {} events", events.size());
            for (OutboxEvent event : events) {
                boolean ok = publisher.publish(event);
                if (ok) {
                    jdbc.update("SELECT event.mark_as_sent(?)", event.eventId());
                } else {
                    jdbc.update("SELECT event.mark_as_failed(?, ?, ?)",
                        event.eventId(), "publish_not_confirmed", maxRetries);
                }
            }
        } catch (Exception e) {
            log.error("Poll tick failed", e);
        }
    }
}
```

### Java: OutboxPublisher (outbox worker)

```java
@Component
@RequiredArgsConstructor
@Slf4j
public class OutboxPublisher {
    private final RabbitTemplate rabbit;

    public boolean publish(OutboxEvent event) {
        MessageProperties props = new MessageProperties();
        props.setMessageId(event.eventId().toString());
        props.setContentType("application/json");
        props.setDeliveryMode(MessageDeliveryMode.PERSISTENT);

        Message msg = new Message(event.payload().getBytes(StandardCharsets.UTF_8), props);
        CorrelationData cd = new CorrelationData(event.eventId().toString());

        try {
            rabbit.send("clipforge.events", event.eventType(), msg, cd);
            var confirm = cd.getFuture().get(5, TimeUnit.SECONDS);
            return confirm != null && confirm.isAck();
        } catch (Exception e) {
            log.warn("Publish failed for event {}", event.eventId(), e);
            return false;
        }
    }
}
```

### Python: Consumer with inbox dedup

```python
import json
import os
import psycopg
import pika
from psycopg.errors import UniqueViolation

RABBITMQ_URL = os.environ["RABBITMQ_URL"]
DATABASE_URL = os.environ["DATABASE_URL"]
QUEUE_NAME = os.environ.get("QUEUE_NAME", "clipforge.jobs")


def on_message(ch, method, properties, body, db_conn):
    event_id = properties.message_id
    event_type = method.routing_key
    payload = json.loads(body)

    try:
        with db_conn.transaction():
            # Dedup check — unique constraint does the work.
            db_conn.execute(
                "INSERT INTO event.inbox_events (message_id, event_type) VALUES (%s, %s)",
                (event_id, event_type)
            )
            # Business work goes here (future stories).
            print(f"PROCESSED event_id={event_id} type={event_type} payload={payload}")
    except UniqueViolation:
        print(f"SKIP: already processed event_id={event_id}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    db_conn = psycopg.connect(DATABASE_URL, autocommit=False)
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(
        exchange="clipforge.events", exchange_type="topic", durable=True
    )
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(
        queue=QUEUE_NAME, exchange="clipforge.events", routing_key="job.created"
    )
    channel.basic_qos(prefetch_count=4)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=lambda ch, m, p, b: on_message(ch, m, p, b, db_conn),
        auto_ack=False,
    )

    print(f"Consuming from {QUEUE_NAME}...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
```

### SQL: The polling function

```sql
CREATE OR REPLACE FUNCTION event.get_pending_events(
    p_batch_size INT,
    p_max_retries INT
)
RETURNS SETOF event.job_events AS $$
    UPDATE event.job_events
    SET status = 'PROCESSING', updated_at = now()
    WHERE event_id IN (
        SELECT event_id FROM event.job_events
        WHERE (status = 'PENDING')
           OR (status = 'FAILED' AND retry_count < p_max_retries)
        ORDER BY created_at ASC
        LIMIT p_batch_size
        FOR UPDATE SKIP LOCKED
    )
    RETURNING *;
$$ LANGUAGE sql;
```

### SQL: mark_as_failed with DEAD transition

```sql
CREATE OR REPLACE FUNCTION event.mark_as_failed(
    p_event_id UUID,
    p_error TEXT,
    p_max_retries INT
)
RETURNS void AS $$
    UPDATE event.job_events
    SET retry_count = retry_count + 1,
        last_error = p_error,
        status = CASE
            WHEN retry_count + 1 >= p_max_retries THEN 'DEAD'
            ELSE 'FAILED'
        END,
        updated_at = now()
    WHERE event_id = p_event_id;
$$ LANGUAGE sql;
```

### SQL: Stale processing recovery

```sql
CREATE OR REPLACE FUNCTION event.recover_stale_processing(p_timeout_seconds INT)
RETURNS INT AS $$
    WITH reset AS (
        UPDATE event.job_events
        SET status = 'PENDING',
            retry_count = retry_count + 1,
            updated_at = now()
        WHERE status = 'PROCESSING'
          AND updated_at < now() - (p_timeout_seconds || ' seconds')::interval
        RETURNING event_id
    )
    SELECT COUNT(*)::INT FROM reset;
$$ LANGUAGE sql;
```

---

## Where Changes Happen

| Story | Repo | Key files |
|---|---|---|
| **0. Schema + functions** | `clipforge-backend` | `db/migration/V*__*.sql` |
| **1. Backend writes to outbox** | `clipforge-backend` | `outbox/OutboxEventPublisher.java`, `service/JobService.java` |
| **2. Bootstrap outbox worker** | `clipforge-outbox-worker` (NEW) | `pom.xml`, `OutboxWorkerApplication.java`, `Dockerfile`, GitHub Actions workflow |
| **3. Polling loop** | `clipforge-outbox-worker` | `poller/OutboxPoller.java`, `OutboxEventRowMapper.java` |
| **4. Publish to RabbitMQ** | `clipforge-outbox-worker` | `publisher/OutboxPublisher.java`, `config/RabbitConfig.java` |
| **5. Update status** | `clipforge-outbox-worker` | `poller/OutboxPoller.java` (extend) |
| **6. Retry + DEAD** | `clipforge-backend` (new migration) + `clipforge-outbox-worker` | V-migration updating functions; `OutboxPoller.java` passes maxRetries |
| **7. Stale recovery** | `clipforge-backend` (new migration) + `clipforge-outbox-worker` | V-migration adding `recover_stale_processing`; `recovery/StaleProcessingRecovery.java` |
| **8. Inbox table** | `clipforge-backend` | `db/migration/V*__create_inbox_events_table.sql` |
| **9. Python consumer** | `clipforge-ml-worker` (NEW) | `clipforge_worker/__main__.py`, `Dockerfile`, GitHub Actions workflow |
| **10. E2E validation** | `clipforge-backend` or new `clipforge-integration-tests` | Manual checklist or Testcontainers test |

### Repo map

```
clipforge-backend/              (existing)
├── src/main/java/.../outbox/OutboxEventPublisher.java    [Story 1]
├── src/main/java/.../service/JobService.java             [Story 1]
└── src/main/resources/db/migration/
    ├── V1__create_event_schema.sql                       [Story 0]
    ├── V2__create_job_events_table.sql                   [Story 0]
    ├── V3__create_outbox_functions.sql                   [Story 0]
    ├── V4__create_inbox_events_table.sql                 [Story 8]
    ├── V5__add_dead_status_and_retries.sql               [Story 6]
    └── V6__add_recover_stale_processing.sql              [Story 7]

clipforge-outbox-worker/        (NEW — Story 2)
├── src/main/java/.../
│   ├── OutboxWorkerApplication.java
│   ├── poller/OutboxPoller.java                          [Story 3]
│   ├── publisher/OutboxPublisher.java                    [Story 4]
│   ├── recovery/StaleProcessingRecovery.java             [Story 7]
│   ├── domain/OutboxEvent.java
│   └── config/{DatabaseConfig,RabbitConfig}.java
├── Dockerfile
└── .github/workflows/build.yml

clipforge-ml-worker/            (NEW — Story 9)
├── clipforge_worker/
│   └── __main__.py
├── pyproject.toml
├── Dockerfile
└── .github/workflows/build.yml
```

---

## Key IDs: job_id vs event_id

These are **three distinct IDs** serving three different purposes. Confusing them is the most common bug in this pattern.

| ID | Scope | Generated where | Lives in | Purpose |
|---|---|---|---|---|
| `job_id` | One business job, forever | Backend when job created | `public.jobs.job_id`, event payloads, `aggregate_id` column | Business queries, FK references |
| `event_id` | One event occurrence | Backend when outbox row inserted | `event.job_events.event_id`, Rabbit `message_id` header, `event.inbox_events.message_id` | Uniqueness, dedup |
| RabbitMQ `message_id` | Transport-level identifier | Set by outbox publisher | Rabbit message header | Transport metadata — we set it equal to `event_id` |

### Why `event_id` ≠ `job_id`

One job has many events over its lifetime:

```
job_id = J1
├── event_id = E1, event_type = job.created
├── event_id = E2, event_type = job.processing_started
├── event_id = E3, event_type = job.clip.ready
└── event_id = E4, event_type = job.completed
```

If we reused `job_id` as `event_id`, the primary key constraint on the outbox table would reject E2 onward.

### Rule of thumb

- `job_id` answers: "Which business entity is this about?"
- `event_id` answers: "Which specific event occurrence is this?"
- `event_id` = `message_id` = inbox `message_id` (same value, same meaning, different columns)

---

## Configuration Reference

### Java backend

Nothing new specific to the outbox. Existing DB connection config.

### Outbox worker

```yaml
spring:
  datasource:
    url: ${DATABASE_URL}
    username: ${DATABASE_USER}
    password: ${DATABASE_PASSWORD}
    hikari:
      maximum-pool-size: 5
  rabbitmq:
    host: ${RABBITMQ_HOST}
    port: ${RABBITMQ_PORT:5672}
    username: ${RABBITMQ_USER}
    password: ${RABBITMQ_PASSWORD}
    publisher-confirm-type: correlated
outbox:
  poll:
    interval-ms: 1000
  batch-size: 100
  max-retries: 5
  stale:
    interval-ms: 120000        # 2 minutes between recovery runs
    timeout-seconds: 300       # reset PROCESSING rows older than 5 minutes
```

### Python worker

```bash
RABBITMQ_URL=amqp://user:pass@host:5672/
DATABASE_URL=postgresql://user:pass@host:5432/clipforge
QUEUE_NAME=clipforge.jobs
PREFETCH_COUNT=4
```

### RabbitMQ topology

- Exchange: `clipforge.events` — topic, durable
- Queue: `clipforge.jobs` — durable, bound with routing key `job.created`
- DLQ: `clipforge.events.dlq` — set up when real processing lands

---

## FAQ

### Why use `FOR UPDATE SKIP LOCKED` instead of an advisory lock?

`SKIP LOCKED` lets multiple workers run without any coordination. Each worker's poll grabs a disjoint batch atomically. Advisory locks would force serialization or require manual partitioning. `SKIP LOCKED` is simpler and scales linearly.

### Why not use Postgres LISTEN/NOTIFY instead of polling?

LISTEN/NOTIFY is push-based and feels efficient, but it has gotchas:
- Messages are lost if no listener is connected
- No durability, no retry
- Connection-specific — doesn't survive reconnects cleanly

Polling is boring, reliable, and handles every failure mode without extra logic. For a job queue, the 1-second latency is fine.

### Why not Debezium / CDC?

Debezium is great if you need to stream the actual `public.jobs` table changes to Kafka. But:
- It requires Kafka + Debezium Connect running — operational overhead
- It streams *all* changes, not curated events — you'd still want an outbox table for event shape control
- Overkill for a part-time team MVP

The outbox-with-polling pattern gives you 90% of the benefits with 10% of the operational cost.

### Why not exactly-once delivery with RabbitMQ transactions?

AMQP transactions exist but are slow and don't actually give exactly-once across broker + DB. The outbox+inbox combo gives effective exactly-once processing (at-least-once delivery + idempotent consumer = exactly-once effect).

### Can the Python worker publish events too?

In theory yes — you'd give it write access to `event.job_events` and it would follow the same outbox pattern. For MVP we're keeping it one-way: Java publishes, Python consumes and writes results directly. Add bidirectional events later if a third service needs to react to "clip.ready."

### What happens when the outbox table grows huge?

For MVP, not a concern. Once `SENT` rows accumulate into the millions, polling latency will degrade because the `(status, created_at)` index is doing more work. Fix: cleanup job deleting `SENT` rows older than N days (deferred from MVP per earlier decision).

### How do we monitor this in production?

Deferred from MVP, but the planned approach:
- Actuator `/health` on the outbox worker (DB + RabbitMQ both up)
- Metric: count of `DEAD` rows — alert on any > 0
- Metric: count of `PENDING` rows older than 1 minute — alert on backlog
- Metric: time since last successful poll
- Logs grep-able by `job_id`

### Why does the backend own the inbox table's migration if the Python worker uses it?

Single-writer principle for schema. Only one service owns DDL. Splitting ownership between two services means coordinating migration order across repos, which is painful with a part-time team. Backend owns everything; both workers are schema consumers.

---

## References

- Microsoft Docs: [Transactional Outbox pattern](https://learn.microsoft.com/en-us/azure/architecture/best-practices/transactional-outbox-cosmos)
- microservices.io: [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- microservices.io: [Idempotent Consumer (Inbox)](https://microservices.io/patterns/communication-style/idempotent-consumer.html)
- Postgres docs: [`SELECT ... FOR UPDATE SKIP LOCKED`](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)
- RabbitMQ docs: [Publisher Confirms](https://www.rabbitmq.com/confirms.html)
