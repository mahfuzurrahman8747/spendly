# Spec: Registration

## Overview
Replace the placeholder `GET /register` route with a working registration flow that creates new Spendly users. The form must validate input on the server, hash passwords with werkzeug, persist a new row to the `users` table, log the user in by storing their id in the Flask session, and redirect to a logged-in landing surface. This is the entry point of the authentication flow and unlocks every step that requires a session (login, profile, expenses).

## Depends on
- Step 1 — Database setup (`users` table with `id`, `name`, `email UNIQUE`, `password_hash`, `created_at`).

## Routes
- `GET  /register` — render the registration form. — public
- `POST /register` — validate input, create the user, start a session, redirect to `/`. — public
- `GET  /` — once a user is logged in, the landing/dashboard should reflect the session (for this step: at minimum redirect logged-in users to a logged-in home, or show their name; details below).

The existing `GET /register` stub in `app.py` that simply returns `register.html` is replaced by a real implementation. The other existing public routes (`/login`, `/terms`, `/privacy`, `/landing`) are unchanged.

## Database changes
No database changes. The `users` table from Step 1 already has the required columns and the `UNIQUE` constraint on `email` that this feature relies on for duplicate-email detection.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — no structural change required (form already posts to `/register`); an optional `value="{{ submitted_name }}"` / `value="{{ submitted_email }}"` re-fill so users don't retype after a server-side error.
  - `templates/landing.html` — when `session.user_id` is set, show a minimal "Welcome, {{ name }}" header and a "Sign out" link pointing at `/logout` (the existing `/logout` stub from `app.py` stays for now — wiring the actual logout is Step 3).
  - `templates/base.html` — no changes.

## Files to change
- `app.py` — replace the `register` stub with `GET` + `POST` handlers, add a `SECRET_KEY` (env-driven with a development fallback), wire `session["user_id"]` and `session["user_name"]` on success, and update the `/` route to read the session.
- `templates/register.html` — add `value="{{ ... }}"` re-fill on `name` and `email` from a `submitted_*` context variable.
- `templates/landing.html` — render a logged-in banner when `session.user_id` exists.

## Files to create
- `auth.py` (project root or `database/` — pick one and stick to it; recommend project root for now since it will host `login_required` in Step 3) — exposes:
  - `register_user(name: str, email: str, password: str) -> tuple[int | None, str | None]` returning `(user_id, error_message)`. Encapsulates the validation rules and the insert. Reuses `get_db()`.
- `tests/test_registration.py` — pytest tests covering the happy path, validation errors, and duplicate email (see Definition of done).

## New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` and `flask.session` are already available via `flask==3.1.3` and `werkzeug==3.1.6` in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`.
- Parameterised queries only — no string formatting in SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash`; never store plaintext.
- Use CSS variables — never hardcode hex values in any new styles.
- All templates `{% extends "base.html" %}`; no duplicated `<html>` / `<head>` markup.
- `SECRET_KEY` is read from the `SPENDLY_SECRET_KEY` environment variable; fall back to a clearly-marked development key with a runtime warning when unset. Do not commit a production secret.
- Use `python-dotenv` only if it is already a dependency (it is not in `requirements.txt`, so read env vars directly).
- Server-side validation rules:
  - `name`: required, trimmed length 1–80.
  - `email`: required, matches a basic `^[^@\s]+@[^@\s]+\.[^@\s]+$` shape after `.strip().lower()`.
  - `password`: required, minimum 8 characters.
  - On any validation failure: re-render `register.html` with an `error` message and the previously submitted `name` / `email` (never the password) in context.
- Duplicate email: catch `sqlite3.IntegrityError` from the `UNIQUE` constraint and surface a friendly "An account with that email already exists." message.
- On success: `session.clear()` then set `session["user_id"]` and `session["user_name"]`, then `redirect(url_for("landing"))` (HTTP 302).
- Do not implement login, logout, or password reset in this step — only the registration half.
- The `/` route should remain `GET` only; do not add a `POST` handler to it in this step.

## Definition of done
- [ ] `GET /register` returns HTTP 200 and renders `register.html` extending `base.html`.
- [ ] Submitting valid `name` / `email` / `password` (≥ 8 chars) inserts a new row in `users` with a `password_hash` produced by `werkzeug.security.generate_password_hash` (NOT the plaintext password).
- [ ] After a successful submit, the response is a 302 redirect to `/`, and `flask.session["user_id"]` equals the new user's id.
- [ ] Submitting an email that already exists in `users` re-renders the form with an "already exists" error and does NOT create a duplicate row.
- [ ] Submitting a password shorter than 8 characters re-renders the form with a length error and does NOT insert a row.
- [ ] Submitting an empty `name` or `email` re-renders the form with a required-field error and does NOT insert a row.
- [ ] Submitted `name` and `email` are re-filled in the form on validation errors; the password field is empty.
- [ ] After registration, `GET /` shows the user's name (e.g. "Welcome, <name>") and a "Sign out" link to `/logout`.
- [ ] `pytest tests/test_registration.py` passes (`pytest -q` from the project root).
- [ ] `python app.py` starts without traceback; visiting `/register` in a browser shows the form.
- [ ] No hex color literals introduced in any CSS — only `var(--…)` references.
- [ ] `git grep -nE "f\".*SELECT|f\".*INSERT|f\".*UPDATE|f\".*DELETE" app.py auth.py` returns no matches (no f-string SQL).
