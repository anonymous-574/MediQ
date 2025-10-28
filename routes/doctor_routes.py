from flask import Blueprint, request, jsonify
from auth import role_required
from models import Appointment, Doctor, Patient, TimeSlot
from database import db
import time
from datetime import datetime

doctor_bp = Blueprint('doctor_bp', __name__)

# -----------------------------------------------------------
# GET /doctor/appointments
# -----------------------------------------------------------
@doctor_bp.route('/appointments', methods=['GET'])
@role_required('doctor')
def get_appointments(user):
    appts = Appointment.query.filter_by(doctor_id=user.id).all()
    output = []

    for a in appts:
        # Handle both string and datetime types safely
        if isinstance(a.date_time, str):
            raw_time = a.date_time
        else:
            raw_time = a.date_time.isoformat() if a.date_time else None

        # Clean malformed values like "2025-10-31 2025-10-31T11:00:00"
        if raw_time and " " in raw_time and "T" in raw_time:
            parts = raw_time.split()
            raw_time = parts[-1] if "T" in parts[-1] else parts[0]

        # Normalize to ISO-like format
        clean_time = raw_time.replace(" ", "T") if raw_time else None

        output.append({
            "appointment_id": a.appointment_id,
            "patient_id": a.patient_id,
            "status": a.status,
            "date_time": clean_time,
            "notes": a.notes
        })

    return jsonify(output), 200

# -----------------------------------------------------------
# PUT /doctor/update_status
# -----------------------------------------------------------
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

# -----------------------------------------------------------
# PUT /doctor/update_availability
# -----------------------------------------------------------
@doctor_bp.route('/update_availability', methods=['PUT'])
@role_required('doctor')
def update_availability(user):
    data = request.get_json()
    timeslots = data if isinstance(data, list) else data.get('timeslots', [])

    # ✅ Find the actual doctor record (doctor.id references user.id)
    doctor = Doctor.query.filter_by(id=user.id).first()
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404

    doctor_identifier = doctor.doctor_id  # use this for all time_slot relations

    created, skipped = [], []

    for ts in timeslots:
        try:
            date_str = ts.get('date')
            start_time_str = ts.get('start_time')
            end_time_str = ts.get('end_time')

            # Validate required fields
            if not (date_str and start_time_str and end_time_str):
                skipped.append({
                    "slot_id": ts.get("slot_id"),
                    "reason": "Missing required fields (date/start_time/end_time)"
                })
                continue

            # ✅ Combine date + time strings into proper datetimes
            from datetime import datetime
            import time

            start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")

            # ✅ Determine slot_id (use provided one or generate unique)
            slot_id = ts.get('slot_id') or f"TS-{doctor_identifier}-{int(time.time())}"

            # ✅ Skip existing slots with same slot_id and doctor_id
            existing = TimeSlot.query.filter_by(
                slot_id=slot_id,
                doctor_id=doctor_identifier
            ).first()

            if existing:
                skipped.append({
                    "slot_id": slot_id,
                    "reason": "Already exists"
                })
                continue

            # ✅ Create and store new slot
            slot = TimeSlot(
                slot_id=slot_id,
                doctor_id=doctor_identifier,
                hospital_id=doctor.hospital_id,
                start_time=start_dt,
                end_time=end_dt,
                is_available=True,
                slot_type='consultation'
            )

            db.session.add(slot)
            created.append(slot.slot_id)

        except ValueError as e:
            skipped.append({
                "slot_id": ts.get("slot_id"),
                "reason": f"Invalid datetime format: {str(e)}"
            })

        except Exception as e:
            skipped.append({
                "slot_id": ts.get("slot_id"),
                "reason": f"Unexpected error: {str(e)}"
            })

    db.session.commit()

    return jsonify({
        "message": "Availability updated successfully",
        "created_slots": created,
        "skipped_slots": skipped
    }), 201

# -----------------------------------------------------------
# DELETE /doctor/delete_slot
# -----------------------------------------------------------
@doctor_bp.route('/delete_slot', methods=['DELETE'])
@role_required('doctor')
def delete_slot(user):
    data = request.get_json(silent=True) or {}
    slot_id = data.get("slot_id")

    doctor = Doctor.query.filter_by(id=user.id).first()
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404

    # 🩵 use doctor.doctor_id (not doctor.id)
    slot = TimeSlot.query.filter_by(slot_id=slot_id, doctor_id=doctor.doctor_id).first()
    if not slot:
        print(f"❌ Slot {slot_id} not found for doctor.doctor_id={doctor.doctor_id}")
        return jsonify({"error": f"Slot {slot_id} not found or not owned by this doctor"}), 404

    db.session.delete(slot)
    db.session.commit()
    print(f"🗑️ Deleted slot {slot_id} for doctor.doctor_id={doctor.doctor_id}")
    return jsonify({"message": f"Slot {slot_id} deleted successfully"}), 200

# -----------------------------------------------------------
# GET /doctor/availability
# -----------------------------------------------------------
@doctor_bp.route('/availability', methods=['GET'])
@role_required('doctor')
def get_availability(user):
    slots = TimeSlot.query.filter_by(doctor_id=user.id).all()
    output = []
    for s in slots:
        output.append({
            "slot_id": s.slot_id,
            "day": getattr(s, 'day', None),
            "start_time": s.start_time,
            "end_time": s.end_time,
            "is_available": s.is_available,
            "slot_type": s.slot_type,
            "hospital_id": s.hospital_id
        })
    return jsonify(output), 200
