"""同じブラウザ内に学習履歴を自動保存する。"""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

STORE_KEY = "gkentei_progress_v1"
_COMPONENT_DIR = Path(__file__).resolve().parent / "ls_component"

_ls = components.declare_component("gkentei_ls", path=str(_COMPONENT_DIR))


def load_browser_progress() -> str | None:
    raw = _ls(action="get", store_key=STORE_KEY, default=None, key="gk_ls_get")
    if raw is None:
        return None
    return str(raw)


def save_browser_progress(payload: str, stamp: str = "") -> None:
    _ls(
        action="set",
        store_key=STORE_KEY,
        value=payload,
        default="saved",
        key="gk_ls_set",
    )
