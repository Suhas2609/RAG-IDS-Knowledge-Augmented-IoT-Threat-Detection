# RAG-IDS Production Deployment
## Phase 4: Complete 3-File Architecture

This directory contains the **production-ready** deployment of the RAG-IDS system, consolidating all Phase 3 research logic into three clean, deployable files.

---

## 📁 File Structure

```
Phase_4/
├── api/
│   ├── ragids_engine.py      # Core detection logic (Phases 3.1-3.6)
│   ├── threat_api.py          # FastAPI REST server
│   └── requirements.txt       # Python dependencies
├── dashboard/
│   └── threat_dashboard.py    # Streamlit visualization UI
└── README.md                  # This file
```

---

## 🏗️ Architecture Overview

### **1. ragids_engine.py (The Brain)**

**Role:** Pure detection logic with zero UI code.

**Components:**
- **Phase 3.2**: ChromaDB vector similarity retrieval
- **Phase 3.1**: Adaptive windowing (expands/shrinks based on threat level)
- **Phase 3.3**: Evidence accumulation (recurrence scoring)
- **Phase 3.4**: Quantum fusion (Born rule probability calculation)
- **Phase 3.5**: Decision engine (adaptive threshold + whitelist for 'normal' traffic)
- **Phase 3.6**: Explainability (human-readable narratives)

**Entry Point:** `RealTimeDetector` class orchestrates all phases.

```python
from ragids_engine import RealTimeDetector, FlowRecord

detector = RealTimeDetector(db_path="path/to/chromadb")
result = detector.process_flow(flow_record)

if result and result['decision'].is_attack:
    print(result['explanation'].narrative)
```

---

### **2. threat_api.py (The Gateway)**

**Role:** REST API server connecting engine to the outside world.

**Endpoints:**
- `POST /detect` - Process a single flow (accepts JSON with 99-dim embedding)
- `GET /alerts/latest` - Get recent attack alerts
- `GET /alerts/{id}` - Get full details for specific alert
- `GET /health` - Check API + engine status
- `GET /stats` - Engine metrics and alert statistics

**Storage:** In-memory alert history (can be replaced with database).

---

### **3. threat_dashboard.py (The War Room)**

**Role:** Real-time visualization dashboard.

**Features:**
- Auto-refresh every 2 seconds
- Severity distribution (pie chart)
- Attack type distribution (bar chart)
- Live alert feed with drill-down
- System health monitoring
- Engine statistics

---

## 🚀 Quick Start Guide

### **Prerequisites**

```bash
# Install dependencies
pip install fastapi uvicorn streamlit requests numpy chromadb plotly pandas
```

### **Step 1: Start the API Server**

Open **Terminal 1**:

```bash
cd notebooks/Phase_4/api
uvicorn threat_api:app --reload --port 8000
```

**Verify:** Open http://localhost:8000/docs to see Swagger UI.

### **Step 2: Start the Dashboard**

Open **Terminal 2**:

```bash
cd notebooks/Phase_4/dashboard
streamlit run threat_dashboard.py --server.port 8501
```

**Verify:** Browser opens at http://localhost:8501 automatically.

### **Step 3: Send Test Flows**

The API is now listening. You can:

**Option A:** Use the Phase 3.7 notebook simulation (it already has the webhook integrated).

**Option B:** Send manual requests via `curl` or Python:

```python
import requests
import numpy as np

# Create a test flow
flow = {
    "flow_id": "test_001",
    "timestamp": 1234567890.0,
    "vector_embedding": np.random.rand(99).tolist(),
    "src_ip": "192.168.1.100",
    "dst_ip": "10.0.0.1",
    "src_port": 443,
    "dst_port": 80,
    "protocol": "TCP"
}

# Send to API
response = requests.post("http://localhost:8000/detect", json=flow)
print(response.json())
```

---

## 🔗 Integration with Phase 3.7 Simulation

The Phase 3.7 notebook (60-minute virtual simulation) already includes the `push_alert_to_api()` webhook. When you run that simulation:

1. **Simulation runs** → Generates 7,200 flows with attack bursts at minutes 10-15 and 40-45
2. **Attacks detected** → Automatically sent to `POST /detect`
3. **API stores alerts** → Available via `GET /alerts/latest`
4. **Dashboard updates** → Shows attacks in real-time (2-second refresh)

**Result:** You see the simulation's attack detections appear on the dashboard as they happen!

---

## 📊 Data Flow Diagram

