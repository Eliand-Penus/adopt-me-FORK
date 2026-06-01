from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    url_for
)

from flask_login import (
    login_required,
    current_user
)

from app import db

from app.models.pet import Pet
from app.models.adoption_request import AdoptionRequest
from app.models.pet_image import PetImage
from app.models.pet_valid_id import PetValidId
from app.models.favorite import Favorite
from app.models.notification import Notification

from app.utils import upload_to_cloudinary, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_EXTENSIONS
import json

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
    notifications = Notification.query.filter_by(user_id=current_user.user_id).order_by(Notification.created_at.desc()).all()
    return render_template("dashboard.html", notifications=notifications)

@main.route("/about")
def about():
    return render_template("about.html")

# =========================
# PROFILE ROUTE
# =========================
@main.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        if request.form.get("form_type") == "password_update":
            current_password = request.form.get("current_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")
            
            if not current_password or not new_password or not confirm_password:
                flash("All password fields are required.", "error")
                return redirect(url_for('main.profile'))
                
            from app import bcrypt
            if not current_user.password_hash or not bcrypt.check_password_hash(current_user.password_hash, current_password):
                flash("Incorrect current password.", "error")
                return redirect(url_for('main.profile'))
                
            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                return redirect(url_for('main.profile'))
                
            current_user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
            db.session.commit()
            flash("Password updated successfully.", "success")
            return redirect(url_for('main.profile'))
            
        else:
            current_user.first_name = request.form.get("first_name")
            current_user.last_name = request.form.get("last_name")
            current_user.username = request.form.get("username")
            current_user.email = request.form.get("email")
            current_user.phone_number = request.form.get("phone_number")
            current_user.address = request.form.get("address")
            
            # Profile Picture Upload
            profile_picture = request.files.get("profile_picture")
            if profile_picture and profile_picture.filename != "":
                from app.utils import upload_to_cloudinary
                url = upload_to_cloudinary(profile_picture, "profile_pictures", ALLOWED_IMAGE_EXTENSIONS)
                if url:
                    current_user.profile_picture = url
                
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for('main.profile'))
        
    return render_template("profile.html")

# =========================
# OWNER DASHBOARD
# =========================

