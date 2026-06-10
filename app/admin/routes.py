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

from app.utils import (
    upload_to_cloudinary,
    ALLOWED_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS
)

# =========================
# ADMIN ENTRYPOINT
# =========================

@admin.route("/")
def admin_home():

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

    # PENDING PETS
    pending_pets = Pet.query.filter(
        Pet.status.ilike("pending")
    ).all()

    # APPROVED PETS
    accepted_pets = Pet.query.filter(
        Pet.status.ilike("approved")
    ).all()

    # REJECTED PETS
    rejected_pets = Pet.query.filter(
        Pet.status.ilike("rejected")
    ).all()

    # CANCELLED PETS
    cancelled_pets = Pet.query.filter(
        Pet.status.ilike("cancelled")
    ).all()

    # TOTAL PETS
    total_pets = Pet.query.count() or 0

    # APPROVED COUNT
    approved_pets_count = Pet.query.filter(
        Pet.status.ilike("approved")
    ).count() or 0

    # REJECTED COUNT
    rejected_pets_count = Pet.query.filter(
        Pet.status.ilike("rejected")
    ).count() or 0

    # CANCELLED COUNT
    cancelled_pets_count = Pet.query.filter(
        Pet.status.ilike("cancelled")
    ).count() or 0

    # PENDING COUNT
    pending_pets_count = Pet.query.filter(
        Pet.status.ilike("pending")
    ).count() or 0

    # USERS
    total_users = User.query.count() or 0

    # ADOPTIONS
    total_adoptions = AdoptionRequest.query.filter(
        AdoptionRequest.status.ilike("approved")
    ).count() or 0

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

        flash(
            "Invalid admin credentials.",
            "danger"
        )

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

    # UPDATE STATUS TO APPROVED
    pet.status = "approved"

    try:

        db.session.commit()

        flash(
            f"{pet.pet_name} has been approved successfully.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print("APPROVE ERROR:", e)

        flash(
            "Failed to approve pet.",
            "danger"
        )

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
                    return redirect(f"/admin/edit-pet/{pet.pet_id}")
            except ValueError:
                flash("Invalid age in years.", "error")
                return redirect(f"/admin/edit-pet/{pet.pet_id}")

        if age_months_str:
            try:
                age_months = int(age_months_str)
                if age_months < 0 or age_months > 11:
                    flash("Age in months must be between 0 and 11.", "error")
                    return redirect(f"/admin/edit-pet/{pet.pet_id}")
            except ValueError:
                flash("Invalid age in months.", "error")
                return redirect(f"/admin/edit-pet/{pet.pet_id}")

        if age_years is None and age_months is None:
            flash("Please enter age in years and/or months.", "error")
            return redirect(f"/admin/edit-pet/{pet.pet_id}")

        pet.age = age_years if age_years is not None else 0
        pet.age_months = age_months if age_months is not None else 0

        gender_val = request.form.get("gender")

        if gender_val in ["Male", "Female"]:
            pet.gender = gender_val

        pet.color = request.form.get("color")

        traits_list = request.form.getlist("traits[]")

        pet.traits = json.dumps(
            traits_list
        ) if traits_list else json.dumps([])

        pet.spayed_neutered = request.form.get(
            "spayed_neutered",
            "No"
        )

        pet.vaccinated = request.form.get(
            "vaccinated",
            "No"
        )

        pet.reason_for_rehoming = request.form.get(
            "reason_for_rehoming"
        )

        # STATUS UPDATE
        new_status = request.form.get("status")

        if new_status:
            pet.status = new_status

        # =========================
        # PET IMAGES
        # =========================

        pet_image_files = request.files.getlist(
            "pet_image"
        )

        if pet_image_files and pet_image_files[0].filename:

            for img in pet_image_files:

                path = upload_to_cloudinary(
                    img,
                    "pets",
                    ALLOWED_IMAGE_EXTENSIONS
                )

                if path:

                    pet.images.append(
                        PetImage(image_path=path)
                    )

                    if not pet.pet_image:
                        pet.pet_image = path

        # =========================
        # VALID IDS
        # =========================

        valid_id_files = request.files.getlist(
            "valid_id"
        )

        if valid_id_files and valid_id_files[0].filename:

            for vid in valid_id_files:

                path = upload_to_cloudinary(
                    vid,
                    "valid_ids",
                    ALLOWED_IMAGE_EXTENSIONS
                )

                if path:

                    pet.valid_ids.append(
                        PetValidId(image_path=path)
                    )

                    if not pet.owner_valid_id:
                        pet.owner_valid_id = path

        # =========================
        # MEDICAL RECORD
        # =========================

        medical_record_file_req = request.files.get(
            "medical_record"
        )

        if medical_record_file_req:

            path = upload_to_cloudinary(
                medical_record_file_req,
                "medical_records",
                ALLOWED_EXTENSIONS
            )

            if path:
                pet.medical_record_file = path

        try:

            db.session.commit()

            flash(
                "Pet details updated successfully.",
                "success"
            )

        except Exception as e:

            db.session.rollback()

            print("EDIT PET ERROR:", e)

            flash(
                "Failed to update pet details.",
                "danger"
            )

        return redirect("/admin")

    traits_list = json.loads(
        pet.traits
    ) if pet.traits else []

    return render_template(
        "admin_edit_pet.html",
        pet=pet,
        traits_list=traits_list
    )

# =========================
# REJECT PET
# =========================

@admin.route("/reject-pet/<int:pet_id>")
@login_required
@admin_required
def reject_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    pet.status = "rejected"

    try:

        db.session.commit()

        flash(
            f"{pet.pet_name} has been rejected.",
            "warning"
        )

    except Exception as e:

        db.session.rollback()

        print("REJECT ERROR:", e)

        flash(
            "Failed to reject pet.",
            "danger"
        )

    return redirect("/admin")

# =========================
# DELETE PET
# =========================

@admin.route("/delete-pet/<int:pet_id>")
@login_required
@admin_required
def delete_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    try:

        db.session.delete(pet)

        db.session.commit()

        flash(
            "Pet deleted successfully.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print("DELETE ERROR:", e)

        flash(
            "Failed to delete pet.",
            "danger"
        )

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
        ).order_by(
            User.user_id.desc()
        ).all()

    else:

        users = User.query.order_by(
            User.user_id.desc()
        ).all()

    total_users = User.query.count() or 0

    return render_template(
        "admin_users.html",
        users=users,
        total_users=total_users,
        search=search
    )

# =========================
# XML EXPORT
# =========================

@admin.route("/export/xml")
@login_required
@admin_required
def export_xml():
    import xml.etree.ElementTree as ET
    from flask import Response
    from app.models.user import User
    from app.models.adoption_request import AdoptionRequest
    
    root = ET.Element("AdoptMeData")
    
    # Pets
    pets_elem = ET.SubElement(root, "Pets")
    for pet in Pet.query.all():
        pet_elem = ET.SubElement(pets_elem, "Pet")
        ET.SubElement(pet_elem, "ID").text = str(pet.pet_id)
        ET.SubElement(pet_elem, "Name").text = pet.pet_name
        ET.SubElement(pet_elem, "Type").text = pet.animal_type
        ET.SubElement(pet_elem, "Status").text = pet.status
        ET.SubElement(pet_elem, "Age").text = pet.formatted_age
        ET.SubElement(pet_elem, "SpayedNeutered").text = pet.spayed_neutered
        ET.SubElement(pet_elem, "Vaccinated").text = pet.vaccinated
        
    # Users
    users_elem = ET.SubElement(root, "Users")
    for user in User.query.all():
        u_elem = ET.SubElement(users_elem, "User")
        ET.SubElement(u_elem, "ID").text = str(user.user_id)
        ET.SubElement(u_elem, "Username").text = user.username
        ET.SubElement(u_elem, "Email").text = user.email
        ET.SubElement(u_elem, "Active").text = str(user.is_active)
        
    # Requests
    requests_elem = ET.SubElement(root, "AdoptionRequests")
    for req in AdoptionRequest.query.all():
        r_elem = ET.SubElement(requests_elem, "Request")
        ET.SubElement(r_elem, "ID").text = str(req.request_id)
        ET.SubElement(r_elem, "PetID").text = str(req.pet_id)
        ET.SubElement(r_elem, "RequesterID").text = str(req.requester_id)
        ET.SubElement(r_elem, "Status").text = req.status
        
    xml_str = ET.tostring(root, encoding="utf-8", method="xml").decode('utf-8')
    
    return Response(
        xml_str,
        mimetype="application/xml",
        headers={"Content-Disposition": "attachment;filename=adopt_me_export.xml"}
    )
