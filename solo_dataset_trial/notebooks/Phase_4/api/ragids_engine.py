"""
RAG-IDS Detection Engine - Production Core (FIXED)
==================================================
Updated to align perfectly with Phase 3.1 notebook logic:
- Adaptive Windowing (5.0s to 60.0s)
- Recurrence-based expansion thresholds
- Proper method signatures for RealTimeDetector
"""

import numpy as np
import chromadb
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from collections import deque
from datetime import datetime

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class FlowRecord:
    flow_id: str
    timestamp: float
    vector_embedding: np.ndarray
    src_ip: str = "0.0.0.0"
    dst_ip: str = "0.0.0.0"
    src_port: int = 0
    dst_port: int = 0
    protocol: str = "UNKNOWN"
    retrieval_results: Optional[List[Dict]] = None

@dataclass
class AttackEvidence:
    attack_type: str
    count: int
    avg_similarity: float
    recurrence_score: float
    threat_score: float = 0.0

@dataclass
class ThreatHypothesis:
    attack_type: str
    probability: float
    confidence: float
    evidence_count: int

class SeverityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    BENIGN = "BENIGN"

@dataclass
class ThreatDecision:
    is_attack: bool
    severity: SeverityLevel
    attack_type: Optional[str]
    probability: float
    confidence: float
    recommendation: str
    evidence_summary: str

@dataclass
class ThreatExplanation:
    narrative: str
    top_flows: List[str]
    top_matches: List[Dict]
    decision_factors: Dict[str, float]
    confidence_breakdown: Dict[str, float]
    timeline: List[str]

# ============================================================================
# PHASE 3.2: RETRIEVER
# ============================================================================

