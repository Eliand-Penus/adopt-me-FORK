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

    return render_template(
        "admin_dashboard.html",
        pending_pets=pending_pets,
        accepted_pets=accepted_pets,
        rejected_pets=rejected_pets
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