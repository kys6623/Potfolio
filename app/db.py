import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import g
from typing import Any

def get_db():
    if "db" not in g:
        db_url = os.environ.get('DATABASE_URL')
        # psycopg2를 사용합니다.
        g.db = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id SERIAL PRIMARY KEY,
                asset_type TEXT NOT NULL,
                symbol TEXT,
                name TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                meta TEXT,
                note TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
    db.commit()

# 나머지 함수들도 psycopg2 문법(%s)을 유지합니다.
def fetch_assets() -> list[dict[str, Any]]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM assets ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]

def insert_asset(asset_type, symbol, name, quantity, meta=None, note=None):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO assets (asset_type, symbol, name, quantity, meta, note) VALUES (%s, %s, %s, %s, %s, %s)",
            (asset_type, symbol, name, quantity, meta, note)
        )
    db.commit()

def delete_asset(asset_id: int) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
    db.commit()
    
def update_asset(asset_id: int, quantity: float, note: str | None = None) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE assets SET quantity = %s, note = %s WHERE id = %s", (quantity, note, asset_id))
    db.commit()
# 기타 update_asset, delete_asset 등도 동일하게 psycopg2 문법 유지