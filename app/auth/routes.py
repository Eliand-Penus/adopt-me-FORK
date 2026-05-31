from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
from flask_login import login_user, logout_user, login_required
import string, random
from sqlalchemy.exc import IntegrityError

from app import db, bcrypt, oauth
from app.models.user import User

auth = Blueprint("auth", __name__)

@auth.route("/login/google")
def google_login():
    redirect_uri = url_for('auth.google_auth_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route("/auth/google/callback")
def google_auth_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        flash("Google login was cancelled or failed.", "error")
        return redirect("/login")
        
    user_info = token.get('userinfo')

    if user_info:
        email = user_info.get('email')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')

        user = User.query.filter_by(email=email).first()

        if not user:
            random_pass = ''.join(random.choices(
                string.ascii_letters + string.digits, k=12
            ))

            base_username = email.split('@')[0]
            username = f"{base_username}_{random.randint(100, 999)}"

            hashed_password = bcrypt.generate_password_hash(
                random_pass
            ).decode("utf-8")

            user = User(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                password_hash=hashed_password
            )

            db.session.add(user)
            db.session.commit()

        login_user(user)
        return redirect("/dashboard")

    return redirect("/login")

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

        if User.query.filter_by(email=email).first():
            flash("Email already exists. Please use another email.", "error")
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
            return redirect(url_for('auth.register'))
            
        if phone_number and User.query.filter_by(phone_number=phone_number).first():
            flash("Phone number already registered.", "error")
            return redirect(url_for('auth.register'))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

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
        try:
            db.session.commit()
            return redirect("/login")
        except IntegrityError:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "error")
            return redirect(url_for('auth.register'))

    return render_template("register.html")

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect("/login")
            
        user = User.query.filter_by(email=email).first()

        if user and user.password_hash and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect("/dashboard")

        flash("Invalid email or password", "error")
        return redirect("/login")

    return render_template("login.html")

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")