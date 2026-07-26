import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Keep this simple and explicit -- fine for a local/course-demo app.
    # In a real production app this would come from an environment variable.
    SECRET_KEY = "mad1-trekking-app-secret-key"

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "trekking.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Seed admin credentials (admin is pre-existing, not self-registered)
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin123"
