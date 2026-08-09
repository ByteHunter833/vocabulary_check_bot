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
DEFAULT_TIME_LIMIT_SECONDS=60
```

Admin IDs must be Telegram numeric user IDs. They are never hardcoded.

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

## Example Vocabulary Input

```text
predator - an animal that hunts other animals
habitat - the natural home of an animal or plant
endangered - at risk of becoming extinct
extinct - no longer existing
```

## Notes

V1 uses a deterministic `RuleBasedEvaluator`: normalized exact match first, then keyword matching. OCR is isolated behind `OCRService`; the default implementation uses local Tesseract so it can be replaced later without changing Telegram handlers or checking logic.
