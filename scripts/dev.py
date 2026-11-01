"""
GraphMind quick-start development launcher.
Run from the project root: python scripts/dev.py
"""

import subprocess
import sys
import os
import time
from pathlib import Path


ROOT = Path(__file__).parent.parent


def start_api():
    env = os.environ.copy()
    # Put the engine and api on sys.path
    engine_path = str(ROOT / "engine")
    api_path = str(ROOT)
    env["PYTHONPATH"] = f"{engine_path}{os.pathsep}{api_path}"
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app",
         "--host", "127.0.0.1", "--port", "7430", "--reload"],
        env=env,
        cwd=str(ROOT),
    )


def start_ui():
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(ROOT / "frontend" / "graphmind-ui"),
        shell=True,
    )


def main():
    print("═══════════════════════════════════════════")
    print("  GraphMind Development Environment")
    print("═══════════════════════════════════════════")
    print("Starting API server on http://127.0.0.1:7430")
    api = start_api()
    time.sleep(2)

    print("Starting UI on http://localhost:5173")
    ui = start_ui()

    print("\nPress Ctrl+C to stop both servers.\n")
    try:
        api.wait()
        ui.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        api.terminate()
        ui.terminate()


if __name__ == "__main__":
    main()
