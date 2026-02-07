# FootIQ API Reference

> This document is the source of truth for the frontend team.
> Updated automatically as endpoints and models change.

Base URL: `/api/v1/`

All endpoints require JWT authentication unless noted. Include `Authorization: Bearer <access_token>` header.

---

## Auth (`/api/v1/auth/`)

### POST `/auth/device/`
Register device and get JWT. Creates anonymous user if device is new.

**No auth required.**

**Request:**
```json
{
  "device_id": "uuid",
  "platform": "ios"  // optional
}
```

**Response (200/201):**
```json
{
  "user_id": "uuid",
  "is_anonymous": true,
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token"
}
```

### POST `/auth/upgrade/`
Add email + password to anonymous account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "min8chars"
}
```

**Response (200):**
```json
{
  "user_id": "uuid",
  "is_anonymous": false,
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token"
}
```

### POST `/auth/login/`
Email login. Links device, merges anonymous progress if applicable.

**No auth required.**

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password",
  "device_id": "uuid",
  "platform": "ios"  // optional
}
```

**Response (200):**
```json
{
  "user_id": "uuid",
  "is_anonymous": false,
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token"
}
```

### POST `/auth/token/refresh/`
Refresh JWT access token.

**No auth required.**

**Request:**
```json
{
  "refresh": "jwt-refresh-token"
}
```

**Response (200):**
```json
{
  "access": "new-jwt-access-token",
  "refresh": "new-jwt-refresh-token"
}
```

---

## Daily (`/api/v1/daily/`)

### GET `/daily/today/`
Get today's published daily set with user progress for all 3 games.

**Response (200):**
```json
{
  "date": "2025-01-15",
  "status": "published",
  "career_path": {
    "id": 1,
    "max_attempts": 6,
    "hints": [
      {"order_index": 0, "hint_type": "club_badge", "hint_data": {...}}
    ],
    "answer_player": null,  // shown only after completion
    "progress": {
      "status": "in_progress",
      "guesses": [],
      "attempts_used": 0,
      "hints_revealed": 1,
      "completed_at": null
    }
  },
  "grid": {
    "id": 1,
    "max_total_guesses": 15,
    "enforce_unique_players": true,
    "labels": [
      {"axis": "row", "index": 0, "label_type": "club", "display_text": "Barcelona", "label_data": {...}}
    ],
    "cells": [
      {"row_index": 0, "col_index": 0}
    ],
    "progress": null  // null if not started
  },
  "wordle": {
    "id": 1,
    "word_length": 5,
    "max_attempts": 6,
    "allowed_chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "answer_player": null,
    "progress": null
  }
}
```

### GET `/daily/{YYYY-MM-DD}/`
Get a specific date's published daily set. Same response format.

---

## Games (`/api/v1/games/`)

### POST `/games/career-path/{puzzle_id}/guess/`
Submit a Career Path guess.

**Request:**
```json
{
  "guess_text": "Lionel Messi"
  // OR
  "player_id": 28003
}
```

**Response (200) — correct/incorrect:**
```json
{
  "correct": false,
  "status": "in_progress",
  "attempts_used": 1,
  "hints_revealed": 2,
  "guessed_player": {"id": 28003, "name": "Lionel Messi", "image_url": "..."},
  "answer_player": null
}
```

**Response (200) — ambiguous match:**
```json
{
  "ambiguous_match": true,
  "candidates": [
    {"id": 123, "name": "Player A", "image_url": "..."},
    {"id": 456, "name": "Player B", "image_url": "..."}
  ]
}
```

**Response (200) — no match:**
```json
{
  "no_match": true
}
```

### POST `/games/grid/{puzzle_id}/guess/`
Submit a Grid guess for a specific cell.

**Request:**
```json
{
  "row": 0,
  "col": 1,
  "guess_text": "Messi"
  // OR
  "player_id": 28003
}
```

**Response (200):**
```json
{
  "accepted": true,
  "status": "in_progress",
  "total_guesses_used": 1,
  "cells_filled": 1,
  "board_state": {"0_1": {"player_id": 28003, "player_name": "Lionel Messi"}},
  "guessed_player": {"id": 28003, "name": "Lionel Messi", "image_url": "..."}
}
```

### POST `/games/wordle/{puzzle_id}/guess/`
Submit a Wordle guess.

**Request:**
```json
{
  "word": "MESSI"
}
```

**Response (200):**
```json
{
  "correct": false,
  "feedback": [
    {"letter": "M", "status": "absent"},
    {"letter": "E", "status": "present"},
    {"letter": "S", "status": "correct"},
    {"letter": "S", "status": "absent"},
    {"letter": "I", "status": "absent"}
  ],
  "status": "in_progress",
  "attempts_used": 1,
  "answer_player": null
}
```

---

## Players (`/api/v1/players/`)

### GET `/players/search/?q=de+bru&limit=10`
Autocomplete player search.

**Query params:**
- `q` (required, min 2 chars): search query
- `limit` (optional, default 10, max 20): result limit

**Response (200):**
```json
[
  {
    "id": 282629,
    "name": "Kevin De Bruyne",
    "image_url": "https://...",
    "current_club_name": "Manchester City",
    "nationality": "Belgium"
  }
]
```

---

## Share (`/api/v1/share/`)

### GET `/share/daily/{YYYY-MM-DD}/`
Combined share text for all completed games on a date.

**Response (200):**
```json
{
  "share_text": "FootIQ 2025-01-15\n\nCareer Path: Solved in 3/6 attempts\nGrid: 9/9 | 12 guesses\nWordle: 4/6"
}
```

### GET `/share/career-path/{puzzle_id}/`
### GET `/share/grid/{puzzle_id}/`
### GET `/share/wordle/{puzzle_id}/`
Per-game share text with emoji grids where applicable.

---

## Stats (`/api/v1/stats/`)

### GET `/stats/me/`
Get user streaks and per-game stats.

**Response (200):**
```json
{
  "streak": {
    "current": 5,
    "longest": 12,
    "last_completed_date": "2025-01-15",
    "total_days_played": 30,
    "total_perfect_days": 20
  },
  "career_path": {
    "played": 30,
    "won": 25,
    "win_rate": 83.3
  },
  "grid": {
    "played": 30,
    "completed": 28,
    "completion_rate": 93.3
  },
  "wordle": {
    "played": 30,
    "won": 27,
    "win_rate": 90.0
  }
}
```

### GET `/stats/me/history/?page=1`
Paginated date-by-date completion history.

**Response (200):**
```json
{
  "count": 30,
  "next": "/api/v1/stats/me/history/?page=2",
  "previous": null,
  "results": [
    {
      "date": "2025-01-15",
      "career_path_result": "won",
      "grid_result": "completed",
      "wordle_result": "won",
      "all_completed": true,
      "is_perfect": true
    }
  ]
}
```
