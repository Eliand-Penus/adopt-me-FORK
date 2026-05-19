from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash
)
import json

from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user
)

from app.admin.utils import admin_required

from app.models.pet import Pet
from app.models.admin import Admin
from app.models.pet_image import PetImage
from app.models.pet_valid_id import PetValidId
from app.utils import save_file, allowed_file, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_EXTENSIONS

from app import db, bcrypt

admin = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

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

    pending_pets = Pet.query.filter_by(
        status="pending"
    ).all()

    accepted_pets = Pet.query.filter_by(
        status="approved"
    ).all()

    rejected_pets = Pet.query.filter_by(
        status="rejected"
    ).all()
    
    cancelled_pets = Pet.query.filter_by(
        status="cancelled"
    ).all()
    
    # Analytics Stats
    stats = {
        'pending': len(pending_pets),
        'approved': len(accepted_pets),
        'rejected': len(rejected_pets),
        'adopted': Pet.query.filter_by(status="adopted").count(),
        'cancelled': Pet.query.filter_by(status="cancelled").count()
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

    pet.status = "approved"

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
        pet.gender = request.form.get("gender")
        pet.color = request.form.get("color")
        
        traits_list = request.form.getlist("traits[]")
        pet.traits = json.dumps(traits_list) if traits_list else json.dumps([])
        
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
                if img and allowed_file(img.filename, ALLOWED_IMAGE_EXTENSIONS):
                    path = save_file(img, "pets")
                    if path:
                        pet.images.append(PetImage(image_path=path))
                        if not pet.pet_image:
                            pet.pet_image = path
                        
        if valid_id_files and valid_id_files[0].filename:
            for vid in valid_id_files:
                if vid and allowed_file(vid.filename, ALLOWED_IMAGE_EXTENSIONS):
                    path = save_file(vid, "valid_ids")
                    if path:
                        pet.valid_ids.append(PetValidId(image_path=path))
                        if not pet.owner_valid_id:
                            pet.owner_valid_id = path
            
        if medical_record_file_req and allowed_file(medical_record_file_req.filename, ALLOWED_EXTENSIONS):
            pet.medical_record_file = save_file(medical_record_file_req, "medical_records")

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
# DELETE PET (ADMIN)
# =========================

@admin.route("/delete-pet/<int:pet_id>")
@login_required
@admin_required
def delete_pet(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    db.session.delete(pet)
    db.session.commit()
    return redirect("/admin")

# =========================
# USERS MANAGEMENT
# =========================

@admin.route("/users")
@login_required
@admin_required
def manage_users():
    search = request.args.get("search", "")
    from app.models.user import User
    
    if search:
        users = User.query.filter(User.email.ilike(f"%{search}%") | User.username.ilike(f"%{search}%")).all()
    else:
        users = User.query.all()
        
    return render_template("admin_users.html", users=users, search=search)

@admin.route("/toggle-user-status/<int:user_id>")
@login_required
@admin_required
def toggle_user_status(user_id):
    from app.models.user import User
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    return redirect("/admin/users")

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