"""
start_server.py - Production Container Entrypoint Launcher

Checks SERVICE_TYPE environment variable:
- SERVICE_TYPE=dashboard (default): Launches Streamlit Growth Console on port 8000
- SERVICE_TYPE=api: Launches FastAPI Webhook Engine on port 8000
"""

import os
import sys
import subprocess

def main():
    service_type = os.getenv("SERVICE_TYPE", "dashboard").lower().strip()
    port = os.getenv("PORT", "8000")

    if service_type == "api":
        print(f"🚀 Starting AgentCheckout FastAPI Server on port {port}...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", "mcp_server.server:app",
            "--host", "0.0.0.0", "--port", port
        ])
    else:
        print(f"📊 Starting AgentCheckout Streamlit Growth Dashboard on port {port}...")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
            "--server.port", port, "--server.address", "0.0.0.0"
        ])

if __name__ == '__main__':
    main()
