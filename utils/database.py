from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./events.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PersonEvent(Base):
    __tablename__ = "person_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)        # entry, exit, zone_entered, zone_exited
    id_token = Column(String)          # unique person ID like ID_60001
    store_code = Column(String)        # ST1008, ST1076
    camera_id = Column(String)         # CAM1, CAM2 etc
    event_timestamp = Column(String)
    is_staff = Column(Boolean, default=False)
    gender_pred = Column(String)       # M or F
    age_pred = Column(Integer)
    age_bucket = Column(String)        # 18-24, 25-34 etc
    is_face_hidden = Column(Boolean, default=False)
    group_id = Column(String, nullable=True)
    group_size = Column(Integer, nullable=True)

class ZoneEvent(Base):
    __tablename__ = "zone_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)        # zone_entered, zone_exited
    track_id = Column(Integer)
    store_id = Column(String)
    camera_id = Column(String)
    zone_id = Column(String)
    zone_name = Column(String)
    zone_type = Column(String)         # SHELF, DISPLAY, BILLING
    is_revenue_zone = Column(Boolean)
    event_time = Column(String)
    zone_hotspot_x = Column(Float)
    zone_hotspot_y = Column(Float)
    gender = Column(String)
    age = Column(Integer)
    age_bucket = Column(String)

class QueueEvent(Base):
    __tablename__ = "queue_events"
    
    id = Column(Integer, primary_key=True, index=True)
    queue_event_id = Column(String)
    event_type = Column(String)        # queue_completed, queue_abandoned
    track_id = Column(Integer)
    store_id = Column(String)
    camera_id = Column(String)
    zone_id = Column(String)
    zone_name = Column(String)
    queue_join_ts = Column(String)
    queue_served_ts = Column(String, nullable=True)
    queue_exit_ts = Column(String)
    wait_seconds = Column(Integer)
    queue_position_at_join = Column(Integer)
    abandoned = Column(Boolean)
    zone_hotspot_x = Column(Float)
    zone_hotspot_y = Column(Float)
    gender = Column(String)
    age = Column(Integer)
    age_bucket = Column(String)

class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"
    
    id = Column(Integer, primary_key=True, index=True)
    anomaly_type = Column(String)      # CROWD_BUILDUP, LONG_QUEUE, ENTRY_SPIKE, ZONE_OVERCROWDED
    store_id = Column(String)
    camera_id = Column(String)
    detected_at = Column(String)
    severity = Column(String)          # LOW, MEDIUM, HIGH
    description = Column(Text)
    value_observed = Column(Float)
    threshold = Column(Float)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()