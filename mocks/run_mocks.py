"""One-command launcher for Keepwell Part B mocks (REST :8081 + WebSocket :8082)."""
from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    rest = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mocks.rest.server:app", "--host", "0.0.0.0", "--port", "8081"],
        cwd=str(ROOT),
    )
    ws = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mocks.ws.server:app", "--host", "0.0.0.0", "--port", "8082"],
        cwd=str(ROOT),
    )
    print("Keepwell Part B Mocks running:")
    print("  REST API : http://localhost:8081/v1  (OpenAPI: http://localhost:8081/openapi.json)")
    print("  Live WS  : ws://localhost:8082/v1/live/call")

    def _stop(*_args: object) -> None:
        rest.terminate()
        ws.terminate()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        rest.wait()
        ws.wait()
    finally:
        _stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
