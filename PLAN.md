# FootIQ Backend — Implementation Plan

## Context

FootIQ is a daily football mini-games app delivering 3 puzzles per day (Career Path, Football Grid, Football Wordle). The backend is a Django + PostgreSQL REST API consumed by a React Native (Expo) frontend. It will be hosted on Railway.

Both `footiq_backend/` and `footiq_frontend/` are currently empty — this is a greenfield build.

**Key decisions made:**
- Auth: Anonymous device sessions + optional email sign-up
- Football Grid: Limited total guesses (e.g., 15 across 9 cells)
- Admin: Customized Django Admin (with `django-nested-admin`)
- Data seeding: Management command importing Kaggle Transfermarkt CSVs

---

## 1. Project Structure

```
footiq_backend/
├── manage.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── .env.example
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── apps/
    ├── accounts/      # Auth: custom User, DeviceSession, JWT
    ├── players/       # Player, Alias, Club, ClubHistory; search; seed command
    ├── games/         # DailySet, CareerPath, Grid, Wordle puzzle configs
    └── progress/      # Per-user game state, streaks, daily completions
```

---

## 2. Data Models

### 2.1 `accounts` app

**User** (extends `AbstractUser`)
- `id`: UUIDField (PK)
- `is_anonymous_user`: BooleanField (default=True)
- `email`: EmailField (nullable, unique) — set on upgrade

**DeviceSession**
- `id`: UUIDField (PK)
- `device_id`: UUIDField (unique, indexed) — client-generated
- `user`: FK → User
- `platform`: CharField (ios/android)
- `created_at`, `last_seen_at`: DateTimeFields

### 2.2 `players` app

**Club**
- `id`: IntegerField (PK, transfermarkt club_id)
- `name`, `club_code`, `domestic_competition_id`, `stadium_name`, `logo_url`, `url`

**Player**
- `id`: IntegerField (PK, transfermarkt player_id)
- `first_name`, `last_name`, `name` (display name)
- `name_normalized`: CharField (indexed) — lowercase, no diacritics, for search
- `country_of_birth`, `city_of_birth`, `country_of_citizenship`
- `date_of_birth`: DateField
- `position`: CharField (Goalkeeper/Defender/Midfield/Attack)
- `sub_position`, `foot`, `height_in_cm`
- `image_url`, `url`
- `current_club`: FK → Club
- `last_season`, `market_value_in_eur`, `highest_market_value_in_eur`
- Indexes on: `last_name`, `country_of_citizenship`, `position`, `name_normalized`

**PlayerAlias**
- `player`: FK → Player
- `alias`: CharField
- `alias_normalized`: CharField (indexed) — for matching
- `is_auto_generated`: BooleanField
- Unique together: `(player, alias_normalized)`

**PlayerClubHistory**
- `player`: FK → Player
- `club`: FK → Club
- `season_start`, `season_end`
- `date_joined`, `date_left`
- `appearances`, `goals`, `assists`

### 2.3 `games` app

**DailySet**
- `date`: DateField (unique)
- `status`: draft / published / archived
- `published_at`, `created_at`, `updated_at`
- `notes`: TextField (admin-only)

**CareerPathPuzzle** (OneToOne → DailySet)
- `answer_player`: FK → Player
- `max_attempts`: PositiveIntegerField (default=6)

**CareerPathHint** (FK → CareerPathPuzzle)
- `order_index`: PositiveIntegerField (0-based, hint 0 shown initially)
- `hint_type`: club_badge / nationality / position / age_range / league / trophy / text / image
- `hint_data`: JSONField (structured payload per type)
- Unique together: `(puzzle, order_index)`

**GridPuzzle** (OneToOne → DailySet)
- `max_total_guesses`: PositiveIntegerField (default=15)
- `enforce_unique_players`: BooleanField (default=True)

**GridLabel** (FK → GridPuzzle)
- `axis`: row / col
- `index`: 0-2
- `label_type`: club / nationality / position / league / custom
- `display_text`, `label_data`: JSONField
- Unique together: `(puzzle, axis, index)`

