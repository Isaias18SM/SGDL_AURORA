from functools import wraps
from flask import session, redirect, url_for, jsonify

def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'correo' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def solo_rol(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'correo' not in session:
                return redirect(url_for('auth.login'))
            if session.get('rol') not in roles:
                return redirect(url_for('auth.dashboard_segun_rol'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def solo_rol_api(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'correo' not in session:
                return jsonify({"status": "error", "message": "Debes iniciar sesión."}), 401
            if session.get('rol') not in roles:
                return jsonify({"status": "error", "message": "Acceso restringido solo para Instructores."}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator