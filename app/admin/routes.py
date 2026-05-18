from flask import (
    Blueprint,
    render_template,
    request,
    redirect
)

from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user
)

from app.admin.utils import admin_required

from app.models.pet import Pet
from app.models.admin import Admin

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