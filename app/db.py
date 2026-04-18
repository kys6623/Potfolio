import os
import psycopg
from psycopg.rows import dict_row
from flask import current_app, g
from typing import Any

def get_db():
    if "db" not in g:
        db_url = os.environ.get('DATABASE_URL')
        # psycopg 3는 더 안정적인 연결 방식을 제공합니다.
        # autocommit=True는 데이터 변경 시 자동으로 커밋되도록 하여 복잡함을 줄입니다.
        g.db = psycopg.connect(db_url, row_factory=dict_row, autocommit=True)
    return g.db

def close_db(e: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db() -> None:
    # 앱 컨텍스트 내에서만 실행되도록 주의
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
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
    except Exception as e:
        print(f"DB 초기화 실패: {e}")

def insert_asset(asset_type, symbol, name, quantity, meta=None, note=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO assets (asset_type, symbol, name, quantity, meta, note) VALUES (%s, %s, %s, %s, %s, %s)",
                (asset_type, symbol, name, quantity, meta, note)
            )

def update_asset(asset_id, quantity, note):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE assets SET quantity = %s, note = %s WHERE id = %s", (quantity, note, asset_id))

def delete_asset(asset_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM assets WHERE id = %s", (asset_id,))

def fetch_assets():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM assets ORDER BY id DESC")
            return cur.fetchall()