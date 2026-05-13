from functools import wraps

from flask_login import current_user
from flask import redirect

from app.models.admin import Admin

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        # Not logged in
        if not current_user.is_authenticated:
            return redirect("/admin/login")

        # Check admin table
        admin = Admin.query.filter_by(
            admin_id=current_user.get_id()
        ).first()

        # Not admin
        if not admin:
            return redirect("/")

        return f(*args, **kwargs)

    return decorated_function