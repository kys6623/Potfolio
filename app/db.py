import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import current_app, g
from typing import Any

def get_db():
    """
    PostgreSQL 연결을 관리합니다. (Supabase 연결)
    """
    if "db" not in g:
        db_url = os.environ.get('DATABASE_URL')
        # RealDictCursor를 사용하여 SQLite의 Row처럼 사전형으로 데이터를 가져옵니다.
        g.db = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return g.db

def close_db(e: Exception | None = None) -> None:
    """
    요청이 끝나면 DB 연결을 닫습니다.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db() -> None:
    """
    테이블이 없으면 생성합니다. (PostgreSQL 문법 적용)
    """
    db = get_db()
    with db.cursor() as cur:
        # 1. 테이블 생성 (AUTOINCREMENT 대신 SERIAL 사용)
        cur.execute(
            """
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
            """
        )

        # 2. 마이그레이션 로직 (PostgreSQL 방식)
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'assets'"
        )
        existing_columns = {row['column_name'] for row in cur.fetchall()}
        
        if "meta" not in existing_columns:
            cur.execute("ALTER TABLE assets ADD COLUMN meta TEXT")
        if "note" not in existing_columns:
            cur.execute("ALTER TABLE assets ADD COLUMN note TEXT")
            
    db.commit()

def insert_asset(
    asset_type: str,
    symbol: str | None,
    name: str,
    quantity: float,
    meta: str | None = None,
    note: str | None = None,
) -> None:
    db = get_db()
    with db.cursor() as cur:
        # ? 대신 %s 사용
        cur.execute(
            """
            INSERT INTO assets (asset_type, symbol, name, quantity, meta, note)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (asset_type, symbol, name, quantity, meta, note),
        )
    db.commit()

def update_asset(asset_id: int, quantity: float, note: str | None) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE assets
            SET quantity = %s, note = %s
            WHERE id = %s
            """,
            (quantity, note, asset_id),
        )
    db.commit()

def delete_asset(asset_id: int) -> None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
    db.commit()

def fetch_assets() -> list[dict[str, Any]]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, asset_type, symbol, name, quantity, meta, note, created_at
            FROM assets
            ORDER BY id DESC
            """
        )
        rows = cur.fetchall()
    # RealDictCursor를 썼기 때문에 이미 dict 형태입니다.
    return [dict(row) for row in rows]