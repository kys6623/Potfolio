import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import g
from typing import Any

def get_db():
    if "db" not in g:
        # 환경 변수에서 URL을 가져옴
        db_url = os.environ.get('DATABASE_URL')
        
        # psycopg2.connect에 host/port/dbname 등을 분리해서 전달
        # 이렇게 하면 내부적인 주소 해석(DNS Resolution) 이슈를 줄일 수 있습니다.
        g.db = psycopg2.connect(
            db_url,
            cursor_factory=RealDictCursor,
            connect_timeout=15, # 대기 시간을 15초로 늘림
            keepalives=1,       # 연결 끊김 방지
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    try:
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
    except Exception as e:
        print(f"DB 초기화 오류: {e}")

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
