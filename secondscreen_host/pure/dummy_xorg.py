"""Génère la configuration Xorg du repli « écran isolé » (HOST-030, F03).

Fonction pure : produit le texte du fichier de configuration, ne l'écrit
sur disque ni ne lance Xorg (voir `secondscreen_host.system.dummy_xorg`).

Structure reprise de celle déjà écrite et vérifiée dans GUIDE_UBUNTU.md et
GUIDE_MX_LINUX.md du projet SecondScreen (pilote `dummy`, sections
Device/Monitor/Screen, identique dans les deux guides). La `Modeline`
n'y est cependant pas recopiée en dur : elle vient du même `CvtMode` que
HOST-020 utilise pour l'écran étendu (F02), pour ne calculer le mode
qu'une seule fois. Ce n'est pas cosmétique : la version d'`xcvt` capturée
pour ce projet (voir tests/fixtures/cvt_1280x800_60.txt) ne produit pas
exactement les mêmes valeurs que l'exemple figé dans les guides
(porches différents) — recalculer à chaque fois plutôt que de figer une
valeur reste donc plus correct.
"""

from __future__ import annotations

from secondscreen_host.pure.cvt import CvtMode

# Valeurs fixes reprises telles quelles de GUIDE_UBUNTU.md/GUIDE_MX_LINUX.md
# (déjà vérifiées en conditions réelles pour ce projet) : assez larges pour
# ne jamais être la cause d'un problème sur une machine différente, pas des
# valeurs à calculer.
VIDEO_RAM_KB = 256000
HORIZ_SYNC_RANGE = "5.0 - 1000.0"
VERT_REFRESH_RANGE = "5.0 - 200.0"

_CONFIG_TEMPLATE = """\
Section "Device"
    Identifier  "DummyDevice"
    Driver      "dummy"
    VideoRam    {video_ram}
EndSection

Section "Monitor"
    Identifier  "DummyMonitor"
    HorizSync   {horiz_sync}
    VertRefresh {vert_refresh}
    Modeline "{mode_name}"  {mode_parameters}
EndSection

Section "Screen"
    Identifier  "DummyScreen"
    Device      "DummyDevice"
    Monitor     "DummyMonitor"
    DefaultDepth 24
    SubSection "Display"
        Depth   24
        Modes   "{mode_name}"
        Virtual {width} {height}
    EndSubSection
EndSection
"""


def generate_dummy_xorg_config(mode: CvtMode, *, width: int = 1280, height: int = 800) -> str:
    return _CONFIG_TEMPLATE.format(
        video_ram=VIDEO_RAM_KB,
        horiz_sync=HORIZ_SYNC_RANGE,
        vert_refresh=VERT_REFRESH_RANGE,
        mode_name=mode.name,
        mode_parameters=" ".join(mode.parameters),
        width=width,
        height=height,
    )


def describe_dummy_screen(display_number: int) -> str:
    """Message à afficher à l'utilisateur (fonction pure : le texte, pas
    l'affichage GTK) : rappelle explicitement que c'est un second bureau
    **séparé**, pas une extension du bureau existant (CAHIER_DES_CHARGES.md,
    F03) — pour ne pas laisser croire qu'on peut y glisser une fenêtre
    depuis le bureau habituel."""
    return (
        f"Écran isolé (affichage :{display_number}) : un second bureau séparé, "
        "pas une extension de votre bureau actuel. Vous ne pouvez pas y glisser "
        "une fenêtre directement ; une application doit être lancée dessus "
        f"explicitement, par exemple : DISPLAY=:{display_number} <application>."
    )
