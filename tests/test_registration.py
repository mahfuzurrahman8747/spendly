"""Tests for the registration flow (Spec 02)."""

import importlib
import re
import sys
import warnings


# ------------------------------------------------------------------ #
# GET /register                                                       #
# ------------------------------------------------------------------ #

def test_get_register_renders_form(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Create your account" in body
    assert '<input type="text" id="name" name="name"' in body
    assert '<input type="email" id="email" name="email"' in body
    assert '<input type="password" id="password" name="password"' in body


def test_get_register_does_not_create_user(client, db):
    client.get("/register")
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


# ------------------------------------------------------------------ #
# POST /register — happy path                                         #
# ------------------------------------------------------------------ #

def test_post_register_success_inserts_user_and_redirects(client, db):
    resp = client.post(
        "/register",
        data={"name": "Priya Sharma", "email": "priya@example.com",
              "password": "hunter22!"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].rstrip("/") in ("", "/")
    # Either a relative "/", or any host. What we care about is that it's the landing root.
    assert resp.headers["Location"].endswith("/")

    # Exactly one user row, and the password is hashed (not plaintext).
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    row = db.execute(
        "SELECT * FROM users WHERE email = ?", ("priya@example.com",)
    ).fetchone()
    assert row["name"] == "Priya Sharma"
    assert row["password_hash"] != "hunter22!"
    assert row["password_hash"].startswith(("pbkdf2:", "scrypt:"))

    with client.session_transaction() as sess:
        assert sess["user_id"] == row["id"]
        assert sess["user_name"] == "Priya Sharma"


def test_post_register_redirected_landing_shows_welcome(client):
    # follow_redirects=False so the session cookie survives into the
    # subsequent GET / (Flask test client strips cookies across chained
    # requests unless you capture the redirect response and re-attach).
    post = client.post(
        "/register",
        data={"name": "Priya Sharma", "email": "priya@example.com",
              "password": "hunter22!"},
        follow_redirects=False,
    )
    assert post.status_code == 302
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Banner block is rendered (template inserts a <strong> between the
    # comma and the name, so assert on structural markers, not a contiguous
    # substring).
    assert 'class="welcome-banner"' in body
    assert "<strong>Priya Sharma</strong>" in body
    assert 'href="/logout"' in body


# ------------------------------------------------------------------ #
# POST /register — failure paths                                      #
# ------------------------------------------------------------------ #

def test_post_register_duplicate_email_shows_error_no_row_added(client, db):
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Existing User", "taken@example.com", "x"),
    )
    db.commit()

    resp = client.post(
        "/register",
        data={"name": "Other User", "email": "taken@example.com",
              "password": "hunter22!"},
    )
    assert resp.status_code == 400
    assert "already exists" in resp.get_data(as_text=True)
    # Only the pre-inserted row remains.
    rows = db.execute(
        "SELECT * FROM users WHERE email = ?", ("taken@example.com",)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "Existing User"


def test_post_register_password_too_short(client, db):
    resp = client.post(
        "/register",
        data={"name": "Priya", "email": "priya@example.com", "password": "short"},
    )
    assert resp.status_code == 400
    assert "at least 8" in resp.get_data(as_text=True)
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_post_register_empty_name(client, db):
    resp = client.post(
        "/register",
        data={"name": "   ", "email": "priya@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 400
    assert "Please enter your name" in resp.get_data(as_text=True)
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_post_register_empty_email(client, db):
    resp = client.post(
        "/register",
        data={"name": "Priya", "email": "", "password": "hunter22!"},
    )
    assert resp.status_code == 400
    assert "Please enter your email" in resp.get_data(as_text=True)
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_post_register_invalid_email_shape(client, db):
    resp = client.post(
        "/register",
        data={"name": "Priya", "email": "not-an-email", "password": "hunter22!"},
    )
    assert resp.status_code == 400
    assert "valid email" in resp.get_data(as_text=True)
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_post_register_refills_name_and_email_but_not_password(client, db):
    # Pre-insert so the duplicate-email branch fires and we re-render the form.
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Existing", "aarav@example.com", "x"),
    )
    db.commit()

    resp = client.post(
        "/register",
        data={"name": "Aarav", "email": "AARAV@Example.COM", "password": "hunter22!"},
    )
    assert resp.status_code == 400
    body = resp.get_data(as_text=True)

    # name re-filled with what the user typed. email refills with the raw
    # user input (not lowercased) — auth normalises storage, but we surface
    # what was typed. Password must NOT be re-filled.
    name_match = re.search(
        r'<input type="text" id="name" name="name"[^>]*value="([^"]*)"', body
    )
    email_match = re.search(
        r'<input type="email" id="email" name="email"[^>]*value="([^"]*)"', body
    )
    password_match = re.search(
        r'<input type="password" id="password" name="password"[^>]*>', body
    )
    assert name_match is not None and name_match.group(1) == "Aarav"
    assert email_match is not None and email_match.group(1) == "AARAV@Example.COM"
    assert password_match is not None
    assert "value=" not in password_match.group(0)


def test_post_register_long_name_over_80_rejected(client, db):
    resp = client.post(
        "/register",
        data={"name": "x" * 81, "email": "priya@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 400
    assert "80 characters or fewer" in resp.get_data(as_text=True)
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_post_register_email_is_lowercased(client, db):
    resp = client.post(
        "/register",
        data={"name": "Priya", "email": "MiXed@Case.COM", "password": "hunter22!"},
    )
    assert resp.status_code == 302
    row = db.execute("SELECT email FROM users").fetchone()
    assert row["email"] == "mixed@case.com"


def test_post_register_session_clears_existing(client):
    with client.session_transaction() as sess:
        sess["stale"] = "x"
    resp = client.post(
        "/register",
        data={"name": "Priya", "email": "priya@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert "stale" not in sess
        assert sess["user_id"] is not None
        assert sess["user_name"] == "Priya"


# ------------------------------------------------------------------ #
# SECRET_KEY warning                                                  #
# ------------------------------------------------------------------ #

def test_secret_key_warning_when_env_missing(monkeypatch, tmp_path):
    # Point the DB at a tmp file so the reload's before_request hook can
    # run init_db() without touching the real spendly.db.
    monkeypatch.delenv("SPENDLY_SECRET_KEY", raising=False)
    import database.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "isolated.db")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # Drop cached modules so the reload re-reads the env and DB_PATH.
        for mod in ("app", "auth", "database.db"):
            if mod in sys.modules:
                del sys.modules[mod]
        import app as app_module  # noqa: F401
    messages = [str(w.message) for w in caught]
    assert any("SPENDLY_SECRET_KEY" in m for m in messages), messages