from datetime import datetime
from app import db

class Pet(db.Model):
    __tablename__ = "pets"

    pet_id = db.Column(db.Integer, primary_key=True)

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    pet_name = db.Column(
        db.String(100),
        nullable=False
    )

    animal_type = db.Column(
        db.String(50),
        nullable=False
    )

    breed = db.Column(db.String(100))

    age = db.Column(db.Integer)

    gender = db.Column(db.String(20))

    color = db.Column(db.String(50))

    description = db.Column(db.Text)

    adoption_status = db.Column(
        db.String(50),
        default="pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    adoption_requests = db.relationship(
        "AdoptionRequest",
        backref="pet",
        lazy=True
    )