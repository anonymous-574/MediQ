import jwt
from flask import current_app, request, jsonify
from functools import wraps
from models import User, Patient, Doctor, HospitalAdministrator
from database import db

def generate_jwt(payload, exp_seconds=3600):
    import datetime
    secret = current_app.config['SECRET_KEY']
    payload_copy = payload.copy()
    payload_copy['exp'] = datetime.datetime.utcnow() + datetime.timedelta(seconds=exp_seconds)
    token = jwt.encode(payload_copy, secret, algorithm='HS256')
    return token

def decode_jwt(token):
    secret = current_app.config['SECRET_KEY']
    try:
        data = jwt.decode(token, secret, algorithms=['HS256'])
        return data
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None

def get_current_user():
    auth = request.headers.get('Authorization', None)
    print("Authorization header:", auth)  # 👈 add this
    if not auth:
        return None
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    token = parts[1]
    print("Token:", token[:30], "...")  # 👈 add this
    data = decode_jwt(token)
    print("Decoded data:", data)  # 👈 add this
    if not data:
        return None
    user = User.query.get(data.get('user_id'))
    print("User found:", user)
    return user


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            if user.role not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(user, *args, **kwargs)
        return wrapper
    return decorator
