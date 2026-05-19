from datetime import datetime
from app import db

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.pet_id'), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships are handled via backrefs on User and Pet models if needed,
    # but we can explicitly define them here if not already defined there.
    # For simplicity, we just rely on explicit queries or we can add relationships:
    pet_rel = db.relationship("Pet", foreign_keys=[pet_id])
