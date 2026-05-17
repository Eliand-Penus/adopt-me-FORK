from flask import Blueprint, render_template, request, redirect
from flask_login import login_user, logout_user, login_required

from app import db, bcrypt
from app.models.user import User

auth = Blueprint("auth", __name__)

@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password_hash=hashed_password,
            phone_number=phone_number,
            address=address
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(
            user.password_hash,
            password
        ):

            login_user(user)

            return redirect("/dashboard")

        return "Invalid email or password"

    return render_template("login.html")

@auth.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/login")