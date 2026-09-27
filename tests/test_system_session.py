"""Test de `secondscreen_host.system.session` (HOST-011, partie
exécutante) : vérifie seulement que les bonnes variables d'environnement
sont lues et transmises, pas la logique de décision (voir test_session.py).
"""

from secondscreen_host.pure.session import SessionType
from secondscreen_host.system.session import get_session_info


def test_get_session_info_reads_real_environment(monkeypatch) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")

    info = get_session_info()

    assert info.session_type is SessionType.X11
    assert "DISPLAY=':0'" in info.detail