**GridCell** (FK → GridPuzzle)
- `row_index`, `col_index`: 0-2
- `accepted_players`: M2M → Player (through GridCellAcceptedPlayer)
- Unique together: `(puzzle, row_index, col_index)`

**GridCellAcceptedPlayer** (through table)
- `cell`: FK → GridCell
- `player`: FK → Player

**WordlePuzzle** (OneToOne → DailySet)
- `answer_player`: FK → Player
- `answer_word`: CharField (uppercase surname)
- `word_length`: PositiveIntegerField (auto-computed)
- `max_attempts`: PositiveIntegerField (default=6)
- `allowed_chars`: CharField (default="ABCDEFGHIJKLMNOPQRSTUVWXYZ")

### 2.4 `progress` app

**CareerPathProgress**
- `user`: FK → User
- `puzzle`: FK → CareerPathPuzzle
- `status`: in_progress / won / lost
- `guesses`: JSONField (list of `{guess_text, player_id, correct}`)
- `attempts_used`, `hints_revealed` (default=1)
- `completed_at`
- Unique together: `(user, puzzle)`

**GridProgress**
- `user`: FK → User
- `puzzle`: FK → GridPuzzle
- `status`: in_progress / completed / exhausted
- `total_guesses_used`, `cells_filled`
- `board_state`: JSONField (`{"0_0": {player_id, player_name}, ...}`)
- `guesses`: JSONField (full log)
- `used_player_ids`: JSONField (for uniqueness enforcement)
- Unique together: `(user, puzzle)`

**WordleProgress**
- `user`: FK → User
- `puzzle`: FK → WordlePuzzle
- `status`: in_progress / won / lost
- `guesses`: JSONField (list of `{word, feedback: [{letter, status}]}`)
- `attempts_used`
- Unique together: `(user, puzzle)`

**UserStreak** (OneToOne → User)
- `current_streak`, `longest_streak`
- `last_completed_date`
- `total_days_played`, `total_perfect_days`

**UserDailyCompletion**
- `user`: FK → User
- `date`: DateField
- `career_path_result`, `grid_result`, `wordle_result`: CharField
- `all_completed`, `is_perfect`: BooleanField
- Unique together: `(user, date)`

---

## 3. API Endpoints

Base: `/api/v1/`

### Auth (`/auth/`)
| Method | URL | Purpose |
|--------|-----|---------|
| POST | `/auth/device/` | Register device, get JWT (creates anonymous user if new) |
| POST | `/auth/upgrade/` | Add email+password to anonymous account |
| POST | `/auth/login/` | Email login (links device, merges anonymous progress) |
| POST | `/auth/token/refresh/` | Refresh JWT |

### Daily (`/daily/`)
| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/daily/today/` | Today's published set + user progress for all 3 games |
| GET | `/daily/{date}/` | Specific date's set (read-only if past) |

The response nests all 3 game states, merging puzzle config with the user's progress. Unrevealed hints are excluded. Answers only shown after completion.

### Games (`/games/`)
| Method | URL | Purpose |
|--------|-----|---------|
| POST | `/games/career-path/{puzzle_id}/guess/` | Submit Career Path guess |
| POST | `/games/grid/{puzzle_id}/guess/` | Submit Grid guess (includes row/col) |
| POST | `/games/wordle/{puzzle_id}/guess/` | Submit Wordle guess |

Each guess endpoint:
- Accepts `guess_text` (free text) or `player_id` (from autocomplete)
- Grid also requires `row` and `col`
- Wordle accepts `word` (must match required length)
- Returns updated game state, correctness, and new hints/feedback
- Returns `ambiguous_match` with candidates if guess resolves to multiple players
- Returns `no_match` if unresolvable

### Players (`/players/`)
| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/players/search/?q=de+bru&limit=10` | Autocomplete player search |

Returns: `player_id`, `name`, `image_url`, `current_club`, `nationality`