class Phase3_2_Retriever:
    def __init__(self, db_path: str, collection_name: str = "iot_behavioral_memory_hybrid"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection(name=collection_name)
        self.vector_count = self.collection.count()
        
    def retrieve(self, flow: FlowRecord, n_results: int = 5) -> List[Dict]:
        try:
            results = self.collection.query(
                query_embeddings=[flow.vector_embedding.tolist()],
                n_results=n_results,
                include=['metadatas', 'distances']
            )
            matches = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    dist = results['distances'][0][i]
                    sim = max(0.0, min(1.0, 1.0 - dist))
                    meta = results['metadatas'][0][i]
                    attack_type = meta.get('type', meta.get('label', 'unknown'))
                    matches.append({
                        'attack_type': attack_type,
                        'similarity': sim,
                        'distance': dist,
                        'metadata': meta
                    })
            return matches
        except Exception as e:
            print(f"Retrieval Error: {e}")
            return []

# ============================================================================
# PHASE 3.1: ADAPTIVE WINDOW (ALIGNED WITH NOTEBOOK)
# ============================================================================

# ... (Previous imports stay the same)

class Phase3_1_Window:
    def __init__(
        self,
        min_time_seconds: float = 5.0,
        max_time_seconds: float = 60.0,
        min_flow_count: int = 20,
        max_flow_count: int = 500,
        similarity_expansion_threshold: float = 0.75,
        similarity_shrinkage_threshold: float = 0.50,
        recurrence_expansion_threshold: int = 3
    ):
        self.min_time_seconds = min_time_seconds
        self.max_time_seconds = max_time_seconds
        self.min_flow_count = min_flow_count
        self.max_flow_count = max_flow_count
        
        self.similarity_expansion_threshold = similarity_expansion_threshold
        self.similarity_shrinkage_threshold = similarity_shrinkage_threshold
        self.recurrence_expansion_threshold = recurrence_expansion_threshold
        
        self.buffer: deque[FlowRecord] = deque(maxlen=max_flow_count)
        self.window_size = min_time_seconds  # Start at 5.0s
        self.recent_avg_similarities: deque[float] = deque(maxlen=10)
        self._attack_type_counter: Dict[str, int] = {}

    def add_flow(self, flow: FlowRecord, matches: List[Dict]) -> Tuple[bool, List[FlowRecord]]:
        """Add flow and adjust window size dynamically."""
        flow.retrieval_results = matches
        self.buffer.append(flow)
        
        # 1. Update Stats
        similarities = [m['similarity'] for m in matches]
        avg_sim = np.mean(similarities) if similarities else 0.0
        self.recent_avg_similarities.append(avg_sim)
        
        for m in matches:
            atype = m['attack_type']
            if atype.lower() not in ['normal', 'benign']:
                self._attack_type_counter[atype] = self._attack_type_counter.get(atype, 0) + 1

        # 2. SMOOTH ADAPTIVE LOGIC
        if len(self.recent_avg_similarities) >= 5:
            recent_avg = np.mean(list(self.recent_avg_similarities))
            max_recurrence = max(self._attack_type_counter.values()) if self._attack_type_counter else 0
            
            # EXPAND: Grow by 5% per flow (Smoother visual)
            if recent_avg > self.similarity_expansion_threshold or max_recurrence >= self.recurrence_expansion_threshold:
                self.window_size = min(self.window_size * 1.05, self.max_time_seconds)
            
            # SHRINK: Reduce by 5% per flow
            elif recent_avg < self.similarity_shrinkage_threshold:
                self.window_size = max(self.window_size * 0.95, self.min_time_seconds)
                # Clear counter if we shrink back to baseline
                if self.window_size <= self.min_time_seconds + 1.0:
                    self._attack_type_counter.clear()

        # 3. Check Flush
        if len(self.buffer) >= self.min_flow_count:
            duration = self.buffer[-1].timestamp - self.buffer[0].timestamp
            if duration >= self.window_size:
                batch = list(self.buffer)
                self.buffer.clear()
                return True, batch
        
        return False, []

# ============================================================================
# PHASE 3.3 - 3.6: ACCUMULATOR, FUSION, DECISION, EXPLAINER
# ============================================================================

class Phase3_3_Accumulator:
    def accumulate(self, window: List[FlowRecord]) -> Dict[str, AttackEvidence]:
        evidence_map = {}
        for flow in window:
            if not flow.retrieval_results: continue
            for match in flow.retrieval_results:
                atype = match['attack_type']
                if atype not in evidence_map:
                    evidence_map[atype] = {'sims': [], 'count': 0}
                evidence_map[atype]['sims'].append(match['similarity'])
                evidence_map[atype]['count'] += 1
        
        results = {}
        for atype, data in evidence_map.items():
            count = data['count']
            avg_sim = np.mean(data['sims'])
            recurrence = min(1.0, count / len(window))
            results[atype] = AttackEvidence(
                attack_type=atype, count=count, avg_similarity=avg_sim,
                recurrence_score=recurrence,
                threat_score=(0.6 * recurrence) + (0.4 * avg_sim)
            )
        return results

class Phase3_4_QuantumFusion:
    def fuse(self, evidence_map: Dict[str, AttackEvidence]) -> Dict[str, ThreatHypothesis]:
        if not evidence_map: return {}
        raw_amps = {}
        total_amp_sq = 0.0
        for atype, ev in evidence_map.items():
            amp = np.sqrt(ev.count * ev.recurrence_score * ev.avg_similarity)
            raw_amps[atype] = amp
            total_amp_sq += amp ** 2
        if total_amp_sq == 0: return {}
        hypotheses = {}
        for atype, amp in raw_amps.items():
            prob = (amp ** 2) / total_amp_sq
            ev = evidence_map[atype]
            conf = (0.4 * ev.recurrence_score + 0.3 * ev.avg_similarity + 0.3 * min(1.0, ev.count / 10))
            hypotheses[atype] = ThreatHypothesis(atype, prob, conf, ev.count)
        return hypotheses

class Phase3_5_Decision:
    BENIGN_WHITELIST = {'normal', 'benign', 'legitimate'}
    def decide(self, hypotheses: Dict[str, ThreatHypothesis]) -> ThreatDecision:
        if not hypotheses:
            return ThreatDecision(False, SeverityLevel.BENIGN, None, 0.0, 0.0, "Monitor", "No patterns")
        top = max(hypotheses.values(), key=lambda x: x.probability)
        if top.attack_type.lower() in self.BENIGN_WHITELIST:
            return ThreatDecision(False, SeverityLevel.BENIGN, top.attack_type, top.probability, top.confidence, "PASS", f"Identified as {top.attack_type}")
        
        thresh = 0.50 - (top.confidence * 0.20)
        is_attack = (top.probability > thresh and top.confidence > 0.4)
        if is_attack:
            score = (0.4 * top.probability) + (0.3 * top.confidence)
            sev = SeverityLevel.CRITICAL if score > 0.8 else SeverityLevel.HIGH if score > 0.6 else SeverityLevel.MEDIUM
            return ThreatDecision(True, sev, top.attack_type, top.probability, top.confidence, f"BLOCK {top.attack_type.upper()}", f"Detected {top.attack_type} ({top.confidence:.1%} confidence)")
        return ThreatDecision(False, SeverityLevel.BENIGN, top.attack_type, top.probability, top.confidence, "Monitor", "Below threshold")

class Phase3_6_Explainer:
    def explain(self, decision, evidence, hypotheses, window) -> ThreatExplanation:
        narrative = f"Detected {decision.attack_type} pattern."
        factors = {'probability': decision.probability, 'confidence': decision.confidence}
        breakdown = {}
        if decision.attack_type and decision.attack_type in evidence:
            ev = evidence[decision.attack_type]
            breakdown = {'recurrence': ev.recurrence_score, 'similarity': ev.avg_similarity}
        return ThreatExplanation(narrative, [f"{f.src_ip} -> {f.dst_ip}" for f in window[:3]], [], factors, breakdown, [])

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class RealTimeDetector:
    def __init__(self, db_path: str, collection_name: str = "iot_behavioral_memory_hybrid"):
        self.retriever = Phase3_2_Retriever(db_path, collection_name)
        self.window_mgr = Phase3_1_Window()
        self.accumulator = Phase3_3_Accumulator()
        self.fusion = Phase3_4_QuantumFusion()
        self.judge = Phase3_5_Decision()
        self.explainer = Phase3_6_Explainer()
        print(f">> RAG-IDS Engine Online ({self.retriever.vector_count:,} vectors loaded)")
    
    def process_flow(self, flow: FlowRecord) -> Optional[Dict]:
        """Orchestrate the full Phase 3 pipeline."""
        matches = self.retriever.retrieve(flow, n_results=5)
        ready, window_batch = self.window_mgr.add_flow(flow, matches)
        
        if not ready:
            return None
        
        evidence = self.accumulator.accumulate(window_batch)
        hypotheses = self.fusion.fuse(evidence)
        decision = self.judge.decide(hypotheses)
        explanation = self.explainer.explain(decision, evidence, hypotheses, window_batch)
        
        return {
            'decision': decision,
            'explanation': explanation,
            'evidence': evidence,
            'hypotheses': hypotheses,
            'window_size': self.window_mgr.window_size
        }
    
    def get_stats(self) -> Dict:
        return {
            'vector_count': self.retriever.vector_count,
            'current_window_size': len(self.window_mgr.buffer),
            'adaptive_window_seconds': self.window_mgr.window_size
        }

__all__ = ['RealTimeDetector', 'FlowRecord', 'ThreatDecision', 'ThreatExplanation', 'SeverityLevel']