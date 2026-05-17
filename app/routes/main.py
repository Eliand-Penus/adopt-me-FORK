from flask import (
    Blueprint,
    render_template,
    request,
    redirect
)

from flask_login import (
    login_required,
    current_user
)

from app import db

from app.models.pet import Pet
from app.models.adoption_request import AdoptionRequest

from app.utils import save_file, allowed_file, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_EXTENSIONS

main = Blueprint("main", __name__)

# =========================
# HOME PAGE
# =========================

@main.route("/")
def home():

    return render_template(
        "home.html"
    )

# =========================
# USER DASHBOARD
# =========================

@main.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html"
    )

# =========================
# OWNER DASHBOARD
# =========================

@main.route("/owner-dashboard")
@login_required
def owner_dashboard():

    return render_template(
        "owner_dashboard.html"
    )

# =========================
# ADD PET
# =========================

@main.route("/add-pet", methods=["GET", "POST"])
@login_required
def add_pet():

    if request.method == "POST":

        pet_name = request.form.get("pet_name")
        animal_type = request.form.get("animal_type")
        breed = request.form.get("breed")
        age = request.form.get("age")
        gender = request.form.get("gender")
        color = request.form.get("color")
        description = request.form.get("description")

        # Handle file uploads
        pet_image_file = request.files.get("pet_image")
        valid_id_file = request.files.get("valid_id")
        medical_record_file_req = request.files.get("medical_record")

        pet_image_path = None
        owner_valid_id_path = None
        medical_record_path = None

        if pet_image_file and allowed_file(pet_image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            pet_image_path = save_file(pet_image_file, "pets")
            
        if valid_id_file and allowed_file(valid_id_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            owner_valid_id_path = save_file(valid_id_file, "valid_ids")
            
        if medical_record_file_req and allowed_file(medical_record_file_req.filename, ALLOWED_EXTENSIONS):
            medical_record_path = save_file(medical_record_file_req, "medical_records")

        new_pet = Pet(
            owner_id=current_user.user_id,
            pet_name=pet_name,
            animal_type=animal_type,
            breed=breed,
            age=age,
            gender=gender,
            color=color,
            description=description,
            pet_image=pet_image_path,
            owner_valid_id=owner_valid_id_path,
            medical_record_file=medical_record_path,
            # New uploads require admin approval
            status="pending"
        )

        db.session.add(new_pet)

        db.session.commit()

        return redirect("/my-pets")

    return render_template(
        "add_pet.html"
    )

# =========================
# PUBLIC PETS PAGE
# =========================

@main.route("/pets")
def pets():

    query = Pet.query.filter_by(status="approved")
    
    if current_user.is_authenticated:
        query = query.filter(Pet.owner_id != current_user.user_id)
        
    all_pets = query.all()

    return render_template(
        "pets.html",
        pets=all_pets
    )

# =========================
# PET DETAILS
# =========================

@main.route("/pet/<int:pet_id>")
def pet_details(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    return render_template(
        "pet_details.html",
        pet=pet
    )

# =========================
# ADOPT PET
# =========================

@main.route("/adopt/<int:pet_id>")
@login_required
def adopt_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    # Prevent unavailable pets
    if pet.status != "approved":
        return "Pet is not available."

    # Prevent owner from adopting own pet
    if pet.owner_id == current_user.user_id:
        return "You cannot adopt your own pet."

    # Prevent duplicate requests
    existing_request = AdoptionRequest.query.filter_by(
        pet_id=pet.pet_id,
        requester_id=current_user.user_id
    ).first()

    if existing_request:
        return "You already requested this pet."

    # Create adoption request
    adoption_request = AdoptionRequest(
        pet_id=pet.pet_id,
        requester_id=current_user.user_id
    )

    db.session.add(adoption_request)

    db.session.commit()

    return "Adoption request submitted!"

# =========================
# MY PETS
# =========================

@main.route("/my-pets")
@login_required
def my_pets():

    user_pets = Pet.query.filter_by(
        owner_id=current_user.user_id
    ).all()

    return render_template(
        "my_pets.html",
        pets=user_pets
    )

# =========================
# EDIT PET
# =========================

@main.route(
    "/edit-pet/<int:pet_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    # Prevent editing others' pets
    if pet.owner_id != current_user.user_id:
        return "Unauthorized"

    if request.method == "POST":

        pet.pet_name = request.form.get(
            "pet_name"
        )

        pet.breed = request.form.get(
            "breed"
        )

        pet.age = request.form.get(
            "age"
        )

        pet.gender = request.form.get(
            "gender"
        )

        pet.color = request.form.get(
            "color"
        )

        pet.description = request.form.get(
            "description"
        )

        new_status = request.form.get("status")
        if new_status in ["pending", "approved", "adopted", "rejected"]:
            pet.status = new_status

        # Handle file uploads
        pet_image_file = request.files.get("pet_image")
        medical_record_file_req = request.files.get("medical_record")

        if pet_image_file and allowed_file(pet_image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            pet.pet_image = save_file(pet_image_file, "pets")
            
        if medical_record_file_req and allowed_file(medical_record_file_req.filename, ALLOWED_EXTENSIONS):
            pet.medical_record_file = save_file(medical_record_file_req, "medical_records")

        db.session.commit()

        return redirect("/my-pets")

    return render_template(
        "edit_pet.html",
        pet=pet
    )

# =========================
# DELETE PET
# =========================

@main.route("/delete-pet/<int:pet_id>")
@login_required
def delete_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    # Prevent deleting others' pets
    if pet.owner_id != current_user.user_id:
        return "Unauthorized"

    db.session.delete(pet)

    db.session.commit()

    return redirect("/my-pets")

@main.route("/notifications")
@login_required
def notifications():

    owner_pets = Pet.query.filter_by(
        owner_id=current_user.user_id
    ).all()

    pet_ids = [pet.pet_id for pet in owner_pets]

    requests = AdoptionRequest.query.filter(
        AdoptionRequest.pet_id.in_(pet_ids)
    ).all()

    return render_template(
        "notifications.html",
        requests=requests
    )