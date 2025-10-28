from flask import Blueprint, request, jsonify
from auth import role_required
from models import User, Hospital, Appointment, QueueReport,Patient,Doctor
from database import db
from sqlalchemy import func
from datetime import datetime

admin_bp = Blueprint('admin_bp', __name__)

# ========================= Analytics =========================

@admin_bp.route('/view_analytics', methods=['GET'])
@role_required('admin')
def view_analytics(user):
    hospitals = Hospital.query.all()
    data = []

    for h in hospitals:
        # Total appointments for this hospital
        appt_count = Appointment.query.filter_by(hospital_id=h.id).count()

        # Average wait time from QueueReport
        avg_wait = (
            db.session.query(func.avg(QueueReport.wait_time_reported))
            .filter_by(hospital_id=h.id)
            .scalar()
        ) or 0

        # Latest congestion value
        congestion = getattr(h, "current_congestion_level", 0)

        data.append({
            "hospital_id": h.hospital_id,
            "name": h.name,
            "appointment_count": appt_count,
            "average_wait_time": round(avg_wait, 2),
            "congestion": congestion
        })

    return jsonify({"analytics": data}), 200


# ========================= Stats =========================
@admin_bp.route('/stats', methods=['GET'])
@role_required('admin')
def admin_stats(user):
    user_count = User.query.count()
    hospital_count = Hospital.query.count()
    appointment_count = Appointment.query.count()

    return jsonify({
        "total_users": user_count,
        "total_hospitals": hospital_count,
        "total_appointments": appointment_count
    }), 200

#==========================Get Appointments=========================@admin_bp.route("/appointments", methods=["GET"])
@admin_bp.route("/appointments", methods=["GET"])
@role_required("admin")
def get_all_appointments(user):
    """
    Returns all appointments with doctor, patient, and hospital info.
    """
    try:
        appointments = Appointment.query.all()
        data = []

        for a in appointments:
            patient = Patient.query.get(a.patient_id)
            doctor = Doctor.query.get(a.doctor_id)
            hospital = Hospital.query.get(a.hospital_id)

            # handle both datetime and string
            date_str = "N/A"
            time_str = "N/A"
            if a.date_time:
                if isinstance(a.date_time, str):
                    try:
                        parsed_dt = datetime.fromisoformat(a.date_time)
                        date_str = parsed_dt.strftime("%Y-%m-%d")
                        time_str = parsed_dt.strftime("%H:%M")
                    except ValueError:
                        date_str = a.date_time[:10]
                        time_str = a.date_time[11:16] if "T" in a.date_time else "N/A"
                else:
                    date_str = a.date_time.strftime("%Y-%m-%d")
                    time_str = a.date_time.strftime("%H:%M")

            data.append({
                "id": a.id,
                "patient": patient.name if patient else "Unknown",
                "doctor": doctor.name if doctor else "Unknown",
                "hospital": hospital.name if hospital else "Unknown",
                "date": date_str,
                "time": time_str,
                "status": a.status or "Scheduled"
            })

        return jsonify({"appointments": data}), 200

    except Exception as e:
        print("Error fetching appointments:", e)
        return jsonify({"error": str(e)}), 500
    
# ========================= User Management =========================
@admin_bp.route('/users', methods=['GET'])
@role_required('admin')
def get_all_users(user):
    users = User.query.all()
    data = []
    for u in users:
        data.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "status": "Active" if getattr(u, "is_active", True) else "Inactive"
        })
    return jsonify(data), 200


@admin_bp.route('/users', methods=['POST'])
@role_required('admin')
def create_user(user):
    data = request.json
    required = ['name', 'email', 'password', 'role']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "User already exists"}), 400

    new_user = User(
        name=data['name'],
        email=data['email'],
        role=data['role'],
    )
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@role_required('admin')
def delete_user(user, user_id):
    u = User.query.get(user_id)
    if not u:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(u)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"}), 200


# ========================= Approve Patient =========================
@admin_bp.route('/approve_patient', methods=['POST'])
@role_required('admin')
def approve_patient(user):
    data = request.json
    patient_id = data.get('patient_id')
    from models import Patient
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    patient.is_registered = True
    db.session.commit()
    return jsonify({"message": "Patient approved", "patient_id": patient.id}), 200
