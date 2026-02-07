# FootIQ Backend

Django + DRF backend for FootIQ, a daily football mini-games app with 3 puzzles per day: **Career Path**, **Football Grid**, and **Football Wordle**.

## Tech Stack

- Python 3.12, Django 5.1, Django REST Framework
- PostgreSQL 16 with `pg_trgm` extension
- JWT auth via `djangorestframework-simplejwt`
- Docker & Docker Compose

## Quick Start

### 1. Clone and configure

```bash
cd footiq_backend
cp .env.example .env
```

Edit `.env` if you want to change ports or credentials. Defaults:
- Backend: `http://localhost:8003`
- Postgres: `localhost:5439`

### 2. Start with Docker

```bash
docker compose up --build -d
```

This will:
- Start a Postgres 16 container
- Run migrations automatically
- Start the Django dev server on port 8003

### 3. Create a superuser

```bash
docker compose exec backend python manage.py createsuperuser
```

### 4. Seed player data

Download the [Transfermarkt dataset from Kaggle](https://www.kaggle.com/datasets/davidcariboo/player-scores) and run:

```bash
docker compose exec backend python manage.py seed_players \
    --players-csv /path/to/players.csv \
    --clubs-csv /path/to/clubs.csv \
    --appearances-csv /path/to/appearances.csv \
    --generate-aliases
```

### 5. Verify

- Admin panel: http://localhost:8003/admin/
- Device registration: `POST http://localhost:8003/api/v1/auth/device/`

## Local Development (without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set env vars (point DB_HOST to your local Postgres)
export DJANGO_SETTINGS_MODULE=config.settings.development
export DB_HOST=localhost
export DB_PORT=5432

python manage.py migrate
python manage.py runserver 8003
```

## Project Structure

```
footiq_backend/
├── config/                 # Django project settings, urls, wsgi
│   └── settings/
│       ├── base.py         # Shared settings
│       ├── development.py  # Debug, local DB, CORS open
│       └── production.py   # SSL, dj-database-url, whitenoise
├── apps/
│   ├── accounts/           # User model, device auth, JWT, email backend
│   ├── players/            # Player, Club, Alias models; search; seed command
│   ├── games/              # DailySet, puzzle configs, guess logic, share text
│   └── progress/           # Game progress, streaks, daily completions
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Procfile                # Railway deployment
└── API_REFERENCE.md        # Full endpoint documentation
```

## API Overview

Base URL: `/api/v1/`

| Area | Endpoints | Description |
|------|-----------|-------------|
| Auth | `POST /auth/device/`, `/auth/upgrade/`, `/auth/login/`, `/auth/token/refresh/` | Anonymous device sessions, email upgrade, JWT |
| Daily | `GET /daily/today/`, `/daily/{date}/` | Today's puzzles with user progress |
| Games | `POST /games/career-path/{id}/guess/`, `/games/grid/{id}/guess/`, `/games/wordle/{id}/guess/` | Guess submission for each game |
| Players | `GET /players/search/?q=...` | Autocomplete player search |
| Share | `GET /share/daily/{date}/`, `/share/career-path/{id}/`, etc. | Share text with emoji grids |
| Stats | `GET /stats/me/`, `/stats/me/history/` | Streaks, win rates, history |

See [API_REFERENCE.md](API_REFERENCE.md) for full request/response documentation.

## Management Commands

| Command | Description |
|---------|-------------|
| `seed_players` | Import players, clubs, and club history from Kaggle CSVs |
| `check_daily_sets` | Validate completeness of daily sets in a date range |
| `recalculate_streaks` | Rebuild user streaks from completion history |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `change-me-to-a-random-string` |
| `DJANGO_SETTINGS_MODULE` | Settings module path | `config.settings.development` |
| `DB_NAME` | Database name | `footiq` |
| `DB_USER` | Database user | `footiq` |
| `DB_PASSWORD` | Database password | `footiq_secret` |
| `DB_HOST` | Database host | `db` (Docker service name) |
| `DB_PORT` | Database port (internal) | `5432` |
| `POSTGRES_PORT` | Postgres host port | `5439` |
| `BACKEND_PORT` | Backend host port | `8003` |

## Production Deployment (Railway)

The project is pre-configured for Railway:

- `Procfile` runs gunicorn + migrations
- `runtime.txt` specifies Python 3.12
- Production settings use `DATABASE_URL` via `dj-database-url`
- Static files served by `whitenoise`

Set `DJANGO_SETTINGS_MODULE=config.settings.production` and provide `SECRET_KEY`, `ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` in your Railway environment.
