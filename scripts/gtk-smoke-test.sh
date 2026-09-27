#!/usr/bin/env bash
# Vérifie qu'une fenêtre GTK 3 vide se construit et s'affiche réellement,
# dans un environnement isolé (Xvfb) qui ne touche pas l'affichage réel de
# la machine qui exécute ce script (voir AGENTS.md, règle 4).
#
# Sert de base à HOST-101/HOST-102 (test sur PC Ubuntu/MX Linux réels) :
# ce script vérifie la construction de la fenêtre de façon reproductible et
# automatisée ; le test sur matériel réel vérifie en plus ce qu'un
# environnement Xvfb ne peut pas garantir (rendu par le vrai serveur X,
# gestionnaire de fenêtres réel...).
#
# Usage : ./scripts/gtk-smoke-test.sh [image-docker]
# Par défaut : ubuntu:22.04 (version minimale visée, voir AGENTS.md).

set -euo pipefail

IMAGE="${1:-ubuntu:22.04}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Image : $IMAGE"

docker run --rm -v "$REPO_ROOT":/app -w /app "$IMAGE" bash -c '
    set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq python3 python3-gi gir1.2-gtk-3.0 xvfb >/dev/null
    echo "--- construction et affichage de la fenetre (Xvfb 1280x800) ---"
    xvfb-run -a --server-args="-screen 0 1280x800x24" \
        python3 -m secondscreen_host --self-test
    echo "OK : la fenetre s a construite et affichee sans erreur."
'
