from flask import Flask, jsonify
from flask_cors import CORS
from database import db  # ✅ Import db from database.py

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'super-secret-key'
    
    db.init_app(app)
    

    # Import models after db is bound
    from models import (
        User, Patient, Doctor, Nurse, HospitalAdministrator,
        Appointment, Hospital, SymptomReport, QueueReport, TimeSlot
    )

    from routes.patient_routes import patient_bp
    from routes.doctor_routes import doctor_bp
    from routes.hospital_routes import hospital_bp
    from routes.admin_routes import admin_bp
    from routes.auth_routes import auth_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
    app.register_blueprint(hospital_bp, url_prefix='/api/hospital')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return jsonify({"message": "MediQ API running"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
