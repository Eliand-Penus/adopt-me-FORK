import os

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# pyrefly: ignore [missing-import]
from flask import Flask
# pyrefly: ignore [missing-import]
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
oauth = OAuth()

# LOAD .env VARIABLES
load_dotenv()


def create_app():
    app = Flask(__name__)

    # LOAD CONFIG
    app.config.from_object("config.Config")

    # CLOUDINARY CONFIG
    import cloudinary
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True
    )

    # INIT EXTENSIONS
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"

    # GOOGLE OAUTH
    oauth.init_app(app)

    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    # IMPORT MODELS
    from app.models.user import User

    # IMPORT BLUEPRINTS
    from app.routes.main import main
    from app.auth.routes import auth
    from app.admin.routes import admin

    # USER LOADER
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # REGISTER BLUEPRINTS
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(admin)

    # CUSTOM JINJA FILTERS
    @app.template_filter('ph_time')
    def format_ph_time(dt_utc):
        if not dt_utc:
            return ""
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=ZoneInfo("UTC"))
        dt_ph = dt_utc.astimezone(ZoneInfo("Asia/Manila"))
        return dt_ph.strftime('%m/%d/%Y - %I:%M %p')

    return app