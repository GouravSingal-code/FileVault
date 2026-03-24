# File Vault API

A production-grade Django REST API for file storage with intelligent cross-user deduplication, asynchronous upload processing via Kafka, per-user storage quotas, Redis-backed rate limiting, and structured observability.

---

## Table of Contents

1. [What We Built](#what-we-built)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Quick Start (Docker)](#quick-start-docker)
5. [API Reference](#api-reference)
6. [Configuration](#configuration)
7. [Testing](#testing)
8. [Key Design Decisions](#key-design-decisions)

---

## What We Built

| Feature | Description |
|---|---|
| **File Deduplication** | SHA-256 content hashing detects duplicates across all users. Duplicates store only a metadata reference — no extra physical storage is consumed. |
| **Async Upload Pipeline** | Uploads return immediately (HTTP 202). A Kafka consumer processes files in the background and updates the job status. |
| **Storage Quota Management** | Each user has a configurable quota (default 100 MB). Quota checks run against Redis for sub-millisecond response times. |
| **Rate Limiting** | Sliding-window rate limiter (60 req/min/user) backed by Redis with automatic `Retry-After` headers. |
| **Search & Filtering** | Files can be filtered by name, MIME type, size range, and date range. All searchable fields are indexed. |
| **Structured Logging** | Every request, file operation, security event, and performance metric is logged with consistent context fields. |
| **Health & Metrics** | `/health/` checks database and cache connectivity. `/metrics/` exposes basic counters. |

---

## Architecture

```
┌─────────────────────┐
│    API Layer        │  Django REST Framework ViewSets (files/views.py)
│                     │  Custom middleware stack (files/middleware.py)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Service Layer     │  Pure Python, no Django model imports at module level
│  files/services/    │  file_services   — hashing, deduplication
│                     │  kafka_service   — async upload producer
│                     │  kafka_consumer  — background processor
│                     │  storage_services — usage calculation & stats
│                     │  quota_service   — quota validation
│                     │  performance_services — query optimisation
│                     │  memory_optimizer — cache compression
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Data Layer       │  PostgreSQL (via Django ORM)
│  files/models.py    │  Redis (cache + rate limiting)
│                     │  Local filesystem (physical file storage)
└─────────────────────┘
```

### Infrastructure

| Service | Role |
|---|---|
| **Django 4.2 + DRF** | API framework |
| **Gunicorn** | Production WSGI server (4 sync workers) |
| **PostgreSQL 15** | Primary data store |
| **Redis 7** | Cache, rate-limit counters, quota checks |
| **Apache Kafka** | Async file-processing message queue |
| **Docker Compose** | Local orchestration |

---

## Project Structure

```
file-vault-system/
├── docker-compose.yml
└── backend/
    ├── Dockerfile
    ├── start.sh                       # Runs gunicorn (prod) or runserver (dev)
    ├── manage.py
    ├── requirements/
    │   ├── base.txt                   # Core runtime dependencies
    │   ├── development.txt
    │   ├── production.txt             # + sentry-sdk
    │   └── testing.txt                # + pytest, factory-boy
    │
    ├── core/
    │   ├── settings/
    │   │   ├── __init__.py            # Selects module via DJANGO_ENVIRONMENT
    │   │   ├── base.py                # Shared settings
    │   │   ├── development.py         # DEBUG=True, ALLOWED_HOSTS=*
    │   │   ├── production.py          # Security headers, DEBUG=False
    │   │   └── testing.py             # SQLite in-memory, local-mem cache
    │   ├── logging_config.py          # log_request / log_file_operation / log_error …
    │   ├── monitoring.py              # HealthCheckView, MetricsView
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── asgi.py
    │
    └── files/
        ├── models.py                  # File, UserStorageStats, RateLimitRecord, UploadJob
        ├── views.py                   # FileViewSet (list, retrieve, create, destroy, storage_stats, upload_status)
        ├── serializers.py
        ├── urls.py
        ├── middleware.py              # ApiValidation, RateLimit, Security, Performance
        │
        ├── services/
        │   ├── file_services.py       # FileHashService, DeduplicationService
        │   ├── kafka_service.py       # KafkaService (producer, lazy singleton)
        │   ├── kafka_consumer.py      # FileUploadConsumer (long-running process)
        │   ├── storage_services.py    # StorageService, StatisticsService
        │   ├── quota_service.py       # QuotaService
        │   ├── performance_services.py # performance_monitor decorator, QueryOptimizer
        │   └── memory_optimizer.py    # CacheCompressionService (zlib)
        │
        ├── utils/
        │   ├── file_utils.py          # generate_file_upload_path
        │   ├── hash_utils.py          # compute_sha256, compute_sha256_from_bytes
        │   ├── cache_utils.py         # CacheUtils (versioned invalidation)
        │   ├── validation_utils.py    # validate_file_extension, validate_file_size
        │   └── performance_utils.py   # @timed decorator
        │
        ├── tests/
        │   ├── test_file_services.py
        │   ├── test_kafka_service.py
        │   ├── test_kafka_consumer_flow.py
        │   ├── test_quota_service.py
        │   ├── test_storage_services.py
        │   └── test_performance_services.py
        │
        ├── management/commands/
        │   └── run_kafka_consumer.py  # python manage.py run_kafka_consumer
        │
        └── migrations/
            └── 0001_initial.py
```

---

## Quick Start (Docker)

### Prerequisites

- Docker 20.10+ and Docker Compose 2.x

### 1. Create a `.env` file (or use the provided default)

```bash
cp backend/venv/env/development.env .env
```

### 2. Build and start all services

```bash
docker-compose up --build
```

### 3. Apply database migrations

```bash
docker-compose exec backend python manage.py migrate
```

### 4. Start the Kafka consumer (separate terminal)

```bash
docker-compose exec backend python manage.py run_kafka_consumer
```

### 5. Verify

```bash
curl http://localhost:8000/health/
# {"status": "healthy", "checks": {"database": "ok", "cache": "ok"}}
```

### Service Ports

| Service | Port |
|---|---|
| API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Kafka | 9092 |
| Zookeeper | 2181 |

---

## API Reference

All `/api/` endpoints require:

```
UserId: <your_user_id>
```

### Upload a File (async)

```http
POST /api/files/
Content-Type: multipart/form-data
UserId: user_123

file=<binary>
```

**202 Accepted**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "File queued for processing",
  "estimated_completion_time": "2-5 minutes",
  "quota_info": {
    "quota_mb": 100,
    "used_mb": 12.4,
    "remaining_mb": 87.6,
    "usage_percent": 12.4
  },
  "status_url": "/api/files/upload-status/<job_id>/"
}
```

### Poll Upload Status

```http
GET /api/files/upload-status/<job_id>/
UserId: user_123
```

Status values: `queued` → `processing` → `completed | failed`

### List Files

```http
GET /api/files/?search=report&file_type=application/pdf&min_size=1000&max_size=5000000&page=1
UserId: user_123
```

Query parameters: `search`, `file_type`, `min_size`, `max_size`, `start_date`, `end_date`, `page`, `page_size` (max 100).

### Get File Details

```http
GET /api/files/<file_id>/
UserId: user_123
```

### Delete File

```http
DELETE /api/files/<file_id>/
UserId: user_123
```

Returns **204 No Content**. Reference counting is handled atomically — physical files are only removed when their reference count reaches 0.

### Storage Statistics

```http
GET /api/files/storage_stats/
UserId: user_123
```

```json
{
  "user_id": "user_123",
  "total_storage_used": 52428800,
  "total_storage_used_mb": 50.0,
  "storage_savings": 10485760,
  "storage_savings_mb": 10.0,
  "savings_percent": 20.0,
  "original_files": 8,
  "reference_files": 2,
  "file_count": 10
}
```

### Health Check

```http
GET /health/
```

### Metrics

```http
GET /metrics/
```

---

## Configuration

Environment variables (set in `backend/venv/env/development.env` or via Docker):

| Variable | Default | Description |
|---|---|---|
| `DJANGO_ENVIRONMENT` | `development` | `development`, `production`, or `testing` |
| `SECRET_KEY` | *(dev placeholder)* | Django secret key — **must be changed in production** |
| `DB_HOST` | `postgres` | PostgreSQL host |
| `DB_NAME` | `file_vault_dev` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `REDIS_URL` | `redis://redis:6379/1` | Redis connection URL |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:29092` | Kafka broker(s) |
| `KAFKA_FILE_UPLOAD_TOPIC` | `file-uploads` | Upload topic name |
| `KAFKA_CONSUMER_GROUP_ID` | `file-vault-consumers` | Consumer group |
| `USER_STORAGE_QUOTA_MB` | `100` | Per-user quota in MB |
| `MAX_FILE_SIZE_MB` | `5` | Maximum upload size in MB |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## Testing

Tests use an in-memory SQLite database and local-memory cache — no external services required.

```bash
# Inside the container
docker-compose exec backend python manage.py test files.tests --settings=core.settings.testing -v 2

# Or locally (with a virtualenv)
DJANGO_SETTINGS_MODULE=core.settings.testing python manage.py test files.tests -v 2
```

Test coverage:

| Module | Tests |
|---|---|
| `test_file_services.py` | SHA-256 hashing, deduplication logic, reference counting |
| `test_kafka_service.py` | Producer singleton, success path, error handling |
| `test_kafka_consumer_flow.py` | End-to-end message processing, duplicate detection, missing job |
| `test_quota_service.py` | Quota validation pass/fail, info dict structure |
| `test_storage_services.py` | Usage calculation, incremental stats, negative-value guard |
| `test_performance_services.py` | Search/filter accuracy, queryset passthrough |

---

## Key Design Decisions

### 1. Async Upload via Kafka
Files are processed asynchronously. The API returns a job ID immediately so the user is never blocked waiting for SHA-256 computation, disk I/O, or deduplication lookups.

### 2. Cross-User Deduplication with Reference Counting
A single physical file is shared across all users who upload identical content. Reference counting with `SELECT FOR UPDATE` prevents races during concurrent deletes.

### 3. Versioned Cache Invalidation
Instead of pattern-scanning Redis keys (slow), `CacheUtils` bumps a per-user/namespace version counter. Old entries become unreachable immediately without explicit deletion.

### 4. Layered Settings
`core/settings/__init__.py` imports the correct module based on `DJANGO_ENVIRONMENT`. `wsgi.py` defaults to `production`; `manage.py` defaults to `development`.

### 5. Gunicorn in Production
`start.sh` uses `gunicorn` with 4 sync workers when `DJANGO_ENVIRONMENT=production` and falls back to Django's dev server otherwise. The `Dockerfile` runs `start.sh` as `CMD`.

---

Built with Django, Kafka, PostgreSQL, and Redis.
