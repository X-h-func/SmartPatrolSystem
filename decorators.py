from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Decorator to restrict access to specified roles.
    Usage: @role_required('admin') or @role_required('admin', 'supervisor')
    Must be used AFTER @login_required.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
