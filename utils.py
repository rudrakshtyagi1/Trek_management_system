from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(role):
    """Blocks a route unless the logged-in user's role matches (e.g. a
    trekker hitting /admin/dashboard by guessing the URL gets a 403)."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            current_role = current_user.get_id().split("-")[0]
            if current_role != role:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
