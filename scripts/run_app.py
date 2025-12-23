import subprocess
import time
import os
import sys
import socket
import signal

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def kill_process_on_port(port):
    if not is_port_in_use(port):
        return
    
    print(f"Cleaning zombie process on port {port}...")
    try:
        # Windows specific: find PID using netstat and kill using taskkill
        output = subprocess.check_output(f'netstat -ano | findstr ":{port}"', shell=True).decode()
        pids = set()
        for line in output.strip().split('\n'):
            parts = line.split()
            if len(parts) > 4:
                pids.add(parts[-1])
        
        for pid in pids:
            print(f"  Killing PID {pid}")
            subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
    except Exception as e:
        print(f"  Failed to kill process on port {port}: {e}")

def run_app():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    os.chdir(root_dir)

    print("==========================================")
    print("   Auditor Contabil - Definitive Startup  ")
    print("==========================================")

    # 1. Cleanup
    kill_process_on_port(8010)
    kill_process_on_port(8000)
    time.sleep(1)

    # 2. Start Backend
    print("[1/2] Starting Backend (Port 8010)...")
    backend_cmd = [sys.executable, "-m", "uvicorn", "src.api.main:app", "--reload", "--port", "8010"]
    backend_proc = subprocess.Popen(backend_cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)

    # Wait for backend health
    retries = 10
    while retries > 0:
        if is_port_in_use(8010):
            print("  Backend is UP!")
            break
        time.sleep(1)
        retries -= 1
    
    if retries == 0:
        print("!! WARNING: Backend taking too long to start. Check terminal.")

    # 3. Start Frontend
    print("[2/2] Starting Frontend (Vite)...")
    web_dir = os.path.join(root_dir, "src", "web")
    frontend_proc = subprocess.Popen(["npm", "run", "dev"], cwd=web_dir, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

    print("\nSUCCESS: All services initiated.")
    print("Acesse: http://localhost:5173")
    print("\nKeep this window open. Press Ctrl+C to stop both (or close terminals).")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        # Frontend is started via npm shell, might need process group kill or just let user close CMDs
        print("Done.")

if __name__ == "__main__":
    run_app()
