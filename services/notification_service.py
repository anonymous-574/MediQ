# Minimal notification service - placeholder that prints to console.
def send_booking_confirmation(patient, appointment):
    # patient: Patient object or dict, appointment: dict
    print(f"[NOTIFICATION] Booking confirmation to {patient.email if hasattr(patient,'email') else patient.get('email')}: {appointment}")
    return True

def send_reminder(patient, appointment):
    print(f"[NOTIFICATION] Reminder to {patient.email if hasattr(patient,'email') else patient.get('email')}: {appointment}")
    return True

def send_emergency_alert(patient):
    print(f"[NOTIFICATION] Emergency alert for {patient.name}")
    return True
