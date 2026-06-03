import json
from datetime import datetime
from utils.database import SessionLocal, PersonEvent, ZoneEvent, QueueEvent, AnomalyEvent

db = SessionLocal()
events = []

def to_bool(val):
    if isinstance(val, bytes):
        return bool(int.from_bytes(val, 'little'))
    return bool(val) if val is not None else None


def _serialize_value(v):
    if isinstance(v, bytes):
        try:
            return v.decode('utf-8')
        except Exception:
            import base64
            return base64.b64encode(v).decode('ascii')
    if isinstance(v, datetime):
        return v.isoformat()
    return v

# Person events
for e in db.query(PersonEvent).all():
    events.append({
        "event_type": e.event_type,
        "id_token": e.id_token,
        "store_code": e.store_code,
        "camera_id": e.camera_id,
        "event_timestamp": e.event_timestamp,
        "is_staff": to_bool(e.is_staff),
        "gender_pred": e.gender_pred,
        "age_pred": e.age_pred,
        "age_bucket": e.age_bucket,
        "is_face_hidden": to_bool(e.is_face_hidden),
        "group_id": e.group_id,
        "group_size": e.group_size
    })

# Zone events
for e in db.query(ZoneEvent).all():
    events.append({
        "event_type": e.event_type,
        "track_id": e.track_id,
        "store_id": e.store_id,
        "camera_id": e.camera_id,
        "zone_id": e.zone_id,
        "zone_name": e.zone_name,
        "zone_type": e.zone_type,
        "is_revenue_zone": to_bool(e.is_revenue_zone),
        "event_time": e.event_time,
        "zone_hotspot_x": e.zone_hotspot_x,
        "zone_hotspot_y": e.zone_hotspot_y,
        "gender": e.gender,
        "age": e.age,
        "age_bucket": e.age_bucket
    })

# Queue events
for e in db.query(QueueEvent).all():
    events.append({
        "queue_event_id": e.queue_event_id,
        "event_type": e.event_type,
        "track_id": e.track_id,
        "store_id": e.store_id,
        "camera_id": e.camera_id,
        "zone_id": e.zone_id,
        "zone_name": e.zone_name,
        "queue_join_ts": e.queue_join_ts,
        "queue_served_ts": e.queue_served_ts,
        "queue_exit_ts": e.queue_exit_ts,
        "wait_seconds": e.wait_seconds,
        "queue_position_at_join": e.queue_position_at_join,
        "abandoned": to_bool(e.abandoned),
        "zone_hotspot_x": e.zone_hotspot_x,
        "zone_hotspot_y": e.zone_hotspot_y,
        "gender": e.gender,
        "age": e.age,
        "age_bucket": e.age_bucket
    })

db.close()

with open("events_output.jsonl", "w", encoding="utf-8") as f:
    for event in events:
        safe = {k: _serialize_value(v) for k, v in event.items()}
        f.write(json.dumps(safe, ensure_ascii=False) + "\n")

print(f"Exported {len(events)} events to events_output.jsonl")