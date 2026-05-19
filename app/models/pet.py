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

    traits = db.Column(db.Text)

    pet_image = db.Column(db.Text)

    owner_valid_id = db.Column(db.Text)

    medical_record_file = db.Column(db.Text)

    spayed_neutered = db.Column(db.String(10), default="No")

    vaccinated = db.Column(db.String(10), default="No")

    status = db.Column(
        db.String(50),
        default="pending"
    )

    reason_for_rehoming = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    adoption_requests = db.relationship(
        "AdoptionRequest",
        backref="pet",
        lazy=True
    )

    images = db.relationship(
        "PetImage",
        backref="pet",
        lazy=True,
        cascade="all, delete-orphan"
    )

    valid_ids = db.relationship(
        "PetValidId",
        backref="pet",
        lazy=True,
        cascade="all, delete-orphan"
    )

    favorited_by = db.relationship(
        "Favorite",
        backref="pet_item",
        lazy=True,
        cascade="all, delete-orphan"
    )

    @property
    def traits_list(self):
        if self.traits:
            import json
            try:
                return json.loads(self.traits)
            except:
                return []
        return []