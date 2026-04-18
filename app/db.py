import sqlite3
from typing import Any

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """
    Return one SQLite connection per request context.
    The connection is cached in Flask `g` and closed in teardown.
    """
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e: Exception | None = None) -> None:
    """
    Close DB connection safely after each request.
    """
    _ = e  # Explicitly ignore; kept for Flask teardown signature.
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """
    Initialize schema if it does not already exist.
    This function is idempotent and can be called at app startup.
    """
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_type TEXT NOT NULL,
            symbol TEXT,
            name TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            meta TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Lightweight migration for users who already had the older schema.
    existing_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(assets)").fetchall()
    }
    if "meta" not in existing_columns:
        db.execute("ALTER TABLE assets ADD COLUMN meta TEXT")
    if "note" not in existing_columns:
        db.execute("ALTER TABLE assets ADD COLUMN note TEXT")

    db.commit()


def insert_asset(
    asset_type: str,
    symbol: str | None,
    name: str,
    quantity: float,
    meta: str | None = None,
    note: str | None = None,
) -> None:
    """
    Insert one asset row into DB.
    """
    db = get_db()
    db.execute(
        """
        INSERT INTO assets (asset_type, symbol, name, quantity, meta, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (asset_type, symbol, name, quantity, meta, note),
    )
    db.commit()


def update_asset(asset_id: int, quantity: float, note: str | None) -> None:
    """
    Update editable fields for an existing asset.
    """
    db = get_db()
    db.execute(
        """
        UPDATE assets
        SET quantity = ?, note = ?
        WHERE id = ?
        """,
        (quantity, note, asset_id),
    )
    db.commit()


def delete_asset(asset_id: int) -> None:
    """
    Delete one asset by id.
    """
    db = get_db()
    db.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    db.commit()


def fetch_assets() -> list[dict[str, Any]]:
    """
    Fetch all assets as plain dictionaries for easier processing in services.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT id, asset_type, symbol, name, quantity, meta, note, created_at
        FROM assets
        ORDER BY id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]
