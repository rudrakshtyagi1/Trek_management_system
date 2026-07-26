from flask import Flask, render_template
from config import Config
from extensions import db, login_manager
from models import Admin, Staff, User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from auth.routes import auth_bp
    from admin.routes import admin_bp
    from staff.routes import staff_bp
    from user.routes import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(staff_bp, url_prefix="/staff")
    app.register_blueprint(user_bp, url_prefix="/user")

    @app.route("/")
    def index():
        return render_template("shared/landing.html")

    return app


@login_manager.user_loader
def load_user(composite_id):
    """composite_id looks like 'admin-1', 'staff-4', 'user-9'."""
    try:
        role, raw_id = composite_id.split("-", 1)
        raw_id = int(raw_id)
    except (ValueError, AttributeError):
        return None

    if role == "admin":
        return Admin.query.get(raw_id)
    if role == "staff":
        return Staff.query.get(raw_id)
    if role == "user":
        return User.query.get(raw_id)
    return None


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
