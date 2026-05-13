from flask import Blueprint
from flask_login import login_required, current_user
from flask import render_template, request, redirect
from app.models.pet import Pet
from app import db
from app.models.adoption_request import AdoptionRequest

main = Blueprint("main", __name__)

@main.route("/")
def home():
    return render_template("home.html")

@main.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html"
    )

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

        new_pet = Pet(
            owner_id=current_user.user_id,
            pet_name=pet_name,
            animal_type=animal_type,
            breed=breed,
            age=age,
            gender=gender,
            color=color,
            description=description
        )

        db.session.add(new_pet)
        db.session.commit()

        return redirect("/pets")

    return render_template("add_pet.html")

@main.route("/pets")
def pets():

    all_pets = Pet.query.filter_by(
        adoption_status="available"
    ).all()

    return render_template(
        "pets.html",
        pets=all_pets
    )

@main.route("/pet/<int:pet_id>")
def pet_details(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    return render_template(
        "pet_details.html",
        pet=pet
    )

@main.route("/adopt/<int:pet_id>")
@login_required
def adopt_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    existing_request = AdoptionRequest.query.filter_by(
        pet_id=pet.pet_id,
        requester_id=current_user.user_id
    ).first()

    if existing_request:
        return "You already requested this pet."

    adoption_request = AdoptionRequest(
        pet_id=pet.pet_id,
        requester_id=current_user.user_id
    )

    db.session.add(adoption_request)
    db.session.commit()

    return "Adoption request submitted!"

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

@main.route("/edit-pet/<int:pet_id>", methods=["GET", "POST"])
@login_required
def edit_pet(pet_id):

    pet = Pet.query.get_or_404(pet_id)

    # Prevent editing others' pets
    if pet.owner_id != current_user.user_id:
        return "Unauthorized"

    if request.method == "POST":

        pet.pet_name = request.form.get("pet_name")
        pet.breed = request.form.get("breed")
        pet.age = request.form.get("age")
        pet.gender = request.form.get("gender")
        pet.color = request.form.get("color")
        pet.description = request.form.get("description")

        # Send back to pending after editing
        pet.adoption_status = "pending"

        db.session.commit()

        return redirect("/my-pets")

    return render_template(
        "edit_pet.html",
        pet=pet
    )

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