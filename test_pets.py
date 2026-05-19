from app import create_app, db
from app.models.pet import Pet

app = create_app()
with app.app_context():
    try:
        pets = Pet.query.all()
        print(f"Success! Found {len(pets)} pets.")
    except Exception as e:
        print(f"Error: {e}")
