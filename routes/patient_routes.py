from flask import Blueprint, request, jsonify
from database import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Patient, SymptomReport, Appointment, QueueReport
from auth import role_required, get_current_user
from services.symptom_service import analyze_symptoms
from services.registration_service import register_patient
from services.appointment_service import book_appointment
from sqlalchemy.orm import joinedload
from models import Hospital, Doctor
from flask_cors import cross_origin
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
    print("DEBUG RESULT:", result)
    if result.get('error'):
        return jsonify(result), 400
    return jsonify(result), 201

from sqlalchemy.orm import joinedload

@patient_bp.route('/appointments', methods=['GET'])
@role_required('patient')
def list_patient_appointments(user):
    appointments = (
        Appointment.query.options(
            joinedload(Appointment.doctor),
            joinedload(Appointment.hospital)
        )
        .filter_by(patient_id=user.id)
        .all()
    )

    data = []
    for a in appointments:
        # ✅ Try to resolve hospital properly
        hospital = a.hospital
        if not hospital:
            # fallback: hospital_id might be string like "HOSP-1"
            hospital = Hospital.query.filter_by(hospital_id=str(a.hospital_id)).first()

        # ✅ Normalize date format
        date_str = None
        if hasattr(a.date_time, "isoformat"):
            date_str = a.date_time.isoformat()
        else:
            # Clean up if stored as string like "2025-10-31 2025-10-31T11:00:00"
            parts = str(a.date_time).split()
            date_str = parts[-1] if len(parts) > 1 else parts[0]

        data.append({
            "appointment_id": a.appointment_id,
            "doctor_id": a.doctor_id,
            "doctor_name": a.doctor.name if a.doctor else "Unknown Doctor",
            "hospital_id": a.hospital_id,
            "hospital_name": hospital.name if hospital else "Unknown Hospital",
            "date_time": date_str,
            "status": a.status,
            "notes": a.notes
        })

    print("DEBUG APPOINTMENTS:", data)
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
@patient_bp.route('/queue_status', methods=['GET'])
@role_required('patient')
def queue_status(user):
    """
    Returns the patient's active queue status, or aggregated queue data if not in queue.
    """
    hospital_id_param = request.args.get('hospital_id')
    department = request.args.get('department', 'general')

    # find active appointment
    active_appt = (
        Appointment.query
        .filter_by(patient_id=user.id, status='Scheduled')
        .order_by(Appointment.created_at.desc())
        .first()
    )

    # If no active appointment, return default
    if not active_appt:
        return jsonify({
            "in_queue": False,
            "doctor": "-",
            "hospital": "-",
            "position": 0,
            "estimated_wait": 0,
            "total_in_queue": 0,
            "patients_ahead": 0,
            "room": "-",
            "joined_at": None,
            "status": "Not in Queue"
        }), 200

    # Get proper hospital_id (integer FK)
    hospital_id = active_appt.hospital_id
    if hospital_id_param:
        # try to override only if it matches numeric ID
        try:
            hospital_id = int(hospital_id_param)
        except ValueError:
            pass

    hospital = Hospital.query.get(hospital_id)
    doctor = Doctor.query.get(active_appt.doctor_id)

    # Query queue reports for same hospital + department
    reports = QueueReport.query.filter_by(hospital_id=hospital_id, department=department).all()

    if reports:
        avg_queue = sum(r.queue_length for r in reports) / len(reports)
        avg_wait = sum(r.wait_time_reported for r in reports) / len(reports)
    else:
        avg_queue, avg_wait = 3, 15  # sensible defaults

    total_in_queue = int(round(avg_queue))
    position = min(total_in_queue, 1)
    patients_ahead = max(0, total_in_queue - position)

    response = {
        "in_queue": True,
        "doctor": doctor.name if doctor else "Unassigned",
        "department": specialty if (specialty := getattr(doctor, "specialty", None)) else "General",
        "hospital": hospital.name if hospital else "Unknown",
        "position": position,
        "estimated_wait": round(avg_wait, 2),
        "total_in_queue": total_in_queue,
        "patients_ahead": patients_ahead,
        "room": getattr(doctor, "room", "OPD-1"),
        "joined_at": str(active_appt.date_time),
        "status": "Active"
    }

    print("QUEUE STATUS RESPONSE:", response)
    return jsonify(response), 200



@patient_bp.route('/appointments/<appointment_id>', methods=['DELETE', 'OPTIONS'])
def cancel_appointment(appointment_id):
    # Allow unauthenticated preflight
    if request.method == 'OPTIONS':
        return '', 200

    # For DELETE requests, require authentication
    from auth import get_current_user
    user = get_current_user()

    if not user or user.role != 'patient':
        return jsonify({"error": "Unauthorized"}), 401

    appt = Appointment.query.filter_by(appointment_id=appointment_id, patient_id=user.id).first()
    if not appt:
        return jsonify({"error": "Appointment not found"}), 404

    if appt.status != "Scheduled":
        return jsonify({"error": "Only scheduled appointments can be cancelled"}), 400

    appt.status = "Cancelled"
    db.session.commit()

    return jsonify({"message": "Appointment cancelled", "appointment_id": appointment_id}), 200
