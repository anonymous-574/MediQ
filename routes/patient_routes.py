from flask import Blueprint, request, jsonify
from database import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Patient, SymptomReport, Appointment, QueueReport
from auth import role_required, get_current_user
from services.symptom_service import analyze_symptoms
from services.registration_service import register_patient
from services.appointment_service import book_appointment

patient_bp = Blueprint('patient_bp', __name__)

@patient_bp.route('/profile', methods=['GET'])
@role_required('patient')
def profile(user):
    # user is Patient object via decorator
    p = Patient.query.get(user.id)
    if not p:
        return jsonify({"error": "Patient not found"}), 404
    return jsonify({
        "patient_id": p.patient_id,
        "name": p.name,
        "email": p.email,
        "phone": p.phone,
        "medical_history": p.medical_history,
        "is_registered": p.is_registered
    })

@patient_bp.route('/register', methods=['POST'])
def patient_register():
    data = request.json
    # Reuse registration service
    success, detail = register_patient(data)
    if success:
        return jsonify({"message": "Registration successful", "patient_id": detail}), 201
    else:
        return jsonify({"error": detail}), 400

@patient_bp.route('/submit_symptoms', methods=['POST'])
@role_required('patient')
def submit_symptoms(user):
    data = request.json
    text = data.get('symptoms', '')
    analysis = analyze_symptoms(text)
    # persist SymptomReport
    sr = SymptomReport(
        report_id=f"SR-{int(__import__('time').time())}",
        patient_id=user.id,
        symptoms=text,
        urgency_level=analysis['urgency'],
        classification=analysis['classification'],
        recommendations=";".join(analysis['recommendations'])
    )
    db.session.add(sr)
    db.session.commit()
    return jsonify({
        "message": "Symptoms analyzed",
        "report_id": sr.report_id,
        "urgency": sr.urgency_level,
        "classification": sr.classification,
        "recommendations": analysis['recommendations']
    }), 200

@patient_bp.route('/book_appointment', methods=['POST'])
@role_required('patient')
def book(user):
    data = request.json
    doctor_id = data.get('doctor_id')
    date_time = data.get('date_time')
    hospital_id = data.get('hospital_id')
    result = book_appointment(user.id, doctor_id, hospital_id, date_time)
    if result.get('error'):
        return jsonify(result), 400
    return jsonify(result), 201

@patient_bp.route('/appointments', methods=['GET'])
@role_required('patient')
def get_patient_appointments(user):
    appointments = Appointment.query.filter_by(patient_id=user.id).all()
    data = [
        {
            "appointment_id": a.appointment_id, 
            "doctor_id": a.doctor_id,
            "hospital_id": a.hospital_id,
            "date_time": str(a.date_time),
            "status": a.status,
            "notes": a.notes
        }
        for a in appointments
    ]
    return jsonify(data), 200

@patient_bp.route('/submit_queue_report', methods=['POST'])
@role_required('patient')
def submit_queue_report(user):
    data = request.json
    hospital_id = data.get('hospital_id')
    queue_length = int(data.get('queue_length', 0))
    wait_time = int(data.get('wait_time', 0))
    department = data.get('department', 'general')
    qr = QueueReport(
        report_id=f"QR-{int(__import__('time').time())}",
        hospital_id=hospital_id,
        submitted_by=user.name,
        queue_length=queue_length,
        wait_time_reported=wait_time,
        department=department
    )
    db.session.add(qr)
    db.session.commit()
    return jsonify({"message": "Queue report submitted", "report_id": qr.report_id}), 201
