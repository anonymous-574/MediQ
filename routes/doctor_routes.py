from flask import Blueprint, request, jsonify
from auth import role_required
from models import Appointment, Doctor, Patient
from app import db

doctor_bp = Blueprint('doctor_bp', __name__)

@doctor_bp.route('/appointments', methods=['GET'])
@role_required('doctor')
def get_appointments(user):
    # return appointments for this doctor
    appts = Appointment.query.filter_by(doctor_id=user.id).all()
    output = []
    for a in appts:
        output.append({
            "appointment_id": a.appointment_id,
            "patient_id": a.patient_id,
            "status": a.status,
            "date_time": a.date_time,
            "notes": a.notes
        })
    return jsonify(output), 200

@doctor_bp.route('/update_status', methods=['PUT'])
@role_required('doctor')
def update_status(user):
    data = request.json
    appointment_id = data.get('appointment_id')
    new_status = data.get('status')
    a = Appointment.query.filter_by(appointment_id=appointment_id, doctor_id=user.id).first()
    if not a:
        return jsonify({"error": "Appointment not found"}), 404
    a.status = new_status
    db.session.commit()
    return jsonify({"message": "Status updated", "appointment_id": a.appointment_id, "status": a.status}), 200

@doctor_bp.route('/update_availability', methods=['PUT'])
@role_required('doctor')
def update_availability(user):
    data = request.json
    # Example: accept list of timeslots to create
    timeslots = data.get('timeslots', [])
    created = []
    from models import TimeSlot
    for ts in timeslots:
        slot = TimeSlot(
            slot_id = ts.get('slot_id') or f"TS-{int(__import__('time').time())}",
            doctor_id = user.id,
            hospital_id = ts.get('hospital_id'),
            start_time = ts.get('start_time'),
            end_time = ts.get('end_time'),
            is_available = ts.get('is_available', True),
            slot_type = ts.get('slot_type', 'consult')
        )
        db.session.add(slot)
        created.append(slot.slot_id)
    db.session.commit()
    return jsonify({"message":"Availability updated","created_slots":created}), 201
