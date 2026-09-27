"""Démarre et arrête x11vnc (HOST-041), et suit son état.

Deux points vérifiés en conditions réelles, pas supposés :

1. Contrairement à Xorg (HOST-031), il n'y a pas de fichier de verrou à
   surveiller : la disponibilité réelle est détectée en lisant la sortie de
   x11vnc elle-même, en particulier la ligne « PORT=<num> » qu'il affiche
   une fois qu'il écoute effectivement (voir `secondscreen_host.pure.
   x11vnc_output`).

2. **x11vnc bufferise entièrement sa sortie standard tant qu'elle n'est pas
   un vrai terminal** (comportement par défaut de la libc, pas un bogue
   x11vnc) : avec un simple tube (`subprocess.PIPE`), la ligne « PORT= »
   reste coincée dans un tampon jamais vidé avant la fin du programme —
   vérifié : elle n'apparaît jamais avant plusieurs dizaines de secondes,
   voire jamais, via un tube simple, alors qu'elle apparaît immédiatement
   dès qu'un pseudo-terminal (pty) est utilisé à la place. `stdbuf -oL` a
   été essayé et n'a pas résolu le problème (x11vnc doit imposer son
   propre mode de bufferisation après le démarrage). Ce module utilise donc
   un pty pour la sortie de x11vnc.

   Conséquence à ne pas oublier : un pty a un tampon noyau borné (64 Kio
   sur Linux) qui, si personne ne le lit, finit par se remplir et bloquer
   les écritures de x11vnc — potentiellement geler le serveur VNC en usage
   prolongé. Un fil d'arrière-plan lit donc en continu tant que le serveur
   tourne (`_drain_output_forever`), pas seulement le temps de confirmer le
   démarrage ; les dernières lignes sont gardées (bornées) pour le
   diagnostic (HOST-071/HOST-081), pas juste jetées.
"""

from __future__ import annotations

import os
import pty
import select
import stat
import subprocess
import tempfile
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from secondscreen_host.pure.secret import Secret
from secondscreen_host.pure.x11vnc_command import X11VncTarget, build_x11vnc_command
from secondscreen_host.pure.x11vnc_output import is_ready_line

READY_TIMEOUT_SECONDS = 8.0
POLL_INTERVAL_SECONDS = 0.1
MAX_ERROR_OUTPUT_CHARS = 500
MAX_LOG_LINES = 200


class X11VncStartError(RuntimeError):
    """x11vnc n'a pas pu démarrer : message compréhensible, jamais une
    trace brute (AGENTS.md, règle 5). Ne contient jamais le mot de passe
    (HOST-090) : il n'est de toute façon jamais passé sur la ligne de
    commande (voir `secondscreen_host.pure.x11vnc_command`)."""


def _drain_output_forever(fd: int, log_lines: deque[str], stop_event: threading.Event) -> None:
    """Lit en continu la sortie de x11vnc jusqu'à ce que le pty se ferme ou
    que `stop_event` soit posé, pour ne jamais laisser son tampon se
    remplir (voir la docstring du module)."""
    buffer = b""
    while not stop_event.is_set():
        try:
            readable, _, _ = select.select([fd], [], [], POLL_INTERVAL_SECONDS)
        except OSError:
            return  # fd fermé par stop() pendant le select
        if fd not in readable:
            continue
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            return  # pty fermé côté esclave (processus terminé) ou côté maître
        if not chunk:
            return
        buffer += chunk
        while b"\n" in buffer:
            raw_line, buffer = buffer.split(b"\n", 1)
            log_lines.append(raw_line.decode(errors="replace"))