### Share (`/share/`)
| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/share/daily/{date}/` | Combined share text for a date |
| GET | `/share/career-path/{puzzle_id}/` | Per-game share text |
| GET | `/share/grid/{puzzle_id}/` | Per-game share text |
| GET | `/share/wordle/{puzzle_id}/` | Per-game share text (emoji grid) |

### Stats (`/stats/`)
| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/stats/me/` | Streaks, win rates, per-game stats |
| GET | `/stats/me/history/?page=1` | Date-by-date completion history |

---

## 4. Guess Resolution Logic

`apps/players/services.py` — `resolve_guess(guess_text)`:

1. **Normalize** input: NFKD unicode → ASCII, lowercase, strip diacritics/hyphens/apostrophes
2. **Exact alias match** on `alias_normalized` → single player = success
3. **Exact `name_normalized`** match on Player table
4. **Prefix match** on aliases (startswith)
5. **Contains match** on aliases
6. **Trigram similarity** via `pg_trgm` (threshold 0.3, auto-resolve at 0.6)
7. Return: `exact` (1 player), `ambiguous` (2+ candidates), or `no_match`

Autocomplete (`search_players`) uses the same normalization, prioritizing prefix matches, limited to 10 results.

Wordle feedback uses standard Wordle algorithm with correct repeated-letter handling (two-pass: greens first, then yellows).

---

## 5. Admin Customization

**DailySet admin page** — central hub with stacked inlines for all 3 puzzles:
- CareerPathPuzzle inline (with nested CareerPathHint inline via `django-nested-admin`)
- GridPuzzle inline (with nested GridLabel, GridCell, GridCellAcceptedPlayer)
- WordlePuzzle inline
- Custom actions: "Publish" / "Unpublish" with validation checks
- `autocomplete_fields` on all Player FKs

**Player admin** — search across name + aliases, inline alias editor

**Validation warnings on save:**
- DailySet missing any of the 3 games
- GridPuzzle with <9 cells or cells with no accepted players
- CareerPathPuzzle with 0 hints
- WordlePuzzle with invalid characters in answer_word
- Player missing image_url when used as answer

---

## 6. Management Commands

### `seed_players` (primary)
```
python manage.py seed_players \
    --players-csv path/to/players.csv \
    --clubs-csv path/to/clubs.csv \
    --appearances-csv path/to/appearances.csv \
    --generate-aliases --batch-size 1000
```
1. Import clubs (bulk upsert)
2. Import players (bulk upsert, compute `name_normalized`)
3. Generate auto-aliases (full name, last name, first+last, slug)
4. Import club history from appearances (grouped by player+club)

### `check_daily_sets`
Validate completeness of daily sets in a date range. Output warnings.

### `recalculate_streaks`
Rebuild UserStreak from UserDailyCompletion history.

---

## 7. Authentication Flow

- JWT via `djangorestframework-simplejwt` (access: 7 days, refresh: 90 days)
- Device registration: client sends UUID → backend creates anonymous User + DeviceSession → returns JWT
- Upgrade: anonymous user adds email + password, `is_anonymous_user` flips to False
- Login from new device: if device had anonymous progress, merge into email user's account (reassign progress rows for dates without conflicts, recalculate streaks, delete orphan)
- Custom `EmailBackend` for login by email instead of username

---

## 8. Railway Deployment

**Settings split:** `config/settings/{base,development,production}.py`

**Production settings:**
- `DATABASE_URL` via `dj-database-url` (auto-provided by Railway Postgres plugin)
- `whitenoise` for static files
- CORS restricted to app domain
- SSL redirect, secure cookies

**Procfile:**
```
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
release: python manage.py migrate && python manage.py collectstatic --noinput
```

