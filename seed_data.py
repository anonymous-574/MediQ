from app import create_app, db
from models import Hospital, Doctor, Patient, TimeSlot
from passlib.hash import pbkdf2_sha256

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()

    # create hospital
    h = Hospital(hospital_id="HOSP-1", name="City General Hospital", address="123 Main St", capacity=200, contact_info="0123456789", departments="general,cardiology,emergency")
    db.session.add(h)
    db.session.commit()

    # create doctors
    # create doctors
    d1 = Doctor(
        doctor_id="D-100",
        name="Dr. Alice",
        email="alice@hospital.org",
        phone="1111111111",
        specialty="cardiology",
        password_hash=pbkdf2_sha256.hash("password"),
        is_available=True,
        hospital_id=h.id  # ✅ link to hospital
    )

    d2 = Doctor(
        doctor_id="D-101",
        name="Dr. Bob",
        email="bob@hospital.org",
        phone="2222222222",
        specialty="general",
        password_hash=pbkdf2_sha256.hash("password"),
        is_available=True,
        hospital_id=h.id  # ✅ link to hospital
    )

    db.session.commit()

    # create timeslots
    ts1 = TimeSlot(slot_id="TS-1", doctor_id=d1.id, hospital_id=h.id, start_time="2025-10-24 10:00", end_time="2025-10-24 10:30", is_available=True)
    ts2 = TimeSlot(slot_id="TS-2", doctor_id=d2.id, hospital_id=h.id, start_time="2025-10-24 11:00", end_time="2025-10-24 11:30", is_available=True)
    db.session.add_all([ts1, ts2])
    db.session.commit()

    # create a patient
    p = Patient(patient_id="P-500", name="John Doe", email="john@example.com", phone="9999999999", password_hash=pbkdf2_sha256.hash("password"), is_registered=True)
    db.session.add(p)
    db.session.commit()

    print("Seed data created.")
