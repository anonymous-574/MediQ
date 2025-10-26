from flask import Blueprint, request, jsonify, current_app
from database import db

from models import User, Patient, Doctor, HospitalAdministrator
from passlib.hash import pbkdf2_sha256
from auth import generate_jwt

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    required = ['name', 'email', 'password', 'role']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400
    role = data.get('role')
    existing = User.query.filter_by(email=data.get('email')).first()
    if existing:
        return jsonify({"error": "Email already exists"}), 400

    # create based on role
    pwd = pbkdf2_sha256.hash(data.get('password'))
    if role == 'patient':
        u = Patient(name=data.get('name'), email=data.get('email'), phone=data.get('phone'), password_hash=pwd)
    elif role == 'doctor':
        u = Doctor(name=data.get('name'), email=data.get('email'), phone=data.get('phone'), password_hash=pwd, specialty=data.get('specialty'))
    elif role == 'admin':
        u = HospitalAdministrator(name=data.get('name'), email=data.get('email'), phone=data.get('phone'), password_hash=pwd)
    else:
        return jsonify({"error": "Unsupported role"}), 400

    db.session.add(u)
    db.session.commit()
    return jsonify({"message": "User registered", "user_id": u.id}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing credentials"}), 400
    user = User.query.filter_by(email=data.get('email')).first()
    user = User.query.filter_by(email=data.get('email')).first()
    print("Login attempt:", data.get('email'))
    print("User found:", user)
    if not user:
        print("No such user in DB")
        return jsonify({"error": "Invalid credentials"}), 401
    if not pbkdf2_sha256.verify(data.get('password'), user.password_hash):
        print("Password mismatch")
        return jsonify({"error": "Invalid credentials"}), 401
    payload = {"user_id": user.id, "role": user.role, "name": user.name}
    token = generate_jwt(payload)
    return jsonify({"access_token": token, "user_id": user.id, "role": user.role})
