"""
FraudLens — Python Setup Script
=================================
Ek baar chalao: python setup.py
Yeh script:
  1. Python version check karega
  2. Virtual environment (venv) banayega
  3. Sab dependencies install karega (requirements.txt se)
  4. .env file setup karega

Usage:
    python setup.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):  print(f"  {GREEN}[OK]{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}[!!]{RESET} {msg}")
def err(msg):  print(f"  {RED}[ERR]{RESET} {msg}"); sys.exit(1)
def step(n, msg): print(f"\n{CYAN}[{n}]{RESET} {BOLD}{msg}{RESET}")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def run(cmd: list, **kwargs):
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        err(f"Command failed: {' '.join(str(c) for c in cmd)}")
    return result

# ─── Setup Steps ──────────────────────────────────────────────────────────────

def check_python():
    step(1, "Checking Python version")
    major, minor = sys.version_info.major, sys.version_info.minor
    print(f"  Found: Python {major}.{minor}.{sys.version_info.micro}")
    if major < 3 or (major == 3 and minor < 10):
        err(f"Python 3.10+ required. You have {major}.{minor}. Install from https://python.org")
    ok(f"Python {major}.{minor} - OK")


def create_venv():
    step(2, "Creating virtual environment (venv)")
    venv_dir = Path("venv")

    if venv_dir.exists():
        ok("venv already exists - skipping creation")
        return

    run([sys.executable, "-m", "venv", "venv"])
    ok("Virtual environment created at: ./venv/")


def get_venv_python():
    """Return path to Python inside the venv."""
    if sys.platform == "win32":
        return Path("venv") / "Scripts" / "python.exe"
    return Path("venv") / "bin" / "python"


def get_venv_pip():
    """Return path to pip inside the venv."""
    if sys.platform == "win32":
        return Path("venv") / "Scripts" / "pip.exe"
    return Path("venv") / "bin" / "pip"


def upgrade_pip():
    step(3, "Upgrading pip inside venv")
    venv_python = get_venv_python()
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    ok("pip upgraded")


def install_dependencies():
    step(4, "Installing all dependencies from requirements.txt")

    req_file = Path("requirements.txt")
    if not req_file.exists():
        err("requirements.txt not found! Run from the project root directory.")

    venv_pip = get_venv_pip()
    print(f"  Installing packages - this may take 2-4 minutes on first run...\n")

    run([str(venv_pip), "install", "-r", "requirements.txt"])
    ok("All dependencies installed!")


def setup_env():
    step(5, "Setting up .env file")

    env_file     = Path(".env")
    env_example  = Path(".env.example")

    if env_file.exists():
        ok(".env already exists")
        return

    if not env_example.exists():
        warn(".env.example not found - skipping")
        return

    shutil.copy(env_example, env_file)
    ok(".env created from .env.example")
    warn("IMPORTANT: Edit .env with your credentials before running!")
    print(f"  {YELLOW}  -> TG_HOST, TG_USERNAME, TG_PASSWORD, TG_SECRET{RESET}")
    print(f"  {YELLOW}  -> OPENAI_API_KEY{RESET}")


def print_next_steps():
    venv_activate = (
        r"venv\Scripts\activate" if sys.platform == "win32"
        else "source venv/bin/activate"
    )

    print(f"\n{'='*42}")
    print(f"{GREEN}{BOLD}  Setup Complete!{RESET}")
    print(f"{'='*42}")
    print(f"\n{BOLD}To activate venv next time:{RESET}")
    print(f"  {CYAN}{venv_activate}{RESET}")
    print(f"\n{BOLD}Next steps:{RESET}")
    print(f"  1. Edit .env with your TigerGraph + OpenAI credentials")
    print(f"  2. Load schema:    python scripts\\load_schema.py")
    print(f"  3. Load CSV data:  python scripts\\load_data.py --sample 10000")
    print(f"  4. Run backend:    uvicorn backend.main:app --reload --port 8000")
    print(f"  5. Run frontend:   cd frontend && npm install && npm run dev")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*42}")
    print(f"{CYAN}{BOLD}   FraudLens - Project Setup{RESET}")
    print(f"{'='*42}")

    # Must run from project root
    if not Path("requirements.txt").exists():
        err(
            "requirements.txt not found!\n"
            "  Please run this script from the project root:\n"
            "  cd d:\\Projects\\FRAUDLENS\n"
            "  python setup.py"
        )

    check_python()
    create_venv()
    upgrade_pip()
    install_dependencies()
    setup_env()
    print_next_steps()


if __name__ == "__main__":
    main()
