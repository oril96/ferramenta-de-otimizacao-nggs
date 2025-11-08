import logging
from typing import Dict, Any, List

from src.utils.admin import run_cmd


logger = logging.getLogger(__name__)


COMMANDS = [
    "ipconfig /flushdns",
    "ipconfig /release",
    "ipconfig /renew",
    "ipconfig /registerdns",
    "gpupdate /force",
]


def clear_network_cache() -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    for cmd in COMMANDS:
        code, out, err = run_cmd(cmd, shell="cmd", elevated=True, timeout=120)
        ok = code == 0
        logger.info("[%s] exit=%s", cmd, code)
        if out:
            logger.debug("stdout: %s", out.strip())
        if err:
            logger.warning("stderr: %s", err.strip())
        steps.append({
            "command": cmd,
            "code": code,
            "stdout": out,
            "stderr": err,
            "ok": ok,
        })

    success_count = sum(1 for s in steps if s["ok"])
    fail_count = sum(1 for s in steps if not s["ok"])
    result: Dict[str, Any] = {
        "ok": success_count > 0 and fail_count == 0,
        "steps": steps,
        "totals": {"success": success_count, "failed": fail_count},
    }
    if fail_count > 0 and success_count > 0:
        result["ok"] = True
        result["partial"] = True
        result["message"] = (
            "Operação de rede concluída, porém alguns comandos retornaram mensagens/limitações. "
            "Itens menos relevantes podem não ter sido aplicados."
        )
    elif success_count == 0:
        result["ok"] = False
        result["message"] = "Nenhum comando de rede foi executado com sucesso."
    else:
        result["message"] = "Cache de rede limpo com sucesso."
    return result
