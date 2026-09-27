"""HOST-090, partie statique : revue systématique du code source.

Complète `test_secret_canary.py` (vérification à l'exécution, mot de passe
réel) par une vérification statique. Même principe que
`hygiene/LogHygieneTest` du projet SecondScreen (dépôt virtualScreen).
"""

from __future__ import annotations

import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent.parent / "secondscreen_host"

# Chaque appel à `Secret.reveal()` doit être justifié : cette liste est
# volontairement figée. Un appel ajouté ailleurs fait échouer ce test — pas
# une erreur en soi, un rappel à revoir à la main que ce nouvel usage ne
# journalise ni n'affiche le mot de passe en dehors du champ prévu, avant
# de l'ajouter ici.
EXPECTED_REVEAL_CALL_SITES = {
    # Écrit dans le fichier de mot de passe temporaire (0600, HOST-040) :
    # jamais journalisé.
    "secondscreen_host/system/x11vnc.py",
    # Remplit le champ masqué (Gtk.Entry, visibility=False, HOST-050) :
    # jamais journalisé.
    "secondscreen_host/ui/main_window.py",
}

_PRINT_CALL_RE = re.compile(r"(^|[^.\w])print\(")


def _python_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _files_calling_reveal() -> set[str]:
    found = set()
    for path in _python_files():
        if re.search(r"\.reveal\(\)", path.read_text(encoding="utf-8")):
            found.add(str(path.relative_to(PACKAGE_ROOT.parent)).replace("\\", "/"))
    return found


def test_reveal_is_only_called_from_the_reviewed_locations() -> None:
    assert _files_calling_reveal() == EXPECTED_REVEAL_CALL_SITES


def test_no_print_statements_in_the_application_source() -> None:
    # L'application n'utilise jamais print() pour son propre compte : tout
    # message passe par l'interface (labels GTK) ou une exception typée
    # (voir HOST-081). Un print() oublié pendant le développement est l'un
    # des moyens les plus simples de faire fuiter un secret par erreur dans
    # un terminal.
    offending = []
    for path in _python_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _PRINT_CALL_RE.search(line):
                offending.append(f"{path.relative_to(PACKAGE_ROOT.parent)}:{lineno}")
    assert offending == []


def test_settings_dataclass_has_no_password_like_field() -> None:
    # Revue statique de la définition elle-même (voir aussi le test
    # canari, à l'exécution, dans test_secret_canary.py) : HOST-060 impose
    # qu'aucun champ de ce type n'existe.
    from secondscreen_host.pure.settings import Settings

    field_names = {f.lower() for f in Settings.__dataclass_fields__}
    forbidden_substrings = ("password", "passwd", "secret", "motdepasse")
    for name in field_names:
        for forbidden in forbidden_substrings:
            assert forbidden not in name, f"champ suspect dans Settings : {name!r}"
