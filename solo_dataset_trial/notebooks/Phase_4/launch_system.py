"""
RAG-IDS SYSTEM LAUNCHER
=======================
Single command to start the entire RAG-IDS production system:
- API Server (FastAPI on port 8000)
- Dashboard (Streamlit on port 8501)

Usage:
    python launch_system.py
    
Press Ctrl+C to stop all services.
"""

import subprocess
import sys
import os
import time
import requests
import signal
import atexit
from pathlib import Path

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_banner():
    """Display startup banner"""
    banner = f"""
{BLUE}{'='*70}
{BOLD}RAG-IDS: Knowledge-Augmented IoT Threat Detection System{RESET}
{BLUE}{'='*70}{RESET}

{YELLOW}>> Starting Production System...{RESET}
    """
    print(banner)

def check_prerequisites():
    """Check if required packages are installed"""
    print(f"\n{YELLOW}[1/3] Checking Prerequisites...{RESET}")
    
    required_packages = {
        'api': ['fastapi', 'uvicorn', 'chromadb', 'numpy', 'pydantic'],
        'dashboard': ['streamlit', 'plotly', 'pandas', 'requests']
    }
    
    missing = []
    
    for component, packages in required_packages.items():
        for package in packages:
            try:
                __import__(package)
            except ImportError:
                missing.append((component, package))
    
    if missing:
        print(f"{RED}✗ Missing packages detected:{RESET}")
        for component, package in missing:
            print(f"  - {package} (needed for {component})")
        print(f"\n{YELLOW}Install missing packages:{RESET}")
        print(f"  cd api && pip install -r requirements.txt")
        print(f"  cd dashboard && pip install -r requirements.txt")
        return False
    
    print(f"{GREEN}✓ All prerequisites satisfied{RESET}")
    return True

def check_chromadb_path():
    """Verify ChromaDB path exists"""
    print(f"\n{YELLOW}[2/3] Verifying ChromaDB Path...{RESET}")
    
    # Read the API file to check ChromaDB path
    api_file = Path(__file__).parent / "api" / "threat_api.py"
    
    if not api_file.exists():
        print(f"{RED}✗ threat_api.py not found!{RESET}")
        return False
    
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Look for db_path assignment in startup_event
        for line in content.split('\n'):
            if 'db_path' in line and '=' in line and 'chromadb' in line.lower():
                # Extract the path
                print(f"{YELLOW}  Configuration: {line.strip()}{RESET}")
                
                # Try to extract the actual path value
                try:
                    # Get the path between quotes
                    if '"' in line or "'" in line:
                        path_str = line.split('=')[1].strip()
                        # Remove r prefix and quotes
                        path_str = path_str.replace('r"', '').replace('"', '').replace("r'", '').replace("'", '')
                        path_obj = Path(path_str)
                        
                        if path_obj.exists():
                            print(f"{GREEN}✓ ChromaDB path exists and is accessible{RESET}")
                            return True
                        else:
                            print(f"{YELLOW}⚠ ChromaDB path configured but directory not found{RESET}")
                            print(f"{YELLOW}  Expected: {path_str}{RESET}")
                            return False
                except Exception as e:
                    print(f"{GREEN}✓ ChromaDB configuration found{RESET}")
                    print(f"{YELLOW}  Note: Could not verify path existence{RESET}")
                    return True
    
    print(f"{RED}✗ ChromaDB path not configured{RESET}")
    return False

def start_api_server():
    """Start the FastAPI server in background"""
    print(f"\n{YELLOW}[3/3] Starting API Server...{RESET}")
    
    api_dir = Path(__file__).parent / "api"
    
    # Start uvicorn process with worker threads for blocking operations
    # --timeout-keep-alive 5 prevents hung connections
    # --limit-concurrency 100 controls max concurrent requests
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "threat_api:app", 
         "--host", "127.0.0.1", 
         "--port", "8000",
         "--timeout-keep-alive", "5",
         "--limit-concurrency", "100"],
        cwd=str(api_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    print(f"{BLUE}  → API server starting on http://localhost:8000{RESET}")
    
    # Give it a moment to crash if there are immediate errors
    time.sleep(2)
    
    if process.poll() is not None:
        # Process already terminated
        stdout, _ = process.communicate()
        print(f"\n{RED}✗ API server crashed immediately!{RESET}")
        print(f"{RED}Error output:{RESET}")
        print(stdout)
        return None
    
    # Wait for API to be ready
    max_retries = 20
    
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                vector_count = data.get('vector_count', 'unknown')
                print(f"{GREEN}✓ API server ready!{RESET}")
                print(f"{GREEN}  → Engine initialized with {vector_count} vectors{RESET}")
                print(f"{BLUE}  → API docs: http://localhost:8000/docs{RESET}")
                return process
        except requests.exceptions.RequestException:
            # Connection still not ready
            pass
        
        # Check if process crashed
        if process.poll() is not None:
            stdout, _ = process.communicate()
            print(f"\n{RED}✗ API server crashed during startup!{RESET}")
            if stdout:
                print(f"{RED}Error output:{RESET}")
                print(stdout[:2000])
            return None
        
        if i % 3 == 0 and i > 0:
            print(f"{YELLOW}  ⏳ Waiting for API server... ({i}/{max_retries}){RESET}")
        
        time.sleep(1)
    
    print(f"{RED}✗ API server failed to respond within timeout{RESET}")
    process.terminate()
    return None

def start_dashboard():
    """Start the Streamlit dashboard in background"""
    print(f"\n{YELLOW}[3/3] Starting Dashboard...{RESET}")
    
    dashboard_dir = Path(__file__).parent / "dashboard"
    
    # Start streamlit process
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "threat_dashboard.py", 
         "--server.port", "8501", "--server.headless", "true"],
        cwd=str(dashboard_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"{BLUE}  → Dashboard starting on http://localhost:8501{RESET}")
    
    # Wait for dashboard to be ready
    time.sleep(3)
    
    print(f"{GREEN}✓ Dashboard ready!{RESET}")
    print(f"{BLUE}  → Open: http://localhost:8501{RESET}")
    
    return process

