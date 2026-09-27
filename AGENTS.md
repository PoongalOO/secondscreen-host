# Instructions pour les assistants IA

## Contexte

SecondScreenHost est une application PC (Ubuntu, MX Linux) qui automatise la configuration d'un écran virtuel 1280×800 et d'un serveur VNC restreint à cette zone, pour servir de second écran à [SecondScreen](https://github.com/PoongalOO/virtualScreen) (client Android sur une Samsung Galaxy Tab 2 GT-P5110). Voir [CAHIER_DES_CHARGES.md](CAHIER_DES_CHARGES.md).

## Contraintes non négociables

- Python 3 (3.10 minimum : version par défaut d'Ubuntu 22.04 LTS, la plus ancienne visée) ;
- interface en GTK 3 via PyGObject (`gi.repository.Gtk` version « 3.0 ») ; pas GTK 4, pas Qt, pas Electron ;
- **on enveloppe `x11vnc`, on ne réimplémente pas un serveur RFB/VNC** ;
- session **Xorg** uniquement pour la V1 ; pas de support Wayland (voir CAHIER_DES_CHARGES.md, « Hors périmètre ») ;
- aucune dépendance Python au-delà de PyGObject sans justification explicite ajoutée au cahier des charges ;
- **le mot de passe VNC n'est jamais écrit sur disque** : redemandé à chaque démarrage du serveur (décision prise, voir CAHIER_DES_CHARGES.md, F04/F06/Sécurité) ;
- aucun secret dans les logs ;
- jamais de processus `x11vnc` ou `Xorg` laissé orphelin après un arrêt normal, une erreur ou un plantage de l'application ;
- fonctionnement LAN hors cloud : aucune télémétrie, aucun service distant.

## Avant de proposer du code

1. Ne jamais supposer qu'une commande système (`xrandr`, `cvt`, `x11vnc`, `Xorg`) est présente : la vérifier, et donner un message clair si elle manque plutôt que de laisser l'erreur brute remonter.
2. Traiter la sortie de ces commandes comme non fiable : le format de `xrandr --query` varie selon le pilote et la version ; ne pas écrire un analyseur qui plante sur une variation raisonnable, et couvrir plusieurs sorties réelles en test (avec/sans sortie `VIRTUAL*`, NVIDIA propriétaire).
3. Séparer nettement la **logique pure** (analyser une sortie `xrandr`, construire une commande, calculer un rectangle `--clip`) du code qui **exécute réellement** des commandes système ou touche GTK : la première doit rester testable sans lancer X, GTK, ni un vrai `x11vnc`.
4. Ne jamais exécuter une commande qui modifie l'affichage réel ou lance un serveur sans qu'un chemin de test existe pour la vérifier autrement (simulation, ou exécution isolée dans un conteneur/Xorg jetable — voir les vérifications déjà faites dans le projet SecondScreen, `GUIDE_UBUNTU.md`).
5. Vérifier qu'un code de retour non nul, ou une sortie inattendue, d'une commande externe produit un message compréhensible dans l'interface, jamais une exception non gérée visible seulement dans un terminal.

## Tests obligatoires

- toute fonction d'analyse ou de construction de commande (lecture de `xrandr --query`, calcul du `--clip`, construction de la commande `x11vnc`, génération de la configuration Xorg `dummy`) a des tests unitaires, avec des fixtures tirées de vraies sorties (pas seulement un cas inventé qui arrange le code) ;
- tout appel à une commande système a un test qui vérifie le comportement en cas d'échec (commande absente, code de retour non nul, sortie tronquée ou inattendue) ;
- un test vérifie qu'aucun processus `x11vnc`/`Xorg` ne reste actif après un arrêt normal, une erreur simulée, ou la fermeture de la fenêtre.

## Interdictions

- réimplémenter un serveur RFB/VNC ;
- GTK 4, Qt, Electron, ou toute bibliothèque d'interface graphique autre que GTK 3/PyGObject, sans décision explicite documentée ;
- stocker le mot de passe VNC sur disque, sous quelque forme que ce soit, tant que CAHIER_DES_CHARGES.md n'a pas été mis à jour pour en décider autrement ;
- support Wayland présenté comme fonctionnel en V1 ;
- lancer `x11vnc` sans mot de passe par défaut ;
- réécriture massive sans issue correspondante ;
- optimisation prématurée avant qu'une V1 fonctionnelle existe.
