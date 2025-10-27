from database import db

from models import Appointment, Doctor, Patient, TimeSlot, Hospital
import time

def find_available_slots(doctor_id=None, hospital_id=None, date=None):
    q = TimeSlot.query.filter_by(is_available=True)
    if doctor_id:
        q = q.filter_by(doctor_id=doctor_id)
    if hospital_id:
        q = q.filter_by(hospital_id=hospital_id)
    slots = q.all()
    out = []
    for s in slots:
        out.append({
            "slot_id": s.slot_id,
            "doctor_id": s.doctor_id,
            "hospital_id": s.hospital_id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "is_available": s.is_available
        })
    return out

def validate_booking_rules(patient: Patient, doctor_id, date_time):
    # Business rules simplified:
    # - A patient cannot have another active appointment for same doctor
    s = Appointment.query.filter_by(patient_id=patient.id, doctor_id=doctor_id).filter(Appointment.status=='Scheduled').first()
    if s:
        return False, "Patient already has an active appointment with this doctor"
    return True, None

def book_appointment(patient_id, doctor_id, hospital_id, date_time):
    # Validate doctor and patient exist
    patient = Patient.query.get(patient_id)
    if not patient:
        return {"error": "Patient not found"}

    # Attempt to find doctor by either numeric id or string doctor_id
    try:
        doctor_id_int = int(doctor_id)
    except (TypeError, ValueError):
        doctor_id_int = None

    doctor = Doctor.query.filter(
        (Doctor.id == doctor_id_int) | (Doctor.doctor_id == str(doctor_id))
    ).first()

    if not doctor:
        print(f"DEBUG: No doctor found for doctor_id={doctor_id}")
        return {"error": "Doctor not found"}

    # Validate business rules
    valid, reason = validate_booking_rules(patient, doctor.id, date_time)
    if not valid:
        return {"error": reason}

    # Create appointment
    appt = Appointment(
        appointment_id=f"APPT-{int(time.time())}",
        patient_id=patient_id,
        doctor_id=doctor.id,  # always use the internal numeric ID
        hospital_id=hospital_id,
        date_time=date_time,
        status="Scheduled"
    )

    db.session.add(appt)
    db.session.commit()

    return {
        "message": "Appointment booked",
        "appointment_id": appt.appointment_id,
        "status": appt.status,
        "date_time": appt.date_time
    }

