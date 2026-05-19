# pyrefly: ignore [missing-import]
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash
)

# pyrefly: ignore [missing-import]
from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user
)

import json
import os
from uuid import uuid4
from werkzeug.utils import secure_filename

from app.admin.utils import admin_required

from app.models.pet import Pet
from app.models.admin import Admin
from app.models.pet_image import PetImage
from app.models.pet_valid_id import PetValidId

from app import db, bcrypt

admin = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

from app.utils import upload_to_cloudinary, ALLOWED_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS

# =========================
# ADMIN ENTRYPOINT
# =========================

@admin.route("/")
def admin_home():

    # If not logged in
    if not current_user.is_authenticated:
        return redirect("/admin/login")

    return admin_dashboard()

# =========================
# ADMIN DASHBOARD
# =========================

@login_required
@admin_required
def admin_dashboard():
    from app.models.user import User
    from app.models.adoption_request import AdoptionRequest

    pending_pets = Pet.query.filter_by(status="pending").all()
    accepted_pets = Pet.query.filter(Pet.status.ilike("approved") | Pet.status.ilike("available")).all()
    rejected_pets = Pet.query.filter(Pet.status.ilike("rejected")).all()
    cancelled_pets = Pet.query.filter(Pet.status.ilike("cancelled")).all()
    
    total_pets = Pet.query.count() or 0
    approved_pets_count = Pet.query.filter(Pet.status.ilike("approved")).count() or 0
    # Also include available just in case, or just approved as requested. The user's system sometimes uses "available". Let's stick to "approved" as requested.
    rejected_pets_count = Pet.query.filter(Pet.status.ilike("rejected")).count() or 0
    cancelled_pets_count = Pet.query.filter(Pet.status.ilike("cancelled")).count() or 0
    pending_pets_count = Pet.query.filter(Pet.status.ilike("pending")).count() or 0
    
    total_users = User.query.count() or 0
    # Adoptions could be where AdoptionRequest status = 'approved'
    total_adoptions = AdoptionRequest.query.filter(AdoptionRequest.status.ilike("approved")).count() or 0

    stats = {
        "total_pets": total_pets,
        "pending": pending_pets_count,
        "approved": approved_pets_count,
        "rejected": rejected_pets_count,
        "adopted": total_adoptions,
        "cancelled": cancelled_pets_count,
        "total_users": total_users
    }

    return render_template(
        "admin_dashboard.html",
        pending_pets=pending_pets,
        accepted_pets=accepted_pets,
        rejected_pets=rejected_pets,
        cancelled_pets=cancelled_pets,
        stats=stats
    )

# =========================
# ADMIN LOGIN
# =========================

@admin.route("/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        admin_user = Admin.query.filter_by(
            email=email
        ).first()

        if admin_user and bcrypt.check_password_hash(
            admin_user.password_hash,
            password
        ):

            login_user(admin_user)

            return redirect("/admin")

        return "Invalid admin credentials"

    return render_template("admin_login.html")

# =========================
# ADMIN LOGOUT
# =========================

@admin.route("/logout")
@login_required
@admin_required
def admin_logout():

    logout_user()

    return redirect("/admin/login")

# =========================
# APPROVE PET
# =========================

@admin.route("/approve-pet/<int:pet_id>")
@login_required
@admin_required
def approve_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    pet.status = "available"

    db.session.commit()

    return redirect("/admin")

# =========================
# EDIT PET (ADMIN)
# =========================

@admin.route("/edit-pet/<int:pet_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    if request.method == "POST":
        pet.pet_name = request.form.get("pet_name")
        pet.breed = request.form.get("breed")
        pet.age = request.form.get("age")
        gender_val = request.form.get("gender")
        if gender_val in ["Male", "Female"]:
            pet.gender = gender_val
            
        pet.color = request.form.get("color")
        
        traits_list = request.form.getlist("traits[]")
        pet.traits = json.dumps(traits_list) if traits_list else json.dumps([])
        
        pet.spayed_neutered = request.form.get("spayed_neutered", "No")
        pet.vaccinated = request.form.get("vaccinated", "No")
        
        pet.reason_for_rehoming = request.form.get("reason_for_rehoming")

        # Admin can update status
        new_status = request.form.get("status")
        if new_status:
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
        return redirect("/admin")

    traits_list = json.loads(pet.traits) if pet.traits else []
    return render_template("admin_edit_pet.html", pet=pet, traits_list=traits_list)


# =========================
# REJECT PET
# =========================

@admin.route("/reject-pet/<int:pet_id>")
@login_required
@admin_required
def reject_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    pet.status = "rejected"

    db.session.commit()

    return redirect("/admin")

# =========================
# DELETE PET
# =========================

@admin.route("/delete-pet/<int:pet_id>")
@login_required
@admin_required
def delete_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    db.session.delete(pet)
    db.session.commit()

    flash("Pet deleted successfully.", "success")
    return redirect("/admin")

# =========================
# ADMIN USERS PAGE
# =========================

@admin.route("/users")
@login_required
@admin_required
def admin_users():
    from app.models.user import User

    search = request.args.get("search", "")

    if search:
        users = User.query.filter(
            User.email.ilike(f"%{search}%") | 
            User.username.ilike(f"%{search}%") |
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%")
        ).order_by(User.user_id.desc()).all()
    else:
        users = User.query.order_by(User.user_id.desc()).all()

    total_users = User.query.count() or 0

    return render_template(
        "admin_users.html",
        users=users,
        total_users=total_users,
        search=search
    )