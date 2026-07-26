from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# These are created here (not inside app.py) so that models.py and every
# blueprint can import `db` without causing circular imports.
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