**Environment variables:** `SECRET_KEY`, `DATABASE_URL`, `DJANGO_SETTINGS_MODULE`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`

**Enable `pg_trgm`** extension via Django migration (`TrigramExtension()`)

---

## 9. Key Dependencies

```
django>=5.1,<5.2
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
django-cors-headers>=4.3
django-filter>=24.3
django-nested-admin>=4.0
dj-database-url>=2.1
gunicorn>=22.0
whitenoise>=6.7
psycopg[binary]>=3.1
```

---

## 10. Implementation Order

| Step | What | Files |
|------|------|-------|
| 0a | Save this plan as `footiq_backend/PLAN.md` | `footiq_backend/PLAN.md` |
| 0b | Create `footiq_backend/CLAUDE.md` with project rules | `footiq_backend/CLAUDE.md` |
| 0c | Create empty `footiq_backend/API_REFERENCE.md` (updated whenever endpoints/models change) | `footiq_backend/API_REFERENCE.md` |
| 1 | Django project init + settings split | `config/`, `manage.py`, `requirements.txt` |
| 2 | `accounts` app — User model, DeviceSession, auth views, JWT | `apps/accounts/` |
| 3 | `players` app — Player, Club, Alias, ClubHistory models + admin | `apps/players/` |
| 4 | `seed_players` management command | `apps/players/management/commands/seed_players.py` |
| 5 | Player search/autocomplete + guess resolution service | `apps/players/services.py`, `apps/players/views.py` |
| 6 | `games` app — DailySet + all puzzle config models + admin | `apps/games/` |
| 7 | `progress` app — all progress/streak models | `apps/progress/` |
| 8 | Daily set API (GET today/date with merged progress) | `apps/games/views.py`, `apps/games/serializers.py` |
| 9 | Guess submission endpoints (Career Path, Grid, Wordle) | `apps/games/views.py`, `apps/games/services.py` |
| 10 | Share output endpoints | `apps/games/views.py` (share logic) |
| 11 | Stats/streaks endpoints | `apps/progress/views.py`, `apps/progress/services.py` |
| 12 | Railway deployment config | `Procfile`, `runtime.txt`, `.env.example`, production settings |

---

## 11. CLAUDE.md Rules

Create `footiq_backend/CLAUDE.md` with the following:

```markdown
# FootIQ Backend

Django + DRF backend for the FootIQ daily football mini-games app.

## Stack
- Python 3.12, Django 5.1, Django REST Framework
- PostgreSQL with pg_trgm extension
- JWT auth via djangorestframework-simplejwt

## Commands
- `python manage.py runserver` — run dev server
- `python manage.py test` — run tests
- `python manage.py seed_players --players-csv ... --clubs-csv ... --generate-aliases` — seed player data
- `DJANGO_SETTINGS_MODULE=config.settings.development` for local dev

## Project Layout
- `config/` — Django project settings, urls, wsgi
- `apps/accounts/` — User model, device auth, JWT
- `apps/players/` — Player, Alias, Club models; search; seed command
- `apps/games/` — DailySet, puzzle configs (CareerPath, Grid, Wordle)
- `apps/progress/` — User game state, streaks, completions

## Rules
- Always use the `apps/` prefix when importing between apps (e.g., `from apps.players.models import Player`)
- Keep business logic in `services.py`, not in views or serializers
- Use `PROTECT` on FKs referencing Player when used as puzzle answers
- All player-matching must go through `apps/players/services.resolve_guess()` — never match by raw text
- Admin-facing validation goes in model `clean()` methods

## API Reference
- **Always update `API_REFERENCE.md`** whenever endpoints, request/response shapes, or models change
- This file is the source of truth for the frontend team
```

---

## 12. Verification

1. **Run locally:** `python manage.py runserver` — confirm Django admin loads, all models visible
2. **Seed data:** Download Kaggle CSVs, run `seed_players` — verify player count, aliases generated, club history populated
3. **Admin workflow:** Create a DailySet via admin with all 3 games, publish it
4. **Auth flow:** `POST /auth/device/` → get token → `GET /daily/today/` → see the published set
5. **Gameplay:** Submit guesses via each game endpoint, verify correct state transitions (in_progress → won/lost)
6. **Search:** `GET /players/search/?q=mess` → returns Messi with correct data
7. **Streaks:** Complete all 3 games, verify streak increments
8. **Share:** `GET /share/daily/{date}/` → returns formatted share text
