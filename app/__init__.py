from flask import Flask

from .db import close_db
from .routes import dashboard_bp


def create_app() -> Flask:
    """
    Flask application factory.

    Why factory pattern:
    - Makes the project easier to scale and test.
    - Keeps initialization concerns (config, blueprints, teardown) in one place.
    """
    app = Flask(__name__, instance_relative_config=True)

    import os

    # Secret key is required for flash messages/session.
    # For production, replace with a strong value via environment variable.
    app.config["SECRET_KEY"] = "dev-secret-key-change-me"

    # SQLite DB file lives in instance/ so it is separated from source code.
    app.config["DATABASE"] = app.instance_path + "\\portfolio.sqlite3"
    app.config["MOLIT_API_KEY"] = os.getenv("MOLIT_API_KEY", "")

    # Ensure instance folder exists before DB is used.
    os.makedirs(app.instance_path, exist_ok=True)

    # Register routes and DB lifecycle hook.
    app.register_blueprint(dashboard_bp)
    app.teardown_appcontext(close_db)

    return app
