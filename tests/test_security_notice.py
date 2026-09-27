"""Test de `secondscreen_host.pure.security_notice` (HOST-072)."""

from secondscreen_host.pure.security_notice import SECURITY_NOTICE


def test_mentions_vnc_is_unencrypted_and_lan_only() -> None:
    assert "VNC" in SECURITY_NOTICE
    assert "chiffr" in SECURITY_NOTICE.lower()
    assert "local" in SECURITY_NOTICE.lower()


def test_is_not_empty() -> None:
    assert SECURITY_NOTICE.strip()
