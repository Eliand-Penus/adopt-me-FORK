# app/admin/create_admin.py

from app.models.admin import Admin
from app import db, bcrypt
import os

def create_default_admin():
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        return

    existing = Admin.query.filter_by(
        email=admin_email
    ).first()

    if existing:
        return

    admin = Admin(
        username=admin_username,
        email=admin_email,
        password_hash=bcrypt.generate_password_hash(
            admin_password
        ).decode("utf-8")
    )

    db.session.add(admin)
    db.session.commit()

    print("Default admin created.")
