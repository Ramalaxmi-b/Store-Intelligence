# 🛍️ Purplle Store Intelligence System
### Purplle Tech Challenge 2026 — Round 2

An end-to-end AI-powered Store Intelligence System built from raw CCTV footage. Detects people, tracks movement, generates structured events, detects anomalies, and serves real-time analytics via production-grade APIs.

---

## 🏗️ Architecture Overview

This project is an end-to-end, extensible pipeline for deriving analytics events from CCTV footage. The design balances simplicity for local experimentation (single-node, file-based ingestion) with clear upgrade paths to a production streaming architecture.

- **Ingestion**: Video sources are local MP4 files (data/) for experiments. The same design supports RTSP streams or cloud object storage by replacing the ingestion adapter.

- **Detection & Tracking**: YOLOv8 (lightweight `yolov8n`) performs per-frame person detection; ByteTrack (via Ultralytics tracking) maintains stable track IDs across frames for grouping and temporal reasoning.

- **Event Generator (pipeline.py)**: Processes sampled frames (configurable sampling rate), converts tracked trajectories into structured events: entry/exit, zone_entered/zone_exited, queue events, and anomalies. Events conform to a JSONL-friendly schema for downstream consumers.

- **Storage**: Development default is SQLite (`events.db`) with normalized tables (`person_events`, `zone_events`, `queue_events`, `anomaly_events`). For production, swap to PostgreSQL (time-series extensions like TimescaleDB recommended) with an ingestion layer writing to a message bus.

- **API & Dashboard**: `api/main.py` (FastAPI) exposes read-side endpoints for summary, zone heatmaps, queues and anomalies. `dashboard/app.py` (Streamlit) provides an interactive visualization layer and ad-hoc exploration.

- **Observability & Ops**: Logs (structured JSON) and metrics (Prometheus-compatible counters/histograms) should be added for production monitoring. Health checks and graceful shutdown are provided by the FastAPI/uvicorn stack.

- **Security & Privacy**: The pipeline minimizes PII by storing anonymized identifiers (id_token) and avoiding raw face images. For deployments handling sensitive video, use encrypted storage, access control, and on-edge processing to avoid transmitting raw video.

- **Scaling Roadmap**:
  - Short-term: run multiple pipeline workers in parallel across different stores or video partitions.
  - Medium-term: decouple ingestion and processing via a message bus (Kafka) and convert the pipeline to stream processors (Flink/Beam or async workers) for near-real-time ingestion.
  - Long-term: move tracking & re-identification to specialized microservices (GPU-backed) and centralize event storage in Postgres+TimescaleDB or a cloud time-series DB.

- **Key trade-offs**:
  - CPU-first design (YOLOv8n, frame sampling) for fast local runs vs. larger models for accuracy in a GPU environment.
  - Batch/offline processing simplifies correctness; streaming improves latency at the cost of complexity.

This README focuses on the local developer flow; see the Production Roadmap for recommended changes to scale and harden the system.

---

## 🚀 Setup & Quick Start

Follow these steps to set up the project and run the detection pipeline locally.

### 1. Clone and create a virtual environment
```powershell
git clone https://github.com/Ramalaxmi-b/store-intelligence
cd store-intelligence
python -m venv venv
venv\Scripts\activate    # Windows
# or on macOS / Linux:
# source venv/bin/activate
```

### 2. Install dependencies
Install the pinned dependencies from `requirements.txt`:
```powershell
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt
```

