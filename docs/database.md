# Database Guide

## Overview

The database is **PostgreSQL 16**, managed via **Flyway** for schema migrations. Flyway runs automatically on API startup and applies any pending migrations in version order.

Migration files live at:
```
services/api/src/main/resources/db/migration/
```

---

## Creating a Migration

Always use the script — never create migration files manually to avoid version conflicts:

```bash
make migration
```

This will:
1. Detect the next version number automatically
2. Prompt for a description in snake_case
3. Create the file in the correct location

**Example:**
```
Next version : V2
Description  : snake_case only (e.g. add_users_table)
Migration description: add_video_url_to_jobs
Created: services/api/src/main/resources/db/migration/V2__add_video_url_to_jobs.sql
```

Then open the file and write your SQL.

---

## Naming Convention

Flyway requires a strict naming format:

```
V{version}__{description}.sql
```

- Version is an incrementing integer: `V1`, `V2`, `V3` ...
- Two underscores between version and description
- Description must be snake_case (letters, numbers, underscores only)

**Valid:** `V2__add_video_url_to_jobs.sql`  
**Invalid:** `V2__add video url.sql`, `V2__add-video-url.sql`

---

## Applying Migrations

Migrations run automatically when the API starts. To apply them locally:

```bash
make dev
```

Or if the API is already running, restart it:
```bash
docker compose -f infra/docker-compose.yml restart api
```

---

## Rules

- **Never edit a committed migration.** Once a migration has been applied anywhere, treat it as immutable. Create a new migration to make further changes.
- **Never delete a migration file.** Flyway will error if a previously applied migration is missing.
- **One migration per change.** Keep migrations focused — don't bundle unrelated schema changes.
