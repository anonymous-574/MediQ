from models import Appointment, QueueReport
from database import db

from datetime import datetime, timedelta

def update_historical_data(wait_data):
    # placeholder
    return True

def calculate_average_wait_time(hospital_id, department):
    # compute average from queue reports last 24 hours
    now = datetime.utcnow()
    since = now - timedelta(hours=24)
    reports = QueueReport.query.filter(QueueReport.hospital_id == hospital_id, QueueReport.timestamp >= since).all()
    if not reports:
        return None
    total = sum([r.wait_time_reported for r in reports if r.wait_time_reported is not None])
    return total / max(1, len(reports))

def get_wait_time_trends(hospital_id, department):
    # simple trend stub
    return {"trend": "stable"}

def predict_wait_time(hospital_id, department):
    """
    Simple predictor based on:
     - number of scheduled appointments in next 2 hours for that hospital
     - recent queue report average
    """
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    # count appointments scheduled (very naive because date_time is string)
    upcoming = Appointment.query.filter_by(hospital_id=hospital_id, status='Scheduled').count()
    avg_recent = calculate_average_wait_time(hospital_id, department)
    # base estimate
    base = 20  # default
    est = base + upcoming * 5
    if avg_recent:
        est = (est + avg_recent) / 2
    # clamp
    if est < 5:
        est = 5
    return int(est)
