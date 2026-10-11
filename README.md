# Telegram Vocabulary Checking Bot MVP

Production-shaped MVP for a Telegram-first vocabulary assessment system. Admins upload vocabulary, publish checks, students answer timed questions, and both students and admins can see results.

## Requirements

- Python 3.12+
- PostgreSQL 16+
- Telegram bot token from BotFather
- Optional OCR: Tesseract installed locally, or use the Docker image which installs it

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
BOT_TOKEN=123456:telegram-token
DATABASE_URL=postgresql+asyncpg://vocab:vocab@localhost:5432/vocab
ADMIN_TELEGRAM_IDS=123456789,987654321
OCR_PROVIDER=tesseract
OCR_API_KEY=
API_TOKEN=
DEFAULT_TIME_LIMIT_SECONDS=60
QUESTIONS_PER_CHECK=50
```

Admin IDs must be Telegram numeric user IDs. They are never hardcoded.

> The app accepts `DATABASE_URL` in both `postgresql://` and
> `postgresql+asyncpg://` form; plain `postgresql://` (what Railway's Postgres
> plugin exposes) is converted automatically.

## Local Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ocr]"
cp .env.example .env
```

Start PostgreSQL and update `DATABASE_URL` if needed.

## Database Migrations

```bash
alembic upgrade head
```

## Docker Installation

```bash
cp .env.example .env
docker compose up --build
```

The API runs on `http://localhost:8000`. The Telegram bot runs in the same application process when `BOT_TOKEN` is set.

## Deploying to Railway

The repo includes `railway.json` and a `Dockerfile` configured for Railway.

1. Create a project on Railway and add a **PostgreSQL** service (v16+).
2. Add a **service from your GitHub repo** (Dockerfile builder is used).
3. Set the environment variables:
   - `BOT_TOKEN` — from @BotFather.
   - `ADMIN_TELEGRAM_IDS` — comma-separated numeric Telegram IDs.
   - `SUPER_ADMIN_TELEGRAM_IDS` — optional, for super admins.
   - `DATABASE_URL` — reference the Postgres service variable:
     `${{Postgres.DATABASE_URL}}` (the plain `postgresql://` scheme is
     auto-converted to `postgresql+asyncpg://`).
   - `OCR_PROVIDER` — `tesseract` is preinstalled in the image; leave `OCR_API_KEY` empty.
   - `API_TOKEN` — optional token required by `/api/v1/*` routes when set.
4. Deploy. On start, the container runs `alembic upgrade head` and then serves
   the FastAPI app on the port Railway assigns via `$PORT`. Migrations run before
   every start, so no extra steps are needed after deploy.

`railway.json` pins a single replica and an `/health` check; the bot uses long
polling, so it runs inside the same web process.

## Telegram Bot Setup

1. Open Telegram and message `@BotFather`.
2. Run `/newbot` and follow the prompts.
3. Copy the token into `BOT_TOKEN`.
4. Find your numeric Telegram user ID with a user info bot or Telegram API tooling.
5. Add that ID to `ADMIN_TELEGRAM_IDS`.

## Starting the Application

Local:

```bash
uvicorn app.main:app --reload
```

Docker:

```bash
docker compose up --build
```

## Bot Usage

Admin:

- `/start` authenticates based on `ADMIN_TELEGRAM_IDS`.
- `/new_check` starts vocabulary upload.
- Send vocabulary as text or a photo.
- Confirm and publish with the inline keyboard.
- `/results <check_id>` shows completed student results.

Student:

- `/start` registers as a student.
- `/checks` lists active checks.
- Press `Start Checking`.
- Answer each question as a normal message.
- `/resume` returns to an active unfinished check.

## REST API

- `GET /health`
- `GET /api/v1/checks`
- `GET /api/v1/checks/{check_id}`
- `GET /api/v1/checks/{check_id}/results`
- `GET /api/v1/users/{user_id}/results`

## Running Tests

```bash
pytest
```

To include the PostgreSQL user-service regression tests with the local Docker database:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://vocab:vocab@localhost:5432/vocab pytest
```

These tests create and remove isolated schemas without modifying application users.

## Example Vocabulary Input

```text
predator - an animal that hunts other animals
habitat - the natural home of an animal or plant
endangered - at risk of becoming extinct
extinct - no longer existing
```

## Notes

V1 uses a deterministic `RuleBasedEvaluator`: normalized exact match first, then keyword matching. OCR is isolated behind `OCRService`; the default implementation uses local Tesseract so it can be replaced later without changing Telegram handlers or checking logic.

Each student attempt uses `QUESTIONS_PER_CHECK` randomly selected vocabulary items from the uploaded list. The selection is stable for that attempt, so resume/restart keeps the same question set.
