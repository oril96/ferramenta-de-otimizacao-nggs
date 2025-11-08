import ctypes
import logging
import os
import shlex
import subprocess
import tempfile
from typing import Tuple


logger = logging.getLogger(__name__)


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


def expand_env(path: str) -> str:
    return os.path.expandvars(path)


def _run_normal(command: str, shell: str = "cmd", timeout: int | None = None) -> Tuple[int, str, str]:
    if shell not in {"cmd", "powershell"}:
        raise ValueError("shell must be 'cmd' or 'powershell'")

    if shell == "cmd":
        full_cmd = ["cmd", "/c", command]
    else:
        full_cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ]

    logger.debug("Running (normal): %s", full_cmd)
    proc = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def _run_elevated(command: str, shell: str = "cmd", timeout: int | None = None) -> Tuple[int, str, str]:
    """
    Run command as administrator by creating a temporary elevated PowerShell script
    that redirects stdout/stderr to temp files. Returns (code, stdout, stderr).
    """
    # Prepare a temporary folder for I/O redirection
    tmpdir = tempfile.mkdtemp(prefix="optimus_elev_")
    stdout_path = os.path.join(tmpdir, "stdout.txt")
    stderr_path = os.path.join(tmpdir, "stderr.txt")
    script_path = os.path.join(tmpdir, "run.ps1")

    if shell == "cmd":
        # Use Start-Process with redirection to capture reliably
        # Escape double quotes inside command for PS -ArgumentList
        escaped = command.replace("\"", "`\"")
        ps = f"$p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c \"{escaped}\"' -RedirectStandardOutput '{stdout_path}' -RedirectStandardError '{stderr_path}' -PassThru -Wait; exit $p.ExitCode"
    elif shell == "powershell":
        # Run directly in PowerShell and redirect
        ps = f"powershell -NoProfile -ExecutionPolicy Bypass -Command \"{command.replace('\"', '`\"')}\" 1> '{stdout_path}' 2> '{stderr_path}'; exit $LASTEXITCODE"
    else:
        raise ValueError("shell must be 'cmd' or 'powershell'")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(ps)

    # Launch elevated PowerShell to run the script
    launch = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        f"Start-Process -Verb RunAs -FilePath 'powershell' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','{script_path}' -Wait; exit $LASTEXITCODE",
    ]

    logger.debug("Running (elevated): %s", launch)
    proc = subprocess.run(launch, capture_output=True, text=True, timeout=timeout)

    # Read redirected outputs if present
    out = ""
    err = ""
    try:
        if os.path.exists(stdout_path):
            with open(stdout_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        if os.path.exists(stderr_path):
            with open(stderr_path, "r", encoding="utf-8", errors="replace") as f:
                err = f.read()
    except Exception as read_ex:
        err = (err or "") + f"\n[read-error] {read_ex}"

    # If the launcher failed (e.g., UAC canceled), reflect that
    code = proc.returncode
    if code != 0 and not out and not err:
        err = (proc.stderr or "") + "\nFalha ao elevar o processo (UAC cancelado?)."

    return code, out, err


def run_cmd(command: str, shell: str = "cmd", elevated: bool = True, timeout: int | None = None) -> Tuple[int, str, str]:
    """Run a command optionally elevated. Returns (code, stdout, stderr)."""
    if elevated and not is_admin():
        return _run_elevated(command, shell=shell, timeout=timeout)
    return _run_normal(command, shell=shell, timeout=timeout)

