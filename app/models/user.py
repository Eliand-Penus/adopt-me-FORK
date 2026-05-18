from datetime import datetime
from app import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)

    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    phone_number = db.Column(db.String(20))
    address = db.Column(db.Text)

    profile_picture = db.Column(db.Text)

    valid_id_type = db.Column(db.String(100))
    valid_id_image_url = db.Column(db.Text)

    verification_status = db.Column(
        db.String(50),
        default="pending"
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def get_id(self):
        return str(self.user_id)
    
    pets = db.relationship(
        "Pet",
        backref="owner",
        lazy=True
    )

    adoption_requests = db.relationship(
        "AdoptionRequest",
        backref="requester",
        lazy=True
    )

    favorites = db.relationship(
        "Favorite",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )