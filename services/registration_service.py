from database import db

from models import Patient
def register_patient(data):
    # basic validation
    required = ['name', 'email']
    if not all(k in data for k in required):
        return False, "Missing required fields"
    existing = Patient.query.filter_by(email=data.get('email')).first()
    if existing:
        return False, "Email already registered"
    p = Patient(
        patient_id = data.get('patient_id') or f"P-{int(__import__('time').time())}",
        name = data.get('name'),
        email = data.get('email'),
        phone = data.get('phone'),
        date_of_birth = data.get('dob'),
        medical_history = data.get('medical_history'),
        insurance_details = data.get('insurance_details'),
        is_registered = True
    )
    db.session.add(p)
    db.session.commit()
    return True, p.patient_id
