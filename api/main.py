from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from utils.database import get_db, PersonEvent, ZoneEvent, QueueEvent, AnomalyEvent
from datetime import datetime
import json

app = FastAPI(
    title="Purplle Store Intelligence API",
    description="Real-time store analytics from CCTV footage",
    version="1.0.0"
)

# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# ── Footfall ─────────────────────────────────────────────────────────────────
@app.get("/api/v1/footfall")
def get_footfall(
    store_id: str = Query(None, description="Filter by store e.g. ST1008"),
    db: Session = Depends(get_db)
):
    query = db.query(PersonEvent).filter(PersonEvent.event_type == "entry")
    if store_id:
        query = query.filter(PersonEvent.store_code == store_id)

    entries = query.all()
    total = len(entries)

    gender_split = {"M": 0, "F": 0}
    age_split = {}
    for e in entries:
        gender_split[e.gender_pred] = gender_split.get(e.gender_pred, 0) + 1
        age_split[e.age_bucket] = age_split.get(e.age_bucket, 0) + 1

    return {
        "store_id": store_id or "all",
        "total_footfall": total,
        "gender_split": gender_split,
        "age_distribution": age_split,
        "timestamp": datetime.now().isoformat()
    }

# ── Zone Heatmap ──────────────────────────────────────────────────────────────
@app.get("/api/v1/zone-heatmap")
def get_zone_heatmap(
    store_id: str = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(
        ZoneEvent.zone_name,
        ZoneEvent.zone_type,
        ZoneEvent.zone_id,
        func.count(ZoneEvent.id).label("visits"),
        func.avg(ZoneEvent.zone_hotspot_x).label("avg_x"),
        func.avg(ZoneEvent.zone_hotspot_y).label("avg_y")
    ).filter(ZoneEvent.event_type == "zone_entered")

    if store_id:
        query = query.filter(ZoneEvent.store_id == store_id)

    results = query.group_by(ZoneEvent.zone_id).all()

    zones = []
    for r in results:
        zones.append({
            "zone_id": r.zone_id,
            "zone_name": r.zone_name,
            "zone_type": r.zone_type,
            "total_visits": r.visits,
            "avg_hotspot_x": round(r.avg_x or 0, 2),
            "avg_hotspot_y": round(r.avg_y or 0, 2)
        })

    zones.sort(key=lambda x: x["total_visits"], reverse=True)

    return {
        "store_id": store_id or "all",
        "zones": zones,
        "most_visited": zones[0]["zone_name"] if zones else None,
        "timestamp": datetime.now().isoformat()
    }

# ── Queue Status ──────────────────────────────────────────────────────────────
@app.get("/api/v1/queue-status")
def get_queue_status(
    store_id: str = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(QueueEvent)
    if store_id:
        query = query.filter(QueueEvent.store_id == store_id)

    events = query.all()
    total = len(events)
    abandoned = sum(1 for e in events if e.abandoned)
    completed = total - abandoned
    avg_wait = sum(e.wait_seconds for e in events) / total if total > 0 else 0

    long_waits = sum(1 for e in events if e.wait_seconds > 300)

    return {
        "store_id": store_id or "all",
        "total_queue_events": total,
        "completed": completed,
        "abandoned": abandoned,
        "abandonment_rate": round(abandoned / total * 100, 2) if total > 0 else 0,
        "avg_wait_seconds": round(avg_wait, 2),
        "long_wait_count": long_waits,
        "queue_health": "CRITICAL" if avg_wait > 300 else "WARNING" if avg_wait > 180 else "GOOD",
        "timestamp": datetime.now().isoformat()
    }

# ── Anomalies ─────────────────────────────────────────────────────────────────
@app.get("/api/v1/anomalies")
def get_anomalies(
    store_id: str = Query(None),
    severity: str = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(AnomalyEvent)
    if store_id:
        query = query.filter(AnomalyEvent.store_id == store_id)
    if severity:
        query = query.filter(AnomalyEvent.severity == severity.upper())

    anomalies = query.order_by(desc(AnomalyEvent.id)).limit(50).all()

    return {
        "store_id": store_id or "all",
        "total_anomalies": len(anomalies),
        "anomalies": [
            {
                "type": a.anomaly_type,
                "severity": a.severity,
                "description": a.description,
                "detected_at": a.detected_at,
                "camera_id": a.camera_id
            } for a in anomalies
        ],
        "timestamp": datetime.now().isoformat()
    }

# ── Store Summary ─────────────────────────────────────────────────────────────
@app.get("/api/v1/store-summary")
def get_store_summary(
    store_id: str = Query(None),
    db: Session = Depends(get_db)
):
    stores = ["ST1008", "ST1076"] if not store_id else [store_id]
    summary = []

    for s in stores:
        footfall = db.query(PersonEvent).filter(
            PersonEvent.store_code == s,
            PersonEvent.event_type == "entry"
        ).count()

        zone_visits = db.query(ZoneEvent).filter(
            ZoneEvent.store_id == s,
            ZoneEvent.event_type == "zone_entered"
        ).count()

        queue_events = db.query(QueueEvent).filter(QueueEvent.store_id == s).all()
        avg_wait = sum(e.wait_seconds for e in queue_events) / len(queue_events) if queue_events else 0
        abandoned = sum(1 for e in queue_events if e.abandoned)

        anomaly_count = db.query(AnomalyEvent).filter(
            AnomalyEvent.store_id == s
        ).count()

        summary.append({
            "store_id": s,
            "total_footfall": footfall,
            "zone_visits": zone_visits,
            "avg_queue_wait_seconds": round(avg_wait, 2),
            "abandoned_queues": abandoned,
            "anomalies_detected": anomaly_count
        })

    return {
        "summary": summary,
        "generated_at": datetime.now().isoformat()
    }

# ── Live Footfall (last N minutes simulation) ─────────────────────────────────
@app.get("/api/v1/live-footfall")
def get_live_footfall(
    store_id: str = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(PersonEvent).filter(PersonEvent.event_type == "entry")
    if store_id:
        query = query.filter(PersonEvent.store_code == store_id)

    entries = query.all()

    # group by hour from timestamp
    hourly = {}
    for e in entries:
        try:
            hour = e.event_timestamp[:13]  # "2026-03-08T10"
            hourly[hour] = hourly.get(hour, 0) + 1
        except:
            pass

    return {
        "store_id": store_id or "all",
        "hourly_footfall": [
            {"hour": k, "count": v}
            for k, v in sorted(hourly.items())
        ],
        "timestamp": datetime.now().isoformat()
    }