def monitor_processes(api_process, dashboard_process):
    """Monitor both processes and handle shutdown"""
    print(f"\n{BOLD}{GREEN}{'='*70}")
    print(f">> RAG-IDS SYSTEM RUNNING")
    print(f"{'='*70}{RESET}")
    print(f"\n{GREEN}Services:{RESET}")
    print(f"  > API Server:    {BLUE}http://localhost:8000{RESET}")
    print(f"  > API Docs:      {BLUE}http://localhost:8000/docs{RESET}")
    print(f"  > Dashboard:     {BLUE}http://localhost:8501{RESET}")
    print(f"\n{BOLD}{YELLOW}SYSTEM IS NOW LIVE - Leave this window open!{RESET}")
    print(f"{YELLOW}Press Ctrl+C to stop all services{RESET}")
    print(f"{GREEN}Health checks running every 30 seconds...{RESET}\n")
    
    last_health_check = time.time()
    
    try:
        while True:
            # Check if processes are still running
            api_status = api_process.poll()
            dashboard_status = dashboard_process.poll()
            
            if api_status is not None:
                print(f"\n{RED}⚠ API server stopped unexpectedly (exit code: {api_status}){RESET}")
                # Try to get error output
                try:
                    stdout, stderr = api_process.communicate(timeout=1)
                    if stdout:
                        print(f"{RED}Last output:{RESET}\n{stdout[-500:]}")
                except:
                    pass
                break
            
            if dashboard_status is not None:
                print(f"\n{RED}⚠ Dashboard stopped unexpectedly (exit code: {dashboard_status}){RESET}")
                break
            
            # Health check every 30 seconds
            current_time = time.time()
            if current_time - last_health_check >= 30:
                try:
                    response = requests.get("http://localhost:8000/health", timeout=2)
                    if response.status_code == 200:
                        data = response.json()
                        uptime_min = data.get('uptime_seconds', 0) / 60
                        print(f"{GREEN}✓ Health Check OK - Uptime: {uptime_min:.1f}m{RESET}")
                    else:
                        print(f"{YELLOW}⚠ API returned status {response.status_code}{RESET}")
                except requests.exceptions.RequestException:
                    print(f"{RED}⚠ API health check failed - service may be down{RESET}")
                except Exception as e:
                    print(f"{YELLOW}⚠ Health check error: {str(e)[:50]}{RESET}")
                
                last_health_check = current_time
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Shutting down...{RESET}")
        
        # Graceful shutdown
        print(f"{YELLOW}  → Stopping dashboard...{RESET}")
        dashboard_process.terminate()
        try:
            dashboard_process.wait(timeout=5)
            print(f"{GREEN}  ✓ Dashboard stopped{RESET}")
        except subprocess.TimeoutExpired:
            dashboard_process.kill()
            print(f"{YELLOW}  ⚠ Dashboard force-killed{RESET}")
        
        print(f"{YELLOW}  → Stopping API server...{RESET}")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
            print(f"{GREEN}  ✓ API server stopped{RESET}")
        except subprocess.TimeoutExpired:
            api_process.kill()
            print(f"{YELLOW}  ⚠ API server force-killed{RESET}")
        
        print(f"\n{GREEN}{'='*70}")
        print(f"✓ All services stopped successfully")
        print(f"{'='*70}{RESET}\n")

def cleanup_processes(api_process, dashboard_process):
    """Cleanup function for atexit"""
    try:
        if api_process and api_process.poll() is None:
            api_process.terminate()
            api_process.wait(timeout=3)
        if dashboard_process and dashboard_process.poll() is None:
            dashboard_process.terminate()
            dashboard_process.wait(timeout=3)
    except:
        pass

def main():
    """Main launcher function"""
    # Setup signal handlers
    api_process = None
    dashboard_process = None
    
    def signal_handler(sig, frame):
        print(f"\n\n{YELLOW}Received interrupt signal, shutting down...{RESET}")
        cleanup_processes(api_process, dashboard_process)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    print_banner()
    
    # Step 1: Check prerequisites
    if not check_prerequisites():
        print(f"\n{RED}❌ Prerequisites check failed. Please install missing packages.{RESET}")
        sys.exit(1)
    
    # Step 2: Verify ChromaDB
    if not check_chromadb_path():
        print(f"\n{YELLOW}⚠ Warning: ChromaDB path may need configuration{RESET}")
        response = input(f"{YELLOW}Continue anyway? (y/n): {RESET}").strip().lower()
        if response != 'y':
            print(f"{YELLOW}Aborted by user{RESET}")
            sys.exit(0)
    
    # Step 3: Start API server
    api_process = start_api_server()
    if api_process is None:
        print(f"\n{RED}❌ Failed to start API server{RESET}")
        sys.exit(1)
    
    # Step 4: Start dashboard
    try:
        dashboard_process = start_dashboard()
    except Exception as e:
        print(f"\n{RED}❌ Failed to start dashboard: {e}{RESET}")
        print(f"{YELLOW}Cleaning up...{RESET}")
        api_process.terminate()
        sys.exit(1)
    
    # Register cleanup on exit
    atexit.register(cleanup_processes, api_process, dashboard_process)
    
    # Step 5: Monitor processes (this blocks forever until Ctrl+C)
    monitor_processes(api_process, dashboard_process)

if __name__ == "__main__":
    main()
