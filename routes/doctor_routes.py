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

    # ✅ user.id is the doctor's id (from user table, same as doctor.id)
    doctor = Doctor.query.filter_by(id=user.id).first()
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404

    created, skipped = [], []

    for ts in timeslots:
        try:
            date_str = ts.get('date')
            start_time_str = ts.get('start_time')
            end_time_str = ts.get('end_time')

            if not (date_str and start_time_str and end_time_str):
                skipped.append({
                    "slot_id": ts.get("slot_id"),
                    "reason": "Missing required fields (date/start_time/end_time)"
                })
                continue

            start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")

            # ✅ Generate unique slot ID
            slot_id = ts.get('slot_id') or f"TS-{user.id}-{int(time.time())}"

            # ✅ Check for existing slot
            existing = TimeSlot.query.filter_by(
                slot_id=slot_id,
                doctor_id=user.id
            ).first()

            if existing:
                skipped.append({
                    "slot_id": slot_id,
                    "reason": "Already exists"
                })
                continue

            # ✅ Create new slot with doctor_id as INTEGER
            slot = TimeSlot(
                slot_id=slot_id,
                doctor_id=user.id,  # INTEGER foreign key
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

    # ✅ Use user.id directly (it's the doctor's id)
    slot = TimeSlot.query.filter_by(slot_id=slot_id, doctor_id=user.id).first()
    if not slot:
        return jsonify({"error": f"Slot {slot_id} not found or not owned by this doctor"}), 404

    db.session.delete(slot)
    db.session.commit()
    return jsonify({"message": f"Slot {slot_id} deleted successfully"}), 200

# -----------------------------------------------------------
# GET /doctor/availability
# -----------------------------------------------------------
@doctor_bp.route('/availability', methods=['GET'])
@role_required('doctor')
def get_availability(user):
    # ✅ Query slots by user.id (which is the doctor_id in time_slot table)
    slots = TimeSlot.query.filter_by(doctor_id=user.id).all()

    output = []
    for s in slots:
        # ✅ Format to match frontend expectations
        if isinstance(s.start_time, str):
            start_dt = datetime.fromisoformat(s.start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(s.end_time.replace('Z', '+00:00'))
        else:
            start_dt = s.start_time
            end_dt = s.end_time
        
        output.append({
            "slot_id": s.slot_id,
            "date": start_dt.strftime("%Y-%m-%d"),           # ✅ Separate date field
            "start_time": start_dt.strftime("%H:%M"),        # ✅ Time only
            "end_time": end_dt.strftime("%H:%M"),            # ✅ Time only
            "is_available": s.is_available,
            "slot_type": s.slot_type,
            "hospital_id": s.hospital_id
        })

    return jsonify(output), 200

# -----------------------------------------------------------
# GET /doctor/available_slots/<doctor_id>?date=YYYY-MM-DD
# For patients booking appointments
# -----------------------------------------------------------
@doctor_bp.route('/available_slots/<int:doctor_id>', methods=['GET'])
def get_available_slots(doctor_id):
    """
    Get available time slots for a specific doctor on a specific date
    Used by patients when booking appointments
    """
    # Get the date from query parameters
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "Date parameter is required"}), 400
    
    try:
        # Parse the date
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    # Query time slots for this doctor on this date
    # Filter by date range (start of day to end of day)
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    slots = TimeSlot.query.filter(
        TimeSlot.doctor_id == doctor_id,
        TimeSlot.is_available == True,
        TimeSlot.start_time >= start_of_day,
        TimeSlot.start_time <= end_of_day
    ).order_by(TimeSlot.start_time).all()
    
    available_slots = []
    for slot in slots:
        # Format datetime objects to ISO strings for frontend
        if isinstance(slot.start_time, str):
            start_dt = datetime.fromisoformat(slot.start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(slot.end_time.replace('Z', '+00:00'))
        else:
            start_dt = slot.start_time
            end_dt = slot.end_time
        
        available_slots.append({
            "slot_id": slot.slot_id,
            "start_time": start_dt.isoformat(),  # ISO format for formatTime() function
            "end_time": end_dt.isoformat(),      # ISO format for formatTime() function
            "date": start_dt.strftime("%Y-%m-%d"),
            "is_available": slot.is_available,
            "slot_type": slot.slot_type
        })
    
    return jsonify({
        "available_slots": available_slots,
        "date": date_str,
        "doctor_id": doctor_id,
        "total_slots": len(available_slots)
    }), 200

# -----------------------------------------------------------
# GET /doctor/patients
# -----------------------------------------------------------
@doctor_bp.route('/patients', methods=['GET'])
@role_required('doctor')
def get_doctor_patients(user):
    """
    Get all unique patients who have appointments with this doctor
    """
    from sqlalchemy import distinct
    
    # Get distinct patient IDs from appointments
    patient_ids = db.session.query(distinct(Appointment.patient_id)).filter(
        Appointment.doctor_id == user.id
    ).all()
    
    patients = []
    for (patient_id,) in patient_ids:
        patient = Patient.query.filter_by(id=patient_id).first()
        if patient:
            user_info = patient.user  # Get related user info
            
            # Count appointments
            total_appointments = Appointment.query.filter_by(
                patient_id=patient_id,
                doctor_id=user.id
            ).count()
            
            # Get last visit
            last_appointment = Appointment.query.filter_by(
                patient_id=patient_id,
                doctor_id=user.id
            ).order_by(Appointment.created_at.desc()).first()
            
            patients.append({
                "patient_id": patient.patient_id,
                "patient_name": user_info.name,
                "name": user_info.name,
                "email": user_info.email,
                "phone": user_info.phone,
                "status": "Active" if patient.account_status == "active" else "Inactive",
                "total_appointments": total_appointments,
                "last_visit": last_appointment.date_time if last_appointment else None
            })
    
    return jsonify(patients), 200
