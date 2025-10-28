from flask import Flask, jsonify
from flask_cors import CORS
from database import db 

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')

    # CORS setup
    origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS(app, origins=origins)
    
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
    from routes.nurse_routes import nurse_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
    app.register_blueprint(hospital_bp, url_prefix='/api/hospital')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(nurse_bp, url_prefix="/api/nurse")
    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return jsonify({"message": "MediQ API running"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
