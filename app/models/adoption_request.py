from datetime import datetime
from app import db

class AdoptionRequest(db.Model):
    __tablename__ = "adoption_requests"

    request_id = db.Column(
        db.Integer,
        primary_key=True
    )

    pet_id = db.Column(
        db.Integer,
        db.ForeignKey("pets.pet_id"),
        nullable=False
    )

    requester_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        default="pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )