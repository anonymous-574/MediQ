from models import Appointment, QueueReport
from database import db

from datetime import datetime, timedelta

from models import Appointment, QueueReport
from database import db
from datetime import datetime, timedelta
import statistics

def update_historical_data(wait_data):
    try:
        hospital_id = wait_data.get("hospital_id")
        department = wait_data.get("department")
        avg_wait = wait_data.get("average_wait_time", 0)
        avg_queue = wait_data.get("average_queue_length", 0)
        timestamp = datetime.utcnow()

        since = timestamp - timedelta(hours=24)
        recent_reports = QueueReport.query.filter(
            QueueReport.hospital_id == hospital_id,
            QueueReport.department == department,
            QueueReport.timestamp >= since
        ).all()

        if not recent_reports:
            return False

        avg_wait_time = statistics.mean([r.wait_time_reported for r in recent_reports if r.wait_time_reported is not None])
        avg_queue_len = statistics.mean([r.queue_length for r in recent_reports if r.queue_length is not None])

       
        print(f"[Historical Update] Hospital {hospital_id}, Dept {department}: Avg Wait={avg_wait_time:.2f}, Avg Queue={avg_queue_len:.2f}")

        return True
    except Exception as e:
        print(f"Error updating historical data: {e}")
        return False


def get_wait_time_trends(hospital_id, department):
    """
    Determines the short-term trend of waiting times.
    Returns: dict like {"trend": "increasing"/"decreasing"/"stable", "change": percent_change}
    """
    try:
        now = datetime.utcnow()
        since = now - timedelta(hours=6)  # analyze last 6 hours
        reports = QueueReport.query.filter(
            QueueReport.hospital_id == hospital_id,
            QueueReport.department == department,
            QueueReport.timestamp >= since
        ).order_by(QueueReport.timestamp.asc()).all()

        if len(reports) < 4:
            return {"trend": "insufficient data"}

        mid = len(reports) // 2
        first_half = [r.wait_time_reported for r in reports[:mid] if r.wait_time_reported is not None]
        second_half = [r.wait_time_reported for r in reports[mid:] if r.wait_time_reported is not None]

        if not first_half or not second_half:
            return {"trend": "insufficient data"}

        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)

        if avg_first == 0:
            return {"trend": "stable", "change": 0.0}

        percent_change = ((avg_second - avg_first) / avg_first) * 100

        if percent_change > 10:
            trend = "increasing"
        elif percent_change < -10:
            trend = "decreasing"
        else:
            trend = "stable"

        return {"trend": trend, "change": round(percent_change, 2)}

    except Exception as e:
        print(f"Error computing wait time trends: {e}")
        return {"trend": "error"}

def calculate_average_wait_time(hospital_id, department):
   
    now = datetime.utcnow()
    since = now - timedelta(hours=24)
    reports = QueueReport.query.filter(QueueReport.hospital_id == hospital_id, QueueReport.timestamp >= since).all()
    if not reports:
        return None
    total = sum([r.wait_time_reported for r in reports if r.wait_time_reported is not None])
    return total / max(1, len(reports))

def predict_wait_time(hospital_id, department):
   
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    upcoming = Appointment.query.filter_by(hospital_id=hospital_id, status='Scheduled').count()
    avg_recent = calculate_average_wait_time(hospital_id, department)
    
    base = 20  
    est = base + upcoming * 5
    if avg_recent:
        est = (est + avg_recent) / 2
    # clamp
    if est < 5:
        est = 5
    return int(est)
