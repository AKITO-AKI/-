\
"""
One-command runner for StudyRoom App.

✅ Works on Linux/macOS/Windows (including GitHub Codespaces).
✅ No venv activation needed.
✅ Creates .venv, installs deps, loads .env, and runs uvicorn.

Usage:
  python run.py
  python run.py --port 8000
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import venv
from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
REQ = BACKEND / "requirements.txt"
VENV_DIR = ROOT / ".venv"
ENV_FILE = ROOT / ".env"


def eprint(*a):
    print(*a, file=sys.stderr)


def read_env_file(path: Path) -> dict:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def ensure_env_file() -> None:
    """
    Create .env if missing, with a random secret key.
    Admin password is set to 'change-me' by default (you MUST change it).
    """
    if ENV_FILE.exists():
        return
    secret = secrets.token_urlsafe(32)
    ENV_FILE.write_text(
        "# StudyRoom App env (edit this)\n"
        "STUDYROOM_ADMIN_PASSWORD=change-me\n"
        f"STUDYROOM_SECRET_KEY={secret}\n"
        "# STUDYROOM_DB_PATH=backend/studyroom.sqlite3\n",
        encoding="utf-8",
    )
    print("Created .env (please change STUDYROOM_ADMIN_PASSWORD).")


def venv_python() -> Path:
    if platform.system().lower().startswith("win"):
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv() -> None:
    if not VENV_DIR.exists():
        print("Creating .venv ...")
        venv.create(VENV_DIR, with_pip=True)
    py = venv_python()
    if not py.exists():
        raise RuntimeError("venv python not found; delete .venv and try again.")


def pip_install() -> None:
    if not REQ.exists():
        raise FileNotFoundError(f"requirements not found: {REQ}")
    py = venv_python()
    print("Installing/Updating dependencies ...")
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(REQ)])


def run_uvicorn(port: int) -> None:
    py = venv_python()

    # Load .env and merge with current env (current env wins)
    ensure_env_file()
    file_env = read_env_file(ENV_FILE)
    env = os.environ.copy()
    for k, v in file_env.items():
        env.setdefault(k, v)

    # Safety: warn if admin password unchanged
    if env.get("STUDYROOM_ADMIN_PASSWORD", "") in ("change-me", "your_admin_password", ""):
        eprint("\n⚠️ STUDYROOM_ADMIN_PASSWORD is not set or still default.")
        eprint("   Edit .env and set a strong password before real use.\n")

    cmd = [str(py), "-m", "uvicorn", "backend.main:app", "--reload", "--port", str(port)]
    print("\nRunning:", " ".join(cmd))
    print("Open:")
    print(f"  Home   : http://localhost:{port}/")
    print(f"  Personal: http://localhost:{port}/login")
    print(f"  Admin  : http://localhost:{port}/admin\n")
    subprocess.check_call(cmd, env=env, cwd=str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args = ap.parse_args()

    # quick project sanity checks
    if not (ROOT / "backend" / "main.py").exists():
        eprint("ERROR: backend/main.py not found. You are likely not in the project folder.")
        eprint(f"Expected at: {ROOT / 'backend' / 'main.py'}")
        sys.exit(2)

    ensure_venv()
    pip_install()
    run_uvicorn(args.port)


if __name__ == "__main__":
    main()
