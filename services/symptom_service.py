# Mock symptom analyzer: simple keyword based classifier
def analyze_symptoms(text: str):
    if not text:
        return {
            "urgency": "Unknown",
            "classification": "Insufficient data",
            "recommendations": ["Please provide more details"]
        }
    t = text.lower()
    emergency_keywords = ["chest pain", "severe bleeding", "unconscious", "shortness of breath", "severe difficulty breathing"]
    high = any(k in t for k in emergency_keywords)
    fever = "fever" in t
    cough = "cough" in t
    if high:
        urgency = "High"
        classification = "Emergency"
        recs = ["Visit nearest ER immediately", "Call emergency services"]
    elif fever and cough:
        urgency = "Medium"
        classification = "Possible infection"
        recs = ["Book an appointment with a physician", "Isolate and monitor symptoms"]
    else:
        urgency = "Low"
        classification = "Routine"
        recs = ["Self-care", "Schedule regular checkup if persists"]
    return {"urgency": urgency, "classification": classification, "recommendations": recs}
