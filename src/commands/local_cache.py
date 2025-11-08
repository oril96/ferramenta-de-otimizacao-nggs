import logging
import os
import shutil
from typing import Dict, Any, List

from src.utils.admin import expand_env, run_cmd


logger = logging.getLogger(__name__)


TARGETS = [
    r"%TEMP%",
    r"%LOCALAPPDATA%\Temp",
    r"%WINDIR%\Prefetch",
]

# Lista conservadora de processos que frequentemente bloqueiam arquivos temporários
# (apenas updaters e webview auxiliares; evitamos matar apps do sistema/Explorer)
PROC_LOCKERS = [
    "msedgewebview2.exe",
    "GoogleUpdate.exe",
    "GoogleCrashHandler.exe",
    "Update.exe",
    "squirrel.exe",
    "Teams.exe",
    "Discord.exe",
]


def _safe_remove(path: str) -> Dict[str, int]:
    """Remove conteúdo da pasta, classificando erros comuns (arquivos em uso/permissão) como 'locked'."""
    removed = 0
    failed = 0
    locked = 0

    def classify_exc(ex: Exception) -> None:
        nonlocal failed, locked
        try:
            winerr = getattr(ex, "winerror", None)
            if winerr in (5, 32, 33):  # Access denied / sharing violation / locking violation
                locked += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    if not os.path.isdir(path):
        return {"removed": 0, "failed": 0, "locked": 0}

    # rmtree error handler increments counters and attempts a chmod+retry once
    def on_rm_error(func, p, exc_info):
        # exc_info is (exc_type, exc, traceback)
        ex = exc_info[1]
        classify_exc(ex)
        try:
            # try make writable then retry
            os.chmod(p, 0o700)
            func(p)
        except Exception:
            pass

    try:
        with os.scandir(path) as it:
            for entry in it:
                p = entry.path
                try:
                    if entry.is_dir(follow_symlinks=False):
                        shutil.rmtree(p, ignore_errors=False, onerror=on_rm_error)
                    else:
                        try:
                            os.unlink(p)
                        except Exception as ex:
                            classify_exc(ex)
                            continue
                    removed += 1
                except Exception as ex:  # catch unexpected
                    classify_exc(ex)
        return {"removed": removed, "failed": failed, "locked": locked}
    except Exception as ex:
        classify_exc(ex)
        return {"removed": removed, "failed": failed, "locked": locked}


def clear_local_cache() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    totals = {"removed": 0, "locked": 0, "failed": 0}
    for raw in TARGETS:
        target = expand_env(raw)
        stats = _safe_remove(target)
        totals["removed"] += stats.get("removed", 0)
        totals["locked"] += stats.get("locked", 0)
        totals["failed"] += stats.get("failed", 0)
        ok_target = stats.get("failed", 0) == 0
        logger.info("Limpeza: %s -> %s", raw, target)
        logger.info("Removidos: %s, Bloqueados: %s, Falhas: %s", stats.get("removed", 0), stats.get("locked", 0), stats.get("failed", 0))
        results.append({
            "target": target,
            "raw": raw,
            "removed": stats.get("removed", 0),
            "locked": stats.get("locked", 0),
            "failed": stats.get("failed", 0),
            "ok": ok_target,
        })

    # Determine status: sucesso com observações quando há 'locked' ou algumas falhas não críticas
    result: Dict[str, Any] = {"targets": results, "totals": totals}
    if totals["failed"] == 0:
        result["ok"] = True
        if totals["locked"] > 0:
            result["partial"] = True
            result["message"] = (
                f"Limpeza concluída com observações. Removidos: {totals['removed']}, "
                f"bloqueados (em uso): {totals['locked']}."
            )
        else:
            result["message"] = f"Limpeza concluída. Removidos: {totals['removed']}."
    else:
        # Há falhas; considere êxito parcial se algo foi removido
        if totals["removed"] > 0 or totals["locked"] > 0:
            result["ok"] = True
            result["partial"] = True
            result["message"] = (
                f"Limpeza executada com êxito parcial. Removidos: {totals['removed']}, "
                f"bloqueados: {totals['locked']}, falhas: {totals['failed']}."
            )
        else:
            result["ok"] = False
            result["message"] = "Não foi possível limpar os diretórios temporários."
    return result


def _is_benign_taskkill(out: str, err: str) -> bool:
    s = (out + "\n" + err).lower()
    return (
        "nenhum processo" in s
        or "no instance(s) available" in s
        or "não foi encontrado" in s
        or "not found" in s
    )


def kill_common_lockers() -> Dict[str, Any]:
    """Tenta finalizar processos comuns que bloqueiam %TEMP% (best-effort)."""
    steps: List[Dict[str, Any]] = []
    ok_all = True
    for name in PROC_LOCKERS:
        code, out, err = run_cmd(f"taskkill /IM {name} /F /T", shell="cmd", elevated=True, timeout=30)
        ok = (code == 0) or _is_benign_taskkill(out, err)
        ok_all = ok_all and ok
        steps.append({"process": name, "code": code, "stdout": out, "stderr": err, "ok": ok})
    return {"ok": ok_all, "steps": steps}


def force_clear_local_cache() -> Dict[str, Any]:
    """Finaliza bloqueadores comuns e executa a limpeza."""
    killed = kill_common_lockers()
    cleaned = clear_local_cache()
    return {"ok": killed.get("ok", False) and cleaned.get("ok", False), "killed": killed, "cleaned": cleaned}
