from datetime import datetime
from app import db
# pyrefly: ignore [missing-import]
from flask_login import UserMixin

class Admin(UserMixin, db.Model):
    __tablename__ = "admins"

    admin_id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def get_id(self):
        return str(self.admin_id)