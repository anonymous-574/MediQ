from database import db
from datetime import datetime
from sqlalchemy.orm import validates

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)  # 'patient', 'doctor', 'nurse', 'admin'
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __mapper_args__ = {
        'polymorphic_on': role,
        'polymorphic_identity': 'user'
    }

class Patient(User):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    patient_id = db.Column(db.String(50), unique=True)
    date_of_birth = db.Column(db.String(20))
    address = db.Column(db.String(255))
    medical_history = db.Column(db.Text)
    insurance_details = db.Column(db.Text)
    is_registered = db.Column(db.Boolean, default=False)
    account_status = db.Column(db.String(50), default='active')

    __mapper_args__ = {'polymorphic_identity': 'patient'}

class Doctor(User):
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    doctor_id = db.Column(db.String(50), unique=True)
    specialty = db.Column(db.String(120))
    qualification = db.Column(db.String(120))
    experience = db.Column(db.Integer, default=0)
    license_number = db.Column(db.String(80))
    is_available = db.Column(db.Boolean, default=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'))

    __mapper_args__ = {'polymorphic_identity': 'doctor'}

class Nurse(User):
    __tablename__ = 'nurse'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    nurse_id = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(120))
    shift_timings = db.Column(db.String(80))

    __mapper_args__ = {'polymorphic_identity': 'nurse'}

class HospitalAdministrator(User):
    __tablename__ = 'hospital_admin'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    admin_id = db.Column(db.String(50), unique=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'))
    role_title = db.Column(db.String(80))
    permissions = db.Column(db.Text)  # comma-separated permissions

    __mapper_args__ = {'polymorphic_identity': 'admin'}

class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(200))
    address = db.Column(db.String(255))
    location = db.Column(db.String(255))  # simple string placeholder
    capacity = db.Column(db.Integer, default=0)
    current_congestion_level = db.Column(db.Float, default=0.0)
    contact_info = db.Column(db.String(255))
    departments = db.Column(db.Text)  # csv of departments

    doctors = db.relationship('Doctor', backref='hospital', lazy=True)
    timeslots = db.relationship('TimeSlot', backref='hospital', lazy=True)
    reports = db.relationship('QueueReport', backref='hospital', lazy=True)

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.String(50), unique=True)
    doctor_id = db.Column(db.Integer)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'))
    start_time = db.Column(db.String(50))
    end_time = db.Column(db.String(50))
    is_available = db.Column(db.Boolean, default=True)
    slot_type = db.Column(db.String(50), default='consult')

    def get_duration_minutes(self):
        # naive duration — in real app, parse times
        return 30

    def mark_as_booked(self):
        self.is_available = False

    def mark_as_available(self):
        self.is_available = True

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.String(50), unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'))
    date_time = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Scheduled')  # Scheduled, Completed, Cancelled
    appointment_type = db.Column(db.String(50), default='OPD')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SymptomReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(50), unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    symptoms = db.Column(db.Text)
    urgency_level = db.Column(db.String(20))
    classification = db.Column(db.String(120))
    recommendations = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def is_emergency(self):
        return self.urgency_level and self.urgency_level.lower() == 'high'

class QueueReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(50), unique=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'))
    submitted_by = db.Column(db.String(120))
    queue_length = db.Column(db.Integer)
    wait_time_reported = db.Column(db.Integer)
    department = db.Column(db.String(120))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_validated = db.Column(db.Boolean, default=False)

    def is_expired(self):
        # expired after 30 minutes
        from datetime import datetime, timedelta
        return datetime.utcnow() - self.timestamp > timedelta(minutes=30)

    def mark_as_validated(self):
        self.is_validated = True
