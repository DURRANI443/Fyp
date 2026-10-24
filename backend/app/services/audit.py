from app.models import AuditEvent


def record_event(db, actor_id, event_type, details):
    event = AuditEvent(actor_id=actor_id, event_type=event_type, details=details)
    db.add(event)
    return event
