import cv2
import json
import uuid
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from ultralytics import YOLO
from utils.database import init_db, SessionLocal, PersonEvent, ZoneEvent, QueueEvent, AnomalyEvent
from utils.zones import STORE_ZONES, get_zone_for_point, get_age_bucket

# ── config ──────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.4
PROCESS_EVERY_N_FRAMES = 5      # skip frames to run faster on CPU
BASE_TIMESTAMP = datetime(2026, 3, 8, 10, 0, 0)

# ── helpers ──────────────────────────────────────────────────────────────────
def random_gender():
    return random.choice(["M", "F"])

def random_age():
    # retail store skews 20-45
    return random.randint(18, 55)

def frame_to_timestamp(frame_idx, fps, base_ts):
    seconds = frame_idx / fps
    return (base_ts + timedelta(seconds=seconds)).isoformat()

def is_in_zone(cx_norm, cy_norm, zone):
    x1, y1, x2, y2 = zone["bbox"]
    return x1 <= cx_norm <= x2 and y1 <= cy_norm <= y2

def detect_anomalies(store_id, camera_id, person_count, zone_counts, db):
    anomalies = []
    ts = datetime.now().isoformat()

    # anomaly 1: crowd buildup at entry
    if person_count > 8:
        anomalies.append(AnomalyEvent(
            anomaly_type="CROWD_BUILDUP",
            store_id=store_id,
            camera_id=camera_id,
            detected_at=ts,
            severity="HIGH" if person_count > 12 else "MEDIUM",
            description=f"High footfall detected: {person_count} people in frame",
            value_observed=float(person_count),
            threshold=8.0
        ))

    # anomaly 2: zone overcrowding
    for zone_name, count in zone_counts.items():
        if count > 5:
            anomalies.append(AnomalyEvent(
                anomaly_type="ZONE_OVERCROWDED",
                store_id=store_id,
                camera_id=camera_id,
                detected_at=ts,
                severity="MEDIUM",
                description=f"Zone '{zone_name}' has {count} people",
                value_observed=float(count),
                threshold=5.0
            ))

    for a in anomalies:
        db.add(a)
    db.commit()
    return len(anomalies)

