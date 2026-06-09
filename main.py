"""Punto de entrada de Game Guard."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game_guard.tray_app import TrayApplication


def main() -> None:
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "game_guard.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    app = TrayApplication()
    app.run()


if __name__ == "__main__":
    main()
