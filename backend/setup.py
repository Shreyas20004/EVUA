# backend/setup.py
import os
import sys
import subprocess
import venv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BACKEND_DIR, "venv")
REQ_FILE = os.path.join(BACKEND_DIR, "requirements.txt")


def create_venv():
    if not os.path.exists(VENV_DIR):
        print("🔹 Creating Python virtual environment...")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    else:
        print("✅ Virtual environment already exists.")


def run_pip_install():
    pip_path = os.path.join(
        VENV_DIR, "Scripts", "pip.exe" if os.name == "nt" else "bin/pip"
    )
    if os.path.exists(REQ_FILE):
        print("🔹 Installing Python dependencies...")
        subprocess.check_call([pip_path, "install", "-r", REQ_FILE])
    else:
        print("⚠️ No requirements.txt found, skipping Python deps.")


def run_npm_install():
    print("🔹 Installing Node.js dependencies (lebab, etc.)...")
    subprocess.check_call(["npm", "install"], cwd=BACKEND_DIR)


if __name__ == "__main__":
    print("🚀 Setting up EVUA backend...")

    create_venv()
    run_pip_install()
    run_npm_install()

    print("\n✅ Setup complete!")
    print("To activate your environment manually:")
    if os.name == "nt":
        print(r"   backend\venv\Scripts\activate")
    else:
        print(r"   source backend/venv/bin/activate")
