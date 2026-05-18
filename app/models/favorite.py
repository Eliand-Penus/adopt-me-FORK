from datetime import datetime
from app import db

class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )
    
    pet_id = db.Column(
        db.Integer,
        db.ForeignKey("pets.pet_id"),
        nullable=False
    )
    
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
