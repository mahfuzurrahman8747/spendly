"""Pytest fixtures for Spendly.

The app and database modules are imported lazily inside fixtures so the
monkeypatching of `database.db.DB_PATH` and `SPENDLY_SECRET_KEY` happens
*before* the app reads either of them.
"""

import importlib
import os
import sqlite3
import sys
import warnings

import pytest


# Make the project root importable so `import app` and `import auth` work
# regardless of where pytest is invoked from.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Point the app at a tmp SQLite file instead of the real `spendly.db`.

    The patch must land before `app` or `auth` are imported — the app reads
    `database.db.DB_PATH` via `get_db()` on every request, but `app.config`
    is populated at import time. Patch the module-level constant first.
    """
    target = tmp_path / "test_spendly.db"
    import database.db as db_module

    monkeypatch.setattr(db_module, "DB_PATH", target)
    return target


@pytest.fixture
def app(db_path, monkeypatch):
    """Flask app with an isolated DB and a fixed secret key for signed sessions."""
    monkeypatch.setenv("SPENDLY_SECRET_KEY", "test-secret-do-not-use")

    import app as app_module
    importlib.reload(app_module)
    flask_app = app_module.app

    flask_app.config["TESTING"] = True
    # Skip the per-request init_db()/seed_db() hook — tests control the DB
    # directly via fixtures.
    flask_app.config["SKIP_DB_BOOTSTRAP"] = True

    # Create the schema directly. Skip seed_db() — tests don't want demo data.
    from database.db import init_db
    init_db()

    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(db_path):
    """Direct DB access for assertions. Uses its own connection (not `get_db`)
    so the test doesn't depend on Flask app context."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()