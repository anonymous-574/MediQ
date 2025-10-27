# routes/nurse_routes.py
from flask import Blueprint, request, jsonify
from auth import role_required
from database import db
from models import Appointment, Patient, Doctor,Room,QueueReport
from datetime import datetime


nurse_bp = Blueprint('nurse_bp', __name__)

# ===================== Get Rooms =====================

@nurse_bp.route('/queue', methods=['GET'])
@role_required('nurse')
def get_queue(user):
    hospital_id = request.args.get('hospital_id', 1)
    reports = (
        QueueReport.query
        .filter_by(hospital_id=hospital_id)
        .order_by(QueueReport.timestamp.desc())
        .all()
    )

    queue_data = []
    for r in reports:
        queue_data.append({
            "report_id": r.report_id,
            "department": r.department,
            "queue_length": r.queue_length,
            "wait_time_reported": r.wait_time_reported,
            "submitted_by": r.submitted_by,
            "is_validated": r.is_validated,
            "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "Unknown",
        })

    return jsonify(queue_data), 200

@nurse_bp.route('/submit_queue_report', methods=['POST'])
@role_required('nurse')
def submit_queue_report(user):
    data = request.json
    required = ['department', 'queue_length', 'wait_time_reported']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    from datetime import datetime
    report = QueueReport(
        report_id=f"rep_{int(datetime.utcnow().timestamp())}",
        hospital_id=data.get('hospital_id', 1),
        submitted_by=user.name,
        queue_length=data['queue_length'],
        wait_time_reported=data['wait_time_reported'],
        department=data['department'],
        is_validated=False
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({"message": "Queue report added successfully"}), 201

# ===================== Update Patient Status =====================
@nurse_bp.route('/update_patient_status', methods=['PUT'])
@role_required('nurse')
def update_patient_status(user):
    data = request.json
    patient_id = data.get('patient_id')
    status = data.get('status')
    if not patient_id or not status:
        return jsonify({"error": "Missing patient_id or status"}), 400

    patient = Patient.query.filter_by(id=patient_id).first()
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    patient.account_status = status
    db.session.commit()
    return jsonify({
        "message": "Patient status updated",
        "patient_id": patient_id,
        "status": status
    }), 200

# ===================== Assign Room =====================
@nurse_bp.route('/assign_room', methods=['PUT'])
@role_required('nurse')
def assign_room(user):
    data = request.json
    patient_id = data.get('patient_id')
    room_id = data.get('room_id')

    room = Room.query.filter_by(room_id=room_id).first()
    if not room:
        return jsonify({"error": "Room not found"}), 404

    room.status = "occupied"
    room.patient_id = patient_id
    patient = Patient.query.get(patient_id)
    room.patient_name = patient.name if patient else "Unknown"
    db.session.commit()

    return jsonify({
        "message": "Room assigned successfully",
        "patient_id": patient_id,
        "room_id": room_id
    }), 200


@nurse_bp.route("/rooms", methods=["GET"])
def get_rooms():
    """
    Returns all hospital rooms with their current status.
    """
    try:
        rooms = Room.query.all()
        data = [r.to_dict() for r in rooms]
        return jsonify(data), 200

    except Exception as e:
        print("Error fetching rooms:", e)
        return jsonify({"error": str(e)}), 500


# ===================== Release Room =====================
@nurse_bp.route('/release_room', methods=['PUT'])
@role_required('nurse')
def release_room(user):
    data = request.json
    room_id = data.get('room_id')

    room = Room.query.filter_by(room_id=room_id).first()
    if not room:
        return jsonify({"error": "Room not found"}), 404

    room.status = "cleaning"
    room.patient_id = None
    room.patient_name = None
    db.session.commit()
    return jsonify({"message": f"Room {room_id} released and marked for cleaning"}), 200

# ===================== Clean Room =====================
@nurse_bp.route('/clean_room', methods=['PUT'])
@role_required('nurse')
def clean_room(user):
    data = request.json
    room_id = data.get('room_id')

    room = Room.query.filter_by(room_id=room_id).first()
    if not room:
        return jsonify({"error": "Room not found"}), 404

    room.status = "available"
    db.session.commit()
    return jsonify({"message": f"Room {room_id} cleaned and available"}), 200

@nurse_bp.route("/profile", methods=["GET"])
@role_required("nurse")
def get_nurse_profile(user):
    from models import Nurse

    nurse = Nurse.query.filter_by(email=user.email).first()
    if not nurse:
        return jsonify({"error": "Nurse not found"}), 404

    data = {
        "name": nurse.name,
        "email": nurse.email,
        "phone": nurse.phone,
        "nurse_id": nurse.nurse_id,
        "department": nurse.department,
        "shift_timings": nurse.shift_timings,
    }
    return jsonify(data), 200
