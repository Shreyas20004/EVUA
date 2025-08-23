import os
import subprocess
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BACKEND_DIR, "venv")
REQ_FILE = os.path.join(BACKEND_DIR, "requirements.txt")

def run(cmd, cwd=None, shell=False):
    print(f"▶ Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    subprocess.check_call(cmd, cwd=cwd, shell=shell)

def setup_python():
    if not os.path.exists(VENV_DIR):
        print("📦 Creating virtual environment...")
        run([sys.executable, "-m", "venv", VENV_DIR])
    else:
        print("✅ Virtual environment already exists.")

    pip_exe = os.path.join(VENV_DIR, "Scripts", "pip.exe") if os.name == "nt" else os.path.join(VENV_DIR, "bin", "pip")

    if os.path.exists(REQ_FILE):
        print("📦 Installing Python dependencies...")
        run([pip_exe, "install", "-r", REQ_FILE])
    else:
        print("⚠ No requirements.txt found, skipping Python deps.")

def setup_node():
    print("📦 Installing Node dependencies...")
    run(["npm", "install"], cwd=BACKEND_DIR)

    print("📦 Installing lebab globally...")
    run(["npm", "install", "-g", "lebab"], cwd=BACKEND_DIR)

def main():
    setup_python()
    setup_node()
    print("\n✅ Setup complete! Both Python venv and lebab are ready.")

if __name__ == "__main__":
    main()
