"""User authentication helpers for Spendly.

Currently exposes `register_user`; later steps will add login / logout and a
`login_required` decorator here.
"""

import re
import sqlite3

from werkzeug.security import generate_password_hash

from database.db import get_db

# Basic but useful email shape check — not RFC 5322, just enough to reject
# obvious typos like `foo`, `foo@`, `foo@bar`.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

NAME_MAX_LEN = 80
PASSWORD_MIN_LEN = 8


def register_user(name, email, password):
    """Create a new user row.

    Returns ``(user_id, None)`` on success and ``(None, error_message)`` on
    any validation or database failure. The view layer only needs to know
    whether to redirect or re-render the form with the message.
    """
    # Trim once and reuse the trimmed values for storage + re-fill in the view.
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""

    if not name:
        return None, "Please enter your name."
    if len(name) > NAME_MAX_LEN:
        return None, f"Name must be {NAME_MAX_LEN} characters or fewer."
    if not email:
        return None, "Please enter your email address."
    if not EMAIL_RE.match(email):
        return None, "Please enter a valid email address."
    if len(password) < PASSWORD_MIN_LEN:
        return None, f"Password must be at least {PASSWORD_MIN_LEN} characters."

    conn = get_db()
    try:
        # The only user-input-dependent constraint on `users` is UNIQUE(email),
        # so any IntegrityError here means a duplicate email. Don't substring-
        # match the exception text — brittle across SQLite versions/locales.
        try:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password)),
            )
            conn.commit()
            return cur.lastrowid, None
        except sqlite3.IntegrityError:
            conn.rollback()
            return None, "An account with that email already exists."
    finally:
        conn.close()