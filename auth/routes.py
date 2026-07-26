from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import Admin, Staff, User

auth_bp = Blueprint("auth", __name__)


def _redirect_to_dashboard(role):
    if role == "admin":
        return redirect(url_for("admin.dashboard"))
    if role == "staff":
        return redirect(url_for("staff.dashboard"))
    return redirect(url_for("user.dashboard"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_to_dashboard(current_user.get_id().split("-")[0])

    if request.method == "POST":
        role = request.form.get("role")  # 'admin' | 'staff' | 'user'
        email_or_username = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        account = None
        if role == "admin":
            account = Admin.query.filter_by(username=email_or_username).first()
        elif role == "staff":
            account = Staff.query.filter_by(email=email_or_username).first()
        elif role == "user":
            account = User.query.filter_by(email=email_or_username).first()

        if account is None or not check_password_hash(account.password_hash, password):
            flash("Invalid credentials.", "danger")
            return render_template("auth/login.html")

        # Role-specific gating
        if role == "staff":
            if account.status == "pending":
                flash("Your registration is still awaiting admin approval.", "warning")
                return render_template("auth/login.html")
            if account.status == "rejected":
                flash("Your staff registration was rejected by the admin.", "danger")
                return render_template("auth/login.html")
            if account.status == "blacklisted":
                flash("Your staff account has been blacklisted.", "danger")
                return render_template("auth/login.html")

        if role == "user" and account.is_blacklisted:
            flash("Your account has been blacklisted.", "danger")
            return render_template("auth/login.html")

        login_user(account)
        flash("Logged in successfully.", "success")
        return _redirect_to_dashboard(role)

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registration is allowed for Trek Staff and Users only -- admin is
    pre-seeded (see seed.py) and never registers through this form."""
    if request.method == "POST":
        role = request.form.get("role")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        contact = request.form.get("contact", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if role not in ("staff", "user"):
            flash("Invalid role selected.", "danger")
            return render_template("auth/register.html")

        if not name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("auth/register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        model = Staff if role == "staff" else User
        if model.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html")

        hashed = generate_password_hash(password)
        if role == "staff":
            account = Staff(name=name, email=email, contact=contact, password_hash=hashed)
        else:
            account = User(name=name, email=email, contact=contact, password_hash=hashed)

        db.session.add(account)
        db.session.commit()

        if role == "staff":
            flash("Registered! Your account needs admin approval before you can log in.", "info")
        else:
            flash("Registered successfully. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
