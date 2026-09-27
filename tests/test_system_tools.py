"""Tests de `secondscreen_host.system.tools` (HOST-010, partie exécutante).

Utilise de vrais outils du système (`python3`, garanti présent puisque
c'est ce qui exécute les tests) et un nom garanti absent, plutôt que de
mocker `shutil.which` : vérifie le comportement réel, pas une simulation de
ce que `shutil.which` est censé faire.
"""

from secondscreen_host.pure.tools import RequiredTool
from secondscreen_host.system.tools import check_tool


def test_check_tool_finds_a_real_executable() -> None:
    tool = RequiredTool("python3", "python3", "exécuter les tests eux-mêmes")

    result = check_tool(tool)

    assert result.is_available is True
    assert result.found_at is not None


def test_check_tool_reports_absent_executable() -> None:
    tool = RequiredTool(
        "un-nom-de-commande-qui-ne-devrait-jamais-exister-1234",
        "aucun-paquet",
        "test",
    )

    result = check_tool(tool)

    assert result.is_available is False
    assert result.found_at is None