# ── core processor ────────────────────────────────────────────────────────────
def process_video(video_path, store_key, camera_id, model, db):
    store_config = STORE_ZONES[store_key]
    store_code = store_config["store_code"]
    cam_config = store_config["cameras"].get(camera_id, {})
    cam_type = cam_config.get("type", "zone")

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"\nProcessing: {video_path.name} | Store: {store_code} | Camera: {camera_id}")
    print(f"FPS: {fps:.1f} | Total frames: {total_frames}")

    # tracking state
    track_history = {}       # track_id -> {frames seen, gender, age, zones visited}
    zone_state = {}          # track_id -> current zone
    queue_state = {}         # track_id -> queue join time
    frame_idx = 0
    events_generated = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % PROCESS_EVERY_N_FRAMES != 0:
            continue

        h, w = frame.shape[:2]
        ts = frame_to_timestamp(frame_idx, fps, BASE_TIMESTAMP)

        # run YOLO tracking
        results = model.track(
            frame,
            persist=True,
            classes=[0],           # class 0 = person
            conf=CONFIDENCE_THRESHOLD,
            verbose=False
        )

        if results[0].boxes is None or results[0].boxes.id is None:
            continue

        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.cpu().numpy().astype(int)
        current_ids = set()
        zone_counts = {}

        for box, tid in zip(boxes, track_ids):
            x1, y1, x2, y2 = box
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            cx_norm = cx / w
            cy_norm = cy / w

            current_ids.add(tid)

            # first time seeing this track
            if tid not in track_history:
                gender = random_gender()
                age = random_age()
                track_history[tid] = {
                    "gender": gender,
                    "age": age,
                    "age_bucket": get_age_bucket(age),
                    "first_seen": ts,
                    "id_token": f"ID_{60000 + tid}"
                }

                # generate entry event for entry cameras
                if cam_type == "entry":
                    event = PersonEvent(
                        event_type="entry",
                        id_token=track_history[tid]["id_token"],
                        store_code=store_code,
                        camera_id=camera_id,
                        event_timestamp=ts,
                        is_staff=False,
                        gender_pred=gender,
                        age_pred=age,
                        age_bucket=get_age_bucket(age),
                        is_face_hidden=random.random() < 0.1,
                        group_id=None,
                        group_size=None
                    )
                    db.add(event)
                    events_generated += 1

            info = track_history[tid]

            # zone detection
            current_zone = None
            for zone in cam_config.get("zones", []):
                if is_in_zone(cx_norm, cy_norm, zone):
                    current_zone = zone
                    zone_counts[zone["zone_name"]] = zone_counts.get(zone["zone_name"], 0) + 1
                    break

            prev_zone = zone_state.get(tid)

            if current_zone and (prev_zone is None or prev_zone != current_zone["zone_id"]):
                # zone entered
                zone_event = ZoneEvent(
                    event_type="zone_entered",
                    track_id=tid,
                    store_id=store_code,
                    camera_id=camera_id,
                    zone_id=current_zone["zone_id"],
                    zone_name=current_zone["zone_name"],
                    zone_type=current_zone["zone_type"],
                    is_revenue_zone=current_zone["is_revenue_zone"],
                    event_time=ts,
                    zone_hotspot_x=round(cx_norm * 1000, 1),
                    zone_hotspot_y=round(cy_norm * 1000, 1),
                    gender=info["gender"],
                    age=info["age"],
                    age_bucket=info["age_bucket"]
                )
                db.add(zone_event)
                events_generated += 1

                if prev_zone:
                    # zone exited
                    exit_event = ZoneEvent(
                        event_type="zone_exited",
                        track_id=tid,
                        store_id=store_code,
                        camera_id=camera_id,
                        zone_id=prev_zone,
                        zone_name=prev_zone,
                        zone_type=current_zone["zone_type"],
                        is_revenue_zone=current_zone["is_revenue_zone"],
                        event_time=ts,
                        zone_hotspot_x=round(cx_norm * 1000, 1),
                        zone_hotspot_y=round(cy_norm * 1000, 1),
                        gender=info["gender"],
                        age=info["age"],
                        age_bucket=info["age_bucket"]
                    )
                    db.add(exit_event)
                    events_generated += 1

                zone_state[tid] = current_zone["zone_id"]

            # billing queue logic
            if cam_type == "billing":
                if tid not in queue_state:
                    queue_state[tid] = {
                        "join_ts": ts,
                        "position": len(queue_state) + 1
                    }

        # generate exit events for tracks that disappeared
        disappeared = set(track_history.keys()) - current_ids
        for tid in list(disappeared):
            if tid in zone_state:
                info = track_history[tid]
                exit_event = PersonEvent(
                    event_type="exit",
                    id_token=info["id_token"],
                    store_code=store_code,
                    camera_id=camera_id,
                    event_timestamp=ts,
                    is_staff=False,
                    gender_pred=info["gender"],
                    age_pred=info["age"],
                    age_bucket=info["age_bucket"],
                    is_face_hidden=False,
                    group_id=None,
                    group_size=None
                )
                db.add(exit_event)
                events_generated += 1
                del zone_state[tid]

        # commit every 100 frames
        if frame_idx % 100 == 0:
            db.commit()
            print(f"  Frame {frame_idx}/{total_frames} | Events so far: {events_generated}")

        # anomaly check every 50 frames
        if frame_idx % 50 == 0:
            detect_anomalies(store_code, camera_id, len(current_ids), zone_counts, db)

    # generate queue completion events
    for tid, q_info in queue_state.items():
        if tid in track_history:
            info = track_history[tid]
            wait = random.randint(30, 300)
            abandoned = random.random() < 0.15
            queue_event = QueueEvent(
                queue_event_id=str(uuid.uuid4()),
                event_type="queue_abandoned" if abandoned else "queue_completed",
                track_id=tid,
                store_id=store_code,
                camera_id=camera_id,
                zone_id=f"PURPLLE_{store_code}_Z_BILLING_01",
                zone_name="Billing Counter Queue",
                queue_join_ts=q_info["join_ts"],
                queue_served_ts=None if abandoned else ts,
                queue_exit_ts=ts,
                wait_seconds=wait,
                queue_position_at_join=q_info["position"],
                abandoned=abandoned,
                zone_hotspot_x=random.uniform(550, 650),
                zone_hotspot_y=random.uniform(170, 210),
                gender=info["gender"],
                age=info["age"],
                age_bucket=info["age_bucket"]
            )
            db.add(queue_event)

    db.commit()
    cap.release()
    print(f"Done: {video_path.name} | Total events: {events_generated}")
    return events_generated

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("Initializing database...")
    init_db()

    print("Loading YOLO model...")
    model = YOLO("yolov8n.pt")   # downloads automatically on first run

    db = SessionLocal()

    video_map = [
        # (video_path, store_key, camera_id)
        ("data/store1/CAM3-entry.mp4",   "store1", "CAM3"),
        ("data/store1/CAM1-zone.mp4",    "store1", "CAM1"),
        ("data/store1/CAM2-zone.mp4",    "store1", "CAM2"),
        ("data/store1/CAM5-billing.mp4", "store1", "CAM5"),
        ("data/store2/entry1.mp4",       "store2", "CAM1"),
        ("data/store2/entry2.mp4",       "store2", "CAM2"),
        ("data/store2/zone.mp4",         "store2", "CAM3"),
        ("data/store2/billing_area.mp4", "store2", "CAM4"),
    ]

    total_events = 0
    for video_path, store_key, camera_id in video_map:
        path = Path(video_path)
        if not path.exists():
            print(f"Skipping {video_path} — file not found")
            continue
        total_events += process_video(path, store_key, camera_id, model, db)

    db.close()
    print(f"\nAll done! Total events generated: {total_events}")
    print("Check events.db for all data")

if __name__ == "__main__":
    main()