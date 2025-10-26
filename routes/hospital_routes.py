from flask import Blueprint, request, jsonify
from auth import role_required
from models import Hospital, Doctor, TimeSlot, QueueReport
from database import db

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
    hospital_id = request.args.get('hospital_id')
    h = Hospital.query.filter_by(hospital_id=hospital_id).first()
    if not h:
        return jsonify({"error":"Hospital not found"}), 404
    doctors = Doctor.query.filter_by().all()
    out = []
    for d in doctors:
        out.append({"doctor_id": d.id, "name": d.name, "specialty": d.specialty, "is_available": d.is_available})
    return jsonify(out), 200

@hospital_bp.route('/predict_wait_time', methods=['GET'])
def predict_wait():
    hospital_id = request.args.get('hospital_id')
    department = request.args.get('department', 'general')
    # uses real appointment counts / queue reports inside service
    eta = predict_wait_time(hospital_id, department)
    return jsonify({"hospital_id": hospital_id, "department": department, "predicted_wait_minutes": eta}), 200


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
