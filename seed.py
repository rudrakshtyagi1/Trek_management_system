"""
Run this once before starting the app for the first time:

    python seed.py

This creates all tables programmatically (per the assignment's requirement
that the DB must NOT be built manually with DB Browser) and inserts the
one pre-existing Admin account, since admins never self-register.
"""
from werkzeug.security import generate_password_hash
from app import create_app
from extensions import db
from models import Admin
from config import Config

app = create_app()

with app.app_context():
    db.create_all()
    print("Tables created.")

    existing_admin = Admin.query.filter_by(username=Config.ADMIN_USERNAME).first()
    if existing_admin is None:
        admin = Admin(
            username=Config.ADMIN_USERNAME,
            password_hash=generate_password_hash(Config.ADMIN_PASSWORD),
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin created -> username: {Config.ADMIN_USERNAME}  password: {Config.ADMIN_PASSWORD}")
    else:
        print("Admin already exists, skipped.")
