from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    db.session.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
    db.session.commit()
    print("Vector extension created successfully.")
