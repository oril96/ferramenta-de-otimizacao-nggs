import logging
from typing import Dict, Any, List

from src.utils.admin import run_cmd


logger = logging.getLogger(__name__)


# bcdedit tweaks (some may fail on systems with Secure Boot or if not set)
CMD_COMMANDS: List[str] = [
    "bcdedit /set useplatformtick yes",
    "bcdedit /set disabledynamictick yes",
    "bcdedit /deletevalue useplatformclock",
    "bcdedit /set nx AlwaysOff",
    "bcdedit /set tscsyncpolicy Enhanced",
]

# Registry tweaks (avoid quotes around key names to reduce quoting issues)
POWERSHELL_COMMANDS: List[str] = [
    "reg add HKCU\\System\\GameConfigStore /v GameDVR_Enabled /t REG_DWORD /d 0 /f",
    "reg add HKCU\\Software\\Microsoft\\GameBar /v AllowAutoGameMode /t REG_DWORD /d 0 /f",
    "reg add HKCU\\Software\\Microsoft\\GameBar /v AutoGameModeEnabled /t REG_DWORD /d 0 /f",
]


def _is_benign_error(stderr: str) -> bool:
    s = (stderr or "").lower()
    patterns = [
        "elemento n\u00e3o encontrado",  # PT-BR
        "element not found",            # EN
        "pol\u00edtica de inicializa",   # secure boot policy (PT)
        "secure boot",                  # EN
    ]
    return any(p in s for p in patterns)


def optimize_pubg(confirm: bool = False) -> Dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "Confirmação explícita necessária para aplicar otimizações de jogos."}

    steps: List[Dict[str, Any]] = []
    overall_ok = True

    for cmd in CMD_COMMANDS:
        code, out, err = run_cmd(cmd, shell="cmd", elevated=True, timeout=120)
        ok = (code == 0) or _is_benign_error(err)
        overall_ok = overall_ok and ok
        logger.info("[%s] exit=%s", cmd, code)
        steps.append({"command": cmd, "code": code, "stdout": out, "stderr": err, "ok": ok})

    for ps in POWERSHELL_COMMANDS:
        # These are native 'reg' commands; run via cmd shell for compatibility
        code, out, err = run_cmd(ps, shell="cmd", elevated=True, timeout=120)
        ok = (code == 0) or _is_benign_error(err)
        overall_ok = overall_ok and ok
        logger.info("[%s] exit=%s", ps, code)
        steps.append({"command": ps, "code": code, "stdout": out, "stderr": err, "ok": ok})
    success_count = sum(1 for s in steps if s["ok"])
    fail_count = sum(1 for s in steps if not s["ok"])
    result: Dict[str, Any] = {"steps": steps, "totals": {"success": success_count, "failed": fail_count}}
    if success_count == 0:
        result["ok"] = False
        result["message"] = "Nenhuma otimização foi aplicada (possível política do sistema)."
    else:
        result["ok"] = True
        if fail_count > 0:
            result["partial"] = True
            result["message"] = (
                "Otimizações aplicadas com observações. Alguns ajustes foram ignorados "
                "devido ao estado atual do sistema (ex.: Secure Boot/políticas)."
            )
        else:
            result["message"] = "Otimizações de jogo aplicadas com sucesso."
    return result
