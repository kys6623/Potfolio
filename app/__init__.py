import os
from flask import Flask
from .db import close_db, init_db # init_db 추가
from .routes import dashboard_bp

def create_app() -> Flask:
    app = Flask(__name__) # instance_relative_config 제거 가능 (PostgreSQL 사용 시)

    # 1. 설정 로드
    app.config["SECRET_KEY"] = "dev-secret-key-change-me"
    
    # PostgreSQL 연결을 위해 환경 변수 사용
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
    app.config["MOLIT_API_KEY"] = os.getenv("MOLIT_API_KEY", "")

    # 2. 블루프린트 등록
    app.register_blueprint(dashboard_bp)
    
    # 3. DB 종료 훅 등록
    app.teardown_appcontext(close_db)

    # 4. 앱 컨텍스트에서 DB 초기화
    with app.app_context():
        init_db()

    return app