@main.route("/owner-dashboard")
@login_required
def owner_dashboard():

    # Fetch pets for dashboard display (only approved or adopted)
    dashboard_pets = Pet.query.filter(
        Pet.owner_id == current_user.user_id,
        Pet.status.in_(['approved', 'adopted'])
    ).all()
    
    # Check for pending pets to show a notification banner
    pending_count = Pet.query.filter_by(
        owner_id=current_user.user_id,
        status='pending'
    ).count()

    return render_template(
        "owner_dashboard.html",
        pets=dashboard_pets,
        pending_count=pending_count
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
        # Parse and validate years and months
        age_years_str = request.form.get("age", "")
        age_months_str = request.form.get("age_months", "")

        age_years = None
        age_months = None

        if age_years_str:
            try:
                age_years = int(age_years_str)
                if age_years < 0:
                    flash("Age in years must be a non-negative number.", "error")
                    return redirect(url_for("main.add_pet"))
            except ValueError:
                flash("Invalid age in years.", "error")
                return redirect(url_for("main.add_pet"))

        if age_months_str:
            try:
                age_months = int(age_months_str)
                if age_months < 0 or age_months > 11:
                    flash("Age in months must be between 0 and 11.", "error")
                    return redirect(url_for("main.add_pet"))
            except ValueError:
                flash("Invalid age in months.", "error")
                return redirect(url_for("main.add_pet"))

        if age_years is None and age_months is None:
            flash("Please enter age in years and/or months.", "error")
            return redirect(url_for("main.add_pet"))

        age = age_years if age_years is not None else 0
        age_months_val = age_months if age_months is not None else 0

        breed = request.form.get("breed")
        gender = request.form.get("gender")

        if gender not in ["Male", "Female"]:
            flash("Invalid gender selected.", "error")
            return redirect(url_for("main.add_pet"))
            
        color = request.form.get("color")
        traits_list = request.form.getlist("traits[]")
        traits = json.dumps(traits_list) if traits_list else json.dumps([])
        reason_for_rehoming = request.form.get("reason_for_rehoming")
        
        spayed_neutered = request.form.get("spayed_neutered", "No")
        vaccinated = request.form.get("vaccinated", "No")

        # Handle file uploads
        pet_image_files = request.files.getlist("pet_image")
        valid_id_files = request.files.getlist("valid_id")
        medical_record_file_req = request.files.get("medical_record")

        # Keeping the first one for backward compatibility if we still use pet.pet_image
        # But we added PetImage and PetValidId tables. We will populate them.
        # The main columns will be populated using the first successful uploads in the loop
        pet_image_path = None
        owner_valid_id_path = None
        medical_record_path = None
            
        if medical_record_file_req:
            medical_record_path = upload_to_cloudinary(medical_record_file_req, "medical_records", ALLOWED_EXTENSIONS)

        new_pet = Pet(
            owner_id=current_user.user_id,
            pet_name=pet_name,
            animal_type=animal_type,
            breed=breed,
            age=age,
            age_months=age_months_val,

            gender=gender,
            color=color,
            traits=traits,
            reason_for_rehoming=reason_for_rehoming,
            spayed_neutered=spayed_neutered,
            vaccinated=vaccinated,
            pet_image=pet_image_path,
            owner_valid_id=owner_valid_id_path,
            medical_record_file=medical_record_path,
            # New uploads require admin approval
            status="pending"
        )
        
        for img in pet_image_files:
            if img and img.filename:
                path = upload_to_cloudinary(img, "pets", ALLOWED_IMAGE_EXTENSIONS)
                if path:
                    new_pet.images.append(PetImage(image_path=path))
                    if not new_pet.pet_image:
                        new_pet.pet_image = path
                
        for vid in valid_id_files:
            if vid and vid.filename:
                path = upload_to_cloudinary(vid, "valid_ids", ALLOWED_IMAGE_EXTENSIONS)
                if path:
                    new_pet.valid_ids.append(PetValidId(image_path=path))
                    if not new_pet.owner_valid_id:
                        new_pet.owner_valid_id = path

        db.session.add(new_pet)

        db.session.commit()
        
        flash("Your pet submission is pending admin approval.", "success")

        return redirect("/owner-dashboard")

    return render_template(
        "add_pet.html"
    )

# =========================
# CHOOSE CATEGORY
# =========================

@main.route("/choose-category")
def choose_category():
    dog_count = Pet.query.filter_by(animal_type="dog", status="approved").count()
    cat_count = Pet.query.filter_by(animal_type="cat", status="approved").count()
    return render_template("choose_category.html", dog_count=dog_count, cat_count=cat_count)

# =========================
# PUBLIC PETS PAGE
# =========================

@main.route("/pets")
def pets():
    query = Pet.query.filter_by(status="approved")
    
    pet_type = request.args.get("type")
    gender = request.args.get("gender")
    breed = request.args.get("breed")
    min_age = request.args.get("min_age")
    max_age = request.args.get("max_age")

    if pet_type:
        query = query.filter(Pet.animal_type.ilike(pet_type))
    
    if gender:
        query = query.filter(Pet.gender.ilike(gender))
        
    if breed:
        query = query.filter(Pet.breed.ilike(f"%{breed}%"))
        
    if min_age and min_age.isdigit():
        query = query.filter(Pet.age >= int(min_age))
        
    if max_age and max_age.isdigit():
        query = query.filter(Pet.age <= int(max_age))
        
    if current_user.is_authenticated:
        query = query.filter(Pet.owner_id != current_user.user_id)
        
    all_pets = query.all()
    
    # get favorite IDs if user is logged in
    favorite_ids = []
    if current_user.is_authenticated:
        from app.models.favorite import Favorite
        favs = Favorite.query.filter_by(user_id=current_user.user_id).all()
        favorite_ids = [f.pet_id for f in favs]

    return render_template(
        "pets.html",
        pets=all_pets,
        favorite_ids=favorite_ids
    )

# =========================
# FAVORITES
# =========================

@main.route("/toggle-favorite/<int:pet_id>", methods=["POST"])
@login_required
def toggle_favorite(pet_id):
    from app.models.favorite import Favorite
    pet = Pet.query.get_or_404(pet_id)
    
    existing = Favorite.query.filter_by(user_id=current_user.user_id, pet_id=pet_id).first()
    if existing:
        db.session.delete(existing)
        action = "removed"
    else:
        new_fav = Favorite(user_id=current_user.user_id, pet_id=pet_id)
        db.session.add(new_fav)
        action = "added"
        
    db.session.commit()
    return {"status": "success", "action": action}

@main.route("/favorites")
@login_required
def favorites():
    from app.models.favorite import Favorite
    user_favs = Favorite.query.filter_by(user_id=current_user.user_id).all()
    pet_ids = [f.pet_id for f in user_favs]
    
    pets = Pet.query.filter(Pet.pet_id.in_(pet_ids), Pet.status == 'approved').all()
    
    return render_template("favorites.html", pets=pets)

# =========================
# PET DETAILS
# =========================

@main.route("/pet/<int:pet_id>")
def pet_details(pet_id):

    pet = Pet.query.get_or_404(pet_id)
    
    is_favorite = False
    if current_user.is_authenticated:
        from app.models.favorite import Favorite
        fav = Favorite.query.filter_by(user_id=current_user.user_id, pet_id=pet_id).first()
        if fav:
            is_favorite = True

    traits_list = json.loads(pet.traits) if pet.traits else []
    
    return render_template(
        "pet_details.html",
        pet=pet,
        is_favorite=is_favorite,
        traits_list=traits_list
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

    # Create notification for requester
    notification = Notification(
        user_id=current_user.user_id,
        pet_id=pet.pet_id,
        message=f"Your adoption request for {pet.pet_name} has been submitted."
    )
    db.session.add(notification)
    
    db.session.commit()
    
    flash("Your adoption request has been submitted successfully.", "toast_success")
    return redirect(url_for('main.pet_details', pet_id=pet.pet_id))

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

        # Parse and validate years and months
        age_years_str = request.form.get("age", "")
        age_months_str = request.form.get("age_months", "")

        age_years = None
        age_months = None

        if age_years_str:
            try:
                age_years = int(age_years_str)
                if age_years < 0:
                    flash("Age in years must be a non-negative number.", "error")
                    return redirect(url_for("main.edit_pet", pet_id=pet.pet_id))
            except ValueError:
                flash("Invalid age in years.", "error")
                return redirect(url_for("main.edit_pet", pet_id=pet.pet_id))

        if age_months_str:
            try:
                age_months = int(age_months_str)
                if age_months < 0 or age_months > 11:
                    flash("Age in months must be between 0 and 11.", "error")
                    return redirect(url_for("main.edit_pet", pet_id=pet.pet_id))
            except ValueError:
                flash("Invalid age in months.", "error")
                return redirect(url_for("main.edit_pet", pet_id=pet.pet_id))

        if age_years is None and age_months is None:
            flash("Please enter age in years and/or months.", "error")
            return redirect(url_for("main.edit_pet", pet_id=pet.pet_id))

        pet.age = age_years if age_years is not None else 0
        pet.age_months = age_months if age_months is not None else 0


        gender_val = request.form.get("gender")
        if gender_val in ["Male", "Female"]:
            pet.gender = gender_val

        pet.color = request.form.get(
            "color"
        )

        traits_list = request.form.getlist("traits[]")
        pet.traits = json.dumps(traits_list) if traits_list else json.dumps([])
        
        pet.spayed_neutered = request.form.get("spayed_neutered", "No")
        pet.vaccinated = request.form.get("vaccinated", "No")
        
        pet.reason_for_rehoming = request.form.get(
            "reason_for_rehoming"
        )

        new_status = request.form.get("status")
        # Owner can only update to adopted or cancelled if currently approved
        if new_status and pet.status == "approved" and new_status in ["adopted", "cancelled"]:
            pet.status = new_status

        # Handle file uploads
        pet_image_files = request.files.getlist("pet_image")
        valid_id_files = request.files.getlist("valid_id")
        medical_record_file_req = request.files.get("medical_record")

        if pet_image_files and pet_image_files[0].filename:
            for img in pet_image_files:
                path = upload_to_cloudinary(img, "pets", ALLOWED_IMAGE_EXTENSIONS)
                if path:
                    pet.images.append(PetImage(image_path=path))
                    # update main image if empty
                    if not pet.pet_image:
                        pet.pet_image = path
                        
        if valid_id_files and valid_id_files[0].filename:
            for vid in valid_id_files:
                path = upload_to_cloudinary(vid, "valid_ids", ALLOWED_IMAGE_EXTENSIONS)
                if path:
                    pet.valid_ids.append(PetValidId(image_path=path))
                    if not pet.owner_valid_id:
                        pet.owner_valid_id = path
            
        if medical_record_file_req:
            path = upload_to_cloudinary(medical_record_file_req, "medical_records", ALLOWED_EXTENSIONS)
            if path:
                pet.medical_record_file = path

        db.session.commit()
        
        flash("Pet details updated successfully.", "success")

        return redirect("/owner-dashboard")

    traits_list = json.loads(pet.traits) if pet.traits else []
    return render_template(
        "edit_pet.html",
        pet=pet,
        traits_list=traits_list
    )

# =========================
# DELETE PET
# =========================

@main.route("/delete-pet/<int:pet_id>")
@login_required
def delete_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    # Prevent cancelling others' pets
    if pet.owner_id != current_user.user_id:
        return "Unauthorized"

    # Soft delete
    pet.status = "cancelled"

    db.session.commit()
    
    flash("Adoption listing has been removed (cancelled).", "success")

    return redirect("/owner-dashboard")

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