@dataclass
class X11VncProcess:
    """Le serveur VNC en cours d'exécution. `stop()` est idempotent
    (appelable sans risque même si le processus est déjà arrêté) et efface
    le mot de passe de la mémoire (HOST-042)."""

    process: subprocess.Popen
    port: int
    secret: Secret
    _master_fd: int
    _log_lines: deque[str]
    _stop_event: threading.Event
    _reader_thread: threading.Thread

    def is_running(self) -> bool:
        return self.process.poll() is None

    def recent_log_lines(self) -> list[str]:
        """Les dernières lignes affichées par x11vnc (diagnostic, voir
        HOST-071/HOST-081) : jamais le mot de passe, qui n'y transite
        jamais (voir HOST-090)."""
        return list(self._log_lines)

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self._stop_event.set()
        self._reader_thread.join(timeout=2)
        try:
            os.close(self._master_fd)
        except OSError:
            pass
        self.secret.clear()


def _write_password_file(password: str) -> Path:
    fd, name = tempfile.mkstemp(prefix="secondscreen-host-vnc-", suffix=".pass")
    path = Path(name)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600 avant d'écrire le contenu
        with os.fdopen(fd, "w") as handle:
            handle.write(password)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def _wait_until_ready_or_raise(
    process: subprocess.Popen, output_fd: int, log_lines: deque[str]
) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    buffer = b""

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            process.kill()
            raise X11VncStartError("x11vnc n'a pas confirmé être prêt dans le délai imparti.")

        wait_slice = min(remaining, POLL_INTERVAL_SECONDS)
        try:
            readable, _, _ = select.select([output_fd], [], [], wait_slice)
        except OSError:
            readable = []

        read_something = False
        if output_fd in readable:
            try:
                chunk = os.read(output_fd, 4096)
            except OSError:
                chunk = b""
            if chunk:
                read_something = True
                buffer += chunk
                while b"\n" in buffer:
                    raw_line, buffer = buffer.split(b"\n", 1)
                    line = raw_line.decode(errors="replace")
                    log_lines.append(line)
                    if is_ready_line(line):
                        return

        if not read_something and process.poll() is not None:
            raise X11VncStartError(
                f"x11vnc s'est arrêté immédiatement (code {process.returncode}) : "
                f"{' | '.join(log_lines)[-MAX_ERROR_OUTPUT_CHARS:]}"
            )


def start_x11vnc(*, target: X11VncTarget, password: Secret, port: int = 5900) -> X11VncProcess:
    if password.is_cleared:
        raise X11VncStartError(
            "Le mot de passe a déjà été effacé : impossible de démarrer le serveur."
        )

    password_file = _write_password_file(password.reveal())
    command = build_x11vnc_command(target=target, password_file_path=str(password_file), port=port)

    master_fd, slave_fd = pty.openpty()
    try:
        process = subprocess.Popen(list(command), stdout=slave_fd, stderr=slave_fd, close_fds=True)
    except FileNotFoundError as exc:
        os.close(master_fd)
        password_file.unlink(missing_ok=True)
        raise X11VncStartError("La commande « x11vnc » est introuvable.") from exc
    finally:
        os.close(slave_fd)  # le processus enfant garde sa propre copie de ce descripteur

    log_lines: deque[str] = deque(maxlen=MAX_LOG_LINES)

    try:
        _wait_until_ready_or_raise(process, master_fd, log_lines)
    except X11VncStartError:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        os.close(master_fd)
        password_file.unlink(missing_ok=True)  # x11vnc n'a peut-être pas eu la main
        raise

    # x11vnc a normalement déjà supprimé le fichier lui-même (préfixe
    # « rm: », comportement vérifié en conditions réelles) ; filet de
    # sécurité s'il ne l'a pas fait.
    password_file.unlink(missing_ok=True)

    stop_event = threading.Event()
    reader_thread = threading.Thread(
        target=_drain_output_forever, args=(master_fd, log_lines, stop_event), daemon=True
    )
    reader_thread.start()

    return X11VncProcess(
        process=process,
        port=port,
        secret=password,
        _master_fd=master_fd,
        _log_lines=log_lines,
        _stop_event=stop_event,
        _reader_thread=reader_thread,
    )
