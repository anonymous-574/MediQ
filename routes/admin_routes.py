from flask import Blueprint, request, jsonify
from auth import role_required
from models import User, Hospital, Appointment
from database import db


admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/view_analytics', methods=['GET'])
@role_required('admin')
def analytics(user):
    # Very simple analytics
    hospitals = Hospital.query.all()
    data = []
    for h in hospitals:
        appt_count = Appointment.query.filter_by(hospital_id=h.id).count()
        data.append({
            "hospital_id": h.hospital_id,
            "name": h.name,
            "appointment_count": appt_count,
            "congestion": h.current_congestion_level
        })
    return jsonify({"analytics": data}), 200

@admin_bp.route('/approve_patient', methods=['POST'])
@role_required('admin')
def approve_patient(user):
    data = request.json
    patient_id = data.get('patient_id')
    p = User.query.get(patient_id)
    if not p or p.role != 'patient':
        return jsonify({"error":"Patient not found"}), 404
    # set registered flag
    from models import Patient
    patient = Patient.query.get(patient_id)
    patient.is_registered = True
    db.session.commit()
    return jsonify({"message":"Patient approved", "patient_id": patient.id}), 200
