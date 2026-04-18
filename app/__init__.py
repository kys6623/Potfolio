import os
from flask import Flask
from .db import close_db, init_db
from .routes import dashboard_bp

def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "dev-secret-key-change-me"
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
    app.config["MOLIT_API_KEY"] = os.getenv("MOLIT_API_KEY", "")

    app.register_blueprint(dashboard_bp)
    app.teardown_appcontext(close_db)

    # [수정] 앱 시작 시 즉시 실행하는 대신, 
    # 첫 번째 요청이 처리되기 직전에 테이블이 있는지 확인하도록 설정합니다.
    @app.before_request
    def setup_db():
        # 전역 플래그를 사용하여 앱이 실행되는 동안 딱 한 번만 실행되게 합니다.
        if not getattr(app, '_db_initialized', False):
            init_db()
            app._db_initialized = True

    return app