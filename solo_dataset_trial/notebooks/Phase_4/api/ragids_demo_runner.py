"""
RAG-IDS DEMO RUNNER (Final Fixed Version)
=========================================
Aligned with Engine Phase 3.1 Logic (add_flow signature).
"""
import time
import numpy as np
import requests
import sys
import random
from datetime import datetime
from ragids_engine import RealTimeDetector

API_URL = "http://localhost:8000"
DB_PATH = r"c:\Users\suhas\OneDrive\Desktop\Capstone\RAG-IDS-Knowledge-Augmented-IoT-Threat-Detection\artifacts\chromadb"

# CONFIG
DURATION_MINUTES = 60
FLOWS_PER_SECOND = 2
FLOW_INTERVAL = 1.0 / FLOWS_PER_SECOND 
CYAN, GREEN, RED, RESET, BOLD = "\033[96m", "\033[92m", "\033[91m", "\033[0m", "\033[1m"

def send_telemetry(detector):
    """Pushes live stats (Window Size) to dashboard"""
    payload = {
        "window_size": float(detector.window_mgr.window_size),
        "buffer_size": int(len(detector.window_mgr.buffer)),
        "vector_count": int(detector.retriever.vector_count)
    }
    try:
        # Short timeout to not slow down simulation
        requests.post(f"{API_URL}/stats/ingest", json=payload, timeout=0.1)
    except:
        pass # Silent fail for telemetry to keep viz smooth

def send_to_dashboard(result, flow_id, src_ip, dst_ip):
    decision = result['decision']
    if not decision.is_attack: return

    payload = {
        "alert_id": f"alert_{flow_id}",
        "timestamp": datetime.now().isoformat(),
        "src_ip": src_ip, "dst_ip": dst_ip,
        "decision": {
            "is_attack": True,
            "severity": getattr(decision.severity, 'value', str(decision.severity)),
            "attack_type": str(decision.attack_type),
            "probability": float(decision.probability),
            "confidence": float(decision.confidence)
        },
        "narrative": result['explanation'].narrative,
        "decision_factors": {k: float(v) for k, v in result['explanation'].decision_factors.items()}
    }
    try:
        response = requests.post(f"{API_URL}/alerts/ingest", json=payload, timeout=1)
        if response.status_code == 200:
            print(f"   Dashboard Push: {GREEN}✅ SUCCESS{RESET}")
        else:
            print(f"   Dashboard Push: {RED}❌ FAILED ({response.status_code}){RESET}")
    except Exception as e:
        print(f"   Dashboard Push: {RED}❌ CONNECTION ERROR{RESET}")

def run_simulation():
    print(f"\n{BOLD}INITIALIZING ENGINE...{RESET}")
    detector = RealTimeDetector(DB_PATH)
    
    try:
        seed = detector.retriever.collection.get(limit=1, include=['embeddings'])['embeddings'][0]
        attack_seed = np.array(seed)
    except:
        attack_seed = np.random.rand(99)

    start_time = time.time()
    end_time = start_time + (DURATION_MINUTES * 60)
    flow_cnt = 0

    print(f"\n{BOLD}STARTING DEMO (Attack in 10s){RESET}")
    print("-" * 60)

    while time.time() < end_time:
        current_time = time.time()
        elapsed_min = (current_time - start_time) / 60
        flow_cnt += 1
        flow_id = f"flow_{int(current_time)}_{flow_cnt}"

        # Schedule: Attack at 0.15 min (10s)
        is_attack = (0.15 <= elapsed_min < 2.0) or (5.0 <= elapsed_min < 7.0)
        
        if is_attack:
            vector = attack_seed + np.random.normal(0, 0.02, 99)
            src_ip, dst_ip = "192.168.1.66", "10.0.0.5"
            mode, color = "ATTACK", RED
        else:
            vector = np.random.rand(99)
            src_ip, dst_ip = f"10.0.0.{random.randint(10,50)}", "10.0.0.5"
            mode, color = "NORMAL", GREEN

        # Create flow
        flow_data = {
            "flow_id": flow_id, "timestamp": current_time, "vector": vector,
            "src_ip": src_ip, "dst_ip": dst_ip, "src_port": 123, "dst_port": 80, "protocol": "TCP"
        }
        flow_obj = detector._create_flow_record(flow_data)
        
        # Run Pipeline Steps
        flow_obj.retrieval_results = detector.retriever.retrieve(flow_obj)
        
        # --- FIXED METHOD CALL HERE ---
        # Was: window_batch = detector.window_mgr.add(flow_obj)
        ready, window_batch = detector.window_mgr.add_flow(flow_obj, flow_obj.retrieval_results)
        
        # --- SEND TELEMETRY EVERY FLOW ---
        send_telemetry(detector)
        # ---------------------------------

        # Console Viz
        sim = max([m['similarity'] for m in flow_obj.retrieval_results], default=0)
        win_size = detector.window_mgr.window_size
        
        sys.stdout.write(f"\r[{elapsed_min:.2f}m] Type: {color}{mode:<6}{RESET} | Sim: {sim:.2f} | Win: {win_size:.1f}s | Buff: {len(detector.window_mgr.buffer):<2}")
        sys.stdout.flush()

        # Check 'ready' instead of 'window_batch' directly
        if ready:
            print("\n")
            evidence = detector.accumulator.accumulate(window_batch)
            hypotheses = detector.fusion.fuse(evidence)
            decision = detector.judge.decide(hypotheses)
            expl = detector.explainer.explain(decision, evidence, hypotheses, window_batch)
            
            result = {'decision': decision, 'explanation': expl}

            if decision.is_attack:
                print(f"{RED}🚨 THREAT: {decision.attack_type.upper()}{RESET} (Conf: {decision.confidence:.1%})")
                send_to_dashboard(result, flow_id, src_ip, dst_ip)
            else:
                print(f"{GREEN}✅ BENIGN TRAFFIC{RESET}")
            print("-" * 60)

        time.sleep(FLOW_INTERVAL)

# Monkey Patch for object creation
RealTimeDetector._create_flow_record = lambda self, d: self.process_flow.__globals__['FlowRecord'](
    flow_id=d['flow_id'], timestamp=d['timestamp'], vector_embedding=np.array(d['vector']),
    src_ip=d['src_ip'], dst_ip=d['dst_ip'], src_port=d['src_port'], dst_port=d['dst_port'], protocol=d['protocol']
)

if __name__ == "__main__":
    run_simulation()