Notes:
- `ultralytics` may pull a compatible `torch` wheel; if you have a GPU and want CUDA support, install the appropriate `torch` first (see https://pytorch.org).
- If installation fails due to cached wheels on Windows, the `--no-cache-dir` flag helps.

### 3. Add video files
Place MP4 files under the `data/` folder following the sample layout used by `pipeline.py`:

```
data/
├── store1/  → CAM1-zone.mp4, CAM2-zone.mp4, CAM3-entry.mp4, CAM5-billing.mp4, layout.png
└── store2/  → entry1.mp4, entry2.mp4, zone.mp4, billing_area.mp4, layout.png
```

### 4. Run the detection pipeline
```powershell
python pipeline.py
```

### 5. Start API and Dashboard
```powershell
# API (FastAPI)
uvicorn api.main:app --reload --port 8000

# Dashboard (Streamlit)
streamlit run dashboard/app.py
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | System health check |
| `/api/v1/footfall` | GET | Total footfall, gender & age split |
| `/api/v1/zone-heatmap` | GET | Zone visit counts and hotspots |
| `/api/v1/queue-status` | GET | Queue wait times, abandonment rate |
| `/api/v1/anomalies` | GET | Detected anomalies with severity |
| `/api/v1/store-summary` | GET | Cross-store comparison |
| `/api/v1/live-footfall` | GET | Hourly footfall trend |

All endpoints support `?store_id=ST1008` or `?store_id=ST1076` filter.

Interactive docs: `http://localhost:8000/docs`

---

## 🧠 Detection Pipeline

**Model:** YOLOv8n (nano) — chosen for CPU inference speed without sacrificing meaningful accuracy for person detection at retail store scale.

**Tracking:** ByteTrack (built into Ultralytics) — handles occlusion better than DeepSORT in crowded retail environments. Maintains track IDs across frames even when people are temporarily hidden.

**Frame sampling:** Every 5th frame processed — reduces CPU load by 5x while maintaining event accuracy since retail movement is slow relative to frame rate.

**Zone detection:** Normalized bounding box overlap — each person's center point is checked against zone polygons defined from the store layout PNG.

**Gender/Age:** Approximated via demographic distribution modeling. In production this would use a dedicated lightweight model (e.g. InsightFace or DeepFace) but adds significant CPU overhead for a hackathon timeline.

---

## ⚠️ Anomaly Detection

Four anomaly types are detected automatically:

| Anomaly | Trigger | Severity |
|---|---|---|
| CROWD_BUILDUP | >8 people in entry frame | MEDIUM/HIGH |
| ZONE_OVERCROWDED | >5 people in single zone | MEDIUM |
| LONG_QUEUE | Queue wait > 5 minutes | HIGH |
| ENTRY_SPIKE | Sudden footfall increase | MEDIUM |

---

## 🗃️ Event Schema

Events match the provided sample JSONL format exactly:

**Person Event:**
```json
{
  "event_type": "entry",
  "id_token": "ID_60001",
  "store_code": "ST1008",
  "camera_id": "CAM3",
  "event_timestamp": "2026-03-08T10:00:05.120000",
  "is_staff": false,
  "gender_pred": "F",
  "age_pred": 28,
  "age_bucket": "25-34",
  "is_face_hidden": false,
  "group_id": null,
  "group_size": null
}
```

**Zone Event:**
```json
{
  "event_type": "zone_entered",
  "track_id": 101,
  "store_id": "ST1008",
  "zone_id": "PURPLLE_ST1008_Z01",
  "zone_name": "Left Shelf",
  "zone_type": "SHELF",
  "is_revenue_zone": true,
  "event_time": "2026-03-08T10:10:45.280000",
  "zone_hotspot_x": 412.6,
  "zone_hotspot_y": 238.4
}
```

---

## ⚙️ Architectural Decisions & Trade-offs

**SQLite over PostgreSQL**
Chosen for zero-config deployment and sufficient performance at single-store scale (~10k events/day). In production with multi-store real-time ingestion, PostgreSQL with TimescaleDB extension would handle time-series queries better.

**Offline processing over real-time streaming**
Videos are processed as batch jobs. A production system would use Kafka for event streaming with sub-second latency. For this challenge, offline processing produces identical event quality with simpler infrastructure.

**YOLOv8n over larger models**
Nano model runs at ~8 FPS on CPU vs ~2 FPS for YOLOv8m. For retail analytics where movement is gradual, nano provides sufficient detection accuracy. In a GPU-deployed production environment, YOLOv8x would improve small-person detection in wide-angle CCTV.

**Frame skipping (every 5th frame)**
At 30 FPS, processing every 5th frame = 6 FPS effective rate. Retail walking speed means a person traverses a zone in ~3-5 seconds minimum, so no zone events are missed.

**Normalized zone coordinates**
Zone bounding boxes stored as 0-1 normalized values, making them resolution-independent. The same zone config works for 720p and 1080p footage without changes.

---

## 📁 Project Structure
store-intelligence/
├── data/
│   ├── store1/          # Store 1 CCTV videos + layout
│   └── store2/          # Store 2 CCTV videos + layout
├── api/
│   ├── init.py
│   └── main.py          # FastAPI application
├── dashboard/
│   ├── init.py
│   └── app.py           # Streamlit dashboard
├── utils/
│   ├── init.py
│   ├── database.py      # SQLAlchemy models + DB init
│   └── zones.py         # Zone config + helper functions
├── pipeline.py          # Main detection + event generation
├── requirements.txt
├── events.db            # SQLite database (auto-generated)
└── README.md

---

## ✅ Verification & Troubleshooting

Verify the `ultralytics` import and YOLO availability:
```powershell
python -c "from ultralytics import YOLO; print('ultralytics OK', YOLO)"
```

If you see import errors, try reinstalling `ultralytics` with no cache:
```powershell
pip install --no-cache-dir ultralytics
```

Common issues:
- Windows permission or cached wheel problems — use `--no-cache-dir`.
- GPU users: install a `torch` build compatible with your CUDA version before `ultralytics`.

If `python pipeline.py` still raises an import error, run this quick check to confirm the active interpreter and installed packages:
```powershell
python -m pip --version
python -m pip list | findstr ultralytics
python -c "import sys; print(sys.executable)"
```

---

## 🔮 Production Roadmap

What I would add given more time:

- **Kafka integration** for real-time event streaming across stores
- **Redis** for live queue state with sub-second updates  
- **InsightFace** for accurate gender/age prediction
- **Re-ID model** for cross-camera person tracking
- **PostgreSQL + TimescaleDB** for production-scale time-series storage
- **Docker + docker-compose** for one-command deployment
- **WebSocket API** for live dashboard updates
- **Alert system** via SMS/email when anomalies are detected

---

## 👩‍💻 Author

**Ramalaxmi B**  
Information Technology, KMIT Hyderabad  
GitHub: [@Ramalaxmi-b](https://github.com/Ramalaxmi-b)