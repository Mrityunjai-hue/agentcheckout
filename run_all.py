"""
run_all.py - One-Command Launcher for AgentCheckout

Runs data prep, model training, database seeding, unit tests, and launches both FastMCP/FastAPI server & Streamlit dashboard.
"""

import os
import sys
import subprocess
import time

def main():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(base_dir)

    print("================================================================")
    print("⚡ AGENTCHECKOUT — ONE-COMMAND BUILD & RUN LAUNCHER ⚡")
    print("================================================================")

    # 1. Dataset Prep
    print("\n[1/5] Sourcing and preparing benchmark dataset...")
    subprocess.run([sys.executable, "ml/prepare_dataset.py"], check=True)

    # 2. Train Model
    print("\n[2/5] Training Conversion Intelligence Model & SMOTE pipeline...")
    subprocess.run([sys.executable, "ml/train_model.py"], check=True)

    # 3. Simulate Uplift
    print("\n[3/5] Simulating Conversion Uplift on test split...")
    subprocess.run([sys.executable, "ml/simulate_uplift.py"], check=True)

    # 4. Seed Database
    print("\n[4/5] Initializing and seeding SQLite database...")
    subprocess.run([sys.executable, "seed_data.py"], check=True)

    # 5. Run Unit Tests
    print("\n[5/5] Executing test suite...")
    subprocess.run([sys.executable, "-m", "pytest", "tests/"], check=True)

    print("\n================================================================")
    print("🎉 All components built, trained, and verified successfully!")
    print("Launching FastAPI/FastMCP Webhook Server (Port 8000)...")
    print("To run Streamlit dashboard in a separate terminal:")
    print("   python -m streamlit run dashboard/app.py")
    print("================================================================")

    # Start FastAPI server
    subprocess.run([sys.executable, "mcp_server/server.py"])

if __name__ == '__main__':
    main()
