"""Lit les variables d'environnement pertinentes et délègue la décision à
`secondscreen_host.pure.session` (HOST-011)."""

from __future__ import annotations

import os

from secondscreen_host.pure.session import SessionInfo, detect_session_type


def get_session_info() -> SessionInfo:
    return detect_session_type(
        xdg_session_type=os.environ.get("XDG_SESSION_TYPE"),
        wayland_display=os.environ.get("WAYLAND_DISPLAY"),
        display=os.environ.get("DISPLAY"),
    )