```
┌─────────────────┐
│  Network Flow   │
│  (99-dim vector)│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  threat_api.py (FastAPI Server)                     │
│  - Receives JSON flow                               │
│  - Converts to FlowRecord                           │
│  - Calls detector.process_flow()                    │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  ragids_engine.py (Detection Engine)                │
│  ┌─────────────────────────────────────────────┐   │
│  │ Phase 3.2: Retrieval (ChromaDB similarity) │   │
│  │ Phase 3.1: Adaptive Window                 │   │
│  │ Phase 3.3: Evidence Accumulation           │   │
│  │ Phase 3.4: Quantum Fusion                  │   │
│  │ Phase 3.5: Decision (Adaptive Threshold)   │   │
│  │ Phase 3.6: Explainability                  │   │
│  └─────────────────────────────────────────────┘   │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  API Response: ThreatDecision + Explanation         │
│  - If attack → Store in alert_history               │
│  - Return JSON to caller                            │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  threat_dashboard.py (Streamlit UI)                 │
│  - Polls GET /alerts/latest every 2s                │
│  - Displays pie charts, bar charts, alert feed      │
│  - Shows system health and statistics               │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Configuration

### **ChromaDB Path**

**IMPORTANT:** Update the database path in `threat_api.py` (line ~86):

```python
db_path = r"c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\artifacts\chromadb"
```

Change this to your actual ChromaDB location.

### **API URL**

If running on a different host/port, update `threat_dashboard.py` (line ~26):

```python
API_BASE_URL = "http://localhost:8000"
```

---

## 📈 Production Deployment Tips

### **1. Database Storage**

Replace in-memory `alert_history` list with a database:

```python
# In threat_api.py, replace:
alert_history: List[Dict] = []

# With (e.g., SQLite):
import sqlite3
conn = sqlite3.connect('alerts.db')
```

### **2. Message Queue**

For high-throughput scenarios, add Kafka/RabbitMQ:

```python
# Producer (in API)
producer.send('threat-alerts', alert_record)

# Consumer (in Dashboard)
for message in consumer:
    process_alert(message.value)
```

### **3. Authentication**

Add API key authentication:

```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@app.post("/detect")
async def detect_threat(flow: FlowInput, api_key: str = Depends(api_key_header)):
    if api_key != "your-secret-key":
        raise HTTPException(status_code=403)
    ...
```

### **4. Horizontal Scaling**

Deploy multiple API instances behind a load balancer:

```bash
# Instance 1
uvicorn threat_api:app --port 8001

# Instance 2
uvicorn threat_api:app --port 8002

# Nginx load balancer routes between them
```

---

## 🧪 Testing

### **1. Health Check**

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "ONLINE",
  "engine_status": "ACTIVE",
  "vector_count": 457622,
  "uptime_seconds": 123.45
}
```

### **2. Send Test Flow**

```bash
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{
    "flow_id": "test_001",
    "timestamp": 1234567890.0,
    "vector_embedding": [0.1, 0.2, ..., 0.99],  # 99 values
    "src_ip": "192.168.1.100",
    "dst_ip": "10.0.0.1"
  }'
```

### **3. Get Alerts**

```bash
curl http://localhost:8000/alerts/latest?limit=10
```

---

## 📚 API Documentation

Once the server is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🎓 Academic Defense Talking Points

**Key Strengths of This Architecture:**

1. **Modularity:** Each file has a single responsibility (detection, API, UI).
2. **Testability:** Engine can be unit-tested without starting a web server.
3. **Scalability:** API can be replicated; engine can run on separate workers.
4. **Maintainability:** Changing detection logic doesn't affect the dashboard.
5. **Production-Ready:** Uses industry-standard tools (FastAPI, Streamlit, ChromaDB).

**Research Contributions Demonstrated:**

- **Novel Algorithm:** Quantum-inspired fusion (Phase 3.4) for threat scoring
- **Adaptive Windowing:** Dynamic window sizing based on content (Phase 3.1)
- **Explainability:** Phase 3.6 provides human-readable decisions (defense against "black box" criticism)
- **Real-Time Performance:** Sub-100ms detection latency target
- **Validated on Real Data:** 457,622 attack patterns from ToN-IoT dataset

---

## 🆘 Troubleshooting

**Problem:** `Detection engine failed to initialize`

**Solution:** Check ChromaDB path in `threat_api.py`. Ensure Phase 2.4 created the database.

**Problem:** Dashboard shows "API: OFFLINE"

**Solution:** Ensure API server is running (`uvicorn` command in Terminal 1).

**Problem:** No alerts appearing

**Solution:** 
- Check `GET /health` shows `vector_count > 0`
- Verify flows are being sent to `POST /detect`
- Run Phase 3.7 simulation to generate test traffic

---

## 📝 License

Part of the RAG-IDS Capstone Project. See main repository LICENSE.

---

## 👤 Author

Suhas (Capstone 2026)

**Contact:** Refer to repository issues for questions.
