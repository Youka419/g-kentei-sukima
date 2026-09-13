from __future__ import annotations

import os
from pathlib import Path


def is_cloud() -> bool:
    markers = (
        os.getenv("STREAMLIT_RUNTIME"),
        os.getenv("STREAMLIT_CLOUD"),
        os.getenv("SPACE_ID"),
    )
    if any(markers):
        return True
    return Path("/mount/src").exists() or Path("/home/user/app").exists()


def disk_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False
