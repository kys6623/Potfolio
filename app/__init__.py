import os
from flask import Flask
from .db import close_db
from .routes import dashboard_bp

def create_app() -> Flask:
    """
    Flask application factory.
    """
    # 1. Flask 앱 생성 (instance_path를 사용할 수 있게 설정)
    app = Flask(__name__, instance_relative_config=True)

    # 2. 설정 로드
    app.config["SECRET_KEY"] = "dev-secret-key-change-me"
    
    # OS에 상관없이 경로를 잘 잡도록 os.path.join을 권장합니다.
    # Vercel(리눅스) 환경을 위해 \\ 대신 / 를 사용하거나 join을 쓰세요.
    app.config["DATABASE"] = os.path.join(app.instance_path, "portfolio.sqlite3")
    app.config["MOLIT_API_KEY"] = os.getenv("MOLIT_API_KEY", "")

    # 3. Vercel 환경이 아닐 때만 instance 폴더 생성 시도 (핵심 수정 부분)
    if not os.environ.get('VERCEL'):
        try:
            os.makedirs(app.instance_path, exist_ok=True)
        except OSError:
            pass

    # 4. 블루프린트 및 DB 종료 훅 등록
    app.register_blueprint(dashboard_bp)
    app.teardown_appcontext(close_db)

    return app