"""
RAG-IDS Threat Intelligence API - FastAPI Server
================================================
Gateway between Detection Engine and Dashboard.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import numpy as np

# Import the detection engine
from ragids_engine import (
    RealTimeDetector,
    FlowRecord,
    ThreatDecision,
    ThreatExplanation
)

app = FastAPI(title="RAG-IDS Threat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class FlowInput(BaseModel):
    flow_id: str
    timestamp: float
    vector_embedding: List[float]
    src_ip: str = "0.0.0.0"
    dst_ip: str = "0.0.0.0"
    src_port: int = 0
    dst_port: int = 0
    protocol: str = "TCP"

class DetectionResponse(BaseModel):
    flow_id: str
    is_attack: bool
    severity: str
    attack_type: Optional[str]
    probability: float
    confidence: float
    recommendation: str
    explanation: str
    timestamp: str

class AlertSummary(BaseModel):
    alert_id: str
    timestamp: str
    severity: str
    attack_type: str
    src_ip: str
    dst_ip: str
    confidence: float

# New Model for Simulation Stats
class SimStats(BaseModel):
    window_size: float
    buffer_size: int
    vector_count: int

# --- STATE ---
detector: Optional[RealTimeDetector] = None
alert_history: List[Dict[str, Any]] = []
startup_time: float = 0.0
latest_sim_stats: Optional[Dict] = None  # <--- NEW: Stores stats from simulation

@app.on_event("startup")
async def startup_event():
    global detector, startup_time
    print(">> Starting RAG-IDS Engine...")
    # UPDATE PATH IF NEEDED
    db_path = r"c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\artifacts\chromadb"
    try:
        detector = RealTimeDetector(db_path=db_path)
        startup_time = datetime.now().timestamp()
        print(">> Engine Online")
    except Exception as e:
        print(f">> Engine Init Failed: {e}")

# --- ENDPOINTS ---

@app.post("/detect", response_model=DetectionResponse)
async def detect_threat(flow: FlowInput):
    if not detector: return None
    
    flow_record = FlowRecord(
        flow_id=flow.flow_id, timestamp=flow.timestamp,
        vector_embedding=np.array(flow.vector_embedding),
        src_ip=flow.src_ip, dst_ip=flow.dst_ip,
        src_port=flow.src_port, dst_port=flow.dst_port, protocol=flow.protocol
    )
    
    result = await asyncio.to_thread(detector.process_flow, flow_record)
    
    if result is None:
        return DetectionResponse(
            flow_id=flow.flow_id, is_attack=False, severity="BENIGN",
            attack_type=None, probability=0.0, confidence=0.0,
            recommendation="Buffering", explanation="Window filling",
            timestamp=datetime.now().isoformat()
        )
    
    decision = result['decision']
    explanation = result['explanation']
    
    if decision.is_attack:
        alert_record = {
            'alert_id': f"alert_{flow.flow_id}",
            'timestamp': datetime.now().isoformat(),
            'flow_id': flow.flow_id,
            'severity': decision.severity.value,
            'attack_type': decision.attack_type,
            'src_ip': flow.src_ip,
            'dst_ip': flow.dst_ip,
            'confidence': decision.confidence,
            'probability': decision.probability,
            'recommendation': decision.recommendation,
            'narrative': explanation.narrative,
            'decision_factors': explanation.decision_factors,
            'top_matches': explanation.top_matches
        }
        alert_history.append(alert_record)
        if len(alert_history) > 100: alert_history.pop(0)

    return DetectionResponse(
        flow_id=flow.flow_id, is_attack=decision.is_attack,
        severity=decision.severity.value, attack_type=decision.attack_type,
        probability=decision.probability, confidence=decision.confidence,
        recommendation=decision.recommendation, explanation=explanation.narrative,
        timestamp=datetime.now().isoformat()
    )

# --- CRITICAL: Stats Ingest for Simulation ---
@app.post("/stats/ingest")
async def ingest_stats(stats: SimStats):
    global latest_sim_stats
    latest_sim_stats = stats.dict()
    return {"status": "ok"}

# --- CRITICAL: Alert Ingest for Simulation ---
@app.post("/alerts/ingest")
async def ingest_alert(alert: Dict[str, Any]):
    """Allows external simulation scripts to push alerts manually"""
    decision = alert.get('decision', {})
    
    processed_alert = {
        'alert_id': alert.get('alert_id'),
        'timestamp': alert.get('timestamp'),
        'severity': decision.get('severity', 'UNKNOWN'),
        'attack_type': decision.get('attack_type', 'Unknown'),
        'src_ip': alert.get('src_ip', '192.168.1.X'),
        'dst_ip': alert.get('dst_ip', '10.0.0.5'),
        'confidence': decision.get('confidence', 0.0),
        'probability': decision.get('probability', 0.0),
        'narrative': alert.get('narrative', ''),
        'decision_factors': alert.get('decision_factors', {})
    }
    
    alert_history.append(processed_alert)
    if len(alert_history) > 100: alert_history.pop(0)
    return {"status": "success"}

@app.get("/alerts/latest")
def get_latest_alerts(limit: int = 20):
    return [
        AlertSummary(
            alert_id=a['alert_id'], timestamp=a['timestamp'],
            severity=a['severity'], attack_type=a['attack_type'],
            src_ip=a['src_ip'], dst_ip=a['dst_ip'],
            confidence=a['confidence']
        ) for a in alert_history[-limit:][::-1]
    ]

@app.get("/alerts/{alert_id}")
def get_alert_detail(alert_id: str):
    alert = next((a for a in alert_history if a['alert_id'] == alert_id), None)
    if not alert: raise HTTPException(status_code=404)
    return {
        "narrative": alert.get('narrative', ''),
        "decision": {
            "severity": alert['severity'],
            "attack_type": alert['attack_type'],
            "confidence": alert['confidence'],
            "probability": alert.get('probability', 0.0),
            "is_attack": True
        },
        "decision_factors": alert.get('decision_factors', {})
    }

@app.get("/health")
def health():
    return {"status": "ONLINE", "engine_status": "ACTIVE", "vector_count": detector.retriever.vector_count if detector else 0}

@app.get("/stats")
def stats():
    # 1. Prefer Live Simulation Stats if available
    if latest_sim_stats:
        engine_stats = {
            'vector_count': latest_sim_stats['vector_count'],
            'current_window_size': latest_sim_stats['buffer_size'],
            'adaptive_window_seconds': latest_sim_stats['window_size']
        }
    else:
        # Fallback to local idle detector
        engine_stats = detector.get_stats() if detector else {
            'vector_count': 0, 'current_window_size': 0, 'adaptive_window_seconds': 0.0
        }
    
    # 2. Alert Stats
    total_alerts = len(alert_history)
    severity_counts = {}
    attack_type_counts = {}
    
    for alert in alert_history:
        s = alert.get('severity', 'UNKNOWN')
        severity_counts[s] = severity_counts.get(s, 0) + 1
        t = alert.get('attack_type', 'Unknown')
        attack_type_counts[t] = attack_type_counts.get(t, 0) + 1

    return {
        "engine": engine_stats,
        "alerts": {
            "total": total_alerts,
            "by_severity": severity_counts,
            "by_type": attack_type_counts
        },
        "uptime_seconds": datetime.now().timestamp() - startup_time
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)