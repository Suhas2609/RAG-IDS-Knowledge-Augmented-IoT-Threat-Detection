"""
RAG-IDS API Module
==================

Production deployment of the RAG-IDS detection system.

Components:
    - ragids_engine: Core detection logic (Phases 3.1-3.6)
    - threat_api: FastAPI REST server

Usage:
    from ragids_engine import RealTimeDetector
    
    detector = RealTimeDetector(db_path="artifacts/chromadb")
    result = detector.process_flow(flow)
"""

__version__ = "1.0.0"
__author__ = "Suhas (Capstone 2026)"

from ragids_engine import (
    RealTimeDetector,
    FlowRecord,
    ThreatDecision,
    ThreatExplanation,
    SeverityLevel
)

__all__ = [
    'RealTimeDetector',
    'FlowRecord',
    'ThreatDecision',
    'ThreatExplanation',
    'SeverityLevel'
]
