from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
MODULE0 = ROOT / "module0"
MODULE1 = ROOT / "module1"
PY0 = MODULE0 / ".venv" / "Scripts" / "python.exe"
PY1 = MODULE1 / ".venv" / "Scripts" / "python.exe"
MODULE0_URL = "http://127.0.0.1:8000"


def fail(message: str, code: int = 1) -> None:
    print("\n" + "=" * 72)
    print("GREENLEDGER LAUNCHER")
    print("=" * 72)
    print("ERROR:", message)
    print("\nPress Enter to close...")
    input()
    raise SystemExit(code)


def check_file(path: Path, label: str) -> None:
    if not path.exists():
        fail(f"{label} not found:\n{path}")


def wait_for_module0(timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(MODULE0_URL, timeout=2) as response:
                return 200 <= response.status < 500
        except Exception:
            time.sleep(0.5)
    return False


def main() -> None:
    print("Starting GreenLedger...")
    print(f"Project: {ROOT}")

    check_file(PY0, "Module 0 Python environment")
    check_file(PY1, "Module 1 Python environment")
    check_file(MODULE0 / "app.py", "Module 0 app")
    check_file(MODULE1 / "module1.py", "Module 1")

    env1 = os.environ.copy()
    env1["GREENLEDGER_FARM_API"] = MODULE0_URL

    print("\n[1/3] Starting Module 0 (farm registration)...")
    p0 = subprocess.Popen(
        [str(PY0), "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(MODULE0),
        env=os.environ.copy(),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    print("Waiting for Module 0...")
    if not wait_for_module0():
        p0.terminate()
        fail("Module 0 did not start on http://127.0.0.1:8000 within 30 seconds.")

    print("Module 0 is ready.")
    webbrowser.open(MODULE0_URL)

    print("\n[2/3] Starting Module 1 (automatic satellite monitoring)...")
    p1 = subprocess.Popen(
        [str(PY1), "module1.py"],
        cwd=str(MODULE1),
        env=env1,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    print("Module 1 started.")
    print("\n[3/3] GreenLedger is running.")
    print("  Farmer UI : http://127.0.0.1:8000")
    print("  Module 1  : automatic Sentinel-2 scheduler")
    print("\nTwo console windows were opened for the services.")
    print("Close those service windows to stop GreenLedger.")
    print("\nLauncher finished. You can close this window.")

    # Keep this launcher alive briefly so double-click users can read the status.
    time.sleep(5)


if __name__ == "__main__":
    if sys.platform != "win32":
        fail("This one-click launcher is intended for Windows.")
    main()
