
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

# Project root is two levels up from this file: <root>/database/db.py
DB_PATH = Path(__file__).resolve().parent.parent / "spendly.db"


def get_db():
    """Open a SQLite connection to the project DB.

    Sets `row_factory` so rows support both index and key access, and turns on
    foreign-key enforcement for this connection (SQLite does not persist this
    setting, so it must be re-applied on every new connection).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the `users` and `expenses` tables if they do not already exist.

    Safe to call multiple times thanks to `CREATE TABLE IF NOT EXISTS`.
    """
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
    )
    conn.commit()
    conn.close()


def seed_db():
    """Insert demo data on first run only.

    Guards on the existing user count so repeated invocations do not duplicate
    rows. Creates one demo user (password `demo123`, hashed) and eight sample
    expenses that exercise every fixed category.
    """
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        conn.close()
        return

    hashed = generate_password_hash("demo123")
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", hashed),
    )
    user_id = cur.lastrowid

    expenses = [
        (45.50, "Food",          "2026-06-02", "Groceries"),
        (12.00, "Transport",     "2026-06-04", "Bus pass"),
        (89.99, "Bills",         "2026-06-06", "Electricity"),
        (32.40, "Health",        "2026-06-08", "Pharmacy"),
        (15.00, "Entertainment", "2026-06-11", "Movie ticket"),
        (60.25, "Shopping",      "2026-06-14", "T-shirt"),
        (8.75,  "Other",         "2026-06-17", "Misc"),
        (22.30, "Food",          "2026-06-20", "Lunch"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        [(user_id, *row) for row in expenses],
    )
    conn.commit()
    conn.close()