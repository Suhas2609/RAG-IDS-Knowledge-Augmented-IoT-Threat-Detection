"""
RAG-IDS Test Script
===================

Quick test to verify the 3-file architecture is working.

This script:
1. Checks API health
2. Sends a test flow to /detect endpoint  
3. Retrieves the latest alerts

Usage:
    python test_integration.py
"""

import requests
import numpy as np
import time
from datetime import datetime


API_BASE_URL = "http://localhost:8000"


def test_health():
    """Test API health endpoint"""
    print("\n" + "="*70)
    print("🔍 Testing API Health...")
    print("="*70)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"✅ Engine: {data['engine_status']}")
            print(f"✅ Vectors Loaded: {data['vector_count']:,}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("\n💡 Make sure the API is running:")
        print("   cd notebooks/Phase_4/api")
        print("   uvicorn threat_api:app --reload --port 8000")
        return False


def test_detect():
    """Test flow detection endpoint"""
    print("\n" + "="*70)
    print("🔍 Testing Flow Detection...")
    print("="*70)
    
    # Create test flow
    flow = {
        "flow_id": f"test_{int(time.time())}",
        "timestamp": time.time(),
        "vector_embedding": np.random.rand(99).tolist(),
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.1",
        "src_port": 443,
        "dst_port": 80,
        "protocol": "TCP"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/detect",
            json=flow,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Detection Complete:")
            print(f"   Flow ID: {data['flow_id']}")
            print(f"   Attack: {data['is_attack']}")
            print(f"   Severity: {data['severity']}")
            print(f"   Confidence: {data['confidence']:.2%}")
            print(f"   Recommendation: {data['recommendation']}")
            return True
        else:
            print(f"❌ Detection failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during detection: {e}")
        return False


def test_alerts():
    """Test alerts retrieval endpoint"""
    print("\n" + "="*70)
    print("🔍 Testing Alert Retrieval...")
    print("="*70)
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/alerts/latest",
            params={"limit": 5},
            timeout=5
        )
        
        if response.status_code == 200:
            alerts = response.json()
            print(f"✅ Retrieved {len(alerts)} alerts")
            
            if len(alerts) > 0:
                print("\n📋 Recent Alerts:")
                for alert in alerts[:3]:
                    print(f"   • {alert['severity']}: {alert['attack_type']} "
                          f"({alert['confidence']:.1%} confidence)")
            else:
                print("   No alerts in history yet.")
            return True
        else:
            print(f"❌ Alert retrieval failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error retrieving alerts: {e}")
        return False


def test_stats():
    """Test engine statistics endpoint"""
    print("\n" + "="*70)
    print("🔍 Testing Engine Statistics...")
    print("="*70)
    
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        
        if response.status_code == 200:
            stats = response.json()
            engine = stats['engine']
            alerts = stats['alerts']
            
            print(f"✅ Engine Stats:")
            print(f"   Vector Count: {engine['vector_count']:,}")
            print(f"   Window Buffer: {engine['current_window_size']} flows")
            print(f"   Window Duration: {engine['adaptive_window_seconds']:.1f}s")
            print(f"\n✅ Alert Stats:")
            print(f"   Total Alerts: {alerts['total']}")
            print(f"   By Severity: {alerts['by_severity']}")
            return True
        else:
            print(f"❌ Stats retrieval failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error retrieving stats: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 RAG-IDS Integration Test Suite")
    print("="*70)
    
    # Test sequence
    health_ok = test_health()
    
    if not health_ok:
        print("\n❌ API is not reachable. Stopping tests.")
        return
    
    detect_ok = test_detect()
    alerts_ok = test_alerts()
    stats_ok = test_stats()
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Detection:    {'✅ PASS' if detect_ok else '❌ FAIL'}")
    print(f"Alerts:       {'✅ PASS' if alerts_ok else '❌ FAIL'}")
    print(f"Statistics:   {'✅ PASS' if stats_ok else '❌ FAIL'}")
    
    if all([health_ok, detect_ok, alerts_ok, stats_ok]):
        print("\n✅ All tests passed! System is operational.")
        print("\n🎉 Next steps:")
        print("   1. Open dashboard: http://localhost:8501")
        print("   2. Run Phase 3.7 simulation to see live alerts")
        print("   3. Watch the dashboard update in real-time!")
    else:
        print("\n⚠️ Some tests failed. Check error messages above.")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
