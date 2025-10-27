from flask import Blueprint, request, jsonify
from auth import role_required
from models import Hospital, Doctor, TimeSlot, QueueReport
from database import db
from datetime import datetime
from services.queue_service import predict_wait_time

hospital_bp = Blueprint('hospital_bp', __name__)

@hospital_bp.route('/update_congestion', methods=['PUT'])
@role_required('admin','doctor')
def update_congestion(user):
    data = request.json
    hospital_id = data.get('hospital_id')
    congestion = float(data.get('congestion', 0.0))
    h = Hospital.query.filter_by(hospital_id=hospital_id).first()
    if not h:
        return jsonify({"error":"Hospital not found"}), 404
    h.current_congestion_level = congestion
    db.session.commit()
    return jsonify({"message":"Congestion updated","hospital_id":h.hospital_id,"congestion":h.current_congestion_level}), 200

@hospital_bp.route('/get_doctors', methods=['GET'])
def get_doctors():
    hospital_code = request.args.get('hospital_id')
    hospital = Hospital.query.filter_by(hospital_id=hospital_code).first()
    if not hospital:
        return jsonify({"error": "Hospital not found"}), 404

    # ✅ Support both integer or string linking
    doctors = Doctor.query.filter(
        (Doctor.hospital_id == hospital.id) | (Doctor.hospital_id == hospital_code)
    ).all()

    if not doctors:
        return jsonify({"message": "No doctors found for this hospital"}), 200

    result = [
        {
            "doctor_id": d.doctor_id,
            "name": d.name,
            "specialty": d.specialty,
            "is_available": d.is_available
        } for d in doctors
    ]
    return jsonify(result), 200



@hospital_bp.route('/predict_wait_time', methods=['GET'])
def predict_wait():
    hospital_id = request.args.get('hospital_id')
    department = request.args.get('department', 'general')
    # uses real appointment counts / queue reports inside service
    eta = predict_wait_time(hospital_id, department)
    return jsonify({"hospital_id": hospital_id, "department": department, "predicted_wait_minutes": eta}), 200

@hospital_bp.route('/get_hospitals', methods=['GET'])
def get_all_hospitals():
    hospitals = Hospital.query.all()
    data = []
    for h in hospitals:
        data.append({
            "hospital_id": h.hospital_id,
            "name": h.name,
            "address": h.address,
            "capacity": h.capacity,
            "current_congestion_level": h.current_congestion_level,
            "departments": h.departments.split(',') if h.departments else [],
            "contact_info": h.contact_info
        })
    return jsonify(data), 200

@hospital_bp.route('/get_congestion', methods=['GET'])
def get_congestion():
    hospital_id = request.args.get('hospital_id')
    if not hospital_id:
        return jsonify({"error": "hospital_id is required"}), 400
    h = Hospital.query.filter_by(hospital_id=hospital_id).first()
    if not h:
        return jsonify({"error": "Hospital not found"}), 404
    return jsonify({
        "hospital_id": h.hospital_id,
        "name": h.name,
        "congestion_level": h.current_congestion_level
    }), 200

@hospital_bp.route('/get_departments', methods=['GET'])
def get_departments():
    hospital_id = request.args.get('hospital_id')
    if not hospital_id:
        return jsonify({"error": "hospital_id is required"}), 400
    h = Hospital.query.filter_by(hospital_id=hospital_id).first()
    if not h:
        return jsonify({"error": "Hospital not found"}), 404
    departments = h.departments.split(',') if h.departments else []
    return jsonify({"hospital_id": h.hospital_id, "departments": departments}), 200

@hospital_bp.route('/get_available_slots', methods=['GET'])
def get_available_slots():
    doctor_id = request.args.get('doctor_id')
    date_str = request.args.get('date')

    if not doctor_id or not date_str:
        return jsonify({"error": "doctor_id and date are required"}), 400

    try:
        filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400

    slots = TimeSlot.query.filter_by(doctor_id=int(doctor_id), is_available=True).all()

    available_slots = []
    for s in slots:
        if s.start_time and s.start_time.date() == filter_date:
            available_slots.append({
                "slot_id": s.slot_id,
                "doctor_id": s.doctor_id,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "slot_type": s.slot_type
            })

    return jsonify({"available_slots": available_slots}), 200

@hospital_bp.route('/queue_reports', methods=['GET'])
def get_queue_reports():
    hospital_id = request.args.get('hospital_id')
    if not hospital_id:
        return jsonify({"error": "hospital_id is required"}), 400
    
    reports = QueueReport.query.filter_by(hospital_id=hospital_id).all()
    if not reports:
        return jsonify({"message": "No reports found"}), 200
    
    data = []
    for r in reports:
        data.append({
            "report_id": r.report_id,
            "hospital_id": r.hospital_id,
            "submitted_by": r.submitted_by,
            "queue_length": r.queue_length,
            "wait_time_reported": r.wait_time_reported,
            "department": r.department,
            "timestamp": str(r.timestamp),
            "is_validated": r.is_validated
        })
    return jsonify(data), 200


@hospital_bp.route('/submit_report', methods=['POST'])
def submit_report():
    data = request.json
    qr = QueueReport(
        report_id = f"QR-{int(__import__('time').time())}",
        hospital_id = data.get('hospital_id'),
        submitted_by = data.get('submitted_by'),
        queue_length = data.get('queue_length'),
        wait_time_reported = data.get('wait_time_reported'),
        department = data.get('department')
    )
    db.session.add(qr)
    db.session.commit()
    return jsonify({"message":"Report submitted", "report_id": qr.report_id}),201
