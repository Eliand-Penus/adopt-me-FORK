from datetime import datetime
from app import db

class PetValidId(db.Model):
    __tablename__ = "pet_valid_ids"

    id = db.Column(db.Integer, primary_key=True)
    
    pet_id = db.Column(
        db.Integer,
        db.ForeignKey("pets.pet_id"),
        nullable=False
    )
    
    image_path = db.Column(db.Text, nullable=False)
    
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
