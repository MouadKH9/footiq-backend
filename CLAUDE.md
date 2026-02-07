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
